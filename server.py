import socket
import threading
import json
import time
#from citizencard import CitizenCard
import pickle
from cryptography.hazmat.primitives.asymmetric import rsa
from EntityRSAKeyManagement import EntityRSAKeyManagement
import random
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class Server:

    serverPrivKey = None
    serverPubKey = None
    rsaKeyManagement = None

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
    clientsAgreeTable = {}
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
    def sendLobbyMenu(self, userSocket, userName, clientkey):
        userSocket.send(self.cipherMsgToClient(bytes("Lobby:\n", 'utf-8'), clientkey))
        userSocket.send(self.cipherMsgToClient(bytes("SoloPlayers:\n", 'utf-8'), clientkey))
        for un, ucc in self.playersConnected.values():
            if un != userName:
                userSocket.send(self.cipherMsgToClient(bytes(un + "\n", 'utf-8'), clientkey))
        userSocket.send(self.cipherMsgToClient(bytes("Parties:\n", 'utf-8'), clientkey))
        for lst in self.parties.values():
            partyLobby = []
            for elem in lst:
                for (user_socket, user_address), (user_name, user_pubkey) in elem.items():
                    partyLobby.append(user_name)
            if len(partyLobby) != 0:
                userSocket.send(self.cipherMsgToClient(bytes(str(partyLobby) + "\n", 'utf-8'), clientkey))
        userSocket.send(self.cipherMsgToClient(bytes("\nInvite a player (using his username)", 'utf-8'), clientkey))

        # verify if a member is in a party
        if self.verifyPartyMember(userName):
            userSocket.send(self.cipherMsgToClient(
                bytes("\nWrite LEAVE to leave the party\n", 'utf-8'), clientkey))

    def verifyPartyMember(self, userName):
        verifier = False
        for lst in self.parties.values():
            for elem in lst:
                for (user_name, user_cc) in elem.values():
                    if user_name == userName:
                        verifier = True
        return verifier

    def verifyUsernameTaken(self, client_socket, clientkey):
        validUser = False
        client_username = None
        while not validUser:
            validUser = True
            client_socket.send(self.cipherMsgToClient(bytes("Username: ", 'utf-8'), clientkey))
            client_username = self.decipherMsgFromClient(client_socket.recv(1024)).decode()
            for value in self.playersConnected.values():
                if value[0] == client_username:
                    validUser = False
                    break
            if not validUser:
                client_socket.send(self.cipherMsgToClient(bytes("This Username was already taken",'utf-8'), clientkey))
        return client_username

    def updateLobbyChanges(self, client_socket, client_username, joined):
        for (user_socket, user_address), (user_name, user_pubkey) in self.playersConnected.items():
            if user_socket != client_socket:
                if joined:
                    user_socket.send(self.cipherMsgToClient(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'), user_pubkey))
                self.sendLobbyMenu(user_socket, user_name, user_pubkey)
        for party_num, lst in self.parties.items():
            for user in lst:
                for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                    if user_socket != client_socket:
                        if joined:
                            user_socket.send(self.cipherMsgToClient(bytes("\n" + client_username + " joined the lobby\n", 'utf-8'), user_pubkey))
                        self.sendLobbyMenu(user_socket, user_name, user_pubkey)

    def lobby(self, client_socket, client_address):
        try:
            pem = self.serverPubKey.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            client_socket.send(bytes("ServerPublicKey:", 'utf-8'))
            time.sleep(0.5)
            client_socket.send(pem)
            validate = 'Verification failed'
            while validate == 'Verification failed':
                # ask for the citizenCard
                pem = self.decipherMsgFromClient(client_socket.recv(1024))
                pemRSA = self.decipherMsgFromClient(client_socket.recv(1024))
                clientkey = serialization.load_pem_public_key(pem, backend=default_backend())
                clientkeyRSA = serialization.load_pem_public_key(pemRSA, backend=default_backend())
                d = self.cipherMsgToClient(bytes("Sign your pubkey", 'utf-8'), clientkeyRSA)
                client_socket.send(d)
                signature = self.decipherMsgFromClient(client_socket.recv(1024))
                validate = self.validateSignature(clientkey, pemRSA, signature)
                client_socket.send(self.cipherMsgToClient(bytes(validate, 'utf-8'), clientkeyRSA))

            # verify if client_username was already taken
            client_username = self.verifyUsernameTaken(client_socket, clientkeyRSA)

            connection = (client_socket, client_address)
            # Add to the soloplayers
            dicAux = {connection: (client_username, clientkeyRSA)}
            self.playersConnected.update({connection: (client_username, clientkeyRSA)})

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
                    self.sendLobbyMenu(client_socket, client_username, clientkeyRSA)
                invitationFlag = False
                invitation = self.decipherMsgFromClient(client_socket.recv(1024)).decode()
                # Se o invite for para ele proprio
                if (invitation == client_username):
                    client_socket.send(self.cipherMsgToClient(bytes("You can't invite your self",'utf-8'), clientkeyRSA))
                else:
                    checker = False
                    for (user_socket, user_address), (user_name, user_pubkey) in self.playersConnected.items():
                        if user_name == invitation:
                            resp = ""
                            while resp != "y" and resp != "n":
                                # Envia convite para o player
                                user_socket.send(self.cipherMsgToClient(bytes("Do you want to play with " + client_username + "?[y/n]", 'utf-8'), user_pubkey))
                                resp = self.decipherMsgFromClient(user_socket.recv(1024)).decode()
                                # Player aceita convite
                                if resp == "y":
                                    client_socket.send(self.cipherMsgToClient(bytes(user_name + " accepted the invite", 'utf-8'), clientkeyRSA))
                                    auxList = [party_num for party_num, lst in self.parties.items() if dicAux in lst]
                                    # Se o client ainda não estiver numa party
                                    if len(auxList) == 0:
                                        self.parties.update({self.numberOfParties + 1: [
                                            {(user_socket, user_address): (user_name, user_pubkey)}, dicAux]})
                                        self.numberOfParties += 1
                                    # Se o client já estiver numa party
                                    else:
                                        self.parties[auxList[0]].append(
                                            {(user_socket, user_address): (user_name, user_pubkey)})
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
                                    client_socket.send(self.cipherMsgToClient(bytes(user_name + " refused the invite", 'utf-8'), clientkeyRSA))
                            break
                    # Se o player convidado já estiver numa party
                    if not checker:
                        for party_number, lst in self.parties.items():
                            for user in lst:
                                for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                    if user_name == invitation:
                                        # Se o player convida um player que já esteja numa party
                                        if self.verifyPartyMember(client_username):
                                            checker = True
                                            client_socket.send(
                                                self.cipherMsgToClient(bytes("You'te already in a party, you can't join another", "utf-8"), clientkeyRSA))
                                            break
                                        checker = True
                                        resp = ""
                                        while resp != "y" and resp != "n":
                                            user_socket.send(self.cipherMsgToClient(
                                                bytes("Do you want to play with " + client_username + "?[y/n]",
                                                      "utf-8"), user_pubkey))
                                            resp = self.decipherMsgFromClient(user_socket.recv(1024)).decode()
                                            # Player accepts the invite
                                            if resp == "y":
                                                client_socket.send(self.cipherMsgToClient(
                                                    bytes(user_name + " accepted the invite", 'utf-8'), clientkeyRSA))
                                                # Delete player from solo players
                                                del self.playersConnected[connection]
                                                # Add player to party
                                                self.parties[party_number].append(dicAux)
                                                # Update players lobby
                                                self.updateLobbyChanges(client_socket, client_username, False)
                                            # Player denies the invite
                                            elif resp == "n":
                                                checker = True
                                                client_socket.send(self.cipherMsgToClient(
                                                    bytes(user_name + " refused the invite", 'utf-8'), clientkeyRSA))
                    # Se o player convidade não estiver no lobby, nem numa party
                    # OU ser o utilizador quiser sair da party
                    if not checker:
                        if invitation == "LEAVE":
                            # Se o player nao estiver numa party
                            if not self.verifyPartyMember(client_username):
                                client_socket.send(self.cipherMsgToClient(
                                    bytes("You're not in a party", 'utf-8'), clientkeyRSA))
                            else:
                                for party_num, lst in self.parties.items():
                                    if dicAux in lst:
                                        # Se a party for de tamanho 2
                                        if len(lst) == 2:
                                            for user in lst:
                                                for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                                    if client_socket != user_socket:
                                                        # Enviar informaçao para o outro membro da party
                                                        user_socket.send(self.cipherMsgToClient(bytes(
                                                            "\n" + client_username + " leave the party, party was deleted\n",
                                                            'utf-8'), user_pubkey))
                                                    # Adicionar players da party aos soloplayer
                                                    self.playersConnected.update(
                                                        {(user_socket, user_address): (user_name, user_pubkey)})
                                            client_socket.send(self.cipherMsgToClient(
                                                bytes("You left the party", 'utf-8'), clientkeyRSA))
                                            # Delete party
                                            del self.parties[party_num]
                                            break
                                        else:
                                            for user in lst:
                                                for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                                    if client_socket != user_socket:
                                                        # Enviar informaçao que um membro saiu da party
                                                        user_socket.send(self.cipherMsgToClient(
                                                            bytes("\n" + client_username + " leave the party", 'utf-8'), user_pubkey))
                                            # Remover player da party
                                            lst.remove(dicAux)
                                            client_socket.send(self.cipherMsgToClient(bytes("You left the party", 'utf-8'), clientkeyRSA))
                                            # Adicionar player à party
                                            self.playersConnected.update(dicAux)
                                            break
                                # Atualiza lobby do players
                                for (user_socket2, user_address2), (
                                        user_name2, user_pubkey2) in self.playersConnected.items():
                                    if user_socket2 != client_socket:
                                        self.sendLobbyMenu(user_socket2, user_name2, user_pubkey2)
                                    for party_num, lst in self.parties.items():
                                        for user in lst:
                                            for (user_socket2, user_address2), (user_name2, user_pubkey2) in user.items():
                                                if user_socket2 != client_socket:
                                                    self.sendLobbyMenu(user_socket2, user_name2, user_pubkey2)
                        # Ignorar mensagem (resolver problema do duplo convite)
                        elif invitation == "ignore":
                            invitationFlag = True
                        elif invitation == "startgame":
                            break
                        else:
                            client_socket.send(self.cipherMsgToClient(
                                bytes("\nThat players doesn't exist\n", 'utf-8'), clientkeyRSA))
                    # VERIFICAR SE PARTY = 4
                    party44 = False
                    #if invitation != "ignore":
                    agreement = True
                    for party_num, lst in self.parties.items():
                        if len(lst) == 4:
                            #for user in lst:
                            #    for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                            #        print(self.clientsAgreeTable)
                            #        if user_name == client_username:
                            if client_username not in self.clientsAgreeTable.keys():
                                randomSign = random.randint(0, 1000)
                                resp = ""
                                while resp != "y" and resp != "n":
                                    agreement = True
                                    if resp != "ignore":
                                        client_socket.send(self.cipherMsgToClient(
                                            bytes("\nDo you agree to play with this party?[Y/N]", 'utf-8'
                                                  ), clientkeyRSA))
                                    resp = self.decipherMsgFromClient(client_socket.recv(1024)).decode()
                                    if resp == "y":
                                        client_socket.send(self.cipherMsgToClient(bytes(
                                            "Waiting for all players to agree", 'utf-8'), clientkeyRSA))
                                        client_socket.send(self.cipherMsgToClient(bytes(str(randomSign), 'utf-8'), clientkeyRSA))
                                        signature = self.decipherMsgFromClient(client_socket.recv(1024))
                                        validation = self.validateSignatureRSA(clientkeyRSA, str(randomSign),
                                                                               signature)
                                        if validation == "Verification failed":
                                            agreement = False
                                        break
                                    else:
                                        agreement = False
                                self.clientsAgreeTable[client_username] = agreement
                                if len(self.clientsAgreeTable.keys()) == 1:
                                    for user in lst:
                                        for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                            if user_name != client_username:
                                                user_socket.send(self.cipherMsgToClient(bytes("ignora", 'utf-8'), user_pubkey))

                        #if party44:
                            #break
                    new_table = None
                    #if agreement:
                    create = False
                    if len(self.clientsAgreeTable.keys()) == 4:
                        create = True
                        for k, v in self.clientsAgreeTable.items():
                            if not v:
                                create = False
                        if create:
                            for party_num, lst in self.parties.items():
                                if len(lst) == 4:
                                    for user in lst:
                                        for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                            if user_socket != client_socket:
                                                user_socket.send(self.cipherMsgToClient(
                                                    bytes("\nCREATING NEW TABLE\n", 'utf-8'), user_pubkey))
                                                new_table = party_num
                            party44 = True
                        else:
                            for party_num, lst in self.parties.items():
                                if dicAux in lst:
                                    for user in lst:
                                        for (user_socket, user_address), (
                                                user_name, user_pubkey) in user.items():
                                            user_socket.send(self.cipherMsgToClient(bytes(
                                                "\nThe party was deleted because of the agreement issues\n",
                                                'utf-8'), user_pubkey))
                                            # Adicionar players da party aos soloplayer
                                            self.playersConnected.update(
                                                {(user_socket, user_address): (user_name, user_pubkey)})
                                    # Delete party
                                    del self.parties[party_num]
                                    # Atualiza lobby do players
                                    for (user_socket, user_address), (
                                            user_name, user_pubkey) in self.playersConnected.items():
                                        self.sendLobbyMenu(user_socket, user_name, user_pubkey)
                                    for party_num, lst in self.parties.items():
                                        for user in lst:
                                            for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                                self.sendLobbyMenu(user_socket, user_name, user_pubkey)
                            party44 = False
                    if party44:
                        client_socket.send(self.cipherMsgToClient(
                            bytes("\nCREATING NEW TABLE\n", 'utf-8'), clientkeyRSA))
                        invitationFlag = True
                        self.tables.update({new_table: self.parties[new_table]})
                        # the program is able to exit regardless of if there's any threads still running

                        diamonds = 'diamonds'
                        spades = 'spades'
                        hearts = 'hearts'
                        clubs = 'clubs'
                        self.decks.update({new_table: [(i, diamonds) for i in range(2, 15)]
                                                      + [(i, spades) for i in range(2, 15)]
                                                      + [(i, hearts) for i in range(2, 15)]
                                                      + [(i, clubs) for i in range(2, 15)]})
                        connectionThread = threading.Thread(target=self.gameStart, args=[new_table])
                        connectionThread.daemon = True
                        connectionThread.start()
                        del self.parties[new_table]
            except:
                # Remover player do lobby
                print("player disconnected")
                # self.connections.remove(client_socket)
                # Se o player estiver numa party
                if self.verifyPartyMember(client_username):
                    for party_num, lst in self.parties.items():
                        if dicAux in lst:
                            # Se a party for de 2
                            if len(lst) == 2:
                                for user in lst:
                                    for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                        if client_socket != user_socket:
                                            user_socket.send(self.cipherMsgToClient(
                                                bytes("\n" + client_username + " leave the party, party was deleted\n",
                                                      'utf-8'), user_pubkey))
                                        self.playersConnected.update(
                                            {(user_socket, user_address): (user_name, user_pubkey)})
                                del self.parties[party_num]
                                break
                            # Se a party for maior que 2
                            else:
                                for user in lst:
                                    for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                        if client_socket != user_socket:
                                            user_socket.send(self.cipherMsgToClient(
                                                bytes("\n" + client_username + " leave the party", 'utf-8'), user_pubkey))
                                lst.remove(dicAux)
                                self.playersConnected.update(dicAux)
                                break
                else:
                    # Retirar player dos solo players
                    del self.playersConnected[connection]
                # Atualiza lobby do players
                for (user_socket2, user_address2), (user_name2, user_pubkey2) in self.playersConnected.items():
                    self.sendLobbyMenu(user_socket2, user_name2, user_pubkey2)
                for party_num, lst in self.parties.items():
                    for user in lst:
                        for (user_socket2, user_address2), (user_name2, user_pubkey2) in user.items():
                            self.sendLobbyMenu(user_socket2, user_name2, user_pubkey2)
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
                        for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                            user_socket.send(self.cipherMsgToClient(
                                bytes(str("newlisten" + str(user_address)).encode()), user_pubkey))

            #SEND client socket to each player
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        flag = False
                        for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                            for user2 in lst:
                                for (user_socket2, user_address2), (user_name2, user_pubkey2) in user2.items():
                                    if user_socket != user_socket2:
                                        if flag:
                                            time.sleep(0.2)
                                            user_socket.send(self.cipherMsgToClient(
                                                bytes(str("playersock"+str(user_address2)+"---"+user_name2).encode()), user_pubkey))
                                            time.sleep(0.4)
                                            user_socket2.send(self.cipherMsgToClient(
                                                bytes("acceptNewConnection"+"---"+user_name, 'utf-8'), user_pubkey2))
                                    else:
                                        flag = True

            time.sleep(0.5)

            '''
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                            for user2 in lst:
                                for (user_socket2, user_address2), (user_name2, user_pubkey2) in user2.items():
                                    if user_socket != user_socket2:
                                            user_socket2.send(self.cipherMsgToClient(
                                                bytes("receivingfrom:" + str(user_name), 'utf-8'), user_pubkey2))
                                            time.sleep(0.5)
                                            user_socket.send(self.cipherMsgToClient(
                                                bytes("sendingto:" + str(user_name2), 'utf-8'), user_pubkey))
                                            time.sleep(3)
            
            '''

            usernames = []
            # Send to each player the deck. The player will shuffle it and send it back
            for table_num, lst in self.tables.items():
                if table_num == numTable:
                    for user in lst:
                        for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                            usernames.append(user_name)
                            user_socket.send(self.cipherMsgToClient(
                                bytes("\nSHUFFLE\n", 'utf-8'), user_pubkey))
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

            ##TODO:
            ##O servidor escolhe um jogador aleatorio e manda-lhe o deck
            ##O servidor diz a esse jogador para enviar o deck para um jogador aleatorio
            ##O servidor diz a esse novo jogador aleatorio para madar o deck a outro jogador aleatorio
            ##Ao fim de X iterações o servidor pede para o jogador com o deck para lhe enviar para que ele possa
            ##  verificar se o deck ainda tem cartas

            #Pedaço de codigo nao testado
            while not all(card == self.decks[numTable][0] for card in self.decks[numTable]):
                sendtorandom = random.choice(usernames)
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                if user_name == sendtorandom:
                                    user_socket.send(bytes('recvdeckfromserver', 'utf-8'))
                                    data = json.dumps({"deckEBT": self.decks[table_num]})
                                    user_socket.send(data.encode())
                iterationNUM = random.randint(2,100)
                iterationRN = 0
                while iterationRN < iterationNUM:
                    sendtorandom2 = sendtorandom
                    while sendtorandom2 == sendtorandom:
                        sendtorandom2 = random.choice(usernames)
                    for table_num, lst in self.tables.items():
                        if table_num == numTable:
                            for user in lst:
                                for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                    if user_name == sendtorandom2:
                                        user_socket.send(bytes('recvdeckfromclient:'+sendtorandom, 'utf-8'))
                    for table_num, lst in self.tables.items():
                        if table_num == numTable:
                            for user in lst:
                                for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                    if user_name == sendtorandom:
                                        user_socket.send(bytes('senddecktoclient:'+sendtorandom2, 'utf-8'))
                    sendtorandom = sendtorandom2
                    iterationRN += 1
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                if user_name == sendtorandom:
                                    user_socket.send(bytes('senddecktoserver', 'utf-8'))
                                    dataJson = user_socket.recv(1024)
                                    objectJson = json.loads(dataJson.decode())
                                    dataAfterEBT = objectJson['deckAfterEBT']
                                    self.decks[table_num] = dataAfterEBT


            #Pedaço de codigo a eliminar
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
                            for (user_socket, user_address), (user_name, user_pubkey) in user.items():
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
                        for (user_socket, user_address), (user_name, user_pubkey) in lst[winner].items():
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
                            for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                if client_socket == user_socket:
                                    username = user_name
                for table_num, lst in self.tables.items():
                    if table_num == numTable:
                        for user in lst:
                            for (user_socket, user_address), (user_name, user_pubkey) in user.items():
                                if user_socket != client_socket:
                                    user_socket.send(bytes(username + " started the round", 'utf-8'))
                                    user_socket.send(bytes(username + ": " + card, 'utf-8'))
                self.firstCard = card
                self.firstPlayer = client_socket

    def handler(self, client_socket, client_address):
        self.lobby(client_socket, client_address)

    def cipherMsgToClient(self, msg, clientkey):
        return self.rsaKeyManagement.rsaCipheringConfidentially(msg, clientkey)

    def authenticateMsgFromClient(self, msg, clientkey):
        return self.rsaKeyManagement.rsaDecipheringAuthenticate(msg,clientkey)

    def decipherMsgFromClient(self, msg):
        return self.rsaKeyManagement.rsaDecipheringConfidentially(msg)


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

    def validateSignatureRSA(self, clientPubKey, data, signature):
        if isinstance(data, str):
            data = bytes(data, 'utf-8')
        try:
            clientPubKey.verify(signature, data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                             salt_length=padding.PSS.MAX_LENGTH),
                                hashes.SHA256())
            return 'Verification succeeded'
        except:
            return 'Verification failed'

    def validateSignature(self, clientPubKey, data, signature):
        try:
            clientPubKey.verify(signature, data, padding.PKCS1v15(), hashes.SHA1())
            return 'Verification succeeded'
        except:
            return 'Verification failed'

    def createServerKeys(self):
        self.rsaKeyManagement = EntityRSAKeyManagement(4096)
        self.rsaKeyManagement.generateRSAKey()
        self.serverPrivKey = self.rsaKeyManagement.getRSAPrivKey()
        self.serverPubKey = self.rsaKeyManagement.getRSAPubKey()