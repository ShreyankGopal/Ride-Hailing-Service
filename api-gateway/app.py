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
import ClientCalls.Matching
import ClientCalls.Rider as Rider
import ClientCalls.stream_location as StreamLocation
import ClientCalls.TripStatus
import ClientCalls.UserReg
from Server_Handlers.middleware.auth_middleware import get_current_user

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
    """Initiate a driver–rider match for the authenticated rider.

    The gRPC call to MatchingService is offloaded to a thread so multiple
    concurrent match requests are processed in parallel without blocking
    the event loop.
    """
    rider_id = user.get("sub")
    role = user.get("role")

    if role != "rider" or not rider_id:
        raise HTTPException(status_code=403, detail="Only riders can initiate a match")

    result = await asyncio.to_thread(
        ClientCalls.Matching.request_match, str(rider_id)
    )

    print(f"[Gateway] /initiateMatch result: {result}")
    status_code = 500 if not result.get("found") and "error" in result else 200
    return JSONResponse(content=result, status_code=status_code)


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


# ── Entrypoint ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5001, reload=True)
