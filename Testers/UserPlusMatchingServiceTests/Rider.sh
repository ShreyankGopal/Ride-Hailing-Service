#!/usr/bin/env bash

GATEWAY_URL="http://127.0.0.1:5000"

echo "=== Registering rider 2 via /rider/register ==="

curl -s -X POST "${GATEWAY_URL}/rider/register" \
  -H "Content-Type: application/json" \
  -d '{
    "rider_id": "2",
    "station_id": "1",
    "arrival_time": 1734259200,
    "destination": "Destination for rider 2"
  }'
echo

echo "=== Registering rider 3 via /rider/register ==="

curl -s -X POST "${GATEWAY_URL}/rider/register" \
  -H "Content-Type: application/json" \
  -d '{
    "rider_id": "3",
    "station_id": "2",
    "arrival_time": 1734259300,
    "destination": "Destination for rider 3"
  }'
echo

echo "=== Done (rider registrations) ==="