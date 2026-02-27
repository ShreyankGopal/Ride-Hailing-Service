
import grpc,sys,os
current = os.path.dirname(os.path.realpath(__file__))
api_gateway = os.path.dirname(current)
project_root = os.path.dirname(api_gateway)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.matching.matching_pb2
import Generated_Stubs.matching.matching_pb2_grpc

def request_match(rider_id):
    try:
        channel = grpc.insecure_channel("localhost:50055")
        stub = Generated_Stubs.matching.matching_pb2_grpc.MatchingServiceStub(channel)
        request = Generated_Stubs.matching.matching_pb2.MatchRequest(rider_id=rider_id)
        response = stub.RequestMatch(request)
        return {
            "found": response.found,
            "driver_id": response.driver_id,
            "rider_id": response.rider_id,
            "otp": response.otp,
            "driver_name": response.driver_name,
            "driver_phone": response.driver_phone,
        }
    except Exception as e:
        return {
            "found": False,
            "error": str(e)
        }