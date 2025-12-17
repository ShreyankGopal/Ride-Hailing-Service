#!/bin/bash

echo "🚗 Starting driver location streams..."

# On Ctrl+C or script exit, kill all child processes of this script
trap "echo 'Stopping streams...'; kill 0" SIGINT SIGTERM EXIT

python3 stream_location.py 1 12.9716 77.5946 &
python3 stream_location.py 2 12.9352 77.6245 &

wait