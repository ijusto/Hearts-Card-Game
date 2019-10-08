import socket
import threading
import sys
import pickle # used to serialize objects so that the sent data is an object instead of a string


class Server:
    table = {} # key: tableId, value:playersList
    tableId = 1
    clientDisconnected = False
    # ipv4 tcp socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connections = []
    def __init__ (self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0

    def handler(self, client_socket, client_address):
        while True:
            if not self.numberOfClients % 4:
                data = client_socket.recv(1024)
                if not data:
                    print(str(client_address[0]) + ':' + str(client_address[1]), "disconnected")
                    self.connections.remove(client_socket)
                    client_socket.close()
                    self.clientDisconnected = True
                    break
                else:
                    client_socket.send(bytes("Waiting for more players...", 'utf-8'))
            else:
                data = client_socket.recv(1024)
                for connection in self.connections:
                    if connection != client_socket:
                        connection.send(data)

                if self.numberOfClients % 4:
                    self.tableId += 1
                # self.table[self.tableID].append(player)

                if not data:
                    print(str(client_address[0]) + ':' + str(client_address[1]), "disconnected")
                    self.connections.remove(client_socket)
                    client_socket.close()
                    self.clientDisconnected = True
                    break

    def run(self):
        while True:
            # establish the connection to the client wanting to connect
            clientSocket, clientAddress = self.serverSocket.accept()
            self.numberOfClients += 1

            # create a new thread
            connectionThread = threading.Thread(target=self.handler, args=(clientSocket, clientAddress))
            # the program is able to exit regardless of if there's any threads still running
            connectionThread.daemon = True
            connectionThread.start()

            self.connections.append(clientSocket)
            print(str(clientAddress[0]) + ':' + str(clientAddress[1]), "connected")

            if self.clientDisconnected:
                # stop the server if one of the 4 players gets disconnected
                break

class Client:
    # ipv4 tcp socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def sendMsg(self):
        while True:
            self.clientSocket.send(bytes(input(""), 'utf-8'))

    def __init__(self, address):
        self.clientSocket.connect((address, 10001))

        inputThread = threading.Thread(target=self.sendMsg)
        inputThread.daemon = True
        inputThread.start()

        while True:
            data = self.clientSocket.recv(1024)
            if not data:
                break
            print(str(data, 'utf-8'))


if(len(sys.argv) > 1):
    client = Client(sys.argv[1])
else:
    server = Server()
    server.run()