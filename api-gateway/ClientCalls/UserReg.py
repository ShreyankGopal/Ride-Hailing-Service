import grpc
import Generated_Stubs.user.user_pb2
import Generated_Stubs.user.user_pb2_grpc

def register(name, phone, role, password):
    try:
        channel = grpc.insecure_channel("localhost:50051")
        stub = Generated_Stubs.user.user_pb2_grpc.UserServiceStub(channel)
        request = Generated_Stubs.user.user_pb2.RegisterRequest(name=name, phone=phone, role=role, password=password)
        response = stub.Register(request)# Register is the function on the server end which is being exposed. Grpc provides a remote method to call the methids or procedure
        #request is wrapped as an objects called RegisterRequest
        #response is wrapped as an objects called RegisterResponse
        return {
            "success": response.success
        }
    except Exception as e:
       return {
            "success": False,
            "error": str(e)
        }
def Login(phone, password):
    try:
        channel = grpc.insecure_channel("localhost:50051")
        stub = Generated_Stubs.user.user_pb2_grpc.UserServiceStub(channel)
        request = Generated_Stubs.user.user_pb2.LoginRequest(phone=phone, password=password)
        response = stub.Login(request)
        return {
            "success": response.success
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }