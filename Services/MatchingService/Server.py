import grpc
import os, sys
from concurrent import futures

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
sys.path.append(project_root)

from Services.Common.redis_client import redis_client
from Services.Common.geoHash import get_region

import Generated_Stubs.matching.matching_pb2 as Matching_pb2
import Generated_Stubs.matching.matching_pb2_grpc as Matching_pb2_grpc
from Services.MatchingService.Client import (
    RiderClient,
    StationClient,
    DriverStatusUpdate,
    StartTrip
)


class MatchingService(Matching_pb2_grpc.MatchingServiceServicer):

    def RequestMatch(self, request, context):
        rider_id = request.rider_id
        print("[MatchingService][RequestMatch] RequestMatch for rider:", rider_id)
        
        rider_info = RiderClient.get_rider_info(rider_id)
        print("[MatchingService][RequestMatch] rider_info=", rider_info)
        if not rider_info.station_id:
            print("failing at rider info client")
            return Matching_pb2.MatchResponse(found=False)

        stations = StationClient.get_stations().stations
        print("[MatchingService][RequestMatch] total_stations=", len(stations))
        rider_station = next(
            (s for s in stations if s.station_id == rider_info.station_id),
            None
        )

        if not rider_station:
            print("failing here\n")
            return Matching_pb2.MatchResponse(found=False)

        station_lat = rider_station.lat
        station_lon = rider_station.lon

        region = get_region(station_lat, station_lon)
        drivers = redis_client.hgetall(f"drivers:{region}")
        print("[MatchingService][RequestMatch] region=", region,
              "drivers_count=", len(drivers) if drivers else 0)
        if not drivers:
            print(f'no drivers foind in the region {region}')
            return Matching_pb2.MatchResponse(found=False)

        nearest_driver = None
        best_dist = float("inf")

        for driver_id, pos in drivers.items():
            if redis_client.get(f"driver_status:{driver_id}") != "available":
                print(f"[MatchingService][RequestMatch] driver {driver_id} not available, skipping")
                continue

            lat_d, lon_d = map(float, pos.split(","))
            d = (lat_d - station_lat) ** 2 + (lon_d - station_lon) ** 2

            if d < best_dist:
                best_dist = d
                nearest_driver = driver_id

        if not nearest_driver:
            print("no driver available here\n")
            return Matching_pb2.MatchResponse(found=False)
        
        # Fetch driver name and phone from Redis driver_info:{driver_id}
        driver_info_key = f"driver_info:{nearest_driver}"
        driver_info = redis_client.hgetall(driver_info_key) or {}
        driver_name = driver_info.get("name", "")
        driver_phone = driver_info.get("phone", "")

        print(
            f"[MatchingService][RequestMatch] nearest_driver={nearest_driver}, best_dist={best_dist}, "
            f"name={driver_name}, phone={driver_phone}"
        )

        DriverStatusUpdate.update_driver_status(nearest_driver, "Busy")
        print(f"[MatchingService][RequestMatch] updated driver {nearest_driver} status to Busy")
        trip = StartTrip.start_trip(rider_id, nearest_driver)
        print(
            f"[MatchingService][RequestMatch] trip started: rider_id={rider_id}, "
            f"driver_id={nearest_driver}, otp={trip.otp}"
        )

        return Matching_pb2.MatchResponse(
            found=True,
            driver_id=nearest_driver,
            rider_id=rider_id,
            otp=trip.otp,
            driver_name=driver_name,
            driver_phone=driver_phone,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Matching_pb2_grpc.add_MatchingServiceServicer_to_server(MatchingService(), server)
    server.add_insecure_port("[::]:50055")
    server.start()
    print("MatchingService running on port 50055")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
