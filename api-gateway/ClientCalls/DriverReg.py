import grpc,sys,os
current = os.path.dirname(os.path.realpath(__file__))
api_gateway = os.path.dirname(current)
project_root = os.path.dirname(api_gateway)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.driver.driver_pb2_grpc
import Generated_Stubs.driver.driver_pb2
def Update_Driver_Status(status:str,driver_id:str):
    try:
        channel = grpc.insecure_channel("localhost:50057")
        stub = Generated_Stubs.driver.driver_pb2_grpc.DriverServiceStub(channel)
        request = Generated_Stubs.driver.driver_pb2.UpdateDriverStatusRequest(status=status, driver_id=driver_id)
        response = stub.UpdateDriverStatus(request)
        print(response)
        return {
            "success": response.success
        }
    except Exception as e:
        print(e)
        return {
            "success": False,
            "error": str(e)
        }