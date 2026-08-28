# Rider Service – Ride Matching Microservice

This repository implements the **Rider Service and related backend components** for a ride-hailing / ride-sharing platform. It focuses on **rider registration, station management, driver state management, and real-time rider–driver matching** using gRPC, Redis, geohashing, and **Amazon SQS (via LocalStack)** for asynchronous matching with retries.

## Overview

- **Domain**
  - Models the core flow of a rider requesting a ride and being matched to an available driver near a station.
  - Uses Redis, PostgreSQL, and SQS to simulate realistic back-end behavior.

- **Architecture**
  - Organized as several **gRPC microservices**, each with a single, focused responsibility.
  - Communication between services is defined via Protocol Buffers and implemented using generated stubs.
  - An **async FastAPI gateway** (port 5001) sits in front of all gRPC services, exposing a unified HTTP/WebSocket API to the frontend.
  - Redis is used as a **fast in-memory store** to track driver locations, statuses, distributed locks, and pub/sub notifications.
  - PostgreSQL is used for persistent user storage (registration and auth).
  - **Amazon SQS (simulated via LocalStack)** is used for asynchronous ride request queuing and retry logic.
  - Geohash-based regions are used to group drivers spatially and simplify proximity search.

---

## API Gateway (`api-gateway/`)

The gateway is built with **FastAPI** + **Uvicorn** (replaced legacy Flask).

### Key design decisions

| Concern | Implementation |
|---|---|
| Concurrency | All route handlers are `async def`; blocking gRPC calls are offloaded via `asyncio.to_thread()` so the event loop is never blocked |
| Auth | JWT stored as HTTP-only cookie; validated via FastAPI `Depends(get_current_user)` on protected routes |
| Request validation | Pydantic models on all request bodies |
| CORS | `CORSMiddleware` (Next.js dev server + prod origins) |
| WebSocket | Native FastAPI `@app.websocket` for real-time driver GPS streaming |

### HTTP Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/signup` | — | Register rider or driver; auto-issues JWT cookie |
| `POST` | `/login` | — | Authenticate; sets JWT cookie |
| `GET` | `/me` | ✅ | Returns `user_id` and `role` from JWT |
| `POST` | `/logout` | — | Clears the JWT cookie |
| `POST` | `/registerRider` | ✅ rider | Register rider with station + destination |
| `POST` | `/initiateMatch` | ✅ rider | Queue a match request in SQS (async); MatchingService worker processes it |
| `POST` | `/driver/online` | ✅ driver | Set driver status to `available` |
| `POST` | `/driverPosition` | — | Get latest known position for a driver |

### WebSocket Endpoint

| Path | Description |
|---|---|
| `/ws/driver/location` | Driver sends `{userId, role, lat, lng}` JSON frames; gateway smooths and forwards to Location Service via gRPC streaming |

### Running the gateway

```bash
# From project root
source .venv/bin/activate
cd api-gateway
uvicorn app:app --host 0.0.0.0 --port 5001 --reload
```

### SQS (LocalStack) Integration

The gateway uses **boto3** to enqueue match requests to a LocalStack SQS queue:

- Queue name: `RideRequestsQueue`
- Endpoint: `http://localhost:4566` (configurable via `SQS_ENDPOINT` env var)
- On `/initiateMatch`, the gateway sends a message with `{rider_id, retry_count: 0}` to the queue and returns immediately.
- The MatchingService worker (see below) polls this queue, processes matches, and handles retries.

---

## Core Services

- **User Service** (`Services/User-Service`) — port `50051`
  - Handles `Register` and `Login` for riders and drivers.
  - Passwords are SHA-256 hashed; stored in **PostgreSQL**.
  - Returns a **JWT token** (role embedded) on successful login.
  - On driver registration, pushes driver info to Driver Service via gRPC.

- **Rider Service** (`Services/Rider-Service`) — port `50054`
  - Registers riders with their station, arrival time, destination, and initial status (`waiting`).
  - Exposes APIs to update rider status over time (e.g., waiting → matched → completed).
  - Fetches user name/phone from User Service to enrich rider info responses.

- **Station Service** (`Services/Station-Service`) — port `50053`
  - Maintains static station metadata (ID, name, latitude, longitude).
  - Serves station info to other services when determining a rider's pickup location.

- **Driver Service** (`Services/Driver-Service`) — port `50057`
  - Manages driver metadata and status (`registered`, `available`, `busy`) in Redis.
  - Stores driver GPS positions in Redis, bucketed by **geohash region** (`drivers:{region}` → `driver_id: "lat,lon"`).
  - If a driver is `busy`, returns their assigned passenger details (name, phone, station, OTP) instead of updating position.

- **Location Service** (`Services/Location-Service`) — port `50052`
  - Accepts a **client-streaming gRPC** call (`StreamLocation`) from the API gateway.
  - Applies a **5-point moving average** to smooth GPS noise before forwarding to Driver Service.

- **Matching Service** (`Services/MatchingService`) — port `50055`
  - **SQS worker** that polls `RideRequestsQueue` (LocalStack) for match requests.
  - For each message:
    - Checks if rider cancelled (Redis key `match_cancelled:{rider_id}`).
    - Tries to find a driver in the rider's region using geohash.
    - If found → starts trip, marks driver busy, stores passenger details, notifies driver and rider via NotificationService, deletes message.
    - If not found → re-queues with `retry_count+1` (max 20 retries, 10s delay each). After max retries, notifies rider `no_driver_found` and deletes message.
  - Uses a Redis distributed lock (`SET NX EX`) to atomically claim a driver and prevent double-booking.
  - Stores passenger details in Redis under `drivers:{region}` with field `{driver_id}:passenger` (format: `name+phone+station+otp`).

- **Trip Service** (`Services/Trip-Service`) — port `50056`
  - Generates a unique `trip_id` using a Redis atomic counter.
  - Generates a 4-digit **OTP** to link rider and driver.
  - On `UpdateTripStatus("completed")`: frees the driver (→ `available`) and deletes the trip from Redis.

- **Notification Service** (`Services/NotificationService`) — port `50060`
  - gRPC service that publishes notifications to Redis Pub/Sub.
  - `SendDriverNotification`: publishes to `driver_notifications:{driver_id}` with rider details, OTP, station coords, and trip_id.
  - `SendRiderNotification`: publishes to `rider_notifications:{rider_id}` with notification type (`match_found` or `no_driver_found`) and driver details when applicable.
  - Frontend subscribes to these channels to receive real-time match results.

---

## Supporting Components

- **Protocol Buffers** (`Proto/`)
  - Define the contracts for all gRPC interactions between services.
  - Files: `matching.proto`, `rider.proto`, `driver.proto`, `trip.proto`, `user.proto`, `station.proto`, `Location.proto`, `notification.proto`

- **Generated Stubs** (`Generated_Stubs/`)
  - Auto-generated Python gRPC stubs from the `.proto` definitions via `generate_stubs.sh`.
  - Consumed by both service servers and gateway client calls.

- **Common Utilities** (`Services/Common/`)
  - `redis_client.py`: Centralized Redis connection shared across all services.
  - `geoHash.py`: Wraps `geohash2` at precision 7 (~150 m × 150 m cells) to bucket driver positions.

- **Frontend** (`Frontend/rider-frontend/`)
  - **Next.js** (TypeScript) app for the rider and driver UI.

- **LocalStack** (`docker-compose.yml`)
  - Runs LocalStack with SQS service on port 4566 to simulate AWS SQS locally.
  - Queue `RideRequestsQueue` is created for asynchronous match requests.

- **Kubernetes** (`K8/`)
  - `redis.yaml`: K8s Deployment + Service manifest for Redis.

---

## Typical Flow

```
1. Rider signs up / logs in       → User Service (PostgreSQL) → JWT cookie
2. Driver signs up, goes online   → User Service + Driver Service (Redis)
3. Driver sends GPS updates       → WebSocket → Location Service (smoothing)
                                              → Driver Service (Redis geohash bucket)
4. Rider registers for a station  → Rider Service (Redis)
5. Rider initiates match          → API Gateway enqueues to SQS (RideRequestsQueue)
6. MatchingService worker (SQS)   → Polls queue, processes match:
       ├─ Get rider info           → Rider Service
       ├─ Get station coords       → Station Service
       ├─ Find nearest driver      → Redis geohash lookup
       ├─ Atomic claim driver      → Redis SET NX EX (distributed lock)
       ├─ Mark driver Busy         → Driver Service
       ├─ Create trip + OTP        → Trip Service
       ├─ Store passenger details  → Redis (drivers:{region})
       └─ Notify driver & rider    → NotificationService → Redis Pub/Sub
7. Frontend receives notification → Redis Pub/Sub subscription → displays match/driver info
8. Trip completes                 → Trip Service frees driver, deletes trip & rider from Redis
```

---

## Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.10+** | All service implementations |
| **FastAPI + Uvicorn** | Async HTTP/WebSocket API gateway |
| **gRPC** | Inter-service communication |
| **Protocol Buffers (proto3)** | Service and message contracts |
| **Redis** | Driver state, positions, distributed locks, trip/rider data, pub/sub notifications |
| **PostgreSQL** | Persistent user storage |
| **JWT (PyJWT)** | Stateless authentication |
| **Geohash2** | Spatial bucketing of driver locations |
| **boto3** | AWS SDK for SQS (LocalStack) integration |
| **LocalStack** | Local AWS cloud simulation (SQS) |
| **Next.js** | Rider/driver frontend UI |

---

## Port Map

| Service | Port |
|---|---|
| User Service | 50051 |
| Location Service | 50052 |
| Station Service | 50053 |
| Rider Service | 50054 |
| Matching Service | 50055 |
| Trip Service | 50056 |
| Driver Service | 50057 |
| Notification Service | 50060 |
| API Gateway (FastAPI) | 5001 |
| LocalStack (SQS) | 4566 |

---

## Concurrency & Safety Notes

- **API Gateway**: FastAPI + Uvicorn handles requests concurrently via `asyncio`. Each route handler is `async def`; blocking gRPC calls are offloaded to a thread pool via `asyncio.to_thread()`.
- **gRPC servers**: Each service uses `ThreadPoolExecutor(max_workers=10)`, supporting up to 10 parallel gRPC calls.
- **Race condition fix (Matching Service)**: A **Redis distributed lock** (`SET NX EX 10`) is acquired atomically before claiming a driver, preventing two concurrent match requests from double-booking the same driver. The lock is released once the driver status is persisted as `busy`.
- **Asynchronous matching with SQS**: The `/initiateMatch` endpoint enqueues a request to SQS and returns immediately. The MatchingService worker processes messages sequentially with long-polling (`WaitTimeSeconds=5`). Retries are handled by re-queuing with a delay (`RETRY_DELAY_SECONDS=10`) up to `MAX_RETRIES=20`. Cancellation is handled via a Redis flag `match_cancelled:{rider_id}`.
- **Notifications**: Redis Pub/Sub is used to push match results to driver and rider channels. Frontend clients subscribe to these channels for real-time updates.

---

## Running LocalStack

To start LocalStack (SQS) for local development:

```bash
docker-compose up -d
```

This starts LocalStack with SQS on port 4566. The queue `RideRequestsQueue` should be created manually or via the MatchingService worker on first run (the worker calls `get_queue_url` which may fail if the queue does not exist; ensure the queue is created beforehand).
