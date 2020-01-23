import sys
from client import Client
from server import Server

if(len(sys.argv) > 1):
    client = Client(sys.argv[1])
else:
    server = Server()
    server.run()