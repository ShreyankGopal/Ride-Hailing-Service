import os
import sys
import grpc
from concurrent import futures

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.trip.trip_pb2 as trip_pb2
import Generated_Stubs.trip.trip_pb2_grpc as trip_pb2_grpc
import Generated_Stubs.rider.rider_pb2 as rider_pb2
import Generated_Stubs.rider.rider_pb2_grpc as rider_pb2_grpc
import Generated_Stubs.driver.driver_pb2 as driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc

from Services.Common.redis_client import redis_client


def genOtp():
    import random
    return str(random.randint(1000, 9999))


class TripService(trip_pb2_grpc.TripServiceServicer):

    def __init__(self):
        # Rider Service
        self.rider_channel = grpc.insecure_channel("localhost:50054")
        self.rider_stub = rider_pb2_grpc.RiderServiceStub(self.rider_channel)

        # Driver Service
        self.driver_channel = grpc.insecure_channel("localhost:50057")
        self.driver_stub = driver_pb2_grpc.DriverServiceStub(self.driver_channel)

    def StartTrip(self, request, context):
        print("StartTrip request received")
        print(request)

        # Generate trip_id using Redis atomic counter
        trip_num = redis_client.incr("counter:trip_id")
        trip_id = f"trip_{trip_num}"
        otp = genOtp()

        print("[TripService][StartTrip] creating trip with id", trip_id,
              "for rider_id=", request.rider_id, "driver_id=", request.driver_id)

        redis_client.hset(
            f"trips:{trip_id}",
            mapping={
                "rider_id": request.rider_id,
                "driver_id": request.driver_id,
                "status": "matched",
                "otp": otp
            }
        )

        print("[TripService][StartTrip] Trip created with id", trip_id,
              "otp=", otp)

        return trip_pb2.StartTripResponse(
            trip_id=trip_id,
            otp=otp
        )

    def UpdateTripStatus(self, request, context):
        print("UpdateTripStatus request received")
        print(request)

        trip_key = f"trips:{request.trip_id}"

        if not redis_client.exists(trip_key):
            print("[TripService][UpdateTripStatus] trip_id not found:",
                  request.trip_id)
            return trip_pb2.UpdateTripStatusResponse(success=False)

        trip = redis_client.hgetall(trip_key)
        previous_status = trip.get("status")

        redis_client.hset(trip_key, "status", request.status)

        print(f"[TripService][UpdateTripStatus] trip_id={request.trip_id}, "
              f"prev_status={previous_status}, new_status={request.status}")

        rider_id = trip.get("rider_id")
        driver_id = trip.get("driver_id")

        # 1️⃣ Update Rider status
        try:
            self.rider_stub.UpdateRiderStatus(
                rider_pb2.UpdateRiderStatusRequest(
                    rider_id=rider_id,
                    status=request.status
                )
            )
            print(f"Updated rider {rider_id} status to {request.status}")
        except Exception as e:
            print(f"Error updating rider status: {e}")

        # 2️⃣ If trip completed → free driver
        if request.status.lower() == "completed":
            try:
                self.driver_stub.UpdateDriverStatus(
                    driver_pb2.UpdateDriverStatusRequest(
                        driver_id=driver_id,
                        status="available"
                    )
                )
                print(f"Driver {driver_id} set to available")
            except Exception as e:
                print(f"Error updating driver status: {e}")

            # Optional cleanup: delete trip after completion
            redis_client.delete(trip_key)
            print(f"[TripService] Deleted trip {request.trip_id} from Redis")

        return trip_pb2.UpdateTripStatusResponse(success=True)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trip_pb2_grpc.add_TripServiceServicer_to_server(
        TripService(), server
    )
    server.add_insecure_port('[::]:50056')
    server.start()
    print("Trip service running on port 50056")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
