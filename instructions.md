# Startup Instructions

To run the complete Rider Service application locally, you will need multiple terminal windows (or multiplexers like `tmux`/`screen`). Follow the commands below.

### 1. Prerequisites
Make sure your Python virtual environment is activated in your terminal before running backend services:
```bash
source .venv/bin/activate
```
Ensure that **Redis** is running locally on port `6379`.

Ensure that **Docker** is running (for LocalStack).

---

### 2. Start LocalStack (SQS)
Start LocalStack and create the SQS queue:
```bash
docker compose up -d
python3 scripts/create_sqs_queues.py
```

---

### 3. Microservices (gRPC Backend)
Open a new terminal tab for **each** of the following commands. Run them from the **project root directory** (`Rider_Service/`):

```bash
python3 Services/User-Service/Server.py
python3 Services/Location-Service/Server.py
python3 Services/Station-Service/Server.py
python3 Services/Rider-Service/Server.py
python3 Services/Trip-Service/Server.py
python3 Services/Driver-Service/Server.py
python3 Services/NotificationService/Server.py
```

### 4. MatchingService (SQS Worker)
The MatchingService is now a background worker that polls SQS. Start it in its own terminal:
```bash
python3 Services/MatchingService/Server.py
```

---

### 5. API Gateway (FastAPI)
The API Gateway needs to be started from within its own directory and expects the file to be `app.py` (not `main.py`).

Open a new terminal tab, navigate to the `api-gateway` folder, and run:
```bash
cd api-gateway
python3 -m uvicorn app:app --host 0.0.0.0 --port 5001 --reload
```
*(Note: It must run on port `5001` as the frontend expects it there).*

> **Important**: The API Gateway now connects to LocalStack SQS on startup. Make sure LocalStack is running and the queue is created (Step 2) before starting the gateway.

---

### 6. Frontend (Next.js)
Open a new terminal tab, navigate to the frontend directory, and start the development server:

```bash
cd Frontend/rider-frontend
npm run dev
```

The frontend will be available at [http://localhost:3000](http://localhost:3000).
