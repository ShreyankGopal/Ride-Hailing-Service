import os
import sys
current = os.path.dirname(os.path.realpath(__file__))

project_root = os.path.dirname(current)
if project_root not in sys.path:
    sys.path.append(project_root)
import flask
import os
import grpc
import Generated_Stubs.user.user_pb2
import Generated_Stubs.user.user_pb2_grpc
import Generated_Stubs.driver.driver_pb2
import Generated_Stubs.driver.driver_pb2_grpc
import Generated_Stubs.Location.Location_pb2
import Generated_Stubs.Location.Location_pb2_grpc
import Generated_Stubs.matching.matching_pb2
import Generated_Stubs.matching.matching_pb2_grpc
import Generated_Stubs.notification.notification_pb2
import Generated_Stubs.notification.notification_pb2_grpc
import ClientCalls.UserReg
import ClientCalls.StationReg
import ClientCalls.Rider
import ClientCalls.Matching
import ClientCalls.TripStatus
import ClientCalls.DriverReg
from Server_Handlers.middleware.auth_middleware import auth_required
from flask_cors import CORS
app = flask.Flask(__name__)
CORS(
    app,
    origins=[
        "http://localhost:8000",
        "http://127.0.2.2:8000",
    ],
    supports_credentials=True,
)

# @app.route("/user/register", methods=["POST"])
# def register():
#     data = flask.request.get_json()
#     print(data)
#     return ClientCalls.UserReg.register(data["name"], data["phone"], data["role"], data["password"])
# @app.route("/user/login", methods=["POST"])
# def login():
#     data = flask.request.get_json()
#     print(data)
#     return ClientCalls.UserReg.login(data["phone"], data["password"])
# @app.route("/station/", methods=["GET"])
# def get_stations():
#     print("GetStations request received")
#     return ClientCalls.StationReg.get_stations()
# @app.route("/rider/register", methods=["POST"])
# def register_rider():
#     data = flask.request.get_json()
#     print(data)
#     return ClientCalls.Rider.register(data["rider_id"], data["station_id"], data["arrival_time"], data["destination"])
# @app.route("/rider/update_status", methods=["POST"])
# def update_rider_status():
#     data = flask.request.get_json()
#     print(data)
#     return ClientCalls.Rider.update_rider_status(data["rider_id"], data["status"])

# @app.route("/matching/request", methods=["POST"])
# def request_match():
#     """ match request for a rider"""
#     data = flask.request.get_json()
#     print(data)
#     result = ClientCalls.Matching.request_match(data["rider_id"])
#     print(result)
#     return flask.jsonify(result)

# @app.route("/updateTripStatus", methods=["POST"])
# def update_trip_status():
#     data = flask.request.get_json()
#     print(data)
#     return ClientCalls.TripStatus.update_trip_status(data["trip_id"], data["status"])

'''
#######################################################################################
#                  Login and Signup Handlers                                          #
#######################################################################################
'''

def _set_auth_cookie(response: flask.Response, token: str) -> None:
    """Attach the JWT as an HTTP-only cookie on the response."""

    # Keep cookie semantics consistent with earlier implementation.
    max_age = 60 * 60  # 1 hour
    response.set_cookie(
        "access_token",
        token,
        max_age=max_age,
        httponly=True,
        secure=False,
        samesite="Lax",
        path="/",
    )


@app.route("/signup", methods=["POST"])
def signup():
    print("Signup request received")

    data = flask.request.get_json() or {}
    name = data.get("name")
    phone = data.get("phone")
    role = data.get("role")
    password = data.get("password")

    if not all([name, phone, role, password]):
        return flask.jsonify({"error": "Missing required fields"}), 400

    # Call User-Service via gRPC to register the user.
    reg_result = ClientCalls.UserReg.register(name, phone, role, password)
    if not reg_result.get("success"):
        return flask.jsonify({"error": reg_result.get("error", "Signup failed")}), 500

    # Optionally, perform an implicit login to issue a JWT cookie immediately.
    login_result = ClientCalls.UserReg.Login(phone, password)
    if not login_result.get("success"):
        # Registration succeeded but login failed; return 200 without a token.
        return flask.jsonify({"message": "Signup successful"}), 200

    token = login_result.get("token", "")
    response = flask.jsonify({"message": "Signup successful"})
    if token:
        _set_auth_cookie(response, token)
    return response


@app.route("/login", methods=["POST"])
def login():
    data = flask.request.get_json() or {}
    phone = data.get("phone")
    password = data.get("password")

    if not all([phone, password]):
        return flask.jsonify({"error": "Missing phone or password"}), 400

    # gRPC wrapper call (returns dict)
    grpc_response = ClientCalls.UserReg.Login(phone, password)

    if not grpc_response.get("success"):
        return flask.jsonify({
            "error": grpc_response.get("error", "Invalid credentials")
        }), 401

    token = grpc_response.get("token")
    role = grpc_response.get("role")

    if not token or not role:
        return flask.jsonify({"error": "Invalid credentials"}), 401

    response = flask.jsonify({
        "message": "Login successful",
        "role": role
    })

    _set_auth_cookie(response, token)
    return response


@app.route("/me", methods=["GET"])
@auth_required
def me():
    """Return basic information about the currently authenticated user.

    Uses the JWT payload that auth_required attaches to flask.g.current_user.
    """

    user = getattr(flask.g, "current_user", None)
    if not user:
        return flask.jsonify({"error": "Unauthorized"}), 401

    return flask.jsonify(
        {
            "user_id": user.get("sub"),
            "role": user.get("role"),
        }
    )


@app.route("/logout", methods=["POST"])
def logout():
    """Clear the auth cookie so the user is logged out."""

    response = flask.jsonify({"message": "Logged out"})
    # Overwrite the cookie with empty value and immediate expiry.
    response.set_cookie("access_token", "", max_age=0, expires=0, path="/")
    return response

"""
Sending Driver Updates here -------------------------------------------
"""
@app.route("/driver/online", methods=["POST"])
@auth_required
def driver_online():
    """Mark the driver as online and update status via Driver-Service."""

    # Extract JWT payload from auth_required middleware
    user = getattr(flask.g, "current_user", None)
    if not user:
        return flask.jsonify({"error": "Unauthorized"}), 401

    role = user.get("role")
    driver_id = user.get("sub")

    if role != "driver" or not driver_id:
        return flask.jsonify({"error": "Only drivers can go online"}), 403

    data = flask.request.get_json() or {}
    status = data.get("status")

    if status != "available":
        return flask.jsonify({"error": "Invalid status"}), 400

    # Call Driver-Service via gRPC to update status
    result = ClientCalls.DriverReg.Update_Driver_Status(
        status=status,
        driver_id=str(driver_id),
    )

    if not result.get("success"):
        return (
            flask.jsonify(
                {"error": result.get("error", "Failed to update driver status")}
            ),
            500,
        )

    return flask.jsonify(
        {
            "message": "Driver is now online",
            "driver_id": driver_id,
            "status": status,
        }
    ), 200

if __name__ == "__main__":
    app.run(debug=True, port=5001)
