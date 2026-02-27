import grpc
import sys, os

current = os.path.dirname(os.path.realpath(__file__))
LocationService = os.path.dirname(current)
Services = os.path.dirname(LocationService)
project_root = os.path.dirname(Services)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.driver.driver_pb2 as driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc

def send_driver_position(driver_id, lat, lon,stub):
    try:
        
        request = driver_pb2.SetDriverPositionRequest(
            driver_id=driver_id,
            latitude=lat,
            longitude=lon
        )
        response = stub.SetAndForwardDriverPosition(request)
        return {"success": True, "message": response.message}
    except Exception as e:
        return {"success": False, "error": str(e), "message": ""}