import grpc
import time
import sys
import os
current = os.path.dirname(os.path.realpath(__file__))

project_root = os.path.dirname(current)
if project_root not in sys.path:
    sys.path.append(project_root)
import Generated_Stubs.Location.Location_pb2 as Location_pb2
import Generated_Stubs.Location.Location_pb2_grpc as Location_pb2_grpc

def generate_locations(driver_id, lat, lon):
    """
    Generator that continuously yields LocationUpdate messages
    """
    while True:
        yield Location_pb2.LocationUpdate(
            driver_id=str(driver_id),
            lat=float(lat),
            lon=float(lon),
            timestamp=int(time.time())
        )

        # simulate movement
        lat += 0.0001
        lon += 0.0001

        time.sleep(1)


def stream_location(driver_id, lat, lon):
    channel = grpc.insecure_channel("localhost:50052")
    stub = Location_pb2_grpc.LocationServiceStub(channel)

    response = stub.StreamLocation(
        generate_locations(driver_id, lat, lon)
    )

    print("Server ACK:", response.message)


if __name__ == "__main__":
    driver_id = sys.argv[1]
    lat = float(sys.argv[2])
    lon = float(sys.argv[3])

    stream_location(driver_id, lat, lon)
