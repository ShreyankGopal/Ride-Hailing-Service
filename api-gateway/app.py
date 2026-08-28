"""
api-gateway/app.py  —  FastAPI API Gateway
==========================================
All route handlers are ``async def``.  Blocking gRPC client calls are
offloaded to a thread-pool via ``asyncio.to_thread`` so the event loop
is never blocked, enabling true concurrent request handling.

Run with:
    uvicorn app:app --host 0.0.0.0 --port 5001 --reload
"""

import asyncio
import json
import os
import sys
import time
import redis
import boto3

current = os.path.dirname(os.path.realpath(__file__))
project_root = os.path.dirname(current)
if project_root not in sys.path:
    sys.path.append(project_root)

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import ClientCalls.DriverPosition as DriverPosition
import ClientCalls.DriverReg
import ClientCalls.Rider as Rider
import ClientCalls.stream_location as StreamLocation
import ClientCalls.TripStatus
import ClientCalls.UserReg
from Server_Handlers.middleware.auth_middleware import get_current_user

# ── SQS Client (LocalStack) ─────────────────────────────────────────

SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")

sqs_client = boto3.client(
    "sqs",
    endpoint_url=SQS_ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

RIDE_REQUESTS_QUEUE_URL = sqs_client.get_queue_url(QueueName="RideRequestsQueue")["QueueUrl"]

# Redis client for cancel flags
redis_gw = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True,
)

# ── App & Middleware ─────────────────────────────────────────────────

app = FastAPI(
    title="Ride Hailing API Gateway",
    description="Async FastAPI gateway that proxies all calls to gRPC microservices.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",   # Next.js dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic request body models ─────────────────────────────────────

class SignupBody(BaseModel):
    name: str
    phone: str
    role: str
    password: str

class LoginBody(BaseModel):
    phone: str
    password: str

class RegisterRiderBody(BaseModel):
    station_id: str
    destination: str

class DriverPositionBody(BaseModel):
    driver_id: str

class DriverOnlineBody(BaseModel):
    status: str

class TripStatusBody(BaseModel):
    trip_id: str
    status: str

class StartTripBody(BaseModel):
    trip_id: str
    otp: str

# ── Helper ───────────────────────────────────────────────────────────

def _set_auth_cookie(response: Response, token: str) -> None:
    """Attach the JWT as an HTTP-only cookie on the response."""
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=3600,       # 1 hour
        httponly=True,
        secure=False,       # set True in production behind HTTPS
        samesite="lax",
        path="/",
    )

# ── Auth / User Routes ───────────────────────────────────────────────

@app.post("/signup")
async def signup(body: SignupBody, response: Response):
    """Register a new user (rider or driver) and issue a JWT cookie."""
    print("[Gateway] /signup called")

    reg_result = await asyncio.to_thread(
        ClientCalls.UserReg.register,
        body.name, body.phone, body.role, body.password,
    )
    if not reg_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=reg_result.get("error", "Signup failed"),
        )

    # Auto-login after successful registration
    login_result = await asyncio.to_thread(
        ClientCalls.UserReg.Login, body.phone, body.password
    )
    if login_result.get("success"):
        token = login_result.get("token", "")
        if token:
            _set_auth_cookie(response, token)

    return {"message": "Signup successful"}


@app.post("/login")
async def login(body: LoginBody, response: Response):
    """Authenticate a user and issue a JWT cookie."""
    print("[Gateway] /login called")

    grpc_response = await asyncio.to_thread(
        ClientCalls.UserReg.Login, body.phone, body.password
    )

    if not grpc_response.get("success"):
        raise HTTPException(
            status_code=401,
            detail=grpc_response.get("error", "Invalid credentials"),
        )

    token = grpc_response.get("token")
    role = grpc_response.get("role")

    if not token or not role:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _set_auth_cookie(response, token)
    return {"message": "Login successful", "role": role}


@app.get("/me")
async def me(user: dict = Depends(get_current_user)):
    """Return the current authenticated user's basic info from the JWT."""
    return {"user_id": user.get("sub"), "role": user.get("role")}


@app.get("/me/tripStatus")
async def me_trip_status(user: dict = Depends(get_current_user)):
    """Return the authenticated user's active trip status (if any).

    Uses reverse index keys set by Trip-Service:
      rider_trip:{rider_id}  -> trip_id
      driver_trip:{driver_id} -> trip_id

    Response shape:
      { has_active_trip: false }
      { has_active_trip: true, trip_id: str, trip_status: str,
        driver_id: str|null, driver_name: str|null, driver_phone: str|null,
        rider_id: str|null, otp: str|null }
    """
    user_id = str(user.get("sub"))
    role = user.get("role")

    if role == "rider":
        trip_id = redis_gw.get(f"rider_trip:{user_id}")
    elif role == "driver":
        trip_id = redis_gw.get(f"driver_trip:{user_id}")
    else:
        return {"has_active_trip": False}

    if not trip_id:
        return {"has_active_trip": False}

    trip = redis_gw.hgetall(f"trips:{trip_id}")
    if not trip:
        # Stale reverse index — clean it up
        redis_gw.delete(f"rider_trip:{user_id}")
        redis_gw.delete(f"driver_trip:{user_id}")
        return {"has_active_trip": False}

    return {
        "has_active_trip": True,
        "trip_id": trip_id,
        "trip_status": trip.get("status"),
        "rider_id": trip.get("rider_id"),
        "driver_id": trip.get("driver_id"),
        "otp": trip.get("otp"),
    }


@app.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie so the user is logged out."""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Logged out"}

# ── Rider Routes ─────────────────────────────────────────────────────

@app.post("/registerRider")
async def register_rider(
    body: RegisterRiderBody,
    user: dict = Depends(get_current_user),
):
    """Register an authenticated rider for a station and destination.

    The rider_id is taken from the authenticated JWT subject (sub).
    Arrival time is set to the current epoch seconds.
    """
    rider_id = user.get("sub")
    role = user.get("role")

    if role != "rider" or not rider_id:
        raise HTTPException(status_code=403, detail="Only riders can register")

    arrival_time = int(time.time())

    result = await asyncio.to_thread(
        Rider.register,
        str(rider_id),
        str(body.station_id),
        arrival_time,
        str(body.destination),
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to register rider"),
        )

    return {"message": "Rider registered", "rider_id": rider_id}


@app.post("/initiateMatch")
async def initiate_match(user: dict = Depends(get_current_user)):
    """Queue a match request in SQS and return immediately.

    The MatchingService worker will pick this up, find a driver, and
    push the result to the rider via WebSocket notification.
    """
    rider_id = user.get("sub")
    role = user.get("role")

    if role != "rider" or not rider_id:
        raise HTTPException(status_code=403, detail="Only riders can initiate a match")

    # Clear any previous cancellation flag
    redis_gw.delete(f"match_cancelled:{rider_id}") # clearing a prevoius cancellation flag so that matching can happen

    await asyncio.to_thread(
        sqs_client.send_message,
        QueueUrl=RIDE_REQUESTS_QUEUE_URL,
        MessageBody=json.dumps({"rider_id": str(rider_id), "retry_count": 0}),
    )

    print(f"[Gateway] /initiateMatch queued for rider {rider_id}")
    return JSONResponse(
        content={"status": "queued", "message": "Searching for drivers..."},
        status_code=202,
    )


@app.post("/cancelMatch")
async def cancel_match(user: dict = Depends(get_current_user)):
    """Cancel an in-flight match request.

    Sets a Redis flag that the MatchingService worker checks before
    processing. The message will be skipped and deleted.
    """
    rider_id = user.get("sub")
    role = user.get("role")

    if role != "rider" or not rider_id:
        raise HTTPException(status_code=403, detail="Only riders can cancel a match")

    redis_gw.set(f"match_cancelled:{rider_id}", "1", ex=60)
    print(f"[Gateway] /cancelMatch set for rider {rider_id}")
    return {"status": "cancelled", "message": "Match search cancelled"}


@app.post("/startTrip")
async def start_trip(
    body: StartTripBody,
    user: dict = Depends(get_current_user),
):
    """Verify OTP and transition trip status from 'matched' to 'OnGoing'.

    The driver enters the OTP they received from the rider.
    The gateway checks it against the stored trip OTP in Redis.
    If correct, it calls Trip-Service to update status to 'OnGoing'.
    """
    role = user.get("role")
    driver_id = user.get("sub")

    if role != "driver" or not driver_id:
        raise HTTPException(status_code=403, detail="Only drivers can start a trip")

    trip_key = f"trips:{body.trip_id}"
    trip = redis_gw.hgetall(trip_key)

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.get("status") != "matched":
        raise HTTPException(
            status_code=400,
            detail=f"Trip is not in 'matched' state (current: {trip.get('status')})",
        )

    if trip.get("otp") != body.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # OTP verified — update trip status to OnGoing
    result = await asyncio.to_thread(
        ClientCalls.TripStatus.update_trip_status,
        body.trip_id,
        "OnGoing",
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to update trip status"),
        )

    print(f"[Gateway] /startTrip trip={body.trip_id} now OnGoing (driver={driver_id})")
    return {"success": True, "trip_id": body.trip_id, "status": "OnGoing"}


@app.post("/completeTrip")
async def complete_trip(user: dict = Depends(get_current_user)):
    """Mark the active trip as completed (driver only).

    Looks up the driver's active trip via reverse index, then
    calls Trip-Service to set status to 'completed'.
    Trip-Service handles freeing the driver and deleting the reverse index.
    """
    role = user.get("role")
    driver_id = str(user.get("sub"))

    if role != "driver" or not driver_id:
        raise HTTPException(status_code=403, detail="Only drivers can complete a trip")

    trip_id = redis_gw.get(f"driver_trip:{driver_id}")
    if not trip_id:
        raise HTTPException(status_code=404, detail="No active trip found")

    trip = redis_gw.hgetall(f"trips:{trip_id}")
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.get("status") not in ("OnGoing",):
        raise HTTPException(
            status_code=400,
            detail=f"Trip is not OnGoing (current: {trip.get('status')})",
        )

    result = await asyncio.to_thread(
        ClientCalls.TripStatus.update_trip_status,
        trip_id,
        "completed",
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to complete trip"),
        )

    print(f"[Gateway] /completeTrip trip={trip_id} completed (driver={driver_id})")
    return {"success": True, "trip_id": trip_id, "status": "completed"}


# ── Driver Routes ─────────────────────────────────────────────────────

@app.post("/driverPosition")
async def driver_position(body: DriverPositionBody):
    """Return latest known position for a given driver_id."""
    driver_id = body.driver_id.strip()
    if not driver_id:
        raise HTTPException(status_code=400, detail="driver_id is required")

    result = await asyncio.to_thread(
        DriverPosition.get_driver_position, driver_id
    )
    status_code = 200 if result.get("found") and not result.get("error") else 500
    return JSONResponse(content=result, status_code=status_code)


@app.post("/driver/online")
async def driver_online(
    body: DriverOnlineBody,
    user: dict = Depends(get_current_user),
):
    """Mark the authenticated driver as online / available."""
    role = user.get("role")
    driver_id = user.get("sub")

    if role != "driver" or not driver_id:
        raise HTTPException(status_code=403, detail="Only drivers can go online")

    if body.status != "available":
        raise HTTPException(status_code=400, detail="Invalid status")

    result = await asyncio.to_thread(
        ClientCalls.DriverReg.Update_Driver_Status,
        body.status,
        str(driver_id),
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to update driver status"),
        )

    return {
        "message": "Driver is now online",
        "driver_id": driver_id,
        "status": body.status,
    }


# ── WebSocket Route ───────────────────────────────────────────────────

@app.websocket("/ws/driver/location")
async def ws_driver_location(websocket: WebSocket):
    """WebSocket endpoint to receive driver GPS updates and forward them
    to Location-Service via gRPC streaming.

    The frontend sends JSON messages:
      { "userId": "...", "role": "driver", "lat": 12.88, "lng": 77.58 }

    The server responds with the Location-Service forwarding result:
      { "result": { "success": true, "message": "..." } }
    """
    await websocket.accept()
    print("[WS] Client connected to /ws/driver/location", flush=True)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                payload = json.loads(data)
            except Exception as e:
                print(f"[WS] Invalid JSON payload: {e}", flush=True)
                continue

            driver_id = str(payload.get("userId") or "")
            role = payload.get("role")
            lat = payload.get("lat")
            lng = payload.get("lng")

            print(
                f"[WS] driver_id={driver_id} role={role} lat={lat} lng={lng}",
                flush=True,
            )

            if role != "driver" or not driver_id or lat is None or lng is None:
                print("[WS] Skipping invalid/non-driver update", flush=True)
                continue

            try:
                lat_f = float(lat)
                lon_f = float(lng)
            except (TypeError, ValueError):
                print("[WS] Invalid coordinate types", flush=True)
                continue

            timestamp_ms = int(time.time() * 1000)

            # Offload blocking gRPC streaming call to thread pool
            result = await asyncio.to_thread(
                StreamLocation.stream_location_once,
                driver_id,
                lat_f,
                lon_f,
                timestamp_ms,
            )
            print(f"[WS] Forwarded to Location-Service: {result}", flush=True)

            try:
                await websocket.send_text(json.dumps({"result": result}))
            except Exception as e:
                print(f"[WS] Failed to send result to client: {e}", flush=True)

    except WebSocketDisconnect:
        print("[WS] Client disconnected from /ws/driver/location", flush=True)


@app.websocket("/ws/driver/notifications/{driver_id}")
async def ws_driver_notifications(websocket: WebSocket, driver_id: str):
    await websocket.accept()
    print(f"[WS] Driver {driver_id} connected to notifications", flush=True)

    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True
    )
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"driver_notifications:{driver_id}")

    try:
        while True:
            msg = await asyncio.to_thread(
                pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0
            )
            if msg and msg["type"] == "message":
                print(f"[WS] Sending notification to driver {driver_id}: {msg['data']}")
                await websocket.send_text(msg["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        print(f"[WS] Driver {driver_id} disconnected from notifications", flush=True)
        pubsub.unsubscribe()
        redis_client.close()


@app.websocket("/ws/rider/notifications/{rider_id}")
async def ws_rider_notifications(websocket: WebSocket, rider_id: str):
    """Push match results (match_found / no_driver_found) to rider via WebSocket."""
    await websocket.accept()
    print(f"[WS] Rider {rider_id} connected to notifications", flush=True)

    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )
    pubsub = r.pubsub()
    pubsub.subscribe(f"rider_notifications:{rider_id}")

    try:
        while True:
            msg = await asyncio.to_thread(
                pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0
            )
            if msg and msg["type"] == "message":
                print(f"[WS] Sending notification to rider {rider_id}: {msg['data']}")
                await websocket.send_text(msg["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        print(f"[WS] Rider {rider_id} disconnected from notifications", flush=True)
        pubsub.unsubscribe()
        r.close()


# ── Entrypoint ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5001, reload=True)
