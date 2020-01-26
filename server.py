import socket
import threading
import json
import time
from citizencard import CitizenCard
import pickle
from cryptography.hazmat.primitives.asymmetric import rsa
from EntityKeyManagement import EntityKeyManagement

class Server:

    serverPrivKey = None
    serverPubKey = None

    # table = {} # key: tableId, value:playersList
    # tableId = 1
    clientDisconnected = False
    # ipv4 tcp socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connections = []
    # players individuais
    playersConnected = {}
    # players em parties
    numberOfParties = 0
    parties = {}
    tables = {}
    decks = {}

    firstPlayer = None
    firstCard = None

    def __init__(self):
        self.serverSocket.bind(('0.0.0.0', 10002))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0

    # writes the lobby
    def sendLobbyMenu(self, userSocket, userCc):
        userSocket.send(bytes("Lobby:\n", 'utf-8'))
        userSocket.send(bytes("SoloPlayers:\n", 'utf-8'))
        for un, ucc in self.playersConnected.values():
            if ucc != userCc:
                userSocket.send(bytes(un + "\n", 'utf-8'))
        userSocket.send(bytes("Parties:\n", 'utf-8'))
        for lst in self.parties.values():
            partyLobby = []
            for elem in lst:
                for (user_socket, user_address), (user_name, user_cc) in elem.items():
                    partyLobby.append(user_name)
            if len(partyLobby) != 0:
                userSocket.send(bytes(str(partyLobby) + "\n", 'utf-8'))
        userSocket.send(bytes("\nInvite a player (using his username)", 'utf-8'))

        # verify if a member is in a party
        if self.verifyPartyMember(userCc):
            userSocket.send(bytes("\nWrite LEAVE to leave the party\n", 'utf-8'))

    def verifyPartyMember(self, userCC):
        verifier = False
        for lst in self.parties.values():
            for elem in lst:
                for (user_name, user_cc) in elem.values():
                    if user_cc == userCC:
                        verifier = True
        return verifier

    def verifyUsernameTaken(self, client_socket):
        validUser = False
        client_username = None
        while not validUser:
            validUser = True
            client_socket.send(bytes("Username: ", 'utf-8'))
            client_username = client_socket.recv(1024).decode()
            for value in self.playersConnected.values():
                if value[0] == client_username:
                    validUser = False
                    break
            if not validUser:
                client_socket.send(bytes("This Username was already taken", 'utf-8'))
        return client_username

    def updateLobbyChanges(self, client_socket, client_username, joined):
        for (user_socket, user_address), (user_name, user_cc) in self.playersConnected.items():
            if user_socket != client_socket:
                if joined:
                    user_socket.send(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'))
                self.sendLobbyMenu(user_socket, user_cc)
        for party_num, lst in self.parties.items():
            for user in lst:
                for (user_socket, user_address), (user_name, user_cc) in user.items():
                    if user_socket != client_socket:
                        if joined:
                            user_socket.send(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'))
                        self.sendLobbyMenu(user_socket, user_cc)

    def lobby(self, client_socket, client_address):
        try:
            # verify if client_username was already taken
            client_username = self.verifyUsernameTaken(client_socket)

            # ask for the citizenCard
            client_socket.send(bytes("CitizenCard Authentication: ", 'utf-8'))
            #s = client_socket.recv(1024)
            #ckey = pickle.loads(s)
            cc = client_socket.recv(1024).decode()
            connection = (client_socket, client_address)
            # Add to the soloplayers
            dicAux = {connection: (client_username, cc)}
            self.playersConnected.update({connection: (client_username, cc)})

            # Sending information to other players about the join
            self.updateLobbyChanges(client_socket, client_username, True)

        except:
            print("player disconnected")
            client_socket.close()
            self.clientDisconnected = True
            raise

        # flag de ajuda com os invites
        invitationFlag = False

        while True:
            try:
                # Caso a ultima mensagem enviada seja "ignore"
                if not invitationFlag:
                    self.sendLobbyMenu(client_socket, cc)
                invitationFlag = False
                invitation = client_socket.recv(1024).decode()

                # Se o invite for para ele proprio
                if (invitation == client_username):
                    client_socket.send(bytes("You can't invite your self", 'utf-8'))
                else:
                    checker = False
                    for (user_socket, user_address), (user_name, user_cc) in self.playersConnected.items():
                        if user_name == invitation:
                            resp = ""
                            while resp != "y" and resp != "n":
                                # Envia convite para o player
                                user_socket.send(
                                    bytes("Do you want to play with " + client_username + "?[y/n]", "utf-8"))
                                resp = user_socket.recv(1024).decode()
                                # Player aceita convite
                                if resp == "y":
                                    client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                    auxList = [party_num for party_num, lst in self.parties.items() if dicAux in lst]
                                    # Se o client ainda não estiver numa party
                                    if len(auxList) == 0:
                                        self.parties.update({self.numberOfParties + 1: [
                                            {(user_socket, user_address): (user_name, user_cc)}, dicAux]})
                                        self.numberOfParties += 1
                                    # Se o client já estiver numa party
                                    else:
                                        self.parties[auxList[0]].append(
                                            {(user_socket, user_address): (user_name, user_cc)})
                                    checker = True
                                    # Delete the invited player from the player's list
                                    del self.playersConnected[(user_socket, user_address)]
                                    # Remover da lista de player que nao estão em party o client
                                    # (Se não estiver numa party)
                                    if connection in self.playersConnected:
                                        del self.playersConnected[connection]
                                    # Update players lobby
                                    self.updateLobbyChanges(client_socket, client_username, False)
                                # Player recusa convite
                                elif resp == "n":
                                    client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                            break
                    # Se o player convidado já estiver numa party
                    if not checker:
                        for party_number, lst in self.parties.items():
                            for user in lst:
                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                    if user_name == invitation:
                                        # Se o player convida um player que já esteja numa party
                                        if self.verifyPartyMember(cc):
                                            checker = True
                                            client_socket.send(
                                                bytes("You'te already in a party, you can't join another", "utf-8"))
                                            break
                                        checker = True
                                        resp = ""
                                        while resp != "y" and resp != "n":
                                            user_socket.send(
                                                bytes("Do you want to play with " + client_username + "?[y/n]",
                                                      "utf-8"))
                                            resp = user_socket.recv(1024).decode()
                                            # Player accepts the invite
                                            if resp == "y":
                                                client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                                # Delete player from solo players
                                                del self.playersConnected[connection]
                                                # Add player to party
                                                self.parties[party_number].append(dicAux)
                                                # Update players lobby
                                                self.updateLobbyChanges(client_socket, client_username, False)
                                            # Player denies the invite
                                            elif resp == "n":
                                                checker = True
                                                client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                    # Se o player convidade não estiver no lobby, nem numa party
                    # OU ser o utilizador quiser sair da party
                    if not checker:
                        if invitation == "LEAVE":
                            # Se o player nao estiver numa party
                            if not self.verifyPartyMember(cc):
                                client_socket.send(bytes("You're not in a party", 'utf-8'))
                            else:
                                for party_num, lst in self.parties.items():
                                    if dicAux in lst:
                                        # Se a party for de tamanho 2
                                        if len(lst) == 2:
                                            for user in lst:
                                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                    if client_socket != user_socket:
                                                        # Enviar informaçao para o outro membro da party
                                                        user_socket.send(bytes(
                                                            "\n" + client_username + " leave the party, party was deleted\n",
                                                            'utf-8'))
                                                    # Adicionar players da party aos soloplayer
                                                    self.playersConnected.update(
                                                        {(user_socket, user_address): (user_name, user_cc)})
                                            client_socket.send(bytes("You left the party", 'utf-8'))
                                            # Delete party
                                            del self.parties[party_num]
                                            break
                                        else:
                                            for user in lst:
                                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                    if client_socket != user_socket:
                                                        # Enviar informaçao que um membro saiu da party
                                                        user_socket.send(
                                                            bytes("\n" + client_username + " leave the party", 'utf-8'))
                                            # Remover player da party
                                            lst.remove(dicAux)
                                            client_socket.send(bytes("You left the party", 'utf-8'))
                                            # Adicionar player à party
                                            self.playersConnected.update(dicAux)
                                            break
                                # Atualiza lobby do players
                                for (user_socket2, user_address2), (
                                        user_name2, user_cc2) in self.playersConnected.items():
                                    if user_socket2 != client_socket:
                                        self.sendLobbyMenu(user_socket2, user_cc2)
                                    for party_num, lst in self.parties.items():
                                        for user in lst:
                                            for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                                                if user_socket2 != client_socket:
                                                    self.sendLobbyMenu(user_socket2, user_cc2)
                        # Ignorar mensagem (resolver problema do duplo convite)
                        elif invitation == "ignore":
                            invitationFlag = True
                        elif invitation == "startgame":
                            break
                        else:
                            client_socket.send(bytes("\nThat players doesn't exist\n", 'utf-8'))
                    # VERIFICAR SE PARTY = 4
                    party44 = False
                    for party_num, lst in self.parties.items():
                        if len(lst) == 4:
                            for user in lst:
                                for (user_socket, user_address), (user_name, user_cc) in user.items():
                                    if user_socket == client_socket:
                                        party44 = True
                                    else:
                                        user_socket.send(bytes("\nNEW TABLE\n", 'utf-8'))
                        if party44:
                            break
                    if party44:
                        client_socket.send(bytes("\nNEW TABLE\n", 'utf-8'))
                        invitationFlag = True
                        self.tables.update({party_num: self.parties[party_num]})
                        # the program is able to exit regardless of if there's any threads still running

                        diamonds = 'diamonds'
                        spades = 'spades'
                        hearts = 'hearts'
                        clubs = 'clubs'
                        self.decks.update({party_num: [(i, diamonds) for i in range(2, 15)]
                                                      + [(i, spades) for i in range(2, 15)]
                                                      + [(i, hearts) for i in range(2, 15)]
                                                      + [(i, clubs) for i in range(2, 15)]})
                        connectionThread = threading.Thread(target=self.gameStart, args=[party_num])
                        connectionThread.daemon = True
                        connectionThread.start()
                        del self.parties[party_num]
            except:
                # Remover player do lobby
                print("player disconnected")
                # self.connections.remove(client_socket)
                # Se o player estiver numa party
                if self.verifyPartyMember(cc):
                    for party_num, lst in self.parties.items():
                        if dicAux in lst:
                            # Se a party for de 2
                            if len(lst) == 2:
                                for user in lst:
                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                        if client_socket != user_socket:
                                            user_socket.send(
                                                bytes("\n" + client_username + " leave the party, party was deleted\n",
                                                      'utf-8'))
                                        self.playersConnected.update(
                                            {(user_socket, user_address): (user_name, user_cc)})
                                del self.parties[party_num]
                                break
                            # Se a party for maior que 2
                            else:
                                for user in lst:
                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                        if client_socket != user_socket:
                                            user_socket.send(
                                                bytes("\n" + client_username + " leave the party", 'utf-8'))
                                lst.remove(dicAux)
                                self.playersConnected.update(dicAux)
                                break
                else:
                    # Retirar player dos solo players
                    del self.playersConnected[connection]
                # Atualiza lobby do players
                for (user_socket2, user_address2), (user_name2, user_cc2) in self.playersConnected.items():
                    self.sendLobbyMenu(user_socket2, user_cc2)
                for party_num, lst in self.parties.items():
                    for user in lst:
                        for (user_socket2, user_address2), (user_name2, user_cc2) in user.items():
                            self.sendLobbyMenu(user_socket2, user_cc2)
                client_socket.close()
                self.clientDisconnected = True
                break

    def arrangeTable(self, numTable):
        newOrder = []
        for table_num, lst in self.tables.items():
            if table_num == numTable:
                for user in lst:
                    for (user_socket, user_address) in user.keys():
                        if user_socket == self.firstPlayer:
                            newOrder.append(user)
                        elif user_socket != self.firstPlayer and len(newOrder) != 0:
                            newOrder.append(user)
        for table_num, lst in self.tables.items():
            if table_num == numTable:
                for user in lst:
                    if user not in newOrder:
                        newOrder.append(user)
        self.tables[numTable] = newOrder

    def gameStart(self, numTable):
        while True:
            # Wait for all the messages to be sent
            time.sleep(1)


            #open listens
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes(str("newlisten" + str(user_address)).encode()))

            #SEND client socket to each player
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address) in user.keys():
                            for user2 in lst:
                                for (user_socket2, user_address2) in user2.keys():
                                    if user_socket != user_socket2:
                                        time.sleep(0.2)
                                        user_socket2.send(bytes(str("playersock"+str(user_address)).encode()))
                                        time.sleep(0.4)
                                        user_socket.send(bytes("acceptNewConnection", 'utf-8'))
                                        time.sleep(0.1)



            # Send to each player the deck. The player will shuffle it and send it back
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nSHUFFLE\n", 'utf-8'))
                            data = json.dumps({"deckShuffle": self.decks[table_num]})
                            user_socket.send(data.encode())
                            dataJson = user_socket.recv(1024)
                            objectJson = json.loads(dataJson.decode())
                            dataShuffled = objectJson['deckShuffled']
                            self.decks[table_num] = dataShuffled
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nCARD DISTRIBUTION\n", 'utf-8'))
            print(self.decks[numTable])
            # All players have shuffled it
            # Send for each player. Each player can choose a card, shuffle again or switch a card
            while not all(card == self.decks[numTable][0] for card in self.decks[numTable]):
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address) in user.keys():
                                if not all(card == self.decks[table_num][0] for card in self.decks[table_num]):
                                    data = json.dumps({"deckEBT": self.decks[table_num]})
                                    user_socket.send(data.encode())
                                    dataJson = user_socket.recv(1024)
                                    objectJson = json.loads(dataJson.decode())
                                    dataAfterEBT = objectJson['deckAfterEBT']
                                    self.decks[table_num] = dataAfterEBT
            # Show hands
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nHAND:", 'utf-8'))
                            user_socket.send(bytes("\nPlayer who has the 2 clubs starts playing", 'utf-8'))
                            connectionThread = threading.Thread(target=self.firstPlay,
                                                                args=(user_socket, user_address, numTable))
                            connectionThread.daemon = True
                            connectionThread.start()
            # While no one plays, nothing happens
            while self.firstPlayer is None:
                pass
            # Arrange plays order
            self.arrangeTable(numTable)
            round_ = 1
            graveyardCards = []
            while round_ <= 13:
                time.sleep(1)
                roundCards = []
                # Play of each player
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if round_ == 1:
                                    if user_socket != self.firstPlayer:
                                        user_socket.send(bytes("Your Turn", 'utf-8'))
                                        card = user_socket.recv(1024).decode()
                                        while not self.validCard(card):
                                            user_socket.send(bytes("That is not a card", 'utf-8'))
                                            card = user_socket.recv(1024).decode()
                                        roundCards.append(card)
                                        graveyardCards.append((user_socket, card))
                                        # Send the played card to the rest of the players
                                        for table_num2, list2 in self.tables.items():
                                            if table_num2 == numTable:
                                                for user2 in list2:
                                                    for (user_socket2, user_address2) in user2.keys():
                                                        if user_socket != user_socket2:
                                                            user_socket2.send(bytes(user_name + ": " + card, 'utf-8'))
                                    else:
                                        roundCards.append(self.firstCard)
                                        graveyardCards.append((self.firstPlayer, self.firstCard))
                                else:
                                    user_socket.send(bytes("Your Turn", 'utf-8'))
                                    card = user_socket.recv(1024).decode()
                                    while not self.validCard(card):
                                        user_socket.send(bytes("That is not a card", 'utf-8'))
                                        card = user_socket.recv(1024).decode()
                                    roundCards.append(card)
                                    graveyardCards.append((user_socket, card))
                                    for table_num2, list2 in self.tables.items():
                                        if table_num2 == numTable:
                                            for user2 in list2:
                                                for (user_socket2, user_address2) in user2.keys():
                                                    if user_socket != user_socket2:
                                                        user_socket2.send(bytes(user_name + ": " + card, 'utf-8'))
                # See who won the round
                winner = self.roundWinner(roundCards)
                graveyard = 0
                username = ""
                # Round points
                for card in roundCards:
                    if "hearts" in card:
                        graveyard += 1
                    elif "Q spades" in card:
                        graveyard += 13
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for (user_socket, user_address), (user_name, user_cc) in lst[winner].items():
                            user_socket.send(bytes("You won the round", 'utf-8'))
                            time.sleep(0.1)
                            user_socket.send(bytes("\nHAND:", 'utf-8'))
                            time.sleep(0.1)
                            user_socket.send(bytes("Graveyard " + str(graveyard), 'utf-8'))
                            self.firstPlayer = user_socket
                            username = user_name
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address) in user.keys():
                                if user_socket != self.firstPlayer:
                                    user_socket.send(bytes(username + " won the round", 'utf-8'))
                                    time.sleep(0.1)
                                    user_socket.send(bytes("\nHAND:", 'utf-8'))
                self.arrangeTable(numTable)
                round_ += 1
            # End of game
            score = []
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("End of the game", 'utf-8'))
                            points = int(user_socket.recv(1024).decode())
                            score.append([user_socket, points])
            # Verify if any player has 26 points
            maxPoints = False
            for points in score:
                if 26 == points[1]:
                    maxPoints = True
            for points in score:
                if maxPoints:
                    if 26 == points[1]:
                        points[1] = 0
                    else:
                        points[1] = 26
                points[0].send(bytes("You scored " + str(points[1]) + " points", 'utf-8'))
            # Deck reset
            del self.decks[numTable]
            diamonds = 'diamonds'
            spades = 'spades'
            hearts = 'hearts'
            clubs = 'clubs'
            self.decks.update({numTable: [(i, diamonds) for i in range(2, 15)] + [(i, spades) for i in range(2, 15)]
                                         + [(i, hearts) for i in range(2, 15)] + [(i, clubs) for i in range(2, 15)]})

    def whichRank(self, card):
        court_n_ace = ["J", "Q", "K", "A"]
        if card[0] == court_n_ace[0]:
            card[0] = 11
        elif card[0] == court_n_ace[1]:
            card[0] = 12
        elif card[0] == court_n_ace[2]:
            card[0] = 13
        elif card[0] == court_n_ace[3]:
            card[0] = 14
        card[0] = int(card[0])
        return card

    def roundWinner(self, roundCards):
        biggerCard = roundCards[0].split(" ")
        index = 0
        biggerCard = self.whichRank(biggerCard)
        i = 0
        for card in roundCards[1:]:
            i += 1
            card = card.split(" ")
            if biggerCard[1] == card[1]:
                card = self.whichRank(card)
                if (biggerCard[0] < card[0]):
                    index = i
                    biggerCard = card
        return index

    def validCard(self, card):
        deck = []
        court_n_ace = ["J", "Q", "K", "A"]
        for i in range(2, 11):
            deck.append(str(i) + " diamonds")
            deck.append(str(i) + " clubs")
            deck.append(str(i) + " spades")
            deck.append(str(i) + " hearts")
        for figure in court_n_ace:
            deck.append(figure + " diamonds")
            deck.append(figure + " clubs")
            deck.append(figure + " spades")
            deck.append(figure + " hearts")
        if card in deck:
            return True
        else:
            return False

    def firstPlay(self, client_socket, client_address, numTable):
        card = client_socket.recv(1024).decode()
        if card != "alreadyplayed":
            username = ""
            while not self.validCard(card):
                if card == "alreadyplayed":
                    break
                client_socket.send(bytes("That is not a card", 'utf-8'))
                card = client_socket.recv(1024).decode()
            if card != "alreadyplayed":
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if client_socket == user_socket:
                                    username = user_name
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if user_socket != client_socket:
                                    user_socket.send(bytes(username + " started the round", 'utf-8'))
                                    user_socket.send(bytes(username + ": " + card, 'utf-8'))
                self.firstCard = card
                self.firstPlayer = client_socket

    def handler(self, client_socket, client_address):
        self.lobby(client_socket, client_address)

    def run(self):
        self.createServerKeys()

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

            # if self.clientDisconnected:
            # stop the server if one of the 4 players gets disconnected
            # break


    def createServerKeys(self):
        keyManagement = EntityKeyManagement(4096)
        keyManagement.generateKey()
        self.serverPrivKey = keyManagement.getPrivKey()
        self.serverPubKey = keyManagement.getPubKey()

