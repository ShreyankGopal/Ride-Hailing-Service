import grpc
from concurrent import futures
import os,sys
current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
import Generated_Stubs.station.station_pb2 as Station_pb2
import Generated_Stubs.station.station_pb2_grpc as Station_pb2_grpc
stations = {
    "1": {"name": "Station 1", "lat": 12.88005258237233, "lon": 77.58702374463442},
    "2": {"name": "Station 2", "lat": 12.9352, "lon": 77.6245},
    "3": {"name": "Station 3", "lat": 12.9084, "lon": 77.6753},
    "4": {"name": "Station 4", "lat": 12.8816, "lon": 77.7261},
}
class StationService(Station_pb2_grpc.StationServiceServicer):
    def GetStations(self, request, context):
        print("GetStations request received")
        print (request)
        return Station_pb2.GetStationsResponse(stations=[Station_pb2.Station(station_id="1", name="Station 1", lat=12.88005258237233, lon=77.58702374463442), Station_pb2.Station(station_id="2", name="Station 2", lat=12.9352, lon=77.58702374463442)])
        #an array of station_pb2.station object is returned
        #each station object has station_id, name, lat, lon
        #station_id is a string
        #name is a string
        #lat is a double
        #lon is a double
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Station_pb2_grpc.add_StationServiceServicer_to_server(StationService(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    server.wait_for_termination()
if __name__ == '__main__':
    print("Station service starting...")
    serve()