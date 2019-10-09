import socket
import threading
import sys
import pickle # used to serialize objects so that the sent data is an object instead of a string


class Server:
    #table = {} # key: tableId, value:playersList
    #tableId = 1
    clientDisconnected = False
    # ipv4 tcp socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connections = []
    playersConnected = {}
    def __init__ (self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0


    def handler(self, client_socket, client_address):
        while True:
            '''
            if self.numberOfClients < 4:
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

                if not data:
                    print(str(client_address[0]) + ':' + str(client_address[1]), "disconnected")
                    self.connections.remove(client_socket)
                    client_socket.close()
                    self.clientDisconnected = True
                    break
            '''

            ##VERIFICAR SE O USERNAME JÁ FOI ESCOLHIDO
            validUser=False
            while(not validUser):
                validUser=True
                client_socket.send(bytes("UserName: ", 'utf-8'))
                username = client_socket.recv(1024).decode()
                for value in self.playersConnected.values():
                    if(value[0]==username):
                        validUser=False
                        break
                if(not validUser):
                    client_socket.send(bytes("This username was already taken", 'utf-8'))



            client_socket.send(bytes("CC: ", 'utf-8'))
            cc = client_socket.recv(1024).decode()
            connection = (client_socket,client_address)
            self.playersConnected.update({connection : (username,cc)})
            client_socket.send(bytes("Lobby:\n", 'utf-8'))
            for value in self.playersConnected.values():
                if(value[1]!=cc):
                    client_socket.send(bytes(value[0]+"\n",'utf-8'))
            client_socket.send(bytes("\nInvite a player (using his username)", 'utf-8'))


            #Sending information to other players about the join
            for k, v in self.playersConnected.items():
                if(k[0] != client_socket):
                    k[0].send(bytes(username+" joined the lobby:\n", 'utf-8'))
                    k[0].send(bytes("Lobby:\n", 'utf-8'))
                    for value in self.playersConnected.values():
                        if (value[1] != v[1]):
                            k[0].send(bytes(value[0] + "\n", 'utf-8'))
                    k[0].send(bytes("\nInvite a player (using his username)", 'utf-8'))

            invitation = client_socket.recv(1024).decode()

            for k,v in self.playersConnected.items():
                if v[0] == invitation:
                    resp = ""
                    while resp != "y" and resp != "n":
                        k[0].send(bytes("Do you want to play with "+username+"?[y/n]","utf-8"))
                        resp = k[0].recv(1024).decode()
                        if(resp == "y"):
                            client_socket.send(bytes("yay", 'utf-8'))
                        elif(resp == "n"):
                            client_socket.send(bytes("nay", 'utf-8'))

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