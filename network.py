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
    # players individuais
    playersConnected = {}
    #players em parties
    numberOfParties=0
    parties = {}

    def __init__ (self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0


    ##Função que escreve o lobby
    def lobbyMeny(self, userSocket,userCc):
        userSocket.send(bytes("Lobby:\n", 'utf-8'))
        for un, ucc in self.playersConnected.values():
            if ucc != userCc:
                userSocket.send(bytes(un + "\n", 'utf-8'))
        for list in self.parties.values():
            partyLobby = []
            for elem in list:
                for (user_socket, user_address), (user_name, user_cc) in elem.items():
                    partyLobby.append(user_name)
            if(len(partyLobby)!=0):
                userSocket.send(bytes(str(partyLobby) + "\n", 'utf-8'))
        userSocket.send(bytes("\nInvite a player (using his username)", 'utf-8'))

        #VERIFICAR SE UM MEMBRO ESTÁ NUMA PARTY
        if self.verificarPartyMember(userCc):
            userSocket.send(bytes("\nWrite LEAVE to leave the party\n", 'utf-8'))

    def verificarPartyMember(self,userCC):
        verificador = False
        for list in self.parties.values():
            for elem in list:
                for (user_name, user_cc) in elem.values():
                    if user_cc==userCC:
                        verificador=True
                        break
                if verificador == True:
                     break
            if verificador == True:
                break
        return verificador

    def handler(self, client_socket, client_address):
            try:
                ##VERIFICAR SE O client_username JÁ FOI ESCOLHIDO
                validUser=False
                while not validUser:
                    validUser = True
                    client_socket.send(bytes("Username: ", 'utf-8'))
                    client_username = client_socket.recv(1024).decode()
                    for value in self.playersConnected.values():
                        if value[0] == client_username:
                            validUser=False
                            break
                    if not validUser:
                        client_socket.send(bytes("This Username was already taken", 'utf-8'))

                client_socket.send(bytes("CC: ", 'utf-8'))
                cc = client_socket.recv(1024).decode()
                connection = (client_socket,client_address)
                dicAux = {connection : (client_username,cc)}
                self.playersConnected.update({connection : (client_username,cc)})

                ##Sending information to other players about the join
                for (user_socket, user_address), (user_name,user_cc) in self.playersConnected.items():
                    if user_socket != client_socket:
                        user_socket.send(bytes("\n"+client_username+" joined the lobby\n", 'utf-8'))
                        self.lobbyMeny(user_socket,user_cc)
                for party_num, list in self.parties.items():
                    for user in list:
                        for (user_socket, user_address), (user_name, user_cc) in user.items():
                            if user_socket!=client_socket:
                                user_socket.send(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'))
                                self.lobbyMeny(user_socket, user_cc)
            except:
                print("player disconnected")
                client_socket.close()
                self.clientDisconnected = True

            while True:
                try:
                    self.lobbyMeny(client_socket,cc)
                    invitation = client_socket.recv(1024).decode()

                    if(invitation == client_username):
                        client_socket.send(bytes("You can't invite your self"))
                    else:
                        checker = False
                        for (user_socket, user_address), (user_name, user_cc) in self.playersConnected.items():
                            if user_name == invitation:
                                resp = ""
                                while resp != "y" and resp != "n":
                                    #Envia convite para o player
                                    user_socket.send(bytes("Do you want to play with "+client_username+"?[y/n]", "utf-8"))
                                    resp = user_socket.recv(1024).decode()
                                    ##RESOLVER PROBLEMA DOS 2 RECV()
                                    #Player aceita convite
                                    if resp == "y":
                                        client_socket.send(bytes(user_name+" accepted the invite", 'utf-8'))
                                        auxList=[party_num for party_num, list in self.parties.items() if dicAux in list]
                                        #Se o client ainda não estiver numa party
                                        if(len(auxList)==0):
                                            self.parties.update({self.numberOfParties+1: [{(user_socket, user_address): (user_name, user_cc)}, dicAux]})
                                            self.numberOfParties+=1
                                        #Se o client já estiver numa party
                                        else:
                                            self.parties[auxList[0]].append({(user_socket, user_address): (user_name, user_cc)})
                                        checker = True
                                        #Remover da lista de players que não estão em party o player convidado
                                        del self.playersConnected[(user_socket,user_address)]
                                        #Remover da lista de player que nao estão em party o client (Se não estiver numa party)
                                        if connection in self.playersConnected:
                                            del self.playersConnected[connection]
                                        ##Atualiza lobby do players
                                        for (user_socket2, user_address2), (user_name2, user_cc2) in self.playersConnected.items():
                                            if user_socket2 != client_socket:
                                                self.lobbyMeny(user_socket2, user_cc2)
                                        for party_num, list in self.parties.items():
                                            for user in list:
                                                for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                                                    if user_socket2 != client_socket:
                                                        self.lobbyMeny(user_socket2, user_cc2)
                                    #Player recusa convite
                                    elif resp == "n":
                                        client_socket.send(bytes(user_name+" refused the invite", 'utf-8'))
                                break

                        #Se o player convidado já estiver numa party
                        if not checker:
                            for party_number, list in self.parties.items():
                                for user in list:
                                    for (user_socket,user_address), (user_name,user_cc) in user.items():
                                        if user_name == invitation:
                                            if(self.verificarPartyMember(cc)):
                                                client_socket.send(bytes("You'te already in a party, you can't join another","utf-8"))
                                                break
                                            checker = True
                                            resp = ""
                                            while resp != "y" and resp != "n":
                                                user_socket.send(bytes("Do you want to play with " + client_username + "?[y/n]", "utf-8"))
                                                resp = user_socket.recv(1024).decode()
                                                if resp == "y":
                                                    client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                                    del self.playersConnected[connection]
                                                    self.parties[party_number].append(dicAux)
                                                    ##Atualiza lobby do players
                                                    for (user_socket2, user_address2), (user_name2, user_cc2) in self.playersConnected.items():
                                                        if user_socket2 != client_socket:
                                                            self.lobbyMeny(user_socket2, user_cc2)
                                                    for party_num, list in self.parties.items():
                                                        for user in list:
                                                            for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                                                                if user_socket2 != client_socket:
                                                                    self.lobbyMeny(user_socket2, user_cc2)
                                                elif resp == "n":
                                                    client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                                    if (self.verificarPartyMember(cc)):
                                        break
                            if (self.verificarPartyMember(cc)):
                                 break

                        ##Se o player convidade não estiver no lobby, nem numa party
                        ##OU ser o utilizador quiser sair da party
                        if not checker:
                            if invitation == "LEAVE":
                                if (not self.verificarPartyMember(cc)):
                                    client_socket.send(bytes("You're not in a party",'utf-8'))
                                else:
                                    for party_num, list in self.parties.items():
                                        if(dicAux in list):
                                            if len(list) == 2:
                                                for user in list:
                                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                        if(client_socket!=user_socket):
                                                            user_socket.send(bytes("\n"+client_username+" leave the party, party was deleted\n", 'utf-8'))
                                                        self.playersConnected.update({(user_socket, user_address): (user_name, user_cc)})
                                                client_socket.send(bytes("You left the party",'utf-8'))
                                                del self.parties[party_num]
                                                break
                                            else:
                                                for user in list:
                                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                        if client_socket != user_socket:
                                                            user_socket.send(bytes("\n"+client_username+" leave the party", 'utf-8'))
                                                list.remove(dicAux)
                                                client_socket.send(bytes("You left the party", 'utf-8'))
                                                self.playersConnected.update(dicAux)
                                                break
                                    ##Atualiza lobby do players
                                    for (user_socket2, user_address2), (user_name2, user_cc2) in self.playersConnected.items():
                                        if user_socket2 != client_socket:
                                                self.lobbyMeny(user_socket2, user_cc2)
                                        for party_num, list in self.parties.items():
                                            for user in list:
                                                for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                                                    if user_socket2 != client_socket:
                                                        self.lobbyMeny(user_socket2, user_cc2)
                            else:
                                client_socket.send(bytes("\nThat players doesn't exist\n",'utf-8'))

                        #VERIFICAR SE PARTY = 4
                        party44 = False
                        for party_num, list in self.parties.items():
                            for user in list:
                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                    if user_socket == client_socket:
                                        if len(list) == 4:
                                            party44 = True
                                            break
                                if(party44==True):
                                    break
                            if (party44 == True):
                                break
                        if (party44 == True):
                            client_socket.send(bytes("CRIAR MESA",'utf-8'))
                            break
                except:
                    print("player disconnected")
                    #self.connections.remove(client_socket)
                    if(self.verificarPartyMember(cc)):
                        for party_num, list in self.parties.items():
                            if(dicAux in list):
                                if len(list) == 2:
                                    for user in list:
                                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                if (client_socket != user_socket):
                                                    user_socket.send(bytes("\n" + client_username + " leave the party, party was deleted\n",'utf-8'))
                                                self.playersConnected.update({(user_socket, user_address): (user_name, user_cc)})
                                    del self.parties[party_num]
                                    break
                                else:
                                    for user in list:
                                        for (user_socket, user_address), (user_name, user_cc) in user.items():
                                            if client_socket != user_socket:
                                                user_socket.send(bytes("\n" + client_username + " leave the party", 'utf-8'))
                                    list.remove(dicAux)
                                    self.playersConnected.update(dicAux)
                                    break
                    else:
                        del self.playersConnected[connection]
                    ##Atualiza lobby do players
                    for (user_socket2, user_address2), (user_name2, user_cc2) in self.playersConnected.items():
                        self.lobbyMeny(user_socket2, user_cc2)
                    for party_num, list in self.parties.items():
                        for user in list:
                            for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                                self.lobbyMeny(user_socket2, user_cc2)
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

            #if self.clientDisconnected:
                # stop the server if one of the 4 players gets disconnected
                #break

class Client:
    # ipv4 tcp socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientDisconnect = False

    def sendMsg(self):
        while not self.clientDisconnect:
            try:
                self.clientSocket.send(bytes(input(""), 'utf-8'))
            except:
                self.clientDisconnect = True
                self.clientSocket.close()


    def __init__(self, address):
        self.clientSocket.connect((address, 10001))

        inputThread = threading.Thread(target=self.sendMsg)
        inputThread.daemon = True
        inputThread.start()

        while not self.clientDisconnect:
            try:
                data = self.clientSocket.recv(1024)
                if not data:
                    break
                print(str(data, 'utf-8'))
            except:
                self.clientDisconnect=True
                self.clientSocket.close()


if(len(sys.argv) > 1):
    client = Client(sys.argv[1])
else:
    server = Server()
    server.run()