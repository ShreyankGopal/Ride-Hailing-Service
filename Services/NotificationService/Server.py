import grpc
import os
import sys
import json
from concurrent import futures

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.notification.notification_pb2 as notification_pb2
import Generated_Stubs.notification.notification_pb2_grpc as notification_pb2_grpc
from Services.Common.redis_client import redis_client

class NotificationService(notification_pb2_grpc.NotificationServiceServicer):
    def SendDriverNotification(self, request, context):
        print(f"[NotificationService] Received notification for driver {request.driver_id}")
        
        # Publish to Redis Pub/Sub
        redis_client.publish(
            f"driver_notifications:{request.driver_id}",
            json.dumps({
                "rider_name": request.rider_name,
                "rider_phone": request.rider_phone,
                "otp": request.otp,
                "station_lat": request.station_lat,
                "station_lon": request.station_lon,
                "trip_id": request.trip_id,
            })
        )
        print(f"[NotificationService] Published to driver_notifications:{request.driver_id}")
        return notification_pb2.NotificationAck(success=True)

    def SendRiderNotification(self, request, context):
        print(f"[NotificationService] Received notification for rider {request.rider_id}, type={request.notification_type}")

        payload = {
            "notification_type": request.notification_type,
        }

        if request.notification_type == "match_found":
            payload.update({
                "driver_id": request.driver_id,
                "driver_name": request.driver_name,
                "driver_phone": request.driver_phone,
                "otp": request.otp,
                "trip_id": request.trip_id,
            })

        redis_client.publish(
            f"rider_notifications:{request.rider_id}",
            json.dumps(payload)
        )
        print(f"[NotificationService] Published to rider_notifications:{request.rider_id}")
        return notification_pb2.NotificationAck(success=True)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    notification_pb2_grpc.add_NotificationServiceServicer_to_server(NotificationService(), server)
    server.add_insecure_port("[::]:50060")
    server.start()
    print("NotificationService running on port 50060")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
