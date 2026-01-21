#!/bin/bash

# 1️⃣ Update trip status: matched → picked
curl -X POST http://127.0.0.1:5000/updateTripStatus \
  -H "Content-Type: application/json" \
  -d '{
    "trip_id": "trip_1",
    "status": "picked"
  }'

echo ""
echo "Trip status updated to PICKED"
sleep 1

# 2️⃣ Update trip status: picked → completed
curl -X POST http://127.0.0.1:5000/updateTripStatus \
  -H "Content-Type: application/json" \
  -d '{
    "trip_id": "trip_1",
    "status": "completed"
  }'

echo ""
echo "Trip status updated to COMPLETED"
