import grpc,sys,os
current = os.path.dirname(os.path.realpath(__file__))
api_gateway = os.path.dirname(current)
project_root = os.path.dirname(api_gateway)
if project_root not in sys.path:
    sys.path.append(project_root)
import Generated_Stubs.trip.trip_pb2 as trip_pb2
import Generated_Stubs.trip.trip_pb2_grpc as trip_pb2_grpc
def update_trip_status(trip_id, status):
    try:
        channel = grpc.insecure_channel("127.0.0.1:50056")
        stub = trip_pb2_grpc.TripServiceStub(channel)
        request = trip_pb2.UpdateTripStatusRequest(trip_id=trip_id, status=status)
        response = stub.UpdateTripStatus(request)
        return {
            "success": response.success
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }