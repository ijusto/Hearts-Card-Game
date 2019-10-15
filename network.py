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
    soloPlayersConnected = {}  # key: (client_socket, client_address), value: (username, cc)
    # ipv4 tcp socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    parties = {}  # key: party_number, value: list of dictionaries of players in parties

    ccs = []
    connections = []
    # players in parties
    numberOfParties = 0

    def __init__(self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0

    def playerReady(self, user_socket):
        user_socket.send(bytes("Menu:\n[R] Rules\n[S] Skip Rules\n", 'utf-8'))
        while True:
            resp = user_socket.recv(1024).decode().upper()
            if resp == "R":
                self.rulesMenu(user_socket)
                break
            elif resp == "S":
                break
            else:
                user_socket.send(bytes("Invalid choice 4. Try again.\n", 'utf-8'))
        return True

    def rulesMenu(self, user_socket):
        rules = "Card rank (highest first):	A K Q J 10 9 8 7 6 5 4 3 2, no trump\n" \
                "Played Clockwise.\n" \
                "The overall objective is to be the player with the fewest points by the end of the game.\n" \
                "13 cards are dealt to each player (4 players)\n" \
                "Before each hand begins, each player chooses three cards, and passes them to another player.\n" \
                "It rotates passing through four deals; on the first deal, players pass to the left, the second deal " \
                "to the right, the third across the table.\nOn the fourth deal no cards are passed; the cycle of four " \
                "deals is then repeated.\n" \
                "Players must follow suit;\n" \
                "If they are not able to do so, they can play any card\n" \
                "The player holding the 2 of clubs must lead it to begin the first trick\n" \
                "No penalty card may be played on the first trick (hearts or Queen of spades)\n" \
                "Hearts cannot be led until they have been \"broken\" (discarded on the lead of another suit), unless" \
                " the player who must lead has nothing but Hearts remaining in hand.\n" \
                "Each Heart taken in a trick scores one penalty point against the player winning the trick, and " \
                "taking Queen of spades costs 13 penalty points. There are thus 26 penalty points in each deal.\n" \
                "The game usually ends when one player reaches or exceeds 100 points.\nIf one player takes all the " \
                "penalty cards on one deal, that player's score remains unchanged while 26 penalty points are added " \
                "to the scores of each of the other players.\n"
        user_socket.send(bytes(f"Rules:\n{rules}[Ok]\n", 'utf-8'))
        while True:
            if user_socket.recv(1024).decode().upper() == "OK":
                break
            user_socket.send(bytes("Invalid choice 5. Try again.\n", 'utf-8'))

    def showSoloPlayers(self, user_socket, user_cc):
        print_title = True
        for un, ucc in self.soloPlayersConnected.values():
            if ucc != user_cc:
                if print_title:
                    user_socket.send(bytes("Solo players:\n", 'utf-8'))
                    print_title = False
                user_socket.send(bytes(un + "\n", 'utf-8'))

    def showParties(self, user_socket, user_cc, show):
        in_party = False
        print_title = True
        curr_user_party = []
        p_number = None
        for party_number, party_list in self.parties.items():
            party_lobby = []
            for user in party_list:
                for (u_socket, _), (u_name, u_cc) in user.items():
                    if user_cc == u_cc:
                        in_party = True
                        curr_user_party = party_list
                        p_number = party_number
                    party_lobby.append(u_name)
            if len(party_lobby) != 0:
                if show:
                    if print_title:
                        user_socket.send(bytes("Parties:\n", 'utf-8'))
                        print_title = False
                    user_socket.send(bytes(str(party_lobby) + "\n", 'utf-8'))
        return in_party, curr_user_party, p_number

    def updateAllLobbyMenu(self, new_client_socket, new_client_username):
        for (u_socket, u_add), (u_name, u_cc) in self.soloPlayersConnected.items():
            if new_client_socket != u_socket and new_client_socket is not None:
                u_socket.send(bytes(new_client_username + " joined the lobby\n", 'utf-8'))
            u_socket.send(bytes("Lobby:\n", 'utf-8'))
            self.showSoloPlayers(u_socket, u_cc)
            _, _, _ = self.showParties(u_socket, u_cc, True)

        for party_number, party_list in self.parties.items():
            for user in party_list:
                for (u_socket, u_add), (u_name, u_cc) in user.items():
                    if new_client_socket != u_socket and new_client_socket is not None:
                        u_socket.send(bytes(new_client_username + " joined the lobby\n", 'utf-8'))
                    u_socket.send(bytes("Lobby:\n", 'utf-8'))
                    self.showSoloPlayers(u_socket, u_cc)
                    _, _, _ = self.showParties(u_socket, u_cc, True)

    def lobbyOptions(self, curr_user_info):
        (curr_user_socket, curr_user_address), (curr_user_name, curr_user_cc) = curr_user_info
        curr_user_dict = {(curr_user_socket, curr_user_address): (curr_user_name, curr_user_cc)}



        # player in party
        while self.showParties(curr_user_socket, curr_user_cc, False)[0]:
            in_party, curr_user_party, p_number = self.showParties(curr_user_socket, curr_user_cc, False)
            curr_user_socket.send(bytes("[username] Invite a player to your party (you can only invite solo "
                                        "players)\n", 'utf-8'))
            curr_user_socket.send(bytes("[LEAVE] Leave party\n", 'utf-8'))

            resp = curr_user_socket.recv(1024).decode().upper()
            # if the player wants to leave the party
            if resp == "LEAVE":
                if curr_user_dict in curr_user_party:
                    # party must be deleted and players be status changed to solo players
                    if len(curr_user_party) == 2:
                        for user in curr_user_party:
                            for (u_socket, u_address), (u_name, u_cc) in user.items():
                                if curr_user_socket != u_socket:
                                    u_socket.send(bytes(curr_user_name + " left the party, the party "
                                                                                  "was deleted\n", 'utf-8'))
                                    self.soloPlayersConnected.update({(u_socket, u_address): (u_name, u_cc)})
                                    break
                        self.soloPlayersConnected.update(curr_user_dict)
                        curr_user_socket.send(bytes("You left the party\n", 'utf-8'))
                        del self.parties[p_number]

                    # party still exists
                    else:
                        for user in curr_user_party:
                            for (u_socket, u_address), (_, _) in user.items():
                                if curr_user_socket != u_socket:
                                    u_socket.send(bytes(curr_user_name + " left the party\n", 'utf-8'))
                        curr_user_party.remove(curr_user_dict)
                        curr_user_socket.send(bytes("You left the party\n", 'utf-8'))
                        self.soloPlayersConnected.update(curr_user_dict)

                    # the player left the party - break while True
                    break

            # if the player wants to invite someone to its party
            elif resp is not None:
                break_while = False
                for (u_sock, u_add), (u_n, u_cc) in self.soloPlayersConnected.items():
                    # the player invited someone who exists - breaks while after everything done
                    if resp == u_n and u_cc != curr_user_cc:
                        u_info = (u_sock, u_add), (u_n, u_cc)
                        if self.sendInvite(curr_user_info, u_info):
                            self.acceptInvite(curr_user_info, u_info, p_number)
                        else:
                            (client_socket, _), (_, _) = curr_user_info
                            client_socket.send(bytes(resp + " refused the invite", 'utf-8'))
                        break_while = True
                        break
                    # the player invited someone who doesnt exists - while continues
                    else:
                        curr_user_socket.send(bytes("Invalid choice 1. Try again.\n", 'utf-8'))
                        break
                if break_while:
                    break

        # player in solo queue
        while not self.showParties(curr_user_socket, curr_user_cc, False)[0]:
            in_party, curr_user_party, p_number = self.showParties(curr_user_socket, curr_user_cc, False)
            curr_user_socket.send(bytes("[username] Request to join someone. If you want to join a party, "
                                        "use the username of someone in the party\n", 'utf-8'))
            resp = curr_user_socket.recv(1024).decode().upper()

            if resp == "IGNORA":
                continue
            elif resp is not None:
                break_while = False
                # requested to join a solo player -> create a party
                for (u_sock, u_add), (u_n, u_cc) in self.soloPlayersConnected.items():
                    if resp == u_n.upper() and resp != curr_user_name.upper():
                        u_info = (u_sock, u_add), (u_n, u_cc)
                        if self.sendInvite(curr_user_info, u_info):
                            p_number = None
                            self.acceptInvite(curr_user_info, u_info, p_number)
                        else:
                            (client_socket, _), (_, _) = curr_user_info
                            client_socket.send(bytes(resp + " refused the invite", 'utf-8'))
                        break_while = True
                        break

                # request to join party
                if not break_while:
                    for party_num, users_list in self.parties.items():
                        for user in users_list:
                            for (u_sock, u_add), (u_n, u_cc) in user.items():
                                if resp == u_n.upper() and u_sock != curr_user_socket:
                                    u_info = (u_sock, u_add), (u_n, u_cc)
                                    if self.sendInvite(curr_user_info, u_info):
                                        self.acceptInvite(curr_user_info, u_info, p_number)
                                    else:
                                        (client_socket, _), (_, _) = curr_user_info
                                        client_socket.send(bytes(resp + " refused the invite", 'utf-8'))
                                    break_while = True
                                    break
                            if break_while:
                                break
                        if break_while:
                            break

                if break_while:
                    break
                # the player invited someone who doesnt exists - while continues
                else:
                    curr_user_socket.send(bytes("Invalid choice 2. Try again.\n", 'utf-8'))

    def sendInvite(self, who_invited_info, who_to_invite_info):
        (_, _), (who_invited_name, who_invited_cc) = who_invited_info
        (who_to_invite_socket, who_to_invite_add), (_, _) = who_to_invite_info
        resp = ""
        while True:
            # Send invite to the player
            who_to_invite_socket.send(bytes("Do you want to play with " + who_invited_name + "?[y/n]", "utf-8"))

            # resp = clients[who_to_invite_info]
            resp = who_to_invite_socket.recv(1024).decode().upper()
            # Player accepts the invite
            if resp == "Y":
                return True
            # Player refuses the invite
            elif resp == "N":
                return False
            else:
                who_to_invite_socket.send(bytes("Invalid choice 3. Try again.\n", 'utf-8'))

                #resp = who_to_invite_socket.recv(1024).decode().upper()
                #clients[who_to_invite_info] = resp

    def acceptInvite(self, who_invited_info, who_to_invite_info, party_number):
        (who_invited_socket, who_invited_add), (who_invited_name, who_invited_cc) = who_invited_info
        (who_to_invite_socket, who_to_invite_add), (who_to_invite_name, who_to_invite_cc) = who_to_invite_info

        who_invited_socket.send(bytes(who_to_invite_name + " accepted the invite", 'utf-8'))

        # accept invite from a player in a party
        if party_number is not None:
            self.parties[party_number].append({(who_to_invite_socket, who_to_invite_add):
                                               (who_to_invite_name, who_to_invite_cc)})

            # Remove the invited player from the list of players not in parties
            del self.soloPlayersConnected[(who_to_invite_socket, who_to_invite_add)]

        # accept invite to join a player in a new party
        else:
            self.numberOfParties += 1
            self.parties.update({self.numberOfParties:
                                     [{(who_to_invite_socket, who_to_invite_add):
                                           (who_to_invite_name, who_to_invite_cc)},
                                      {(who_invited_socket, who_invited_add): (who_invited_name, who_invited_cc)}]})

            # Remove the invited player from the list of players not in parties
            del self.soloPlayersConnected[(who_to_invite_socket, who_to_invite_add)]
            # Remove the player who made the invite from the list of players not in parties
            del self.soloPlayersConnected[(who_invited_socket, who_invited_add)]

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
            if client_username.upper() == "Y" or client_username.upper() == "N" or client_username.upper() == "LEAVE":
                valid_user = False
            if valid_user:
                for user_name, user_cc in self.soloPlayersConnected.values():
                    if user_name == client_username:
                        valid_user = False
                        break
            if not valid_user:
                client_socket.send(bytes("This Username was already taken", 'utf-8'))
        return client_username

    def setUser(self, client_socket, client_address):
        # get username
        client_username = self.setUsername(client_socket)
        # get cc
        client_socket.send(bytes("CC: ", 'utf-8'))
        cc = client_socket.recv(1024).decode()
        # add user
        self.soloPlayersConnected.update({(client_socket, client_address): (client_username, cc)})

        return client_username, cc

    def handler(self, new_client_socket, new_client_address):
        new_client_cc, new_client_username, new_client_info = None, None, None
        try:

            if self.playerReady(new_client_socket):
                new_client_username, new_client_cc = self.setUser(new_client_socket, new_client_address)
                new_client_info = (new_client_socket, new_client_address), (new_client_username, new_client_cc)

                # Sending information to other players about the join
                self.updateAllLobbyMenu(new_client_socket, new_client_username)


        except:
            print("player disconnected")
            new_client_socket.close()
            self.clientDisconnected = True

        while True:
            self.lobbyOptions(new_client_info)
            self.updateAllLobbyMenu(None, None)

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
                if "Do you want to play with " in data.decode('utf-8'):
                    self.clientSocket.send(bytes("IGNORA", 'utf-8'))
                print(str(data, 'utf-8'))
            except:
                self.clientDisconnect = True
                self.clientSocket.close()


if len(sys.argv) > 1:
    client = Client(sys.argv[1])
else:
    server = Server()
    server.run()
