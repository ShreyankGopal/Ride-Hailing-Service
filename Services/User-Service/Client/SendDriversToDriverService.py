import grpc
import sys, os

current = os.path.dirname(os.path.realpath(__file__))
LocationService = os.path.dirname(current)
Services = os.path.dirname(LocationService)
project_root = os.path.dirname(Services)
if project_root not in sys.path:
    sys.path.append(project_root)


import Generated_Stubs.driver.driver_pb2 as Driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc as driver_pb2_grpc

def send_drivers_to_driver_service(Drivers):
    # TODO: Implement the logic to send drivers to the driver service
    # For now, just create a simple gRPC client to test connectivity
    try:
        channel = grpc.insecure_channel("localhost:50057")  # Assuming driver service runs on port 50057
        stub = driver_pb2_grpc.DriverServiceStub(channel)
        # Test the connection with a simple ping
        driver_list = []
        for driver_id, driver_info in Drivers.items():
            print(f"Sending driver {driver_id} to Driver Service")
            driver = Driver_pb2.DriverDetails(
                driver_id=driver_id,
                name=driver_info.get('name', ''),
                phone=driver_info.get('phone', '')
            )
            driver_list.append(driver)
        
        # Send all drivers at once
        request = Driver_pb2.SendDriversRequest(drivers=driver_list)
        response = stub.SendDrivers(request)
        print(f"Successfully sent drivers to Driver Service. Response: {response}")
        return True
    except Exception as e:
        print(f"Failed to connect to Driver Service: {e}")
        return False