import socket
import threading
import sys


class Server:
    # table = {} # key: tableId, value:playersList
    # tableId = 1
    party = 0
    newUserConnected = False
    clientDisconnected = False
    # individual players
    soloPlayersConnected = {}  # key: (client_socket, client_address), value: [username, cc, party]
    # ipv4 tcp socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ccs = []
    connections = []
    # players in parties
    numberOfParties = 0
    parties = {}  # key: party_number, value: list of dictionaries of players in parties

    def __init__(self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0

    def playerReady(self, user_socket):
        user_socket.send(bytes("Menu:\n[R] Rules\n[S] Skip Rules\n", 'utf-8'))
        while True:
            resp = user_socket.recv(1024).decode()
            if resp == "R":
                self.rulesMenu(user_socket)
                break
            elif resp != "S":
                break
            else:
                user_socket.send(bytes("Invalid choice. Try again.\n", 'utf-8'))
        return True

    # TODO : Add Rules
    def rulesMenu(self, user_socket):
        user_socket.send(bytes("Rules:\nThis needs development.\n", 'utf-8'))
        user_socket.send(bytes("[Ok]", 'utf-8'))
        while True:
            if user_socket.recv(1024).decode().upper() == "OK":
                break
            user_socket.send(bytes("Invalid choice. Try again.\n", 'utf-8'))

    def showSoloPlayers(self, user_socket, user_cc):
        print_title = True
        for un, ucc in self.soloPlayersConnected.values():
            if ucc != user_cc:
                if print_title:
                    user_socket.send(bytes("Solo players:\n", 'utf-8'))
                    print_title = False
                user_socket.send(bytes(un + "\n", 'utf-8'))

    def showParties(self, user_socket, user_cc):
        in_party = False
        print_title = True
        for party_list in self.parties.values():
            party_lobby = []
            for user in party_list:
                for (_, _), (u_name, u_cc) in user.items():
                    if user_cc == u_cc:
                        in_party = True
                    party_lobby.append(u_name)
            if len(party_lobby) != 0:
                if print_title:
                    user_socket.send(bytes("Parties:\n", 'utf-8'))
                    print_title = False
                user_socket.send(bytes(str(party_lobby) + "\n", 'utf-8'))
        return in_party

    def lobbyMenu(self, user_socket, user_cc):
        user_socket.send(bytes("Lobby:\n", 'utf-8'))

        self.showSoloPlayers(user_socket, user_cc)

        in_party = self.showParties(user_socket, user_cc)

        if in_party:
            user_socket.send(bytes("\nInvite a player (using its username) to your party", 'utf-8'))
            # verify if a member is in a party
            # if self.verifyPartyMember(userCc):
            user_socket.send(bytes("\nWrite LEAVE if you want to leave the party\n", 'utf-8'))
        else:
            user_socket.send(bytes("\nRequest to join with someone (using its username). If you want to join a party, "
                                   "use the username of someone belonging to the party\n", 'utf-8'))

    def verifyPartyMember(self, user_cc):
        for party_list in self.parties.values():
            for user in party_list:
                for (u_name, u_cc) in user.values():
                    if u_cc == user_cc:
                        return True
        return False

    def setUsername(self, client_socket):
        # client_username taken verification
        valid_user = False
        client_username = None
        while not valid_user:
            valid_user = True
            client_socket.send(bytes("Username: ", 'utf-8'))
            client_username = client_socket.recv(1024).decode()
            for user_name, user_cc in self.soloPlayersConnected.values():
                if user_name == client_username:
                    valid_user = False
                    break
            if not valid_user:
                client_socket.send(bytes("This Username was already taken", 'utf-8'))
        return client_username

    def setUser(self, client_socket, client_address):
        connection = (client_socket, client_address)
        # get username
        client_username = self.setUsername(client_socket)
        # get cc
        client_socket.send(bytes("CC: ", 'utf-8'))
        cc = client_socket.recv(1024).decode()
        # add user
        self.soloPlayersConnected.update({connection: (client_username, cc)})

        return [connection, client_username, cc]

    def handler(self, client_socket, client_address):
        cc, connection, client_username, client_info = None, None, None, None
        try:
            if self.playerReady(client_socket):
                connection, client_username, cc = self.setUser(client_socket, client_address)

                client_info = {connection: (client_username, cc)}

                # Sending information to other players about the join
                for (user_socket, user_address), (user_name, user_cc) in self.soloPlayersConnected.items():
                    if user_socket != client_socket:
                        user_socket.send(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'))
                        # Writes the lobby menu
                        self.lobbyMenu(user_socket, user_cc)

                for party_num, users_list in self.parties.items():
                    for user in users_list:
                        for (user_socket, user_address), (user_name, user_cc) in user.items():
                            if user_socket != client_socket:
                                user_socket.send(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'))
                                self.lobbyMenu(user_socket, user_cc)
        except:
            print("player disconnected")
            client_socket.close()
            self.clientDisconnected = True

        while True:
            try:
                self.lobbyMenu(client_socket, cc)
                invitation = client_socket.recv(1024).decode()

                if invitation == client_username:
                    client_socket.send(bytes("You can't invite yourself"))
                else:
                    checker = False
                    for (user_socket, user_address), (user_name, user_cc) in self.soloPlayersConnected.items():
                        if user_name == invitation:
                            resp = ""
                            while resp != "y" and resp != "n":
                                # Send invite to the player
                                user_socket.send(bytes("Do you want to play with " + client_username +
                                                       "?[y/n]", "utf-8"))
                                resp = user_socket.recv(1024).decode()
                                # TODO: RESOLVE PROBLEM OF 2 RECV()
                                # Player accepts the invite
                                if resp == "y":
                                    client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                    aux_list = [party_num for party_num, user_list in self.parties.items()
                                                if client_info in user_list]
                                    # If the client isn't in a party yet
                                    if len(aux_list) == 0:
                                        self.parties.update({self.numberOfParties + 1: [{(user_socket, user_address):
                                                                                             (user_name, user_cc)},
                                                                                        client_info]})
                                        self.numberOfParties += 1
                                    # If the client is already in a party
                                    else:
                                        self.parties[aux_list[0]].append({(user_socket, user_address):
                                                                             (user_name, user_cc)})
                                    checker = True
                                    # Remover da lista de players que não estão em party o player convidado
                                    del self.soloPlayersConnected[(user_socket, user_address)]
                                    # Remover da lista de player que nao estão em party o client
                                    # (Se não estiver numa party)
                                    if connection in self.soloPlayersConnected:
                                        del self.soloPlayersConnected[connection]
                                    # Atualiza lobby do players
                                    for (user_socket2, user_address2), (user_name2, user_cc2) in \
                                            self.soloPlayersConnected.items():
                                        if user_socket2 != client_socket:
                                            self.lobbyMenu(user_socket2, user_cc2)
                                    for party_num, users_list in self.parties.items():
                                        for user in users_list:
                                            for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                                                if user_socket2 != client_socket:
                                                    self.lobbyMenu(user_socket2, user_cc2)
                                # Player refuses the invite
                                elif resp == "n":
                                    client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                            break

                    # If the player is already in a party
                    if not checker:
                        for party_number, users_list in self.parties.items():
                            for user in users_list:
                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                    if user_name == invitation:
                                        if self.verifyPartyMember(cc):
                                            client_socket.send(bytes("You'te already in a party, you can't join "
                                                                     "another", "utf-8"))
                                            break
                                        checker = True
                                        resp = ""
                                        while resp != "y" and resp != "n":
                                            user_socket.send(bytes("Do you want to play with " + client_username +
                                                                   "?[y/n]", "utf-8"))
                                            resp = user_socket.recv(1024).decode()
                                            if resp == "y":
                                                client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                                del self.soloPlayersConnected[connection]
                                                self.parties[party_number].append(client_info)
                                                # Atualiza lobby do players
                                                for (user_socket2, user_address2), (user_name2, user_cc2) in \
                                                        self.soloPlayersConnected.items():
                                                    if user_socket2 != client_socket:
                                                        self.lobbyMenu(user_socket2, user_cc2)
                                                for party_num, u_list in self.parties.items():
                                                    for user in u_list:
                                                        for (user_socket2, user_address2), (user_name2, user_cc2) in \
                                                                user.items():
                                                            if user_socket2 != client_socket:
                                                                self.lobbyMenu(user_socket2, user_cc2)
                                            elif resp == "n":
                                                client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                                if self.verifyPartyMember(cc):
                                    break
                        if self.verifyPartyMember(cc):
                            break

                    # Se o player convidade não estiver no lobby, nem numa party
                    # OU ser o utilizador quiser sair da party
                    if not checker:
                        if invitation == "LEAVE":
                            if not self.verifyPartyMember(cc):
                                client_socket.send(bytes("You're not in a party", 'utf-8'))
                            else:
                                for party_num, users_list in self.parties.items():
                                    if client_info in users_list:
                                        if len(users_list) == 2:
                                            for user in users_list:
                                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                    if client_socket != user_socket:
                                                        user_socket.send(bytes("\n" + client_username + " left the "
                                                                                "party, party was deleted\n", 'utf-8'))
                                                    self.soloPlayersConnected.update({(user_socket, user_address):
                                                                                          (user_name, user_cc)})
                                            client_socket.send(bytes("You left the party", 'utf-8'))
                                            del self.parties[party_num]
                                            break
                                        else:
                                            for user in users_list:
                                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                    if client_socket != user_socket:
                                                        user_socket.send(bytes("\n" + client_username + " left the "
                                                                                                        "party",
                                                                               'utf-8'))
                                            users_list.remove(client_info)
                                            client_socket.send(bytes("You left the party", 'utf-8'))
                                            self.soloPlayersConnected.update(client_info)
                                            break
                                # Updates the players lobby
                                for (user_socket2, user_address2), (user_name2, user_cc2) in \
                                        self.soloPlayersConnected.items():
                                    if user_socket2 != client_socket:
                                        self.lobbyMenu(user_socket2, user_cc2)
                                    for party_num, users_list in self.parties.items():
                                        for user in users_list:
                                            for (user_socket22, user_address22), (user_name22, user_cc22) in user.items():
                                                if user_socket22 != client_socket:
                                                    self.lobbyMenu(user_socket22, user_cc22)
                        else:
                            client_socket.send(bytes("\nThat players doesn't exist\n", 'utf-8'))

                    # verify if PARTY = 4
                    party44 = False
                    for party_num, users_list in self.parties.items():
                        for user in users_list:
                            for (user_socket, user_address), (_, _) in user.items():
                                if user_socket == client_socket and len(users_list) == 4:
                                    party44 = True
                                    break
                            if party44:
                                break
                        if party44:
                            break
                    if party44:
                        client_socket.send(bytes("CREATE TABLE", 'utf-8'))
                        break
            except:
                print("player disconnected")
                # self.connections.remove(client_socket)
                if self.verifyPartyMember(cc):
                    for party_num, users_list in self.parties.items():
                        if client_info in users_list:
                            if len(users_list) == 2:
                                for user in users_list:
                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                        if client_socket != user_socket:
                                            user_socket.send(bytes("\n" + client_username + " leave the party, "
                                                                                            "party was deleted\n",
                                                                   'utf-8'))
                                        self.soloPlayersConnected.update({(user_socket, user_address):
                                                                              (user_name, user_cc)})
                                del self.parties[party_num]
                                break
                            else:
                                for user in users_list:
                                    for (user_socket, user_address), (_, _) in user.items():
                                        if client_socket != user_socket:
                                            user_socket.send(bytes("\n" + client_username + " leave the party",
                                                                   'utf-8'))
                                users_list.remove(client_info)
                                self.soloPlayersConnected.update(client_info)
                                break
                else:
                    del self.soloPlayersConnected[connection]
                # Updates the lobby
                for (user_socket2, user_address2), (user_name2, user_cc2) in self.soloPlayersConnected.items():
                    self.lobbyMenu(user_socket2, user_cc2)
                for party_num, users_list in self.parties.items():
                    for user in users_list:
                        for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                            self.lobbyMenu(user_socket2, user_cc2)
                client_socket.close()
                self.clientDisconnected = True
                break

    def run(self):
        while True:
            # establish the connection to the client wanting to connect
            client_socket, client_address = self.serverSocket.accept()
            self.numberOfClients += 1

            # create a new thread
            connection_thread = threading.Thread(target=self.handler, args=(client_socket, client_address))
            # the program is able to exit regardless of if there's any threads still running
            connection_thread.daemon = True
            connection_thread.start()

            self.connections.append(client_socket)
            print(str(client_address[0]) + ':' + str(client_address[1]), "connected")

            # if self.clientDisconnected:
            # stop the server if one of the 4 players gets disconnected
            # break


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

        input_thread = threading.Thread(target=self.sendMsg)
        input_thread.daemon = True
        input_thread.start()

        while not self.clientDisconnect:
            try:
                data = self.clientSocket.recv(1024)
                if not data:
                    break
                print(str(data, 'utf-8'))
            except:
                self.clientDisconnect = True
                self.clientSocket.close()


if len(sys.argv) > 1:
    client = Client(sys.argv[1])
else:
    server = Server()
    server.run()
