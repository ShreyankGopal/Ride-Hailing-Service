#!/usr/bin/env bash

GATEWAY_URL="http://127.0.0.1:5000"

echo "=== Requesting match for rider 2 via /matching/request ==="

curl -s -X POST "${GATEWAY_URL}/matching/request" \
  -H "Content-Type: application/json" \
  -d '{
    "rider_id": "3"
  }'

echo
echo "=== Done (matching request for rider 2) ==="