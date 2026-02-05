import grpc
import Generated_Stubs.Location.Location_pb2 as Location_pb2
import Generated_Stubs.Location.Location_pb2_grpc as Location_pb2_grpc


def stream_location_once(driver_id: str, lat: float, lon: float, timestamp: int):
    """Send a single LocationUpdate over the StreamLocation RPC.

    This opens a short-lived gRPC stream to the Location-Service, sends
    exactly one LocationUpdate, waits for the Ack, and then closes.
    """
    try:
        channel = grpc.insecure_channel("localhost:50052")
        stub = Location_pb2_grpc.LocationServiceStub(channel)

        def request_iter():
            yield Location_pb2.LocationUpdate(
                driver_id=str(driver_id),
                lat=float(lat),
                lon=float(lon),
                timestamp=int(timestamp),
            )

        response = stub.StreamLocation(request_iter())# the location update must be sent as a function that Yields as it is of type stream and expects a fnction thats yields the format of the message as input to the StreamLocation function
        return {"success": True, "message": response.message}
    except Exception as e:
        return {"success": False, "error": str(e)}
