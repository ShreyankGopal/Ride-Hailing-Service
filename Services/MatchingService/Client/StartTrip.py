import grpc
import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
matching_service_dir = os.path.dirname(current)
services_dir = os.path.dirname(matching_service_dir)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.trip.trip_pb2 as Trip_pb2
import Generated_Stubs.trip.trip_pb2_grpc as Trip_pb2_grpc

TRIP_SERVICE_ADDRESS = "127.0.0.1:50056"

def start_trip(rider_id: str, driver_id: str):
    """Start a trip in Trip-Service."""
    channel = grpc.insecure_channel(TRIP_SERVICE_ADDRESS)
    stub = Trip_pb2_grpc.TripServiceStub(channel)
    try:
        request = Trip_pb2.StartTripRequest(rider_id=rider_id, driver_id=driver_id)
        response = stub.StartTrip(request)
        return response
    finally:
        channel.close()