import grpc
import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
matching_dir = os.path.dirname(current)
services_dir = os.path.dirname(matching_dir)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.notification.notification_pb2 as notification_pb2
import Generated_Stubs.notification.notification_pb2_grpc as notification_pb2_grpc

def notify_driver(driver_id: str, rider_name: str, rider_phone: str, otp: str,
                  station_lat: float, station_lon: float, trip_id: str = ""):
    try:
        channel = grpc.insecure_channel("localhost:50060")
        stub = notification_pb2_grpc.NotificationServiceStub(channel)

        request = notification_pb2.DriverNotificationRequest(
            driver_id=str(driver_id),
            rider_name=rider_name,
            rider_phone=rider_phone,
            otp=otp,
            station_lat=station_lat,
            station_lon=station_lon,
            trip_id=trip_id,
        )
        response = stub.SendDriverNotification(request)
        return {"success": response.success}
    except Exception as e:
        print(f"[NotificationClient] Error notifying driver: {e}")
        return {"success": False, "error": str(e)}


def notify_rider(rider_id: str, notification_type: str, driver_id: str = "",
                 driver_name: str = "", driver_phone: str = "", otp: str = "",
                 trip_id: str = ""):
    try:
        channel = grpc.insecure_channel("localhost:50060")
        stub = notification_pb2_grpc.NotificationServiceStub(channel)

        request = notification_pb2.RiderNotificationRequest(
            rider_id=str(rider_id),
            notification_type=notification_type,
            driver_id=driver_id,
            driver_name=driver_name,
            driver_phone=driver_phone,
            otp=otp,
            trip_id=trip_id,
        )
        response = stub.SendRiderNotification(request)
        return {"success": response.success}
    except Exception as e:
        print(f"[NotificationClient] Error notifying rider: {e}")
        return {"success": False, "error": str(e)}
