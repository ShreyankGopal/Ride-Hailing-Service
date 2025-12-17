import os
import sys
current = os.path.dirname(os.path.realpath(__file__))

project_root = os.path.dirname(current)
if project_root not in sys.path:
    sys.path.append(project_root)
import flask_cors
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

app = flask.Flask(__name__)
flask_cors.CORS(app)
@app.route("/user/register", methods=["POST"])
def register():
    data = flask.request.get_json()
    print(data)
    return ClientCalls.UserReg.register(data["name"], data["phone"], data["role"], data["password"])
@app.route("/user/login", methods=["POST"])
def login():
    data = flask.request.get_json()
    print(data)
    return ClientCalls.UserReg.login(data["phone"], data["password"])
@app.route("/station/", methods=["GET"])
def get_stations():
    print("GetStations request received")
    return ClientCalls.StationReg.get_stations()
@app.route("/rider/register", methods=["POST"])
def register_rider():
    data = flask.request.get_json()
    print(data)
    return ClientCalls.Rider.register(data["rider_id"], data["station_id"], data["arrival_time"], data["destination"])
@app.route("/rider/update_status", methods=["POST"])
def update_rider_status():
    data = flask.request.get_json()
    print(data)
    return ClientCalls.Rider.update_rider_status(data["rider_id"], data["status"])

@app.route("/matching/request", methods=["POST"])
def request_match():
    """ match request for a rider"""
    data = flask.request.get_json()
    print(data)
    result = ClientCalls.Matching.request_match(data["rider_id"])
    print(result)
    return flask.jsonify(result)

   
if __name__ == "__main__":
    app.run(debug=True, port=5000)
