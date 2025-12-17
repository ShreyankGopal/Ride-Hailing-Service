import grpc
import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
matching_service_dir = os.path.dirname(current)
services_dir = os.path.dirname(matching_service_dir)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.station.station_pb2 as Station_pb2
import Generated_Stubs.station.station_pb2_grpc as Station_pb2_grpc

STATION_SERVICE_ADDRESS = "localhost:50053"


def get_stations():
    """Fetch all stations from Station-Service."""
    channel = grpc.insecure_channel(STATION_SERVICE_ADDRESS)
    stub = Station_pb2_grpc.StationServiceStub(channel)
    try:
        request = Station_pb2.GetStationsRequest()
        response = stub.GetStations(request)
        return response
    finally:
        channel.close()
