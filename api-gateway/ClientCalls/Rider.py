import grpc,sys,os
current = os.path.dirname(os.path.realpath(__file__))
api_gateway = os.path.dirname(current)
project_root = os.path.dirname(api_gateway)
if project_root not in sys.path:
    sys.path.append(project_root)
import Generated_Stubs.rider.rider_pb2
import Generated_Stubs.rider.rider_pb2_grpc

def register(rider_id, station_id, arrival_time, destination):
    try:
        channel = grpc.insecure_channel("localhost:50054")
        stub = Generated_Stubs.rider.rider_pb2_grpc.RiderServiceStub(channel)
        request = Generated_Stubs.rider.rider_pb2.RegisterRiderRequest(rider_id=rider_id, station_id=station_id, arrival_time=arrival_time, destination=destination)
        response = stub.RegisterRider(request)
        return {
            "success": response.success
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
def update_rider_status(rider_id, status):
    try:
        channel = grpc.insecure_channel("localhost:50054")
        stub = Generated_Stubs.rider.rider_pb2_grpc.RiderServiceStub(channel)
        request = Generated_Stubs.rider.rider_pb2.UpdateRiderStatusRequest(rider_id=rider_id, status=status)
        response = stub.UpdateRiderStatus(request)
        return {
            "success": response.success
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }