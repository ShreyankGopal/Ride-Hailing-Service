import grpc
import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
matching_service_dir = os.path.dirname(current)
services_dir = os.path.dirname(matching_service_dir)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.driver.driver_pb2 as Driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc as Driver_pb2_grpc

DRIVER_SERVICE_ADDRESS = "localhost:50057"

def update_driver_status(driver_id: str, status: str):
    """Update driver status via Driver-Service."""
    channel = grpc.insecure_channel(DRIVER_SERVICE_ADDRESS)
    stub = Driver_pb2_grpc.DriverServiceStub(channel)
    try:
        request = Driver_pb2.UpdateDriverStatusRequest(driver_id=driver_id, status=status)
        response = stub.UpdateDriverStatus(request)
        return response
    except Exception as e:
        print(f"Error updating driver status: {e}")
        return None
    finally:
        channel.close()