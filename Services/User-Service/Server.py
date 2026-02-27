import os
import sys
import datetime
import hashlib
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
from db_user_repository import create_user, get_user_by_phone, get_user_by_id


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60  # 1 hour


def _create_access_token(payload: dict, expires_in_seconds: int) -> str:
    """Create a signed JWT access token with an expiration time."""

    to_encode = payload.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=expires_in_seconds
    )
    to_encode["exp"] = expire

    import jwt

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class UserService(user_pb2_grpc.UserServiceServicer):

    def Register(self, request, context):
        print("Register request received")
        print(request)

        # Hash the password before persisting it.
        password_hash = hashlib.sha256(request.password.encode("utf-8")).hexdigest()

        # Persist the user in PostgreSQL users table.
        # For drivers, we keep the existing Redis + driver-service behavior
        # and additionally create a user row with role "driver".
        try:
            user_id = create_user(
                name=request.name,
                phone=request.phone,
                role=request.role,
                password=password_hash,
            )
            if user_id is None:
                return user_pb2.RegisterResponse(success=False)
        except Exception as exc:  # noqa: BLE001
            print(f"Error creating user in database: {exc}")
            return user_pb2.RegisterResponse(success=False)

        if request.role == "driver":
            # Existing driver registration logic using Redis and driver service.
            driver_id = str(user_id)

            redis_client.hset(
                f"drivers:{driver_id}",
                mapping={
                    "name": request.name,
                    "phone": request.phone,
                    "role": "driver",
                },
            )

            try:
                drivers = redis_client.hgetall(f"drivers:{driver_id}")
                response = send_drivers_client.send_drivers_to_driver_service(
                    {driver_id: drivers}
                )
                print(f"Response from driver service: {response}")
            except Exception as e:  # noqa: BLE001
                print(f"Error sending drivers to driver service: {e}")
                return user_pb2.RegisterResponse(success=False)

            print(f"Registered driver with ID: {driver_id}")
        else:
            print(f"Registered user with DB user_id: {user_id}")

        return user_pb2.RegisterResponse(success=True)

    def Login(self, request, context):
        print("Login request received")
        print(request)

        # Fetch user by phone from PostgreSQL.
        user_row = get_user_by_phone(request.phone)
        
        if not user_row:
            # No such user.
            return user_pb2.LoginResponse(token="")

        # Verify password.
        password_hash = hashlib.sha256(request.password.encode("utf-8")).hexdigest()
        if user_row["password"] != password_hash:
            return user_pb2.LoginResponse(token="")

        # Build JWT token consistent with previous auth logic.
        token_payload = {
            "sub": str(user_row["user_id"]),
            "role": user_row["role"],
        }
        role=user_row["role"]
        token = _create_access_token(token_payload, ACCESS_TOKEN_EXPIRE_SECONDS)
        print(role)
        return user_pb2.LoginResponse(token=token,role=role)
    
    def GetUserById(self, request, context):
        """Return user details by user_id."""

        # request.user_id will be a string (per proto definition)
        try:
            user_id_int = int(request.user_id)
        except ValueError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("user_id must be an integer")
            return user_pb2.GetUserByIdResponse()

        row = get_user_by_id(user_id_int)
        if not row:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found")
            return user_pb2.GetUserByIdResponse()

        return user_pb2.GetUserByIdResponse(
            user_id=str(row["user_id"]),
            name=row["name"],
            phone=row["phone"],
            role=row["role"],
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("User service starting on port 50051...")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
