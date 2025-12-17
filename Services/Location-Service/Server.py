import grpc
import os,sys

from werkzeug import Client
current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
client_dir = os.path.join(services_dir, "Location-Service", "Client")
if client_dir not in sys.path:
    sys.path.append(client_dir)
from concurrent import futures
import Generated_Stubs.Location.Location_pb2_grpc as Location_pb2_grpc
import Generated_Stubs.Location.Location_pb2 as Location_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc
import Generated_Stubs.driver.driver_pb2 as driver_pb2
import Client.SendDriverPositionToDriverService as SendDriverPositionToDriverService

class LocationService(Location_pb2_grpc.LocationServiceServicer):

    def __init__(self):
        self.driver_service_channel = grpc.insecure_channel("127.0.0.1:50057")
        self.driver_service_stub = driver_pb2_grpc.DriverServiceStub(self.driver_service_channel)
        
    
    def StreamLocation(self, request, context):
        print("GetLocation request received")
        for location in request:
            print("Location received:", location)
            driver_id = location.driver_id
            lat = location.lat
            lon = location.lon
            # Forward to Driver Service using the stub we created in __init__
            try:
                response = SendDriverPositionToDriverService.send_driver_position(driver_id, lat, lon, self.driver_service_stub)
                print(f"Forwarded to DriverService: {response}")
            except Exception as e:
                print(f"Error forwarding to DriverService: {e}")
        return Location_pb2.Ack(message="Location received")
     
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Location_pb2_grpc.add_LocationServiceServicer_to_server(LocationService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    server.wait_for_termination()
 
if __name__ == '__main__':
    print("Location service starting...")
    serve()