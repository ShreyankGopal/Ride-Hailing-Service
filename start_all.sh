#!/bin/bash
# =============================================================================
# start_all.sh — Launch all Rider Service components in separate Terminal windows
#
# Usage: Run this script from the project root (Rider_Service/):
#   ./start_all.sh
#
# Each service opens in its own macOS Terminal.app window with the venv
# activated automatically. Window titles are set for easy identification.
#
# Prerequisites:
#   - Python venv at .venv/
#   - Redis running on port 6379
#   - Docker running (for LocalStack)
# =============================================================================

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Rider Service — Full Stack Launcher"
echo "============================================"
echo ""
echo "Project Root: ${PROJECT_ROOT}"
echo ""

# ---------- Step 1: LocalStack (Docker Compose) ----------
echo "[1] Starting LocalStack..."
(cd "${PROJECT_ROOT}" && docker compose up -d)

# Wait for LocalStack to be healthy before creating queues
echo "[1] Waiting for LocalStack to be ready..."
MAX_RETRIES=15
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
        echo "[1] ✓ LocalStack is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "    Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "[1] ⚠ LocalStack did not start in time. SQS queue may not be created."
    echo "    Make sure Docker is running, then run manually:"
    echo "    python3 scripts/create_sqs_queues.py"
    echo ""
else
    echo "[1] Creating SQS queues..."
    (cd "${PROJECT_ROOT}" && source .venv/bin/activate && python3 scripts/create_sqs_queues.py)
fi

echo ""

# ---------- Helper: Open a new Terminal.app window ----------
launch_in_terminal() {
    local title="$1"
    local cmd="$2"

    osascript <<EOF
tell application "Terminal"
    activate
    set newTab to do script "cd \"${PROJECT_ROOT}\" && source .venv/bin/activate && echo '========== ${title} ==========' && ${cmd}"
    set custom title of front window to "${title}"
end tell
EOF
    echo "  ✓ ${title}"
}

# ---------- Step 2: gRPC Microservices ----------
echo "[2] Launching microservices..."
launch_in_terminal "User-Service"         "python3 Services/User-Service/Server.py"
launch_in_terminal "Location-Service"     "python3 Services/Location-Service/Server.py"
launch_in_terminal "Station-Service"      "python3 Services/Station-Service/Server.py"
launch_in_terminal "Rider-Service"        "python3 Services/Rider-Service/Server.py"
launch_in_terminal "Trip-Service"         "python3 Services/Trip-Service/Server.py"
launch_in_terminal "Driver-Service"       "python3 Services/Driver-Service/Server.py"
launch_in_terminal "Notification-Service" "python3 Services/NotificationService/Server.py"
echo ""

# ---------- Step 3: MatchingService (SQS Worker) ----------
echo "[3] Launching MatchingService..."
launch_in_terminal "Matching-Service" "python3 Services/MatchingService/Server.py"
echo ""

# ---------- Step 4: API Gateway ----------
echo "[4] Launching API Gateway..."
launch_in_terminal "API-Gateway" "cd api-gateway && python3 -m uvicorn app:app --host 0.0.0.0 --port 5001 --reload"
echo ""

# ---------- Step 5: Frontend ----------
echo "[5] Launching Frontend..."
osascript <<EOF
tell application "Terminal"
    activate
    set newTab to do script "cd \"${PROJECT_ROOT}/Frontend/rider-frontend\" && npm run dev"
    set custom title of front window to "Frontend"
end tell
EOF
echo "  ✓ Frontend (Next.js)"

echo ""
echo "============================================"
echo "  All services launched!"
echo "============================================"
echo ""
echo "  Frontend:     http://localhost:3000"
echo "  API Gateway:  http://localhost:5001"
echo ""
echo "  Each service is in its own Terminal.app window."
echo "  Use Cmd+\` to cycle between windows."
echo "============================================"
