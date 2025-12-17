# Rider Service – Ride Matching Microservice

This repository implements the **Rider Service and related backend components** for a ride-hailing / ride-sharing platform. It focuses on **rider registration, station management, driver state management, and real-time rider–driver matching** using gRPC, Redis, and geohashing.

## Overview

- **Domain**
  - Models the core flow of a rider requesting a ride and being matched to an available driver near a station.
  - Uses in-memory data structures and Redis to simulate realistic back-end behavior without external dependencies beyond infrastructure services.

- **Architecture**
  - Organized as several **gRPC microservices**, each with a single, focused responsibility.
  - Communication between services is defined via Protocol Buffers and implemented using generated stubs.
  - Redis is used as a **fast in-memory store** to track driver locations and statuses.
  - Geohash-based regions are used to group drivers spatially and simplify proximity search.

## Core Services

- **Rider Service** (`Services/Rider-Service`)
  - Registers riders with their station, arrival time, destination, and initial status.
  - Exposes APIs to update rider status over time (e.g., waiting, matched, picked, completed).
  - Provides rider information to other services (particularly the Matching Service).

- **Station Service** (`Services/Station-Service`)
  - Maintains a set of stations with basic metadata (ID, name, latitude, longitude).
  - Serves station information to other services, especially when determining where a rider is waiting.

- **Driver Service** (`Services/Driver-Service`)
  - Manages driver metadata and status (e.g., available, busy) in Redis.
  - Receives and stores driver positions, mapping them to geohash-based regions.
  - Acts as a bridge between drivers’ dynamic state and the Matching Service.

- **Matching Service** (`Services/MatchingService`)
  - Central service that **matches riders to available drivers**.
  - Fetches rider details from Rider Service and station details from Station Service.
  - Uses geohash utilities to identify the relevant region for a rider’s station.
  - Queries Redis for drivers in that region and selects the nearest available driver.
  - Updates the chosen driver’s status to busy and triggers trip creation.

- **Trip Service** (`Services/Trip-Service`)
  - Handles **trip lifecycle creation** once a rider and driver have been matched.
  - Exposes gRPC methods for starting a trip and returning details such as OTP.

## Supporting Components

- **Protocol Buffers** (`Proto/`)
  - Define the contracts for all gRPC interactions between services.
  - Example: `matching.proto` describes `DriverPosition`, `MatchRequest`, `MatchResponse`, and the `MatchingService` RPCs.

- **Generated Stubs** (`Generated_Stubs/`)
  - Auto-generated gRPC Python stubs from the `.proto` definitions.
  - Consumed by the various service servers and clients.

- **Common Utilities** (`Services/Common`)
  - `redis_client.py`: Centralized Redis client configuration for services that need fast key-value access.
  - `geoHash.py`: Minimal geohash helper for converting `(lat, lon)` into a region identifier used during matching.

## Typical Flow (Conceptual)

1. A rider registers through the **Rider Service**, specifying station, arrival time, and destination.
2. Stations and their coordinates are provided by the **Station Service**.
3. Drivers periodically send their positions and status via the **Driver Service**, which stores them in Redis and associates them with geohash regions.
4. When a rider requests a match, the **Matching Service**:
   - Retrieves rider info and station details.
   - Calculates the rider’s region using geohash.
   - Looks up available drivers in that region from Redis.
   - Selects the nearest available driver and marks them busy.
   - Starts a trip via the **Trip Service**, which returns trip details (e.g., OTP).
5. Rider and driver statuses are updated through their respective services as the trip progresses.

## Technologies Used

- **Python** for all service implementations.
- **gRPC** for inter-service communication.
- **Protocol Buffers (proto3)** for message and service definitions.
- **Redis** for fast, in-memory storage of driver information and statuses.
- **Geohash utilities** for spatial bucketing of driver locations.

## Scope

This project is intended as a **backend-focused, service-oriented design exercise** for a ride-hailing style platform. It demonstrates:

- Decomposing a problem into small, focused microservices.
- Modeling rider, driver, station, and trip entities.
- Implementing a basic, region-based ride matching algorithm.
- Using Redis and geohashing to approximate proximity-based lookup.

Operational details (how to run, configure, or deploy these services) are intentionally omitted here and can be added later as needed.
