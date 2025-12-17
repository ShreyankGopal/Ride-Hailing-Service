import grpc
import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
matching_service_dir = os.path.dirname(current)
services_dir = os.path.dirname(matching_service_dir)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.rider.rider_pb2 as Rider_pb2
import Generated_Stubs.rider.rider_pb2_grpc as Rider_pb2_grpc

RIDER_SERVICE_ADDRESS = "localhost:50054"


def get_rider_info(rider_id: str):
    """Fetch rider info (station_id, arrival_time, destination, status) from Rider-Service."""
    channel = grpc.insecure_channel(RIDER_SERVICE_ADDRESS)
    stub = Rider_pb2_grpc.RiderServiceStub(channel)
    try:
        request = Rider_pb2.GetRiderInfoRequest(rider_id=rider_id)
        response = stub.GetRiderInfo(request)
        return response
    finally:
        channel.close()


def update_rider_status(rider_id: str, status: str):
    """Update rider status in Rider-Service. Returns True/False for success."""
    channel = grpc.insecure_channel(RIDER_SERVICE_ADDRESS)
    stub = Rider_pb2_grpc.RiderServiceStub(channel)
    try:
        request = Rider_pb2.UpdateRiderStatusRequest(rider_id=rider_id, status=status)
        stub.UpdateRiderStatus(request)
        return True
    except Exception:
        return False
    finally:
        channel.close()
