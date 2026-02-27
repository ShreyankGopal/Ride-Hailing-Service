import grpc
import os, sys
from collections import deque
from concurrent import futures

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

client_dir = os.path.join(services_dir, "Location-Service", "Client")
if client_dir not in sys.path:
    sys.path.append(client_dir)

import Generated_Stubs.Location.Location_pb2_grpc as Location_pb2_grpc
import Generated_Stubs.Location.Location_pb2 as Location_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc
import Client.SendDriverPositionToDriverService as SendDriverPositionToDriverService


SMOOTHING_WINDOW = 5   # last 5 points


class LocationService(Location_pb2_grpc.LocationServiceServicer):

    def __init__(self):
        self.driver_service_channel = grpc.insecure_channel("127.0.0.1:50057")
        self.driver_service_stub = driver_pb2_grpc.DriverServiceStub(
            self.driver_service_channel
        )

        # driver_id -> deque of (lat, lon)
        self.location_buffer = {}

    def _smooth_location(self, driver_id, lat, lon):
        """Return smoothed (lat, lon) using moving average."""
        if driver_id not in self.location_buffer:
            self.location_buffer[driver_id] = deque(maxlen=SMOOTHING_WINDOW)

        buf = self.location_buffer[driver_id]
        buf.append((lat, lon))

        avg_lat = sum(p[0] for p in buf) / len(buf)
        avg_lon = sum(p[1] for p in buf) / len(buf)

        return avg_lat, avg_lon

    def StreamLocation(self, request, context):
        print("StreamLocation request received")

        last_message = ""

        for location in request:
            driver_id = location.driver_id
            raw_lat = location.lat
            raw_lon = location.lon

            # ---- GPS SMOOTHING HERE ----
            smooth_lat, smooth_lon = self._smooth_location(
                driver_id, raw_lat, raw_lon
            )

            print(
                f"Driver {driver_id} | "
                f"raw=({raw_lat:.6f},{raw_lon:.6f}) "
                f"smooth=({smooth_lat:.6f},{smooth_lon:.6f})"
            )

            # Forward smoothed position
            try:
                response = SendDriverPositionToDriverService.send_driver_position(
                    driver_id,
                    smooth_lat,
                    smooth_lon,
                    self.driver_service_stub
                )
                print(f"Forwarded to DriverService: {response}")

                if response.get("success"):
                    last_message = response.get("message", "")
                else:
                    last_message = response.get("error", "")
            except Exception as e:
                print(f"Error forwarding to DriverService: {e}")

        return Location_pb2.Ack(message=last_message)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Location_pb2_grpc.add_LocationServiceServicer_to_server(
        LocationService(), server
    )
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Location service running on port 50052")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
