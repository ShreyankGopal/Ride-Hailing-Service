import os
import sys
import grpc
from concurrent import futures

current = os.path.dirname(os.path.realpath(__file__))
services_dir = os.path.dirname(current)
project_root = os.path.dirname(services_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import Generated_Stubs.user.user_pb2 as user_pb2
import Generated_Stubs.user.user_pb2_grpc as user_pb2_grpc
import Client.SendDriversToDriverService as send_drivers_client
from Services.Common.redis_client import redis_client


class UserService(user_pb2_grpc.UserServiceServicer):

    def Register(self, request, context):
        print("Register request received")
        print(request)

        if request.role == "driver":
            # Atomic driver ID generation
            driver_id = str(redis_client.incr("counter:driver_id"))

            redis_client.hset(
                f"drivers:{driver_id}",
                mapping={
                    "name": request.name,
                    "phone": request.phone,
                    "role": "driver"
                }
            )

            try:
                # Optional: send driver info to driver service
                drivers = redis_client.hgetall(f"drivers:{driver_id}")
                response = send_drivers_client.send_drivers_to_driver_service(
                    {driver_id: drivers}
                )
                print(f"Response from driver service: {response}")
            except Exception as e:
                print(f"Error sending drivers to driver service: {e}")
                return user_pb2.RegisterResponse(success=False)

            print(f"Registered driver with ID: {driver_id}")

        else:
            # Atomic user ID generation
            user_id = str(redis_client.incr("counter:user_id"))

            redis_client.hset(
                f"users:{user_id}",
                mapping={
                    "name": request.name,
                    "phone": request.phone,
                    "role": "rider"
                }
            )

            print(f"Registered user with ID: {user_id}")

        return user_pb2.RegisterResponse(success=True)

    def Login(self, request, context):
        print("Login request received")
        print(request)

        user_key = f"users:{request.user_id}"
        driver_key = f"drivers:{request.user_id}"

        if redis_client.exists(user_key) or redis_client.exists(driver_key):
            return user_pb2.LoginResponse(success=True)

        return user_pb2.LoginResponse(success=False)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("User service starting on port 50051...")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
