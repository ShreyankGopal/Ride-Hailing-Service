import grpc

import Generated_Stubs.driver.driver_pb2 as driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc


def get_driver_position(driver_id: str):
    """Fetch the latest known position for a driver from Driver-Service.

    Returns a dict like:
      {"found": bool, "latitude": float, "longitude": float}
    """
    try:
        channel = grpc.insecure_channel("localhost:50057")
        stub = driver_pb2_grpc.DriverServiceStub(channel)
        request = driver_pb2.GetDriverPositionRequest(driver_id=driver_id)
        response = stub.GetDriverPosition(request)
        return {
            "found": response.found,
            "latitude": response.latitude,
            "longitude": response.longitude,
        }
    except Exception as e:
        return {"found": False, "error": str(e)}
