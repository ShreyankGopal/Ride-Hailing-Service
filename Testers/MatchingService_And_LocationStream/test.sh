
GATEWAY_URL="http://127.0.0.1:5000"

# 1) Register a rider
echo "Registering rider..."
curl -s -X POST "${GATEWAY_URL}/rider/register" \
  -H "Content-Type: application/json" \
  -d '{
    "rider_id": "rider_1",
    "station_id": "1",
    "arrival_time": 1734259200,
    "destination": "Some Destination"
  }'
echo
echo "Rider registered."

# 2) Request a match for this rider
echo "Requesting match..."
curl -s -X POST "${GATEWAY_URL}/matching/request" \
  -H "Content-Type: application/json" \
  -d '{
    "rider_id": "rider_1"
  }'
echo
echo "Done."