"""
MatchingService — SQS Worker
=============================
Polls the RideRequestsQueue (LocalStack SQS) for match requests.
For each message:
  1. Check if rider cancelled (Redis key match_cancelled:{rider_id}).
  2. Try to find a driver in the rider's region.
  3. If found → start trip, notify driver + rider, delete message.
  4. If not found → re-queue with retry_count+1 (max 3, delay 5s each).
     After max retries → notify rider "no_driver_found", delete message.
"""

import boto3
import json
import os
import sys
import time

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from Services.Common.redis_client import redis_client
from Services.Common.geoHash import get_region
from Services.MatchingService.Client import (
    RiderClient,
    StationClient,
    DriverStatusUpdate,
    StartTrip,
    NotificationClient,
)

# ── SQS Config (LocalStack) ─────────────────────────────────────────
SQS_ENDPOINT = os.getenv("SQS_ENDPOINT", "http://localhost:4566")
SQS_REGION = os.getenv("SQS_REGION", "us-east-1")
QUEUE_NAME = "RideRequestsQueue"
MAX_RETRIES = 20
RETRY_DELAY_SECONDS = 10

sqs = boto3.client(
    "sqs",
    endpoint_url=SQS_ENDPOINT,
    region_name=SQS_REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

# Resolve the queue URL once at startup
QUEUE_URL = sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]


def try_match(rider_id: str):
    """Core matching logic. Returns a dict with match result details."""
    rider_info = RiderClient.get_rider_info(rider_id)
    print(f"[MatchingWorker] rider_info= {rider_info}")
    if not rider_info.station_id:
        print("[MatchingWorker] No station_id for rider, skipping")
        return {"found": False, "reason": "no_station"}

    stations = StationClient.get_stations().stations
    rider_station = next(
        (s for s in stations if s.station_id == rider_info.station_id),
        None,
    )
    if not rider_station:
        print("[MatchingWorker] Station not found, skipping")
        return {"found": False, "reason": "station_not_found"}

    station_lat = rider_station.lat
    station_lon = rider_station.lon
    region = get_region(station_lat, station_lon)
    print(f"[MatchingWorker] region={region}")

    drivers = redis_client.hgetall(f"drivers:{region}")
    print(f"[MatchingWorker] drivers_count={len(drivers) if drivers else 0}")

    if not drivers:
        return {"found": False, "reason": "no_drivers_in_region"}

    # Find nearest available driver
    nearest_driver = None
    nearest_lat = None
    nearest_lon = None
    best_dist = float("inf")

    for driver_id_raw, pos in drivers.items():
        driver_id_str = driver_id_raw if isinstance(driver_id_raw, str) else driver_id_raw.decode()
        if ":" in driver_id_str:
            continue

        if redis_client.get(f"driver_status:{driver_id_raw}") != "available":
            print(f"[MatchingWorker] driver {driver_id_raw} not available, skipping")
            continue

        lat_d, lon_d = map(float, pos.split(","))
        d = (lat_d - station_lat) ** 2 + (lon_d - station_lon) ** 2

        if d < best_dist:
            best_dist = d
            nearest_driver = driver_id_raw
            nearest_lat = lat_d
            nearest_lon = lon_d

    if not nearest_driver:
        return {"found": False, "reason": "no_available_driver"}

    # ── Atomic lock ──────────────────────────────────────────────────
    lock_key = f"driver_lock:{nearest_driver}"
    lock_acquired = redis_client.set(lock_key, "1", nx=True, ex=10)
    if not lock_acquired:
        print(f"[MatchingWorker] driver {nearest_driver} already claimed")
        return {"found": False, "reason": "driver_locked"}

    if redis_client.get(f"driver_status:{nearest_driver}") != "available":
        redis_client.delete(lock_key)
        return {"found": False, "reason": "driver_status_changed"}

    # ── Fetch driver profile ─────────────────────────────────────────
    driver_info = redis_client.hgetall(f"driver_info:{nearest_driver}") or {}
    driver_name = driver_info.get("name", "")
    driver_phone = driver_info.get("phone", "")

    print(f"[MatchingWorker] matched driver={nearest_driver}, name={driver_name}")

    # ── Mark driver as Busy ──────────────────────────────────────────
    DriverStatusUpdate.update_driver_status(nearest_driver, "Busy")
    redis_client.delete(lock_key)

    # ── Start trip ───────────────────────────────────────────────────
    trip = StartTrip.start_trip(rider_id, nearest_driver)
    print(f"[MatchingWorker] trip started: otp={trip.otp}")

    # ── Store passenger details ──────────────────────────────────────
    passenger_field = f"{nearest_driver}:passenger"
    passenger_details = "+".join([
        rider_info.name or "",
        rider_info.phone or "",
        rider_info.station_id or "",
        str(trip.otp or ""),
    ])

    driver_region = (
        get_region(nearest_lat, nearest_lon)
        if nearest_lat is not None and nearest_lon is not None
        else region
    )

        # Persist the region for this busy driver so Driver-Service does not
        # have to infer it from the live coordinates (which may move across
        # geohash cells). This lets Driver-Service always look up passenger
        # details from the correct drivers:{region} hash.
    redis_client.set(f"driver_busy_region:{nearest_driver}", driver_region)
    redis_client.hset(f"drivers:{driver_region}", passenger_field, passenger_details)
    print(
            f"[MatchingService][RequestMatch] stored passenger details for driver {nearest_driver} "
            f"in region {driver_region}: {passenger_details}"
        )

    # ── Notify both driver AND rider ─────────────────────────────────
    NotificationClient.notify_driver(
        driver_id=nearest_driver,
        rider_name=rider_info.name or "",
        rider_phone=rider_info.phone or "",
        otp=str(trip.otp or ""),
        station_lat=station_lat,
        station_lon=station_lon,
        trip_id=str(trip.trip_id or ""),
    )

    NotificationClient.notify_rider(
        rider_id=rider_id,
        notification_type="match_found",
        driver_id=nearest_driver,
        driver_name=driver_name,
        driver_phone=driver_phone,
        otp=str(trip.otp or ""),
        trip_id=str(trip.trip_id or ""),
    )

    return {
        "found": True,
        "driver_id": nearest_driver,
        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "otp": str(trip.otp or ""),
    }


def poll_loop():
    """Main worker loop. Long-polls SQS and processes match requests."""
    print(f"[MatchingWorker] Polling {QUEUE_URL} ...")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5,  # long polling
            )
        except Exception as e:
            print(f"[MatchingWorker] SQS receive error: {e}")
            time.sleep(2)
            continue

        messages = response.get("Messages", [])
        if not messages:
            continue

        for msg in messages:
            receipt_handle = msg["ReceiptHandle"]
            try:
                body = json.loads(msg["Body"])
            except Exception:
                print(f"[MatchingWorker] Invalid message body, deleting")
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
                continue

            rider_id = body.get("rider_id")
            retry_count = body.get("retry_count", 0)

            print(f"[MatchingWorker] Processing rider={rider_id}, retry={retry_count}")

            # ── Check cancellation ───────────────────────────────────
            if redis_client.get(f"match_cancelled:{rider_id}"):
                print(f"[MatchingWorker] rider {rider_id} cancelled, skipping")
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
                redis_client.delete(f"match_cancelled:{rider_id}")
                continue

            # ── Try to match ─────────────────────────────────────────
            result = try_match(rider_id)

            if result["found"]:
                print(f"[MatchingWorker] Match found for rider {rider_id}!")
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
            else:
                # No match — retry or give up
                if retry_count < MAX_RETRIES - 1:
                    new_retry = retry_count + 1
                    print(
                        f"[MatchingWorker] No match for rider {rider_id}, "
                        f"re-queuing (retry {new_retry}/{MAX_RETRIES})"
                    )
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
                    sqs.send_message(
                        QueueUrl=QUEUE_URL,
                        MessageBody=json.dumps({
                            "rider_id": rider_id,
                            "retry_count": new_retry,
                        }),
                        DelaySeconds=RETRY_DELAY_SECONDS,
                    )
                else:
                    print(f"[MatchingWorker] Max retries for rider {rider_id}, notifying failure")
                    NotificationClient.notify_rider(
                        rider_id=rider_id,
                        notification_type="no_driver_found",
                    )
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)


if __name__ == "__main__":
    print("MatchingService SQS Worker starting...")
    poll_loop()
