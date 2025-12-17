import grpc
import os,sys
current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
from concurrent import futures
import Generated_Stubs.rider.rider_pb2_grpc as Rider_pb2_grpc
import Generated_Stubs.rider.rider_pb2 as Rider_pb2
Rider = {}
class RiderService(Rider_pb2_grpc.RiderServiceServicer):
    def RegisterRider(self, request, context):
        print("RegisterRider request received")
        print (request)
        Rider[request.rider_id] = {
            "station_id": request.station_id,
            "arrival_time": request.arrival_time,
            "destination": request.destination,
            "status": "waiting"
        }
        return Rider_pb2.RegisterRiderResponse(success=True)
    def UpdateRiderStatus(self, request, context):
        print("UpdateRiderStatus request received")
        print(request)
        if request.rider_id in Rider:
            Rider[request.rider_id]["status"] = request.status
        return Rider_pb2.UpdateRiderStatusResponse(success=True)# the rider status is waiting(0), matched(1), picked(2), completed(3)

    def GetRiderInfo(self, request, context):
        print("GetRiderInfo request received")
        print(request)
        if request.rider_id in Rider:
            rider = Rider[request.rider_id]
            return Rider_pb2.GetRiderInfoResponse(
                station_id=rider["station_id"],
                arrival_time=rider["arrival_time"],
                destination=rider["destination"],
                status=rider["status"]
            )
        return Rider_pb2.GetRiderInfoResponse()
        
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Rider_pb2_grpc.add_RiderServiceServicer_to_server(RiderService(), server)
    server.add_insecure_port('[::]:50054')
    server.start()
    server.wait_for_termination()
if __name__ == '__main__':
    print("Rider service starting...")
    serve()