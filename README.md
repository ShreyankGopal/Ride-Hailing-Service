# Rider Service – Ride Matching Microservice

This repository implements the **Rider Service and related backend components** for a ride-hailing / ride-sharing platform. It focuses on **rider registration, station management, driver state management, and real-time rider–driver matching** using gRPC, Redis, and geohashing.

## Overview

- **Domain**
  - Models the core flow of a rider requesting a ride and being matched to an available driver near a station.
  - Uses Redis and PostgreSQL to simulate realistic back-end behavior.

- **Architecture**
  - Organized as several **gRPC microservices**, each with a single, focused responsibility.
  - Communication between services is defined via Protocol Buffers and implemented using generated stubs.
  - An **async FastAPI gateway** (port 5001) sits in front of all gRPC services, exposing a unified HTTP/WebSocket API to the frontend.
  - Redis is used as a **fast in-memory store** to track driver locations, statuses, and distributed locks.
  - PostgreSQL is used for persistent user storage (registration and auth).
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
| `POST` | `/initiateMatch` | ✅ rider | Request a driver match (proxied to Matching Service) |
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
  - Central service that **matches riders to available drivers**.
  - Fetches rider details from Rider Service and station coordinates from Station Service.
  - Uses geohash to find all drivers in the rider's station region from Redis.
  - Picks the **nearest available driver** using Euclidean distance.
  - **Atomically claims** the driver via a Redis distributed lock (`SET NX EX`) to prevent double-booking under concurrent requests.
  - Marks the driver as `busy` and triggers trip creation via Trip Service.
  - Stores passenger details in Redis for the driver to retrieve during the trip.

- **Trip Service** (`Services/Trip-Service`) — port `50056`
  - Generates a unique `trip_id` using a Redis atomic counter.
  - Generates a 4-digit **OTP** to link rider and driver.
  - On `UpdateTripStatus("completed")`: frees the driver (→ `available`) and deletes the trip from Redis.

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
5. Rider initiates match          → Matching Service:
       ├─ Get rider info           → Rider Service
       ├─ Get station coords       → Station Service
       ├─ Find nearest driver      → Redis geohash lookup
       ├─ Atomic claim driver      → Redis SET NX EX (distributed lock)
       ├─ Mark driver Busy         → Driver Service
       └─ Create trip + OTP        → Trip Service
6. Trip completes                 → Trip Service frees driver, deletes trip & rider from Redis
```

---

## Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.10+** | All service implementations |
| **FastAPI + Uvicorn** | Async HTTP/WebSocket API gateway |
| **gRPC** | Inter-service communication |
| **Protocol Buffers (proto3)** | Service and message contracts |
| **Redis** | Driver state, positions, distributed locks, trip/rider data |
| **PostgreSQL** | Persistent user storage |
| **JWT (PyJWT)** | Stateless authentication |
| **Geohash2** | Spatial bucketing of driver locations |
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
| API Gateway (FastAPI) | 5001 |

---

## Concurrency & Safety Notes

- **API Gateway**: FastAPI + Uvicorn handles requests concurrently via `asyncio`. Each route handler is `async def`; blocking gRPC calls are offloaded to a thread pool via `asyncio.to_thread()`.
- **gRPC servers**: Each service uses `ThreadPoolExecutor(max_workers=10)`, supporting up to 10 parallel gRPC calls.
- **Race condition fix (Matching Service)**: A **Redis distributed lock** (`SET NX EX 10`) is acquired atomically before claiming a driver, preventing two concurrent match requests from double-booking the same driver. The lock is released once the driver status is persisted as `busy`.
