from ast import main
import os
import sys
current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import grpc
from concurrent import futures
import Generated_Stubs.trip.trip_pb2
import Generated_Stubs.trip.trip_pb2_grpc

Trips = {}
def genOtp():
    import random
    return str(random.randint(1000, 9999))

class TripService(Generated_Stubs.trip.trip_pb2_grpc.TripServiceServicer):
    def StartTrip(self, request, context):
        print("StartTrip request received")
        print(request)
        trip_id = f"trip_{len(Trips) + 1}"
        otp = genOtp() # we generate otp for the driver to verify at drop
        Trips[trip_id] = {"rider_id": request.rider_id, "driver_id": request.driver_id, "status": "matched", "otp": otp}
        print("updated trip status")
        return Generated_Stubs.trip.trip_pb2.StartTripResponse(trip_id=trip_id,otp=otp)
    
    def UpdateTripStatus(self, request, context):
        print("UpdateTripStatus request received")
        print(request)
        if request.trip_id in Trips:
            Trips[request.trip_id]["status"] = request.status
            print("updated trip status")
        return Generated_Stubs.trip.trip_pb2.UpdateTripStatusResponse(success=True)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Generated_Stubs.trip.trip_pb2_grpc.add_TripServiceServicer_to_server(TripService(), server)
    server.add_insecure_port('[::]:50056')
    server.start()
    print('Trip service starting on port 50056...')
    server.wait_for_termination()
if __name__ == '__main__':
    print("Trip service starting...")
    serve()
