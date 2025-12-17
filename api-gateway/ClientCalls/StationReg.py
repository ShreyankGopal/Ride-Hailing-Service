import grpc
import os,sys
current = os.path.dirname(os.path.realpath(__file__))
api_gateway = os.path.dirname(current)
project_root = os.path.dirname(api_gateway)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.station.station_pb2 as station_pb2
import Generated_Stubs.station.station_pb2_grpc as station_pb2_grpc

channel = grpc.insecure_channel("localhost:50053")
stub = station_pb2_grpc.StationServiceStub(channel)

def get_stations():
    try:
        response = stub.GetStations(station_pb2.GetStationsRequest())

        stations = []
        for s in response.stations:
            stations.append({
                "station_id": s.station_id,
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon
            })

        return {
            "stations": stations
        }

    except Exception as e:
        return {
            "error": str(e)
        }, 500