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
        print("RequestMatch for rider:", rider_id)

        rider_info = RiderClient.get_rider_info(rider_id)
        print(rider_info)
        if not rider_info.station_id:
            print("failing at rider info client")
            return Matching_pb2.MatchResponse(found=False)

        stations = StationClient.get_stations().stations
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
        print(region)
        if not drivers:
            print(f'no drivers foind in the region {region}')
            return Matching_pb2.MatchResponse(found=False)

        nearest_driver = None
        best_dist = float("inf")

        for driver_id, pos in drivers.items():
            if redis_client.get(f"driver_status:{driver_id}") != "available":
                continue

            lat_d, lon_d = map(float, pos.split(","))
            d = (lat_d - station_lat) ** 2 + (lon_d - station_lon) ** 2

            if d < best_dist:
                best_dist = d
                nearest_driver = driver_id

        if not nearest_driver:
            print("no driver available here\n")
            return Matching_pb2.MatchResponse(found=False)

        DriverStatusUpdate.update_driver_status(nearest_driver, "Busy")
        trip = StartTrip.start_trip(rider_id, nearest_driver)

        return Matching_pb2.MatchResponse(
            found=True,
            driver_id=nearest_driver,
            rider_id=rider_id,
            otp=trip.otp
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
