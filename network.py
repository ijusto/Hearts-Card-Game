import socket
import pickle # used to serialize objects so that the sent data is an object instead of a string

# responsible to connecting to the server
class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = "192.168.1.149" # my local ip address
        self.port = 5555
        self.addr = (self.server, self.port)
        self.player = self.connect()

    def getPlayer(self):
        return self.player

    def connect(self):
        try:
            self.client.connect(self.addr)
            return pickle.loads(self.client.recv(2048)) # pickle is used to decompose the object data
        except socket.error as e:
            print(e)

    def send(self, data):
        try:
            self.client.send(pickle.dumps(data)) # dump the object data into a pickle object and send it
            return pickle.loads(self.client.recv(2048))
        except socket.error as e:
            print(e)
