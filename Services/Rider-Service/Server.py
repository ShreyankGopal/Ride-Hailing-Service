import grpc
import os, sys
from concurrent import futures

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.rider.rider_pb2_grpc as Rider_pb2_grpc
import Generated_Stubs.rider.rider_pb2 as Rider_pb2

from Services.Common.redis_client import redis_client


class RiderService(Rider_pb2_grpc.RiderServiceServicer):

    def RegisterRider(self, request, context):
        print("RegisterRider request received")
        print(request)

        redis_client.hset(
            f"riders:{request.rider_id}",
            mapping={
                "station_id": request.station_id,
                "arrival_time": request.arrival_time,
                "destination": request.destination,
                "status": "waiting"
            }
        )

        return Rider_pb2.RegisterRiderResponse(success=True)

    def UpdateRiderStatus(self, request, context):
        print("UpdateRiderStatus request received")
        print(request)

        rider_key = f"riders:{request.rider_id}"

        if not redis_client.exists(rider_key):
            print(f"[RiderService][UpdateRiderStatus] rider not found in Redis: rider_id={request.rider_id}")
            return Rider_pb2.UpdateRiderStatusResponse(success=False)

        # If trip completed → delete rider
        if request.status.lower() == "completed":
            redis_client.delete(rider_key)
            print(f"Deleted rider {request.rider_id} from Redis")
            return Rider_pb2.UpdateRiderStatusResponse(success=True)

        # Otherwise update status
        redis_client.hset(rider_key, "status", request.status)
        print(f"[RiderService][UpdateRiderStatus] Updated rider {request.rider_id} status to {request.status}")

        return Rider_pb2.UpdateRiderStatusResponse(success=True)

    def GetRiderInfo(self, request, context):
        print("GetRiderInfo request received")
        print(request)

        rider_key = f"riders:{request.rider_id}"

        if not redis_client.exists(rider_key):
            print(f"[RiderService][GetRiderInfo] rider not found in Redis: rider_id={request.rider_id}")
            return Rider_pb2.GetRiderInfoResponse()

        rider = redis_client.hgetall(rider_key)
        print(f"[RiderService][GetRiderInfo] rider data fetched for rider_id={request.rider_id}:", rider)

        return Rider_pb2.GetRiderInfoResponse(
            station_id=rider.get("station_id", ""),
            arrival_time=int(rider.get("arrival_time", 0)),
            destination=rider.get("destination", ""),
            status=rider.get("status", "")
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Rider_pb2_grpc.add_RiderServiceServicer_to_server(
        RiderService(), server
    )
    server.add_insecure_port('[::]:50054')
    server.start()
    print("Rider service running on port 50054")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
