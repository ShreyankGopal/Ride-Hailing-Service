import grpc
from concurrent import futures
import os, sys

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
sys.path.append(project_root)

from Services.Common.redis_client import redis_client
from Services.Common.geoHash import get_region

import Generated_Stubs.driver.driver_pb2 as driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc


class DriverService(driver_pb2_grpc.DriverServiceServicer):

    def UpdateDriverStatus(self, request, context):
        print("[DriverService][UpdateDriverStatus] request received:", request)
        redis_client.set(
            f"driver_status:{request.driver_id}",
            request.status.lower()
        )
        print(f"[DriverService][UpdateDriverStatus] driver_id={request.driver_id}, status={request.status.lower()}")
        return driver_pb2.UpdateDriverStatusResponse(success=True)

    def SendDrivers(self, request, context):
        print("[DriverService][SendDrivers] request received with",
              len(request.drivers), "drivers")
        for d in request.drivers:
            redis_client.hset(
                f"driver_info:{d.driver_id}",
                mapping={
                    "name": d.name,
                    "phone": d.phone
                }
            )
            redis_client.set(f"driver_status:{d.driver_id}", "registered")
            print(f"[DriverService][SendDrivers] stored driver_id={d.driver_id}, name={d.name}, phone={d.phone}")

        return driver_pb2.SendDriversResponse(
            message="Drivers stored in Redis",
            count=len(request.drivers)
        )

    def SetAndForwardDriverPosition(self, request, context):
        driver_id = request.driver_id
        lat = request.latitude
        lon = request.longitude

        status = redis_client.get(f"driver_status:{driver_id}")
        print(f"[DriverService][SetAndForwardDriverPosition] driver_id={driver_id}, lat={lat}, lon={lon}, status={status}")
        # If driver is busy, look up passenger details and return them
        if status == "busy":
            # MatchingService persists the region where it stored
            # this driver's passenger details under driver_busy_region:{id}.
            # Use that instead of recomputing the region from live coords,
            # because the driver may have moved across geohash cells.
            busy_region = redis_client.get(f"driver_busy_region:{driver_id}")
            if busy_region:
                passenger_field = f"{driver_id}:passenger"
                passenger_details = redis_client.hget(
                    f"drivers:{busy_region}",
                    passenger_field,
                )
            else:
                # Fallback: derive region from current lat/lon if no mapping.
                region = get_region(lat, lon)
                passenger_field = f"{driver_id}:passenger"
                passenger_details = redis_client.hget(
                    f"drivers:{region}",
                    passenger_field,
                )

            print(f"[DriverService][SetAndForwardDriverPosition] passenger_details={passenger_details}")
            message = passenger_details if passenger_details else "busy_no_passenger"
            print(
                f"[DriverService][SetAndForwardDriverPosition] driver {driver_id} busy, passenger_details={passenger_details}",
            )
            return driver_pb2.SetDriverPositionResponse(
                success=True,
                message=str(message),
            )

        # For non-available (but not busy) statuses, skip updates
        if status != "available":
            print(
                f"[DriverService][SetAndForwardDriverPosition] driver {driver_id} not available (status={status}), skipping position update",
            )
            return driver_pb2.SetDriverPositionResponse(
                success=True,
                message="not_available",
            )

        region = get_region(lat, lon)

        redis_client.hset(
            f"drivers:{region}",
            driver_id,
            f"{lat},{lon}"
        )
        print(f"[DriverService][SetAndForwardDriverPosition] stored driver {driver_id} in region {region} with position {lat},{lon}")

        return driver_pb2.SetDriverPositionResponse(success=True, message="available")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    driver_pb2_grpc.add_DriverServiceServicer_to_server(DriverService(), server)
    server.add_insecure_port("[::]:50057")
    server.start()
    print("DriverService running on port 50057")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
