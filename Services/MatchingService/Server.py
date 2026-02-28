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
        nearest_lat = None
        nearest_lon = None
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
                nearest_lat = lat_d
                nearest_lon = lon_d

        if not nearest_driver:
            print("no driver available here\n")
            return Matching_pb2.MatchResponse(found=False)

        # ------------------------------------------------------------------
        # Fetch driver profile information for the matched driver.
        # DriverService populated driver_info:{driver_id} with name/phone
        # when drivers were first registered.
        # ------------------------------------------------------------------
        driver_info_key = f"driver_info:{nearest_driver}"
        driver_info = redis_client.hgetall(driver_info_key) or {}
        driver_name = driver_info.get("name", "")
        driver_phone = driver_info.get("phone", "")

        print(
            f"[MatchingService][RequestMatch] nearest_driver={nearest_driver}, best_dist={best_dist}, "
            f"name={driver_name}, phone={driver_phone}"
        )

        # ------------------------------------------------------------------
        # Mark driver as Busy in Driver-Service so they stop receiving
        # new matches while this trip is active.
        # ------------------------------------------------------------------
        DriverStatusUpdate.update_driver_status(nearest_driver, "Busy")
        print(f"[MatchingService][RequestMatch] updated driver {nearest_driver} status to Busy")

        # ------------------------------------------------------------------
        # Start the trip and obtain the OTP that links rider and driver.
        # ------------------------------------------------------------------
        trip = StartTrip.start_trip(rider_id, nearest_driver)
        print(
            f"[MatchingService][RequestMatch] trip started: rider_id={rider_id}, "
            f"driver_id={nearest_driver}, otp={trip.otp}"
        )

        # ------------------------------------------------------------------
        # Store passenger details for this busy driver so Driver-Service
        # can later read them when handling location updates.
        #
        # IMPORTANT: Driver-Service computes the region as
        #   get_region(driver_lat, driver_lon)
        # when handling SetAndForwardDriverPosition. To ensure it reads the
        # same hash we write to here, compute the region from the matched
        # driver's actual coordinates (nearest_lat/nearest_lon), not from the
        # rider's station location.
        #
        # Driver-Service expects passenger details to be stored under
        # the Redis hash key drivers:{region} with field
        #   "{driver_id}:passenger"
        # and value:
        #   name + "+" + phone + "+" + station_id + "+" + otp
        # ------------------------------------------------------------------
        passenger_field = f"{nearest_driver}:passenger"
        passenger_details = "+".join(
            [
                rider_info.name or "",          # rider name from Rider-Service
                rider_info.phone or "",         # rider phone from Rider-Service
                rider_info.station_id or "",    # station identifier
                str(trip.otp or ""),            # trip OTP
            ]
        )

        # Fallback: if for some reason we didn't capture driver coordinates,
        # fall back to the station-based region used above.
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

        redis_client.hset(
            f"drivers:{driver_region}",
            passenger_field,
            passenger_details,
        )
        print(
            f"[MatchingService][RequestMatch] stored passenger details for driver {nearest_driver} "
            f"in region {driver_region}: {passenger_details}"
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
