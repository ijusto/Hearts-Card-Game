import socket
import threading
import json
import random
import time
from citizencard import CitizenCard
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from EntityRSAKeyManagement import EntityRSAKeyManagement
from cryptography.hazmat.primitives import serialization
import string
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ellipticCurveDiffieHellman import EllipticCurveDiffieHellman
import sys
import base64

class Client:
    ecdh = EllipticCurveDiffieHellman()
    ecdh.generateExchangeKeys()
    clientPrivKeyEC = ecdh.exchange_private_key
    clientPubKeyEC = ecdh.exchange_public_key

    # The PBKDF2 generator of Python receives as input the number of bytes to generate, instead of bits
    pwd = ''.join(random.choice(string.ascii_lowercase) for i in range(20))
    salt = b'\x00'
    kdf = PBKDF2HMAC(hashes.SHA1(), 16, salt, 1000, default_backend())
    # Generate a private key for use in the deck encryption
    secretKeyDeck = kdf.derive(bytes(pwd, 'utf-8'))

    # ipv4 tcp socket
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientDisconnect = False

    playerOrder = []

    cc = None
    serverPubKey = None

    sessionsNumber = 0
    username = ""

    playersInTable = {} # username :  [socket, pubcc, pubec, sharedKey, keyCipherDeck]

    probChoice = 0
    probSwitch = 0
    probShuffle = 0

    hand = []

    temporaryDeck = []


    decrypt = False
    clientPrivKeyRSA = None
    clientPubKeyRSA = None
    rsaKeyManagement = None

    graveyard = 0
    totalPoints = 0

    def sendMsg(self):
        while not self.clientDisconnect:
            try:
                if self.flagTurn:
                    sentence = input("")
                    self.serverSocket.send(self.cipherMsgToServer(bytes(sentence,'utf-8')))
                    if sentence in self.printHand():
                        card = sentence.split(" ")
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
                        self.hand.remove(card)
                    if self.flagTurnStart:
                        self.flagTurn = False
            except:
                self.clientDisconnect = True
                self.serverSocket.close()

    def is_json(self, myjson):
        try:
            json_object = json.loads(myjson)
        except:
            return False
        return True

    def shuffle(self, deck):
        random.shuffle(deck)
        return deck

    def printHand(self):
        h = []
        court_n_ace = ["J", "Q", "K", "A"]
        for card in self.hand:
            if card[0] < 11:
                h.append(str(card[0]) + " " + card[1])
            elif 15 > card[0] >= 11:
                h.append(str(court_n_ace[card[0] - 11]) + " " + card[1])
        return h

    def cipherDeck(self, deck):
        if self.username == self.playerOrder[0]:
            cipherDeck = []
            for card in deck:
                cipherDeck += [(self.ecdh.cipherUsingSharedKey(self.secretKeyDeck, str(card[0])),
                                self.ecdh.cipherUsingSharedKey(self.secretKeyDeck, str(card[1])))]
        else:
            cipherDeck = []
            for card in deck:
                cipherDeck += [
                    self.ecdh.cipherUsingSharedKey(self.secretKeyDeck, str(card[0])),

                                    self.ecdh.cipherUsingSharedKey(self.secretKeyDeck, str((card[1])))]

        return cipherDeck

    def decipherDeck(self, deck):
        decipherHand = []
        keys = []
        decipherOrderPlayers = self.playerOrder[::-1]
        for username in decipherOrderPlayers:
            keys.append(self.playersInTable[username][4]) # playersInTable[username] = [socket, pubcc, pubec, sharedKey, keyCipherDeck]

        for key in keys: # all keys to cipher deck in order
            for card in deck:
                decipherHand += [(self.ecdh.decipherUsingSharedKey(key, str(card[0])),
                               self.ecdh.decipherUsingSharedKey(key, str(card[1])))]
            deck = decipherHand

    def cipherMsgToServer(self, msg):
        return self.rsaKeyManagement.rsaCipheringConfidentially(msg, self.serverPubKey)

    def authenticateMsgToServer(self, msg):
        return self.rsaKeyManagement.rsaCipheringAuthenticate(msg)


    def decipherMsgFromServer(self, msg):
        return self.rsaKeyManagement.rsaDecipheringConfidentially(msg)

    def __init__(self, address):
        self.createClientKeys()

        self.serverSocket.connect((address, 10002))

        # Probabilidade do client escolher, trocar e baralhar
        self.probChoice = random.randint(1, 90)
        self.probSwitch = random.randint(1, 50)

        self.flagTurn = True
        self.flagTurnStart = False

        inputThread = threading.Thread(target=self.sendMsg)
        inputThread.daemon = True
        inputThread.start()

        while not self.clientDisconnect:
            #try:
            if self.decrypt:
                data = self.decipherMsgFromServer(self.serverSocket.recv(1024)).decode()
                if "Do you want to play with" in data:
                    self.serverSocket.send(self.cipherMsgToServer(bytes("ignore", 'utf-8')))
                if "Waiting for all players to agree" in data:
                    randomSign = self.decipherMsgFromServer(self.serverSocket.recv(1024)).decode()
                    signature = self.rsaKeyManagement.sign(randomSign)
                    self.serverSocket.send(self.cipherMsgToServer(signature))
                if "Do you agree to play with this party?" in data:
                    self.serverSocket.send(self.cipherMsgToServer(bytes("ignore", 'utf-8')))
                if "CREATING NEW TABLE" in data:
                    self.serverSocket.send(self.cipherMsgToServer(bytes("startgame", 'utf-8')))
                if "SHUFFLE" in data:
                    dataJson = json.loads(self.serverSocket.recv(1024).decode())
                    if "deckShuffle" in dataJson.keys():
                        deck = dataJson["deckShuffle"]
                        deck = self.shuffle(deck)
                        #deck = self.cipherDeck(deck)
                        deckJson = json.dumps({"deckShuffled": deck})
                        self.serverSocket.send(deckJson.encode())
                    self.decrypt = False
                if "Sign your pubkey" in data:
                    pemRSA = self.clientPubKeyRSA.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    sign = self.cc.sign(pemRSA)
                    self.serverSocket.send(self.cipherMsgToServer(sign))
                elif "ignora" in data:
                    self.serverSocket.send(self.cipherMsgToServer(bytes("ignore", 'utf-8')))
                elif "newlisten" in data:
                    sock = data.replace("newlisten", "").replace("(", "").replace(")", "").replace(
                        "\'", "").split(",")
                    self.listener.bind((sock[0], int(sock[1])))
                    self.listener.listen(4)
                elif "playersock" in data:
                        message = data.split("---")
                        sock = message[0].replace("playersock", "").replace("(", "").replace(")", "").replace("\'", "").split(",")
                        self.playersInTable.update({message[1]: [socket.socket(socket.AF_INET,
                                                                              socket.SOCK_STREAM)]})
                        self.playersInTable[message[1]][0].connect((sock[0], int(sock[1])))
                elif "acceptNewConnection" in data:
                    message = data.replace("acceptNewConnection---", "")
                    sock, add = self.listener.accept()
                    self.playersInTable.update({message: [sock]})
                elif "receiving" in data:
                    user = data.split(":")[1]
                    pemCC = self.playersInTable[user][0].recv(1024)
                    pubkeyCC = serialization.load_pem_public_key(pemCC, backend=default_backend())
                    self.playersInTable[user].append(pubkeyCC)
                    self.playersInTable[user][0].send(bytes("manda ai", 'utf-8'))
                    pemEC = self.playersInTable[user][0].recv(1024)
                    pubkeyEC = serialization.load_pem_public_key(pemEC, backend=default_backend())
                    self.playersInTable[user][0].send(bytes("assina ai", 'utf-8'))
                    signature = self.playersInTable[user][0].recv(1024)
                    validate = self.validateSignature(self.playersInTable[user][1], pemEC, signature)
                    print(validate)
                    if validate == "Verification succeeded":
                        self.playersInTable[user].append(pubkeyEC)
                        shared_key = self.ecdh.sharedKeyECDHE(pubkeyEC)
                        self.playersInTable[user].append(shared_key)
                    else:
                        print("Secury issues, verification failed")
                        sys.exit(0)
                elif "sending" in data:
                    print("d"+str(data))
                    user = data.split(":")[1]
                    pemCC = self.cc.pubKey.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    print(user)
                    self.playersInTable[user][0].send(pemCC)
                    self.playersInTable[user][0].recv(1024).decode()
                    pemEC = self.clientPubKeyEC.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    self.playersInTable[user][0].send(pemEC)
                    self.playersInTable[user][0].recv(1024).decode()
                    signature = self.cc.sign(pemEC)
                    self.playersInTable[user][0].send(signature)
                elif "OTeuUsername" in data:
                    print("here")
                    self.username = data.split(":")[1]
                elif "OrdemDosPlayers" in data:
                    print(data)
                    self.playerOrder = data.split(":")[1].split(",")[:4]
                    print(self.playerOrder)
                else:
                    print(data)
            else:
                data = self.serverSocket.recv(1024)
                if not self.is_json(data.decode()):
                    if data and "acceptNewConnection" not in data.decode('utf-8') and "Graveyard" not in \
                            data.decode('utf-8') and "newlisten" not in data.decode('utf-8') and "playersock" not in \
                            data.decode('utf-8') and "RandomToSign" not in data.decode('utf-8')\
                            and "ServerPublicKey" not in data.decode('utf-8')\
                            and "receivingfrom" not in data.decode('utf-8') and "sendingto" not in data.decode('utf-8'):
                        print(str(data, 'utf-8'))
                    if "ServerPublicKey" in data.decode('utf-8'):
                        pem = self.serverSocket.recv(1024)
                        self.serverPubKey = serialization.load_pem_public_key(pem, backend=default_backend())
                        self.cc = CitizenCard()
                        pemCC = self.cc.pubKey.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        pemRSA = self.clientPubKeyRSA.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        self.serverSocket.send(self.cipherMsgToServer(pemCC))
                        self.serverSocket.send(self.cipherMsgToServer(pemRSA))
                        self.decrypt = True
                    if "HAND" in data.decode('utf-8'):
                        print(self.printHand())
                    if "started the round" in data.decode('utf-8'):
                        self.serverSocket.send(bytes("alreadyplayed", 'utf-8'))
                        self.flagTurn = False
                        self.flagTurnStart = True
                    if "Your Turn" in data.decode('utf-8'):
                        self.flagTurn = True
                    if "Graveyard" in data.decode('utf-8'):
                        self.graveyard += int(data.decode('utf-8').split(" ")[1])
                    if "End of the game" in data.decode('utf-8'):
                        self.serverSocket.send(bytes(str(self.graveyard), 'utf-8'))
                        self.hand.clear()
                        self.graveyard = 0
                    if "You scored" in data.decode('utf-8'):
                        self.totalPoints += int(data.decode('utf-8').split("You scored ")[1].split(" points")[0])
                        print("Do you agree with the scoreboard?[y/n]")
                        resp = input("")
                        if resp == "y":
                            sign = self.cc.sign(data)
                            self.serverSocket.send(sign)#self.cipherMsgToServer(sign))
                        else:
                            self.serverSocket.send(bytes("I don't accept the scoreboard.", 'utf-8'))#self.cipherMsgToServer("I don't accept the scoreboard."))

                    if "recvdeckfromserver" in data.decode('utf-8'):
                        print("here")
                        newjsondata = self.serverSocket.recv(1024).decode()
                        newdata = json.loads(newjsondata)
                        if "deckEBT" in newdata.keys():
                            deck = newdata["deckEBT"]
                            self.temporaryDeck = self.doTheEBT(deck)
                    if "recvdeckfromclient" in data.decode('utf-8'):
                        user = data.decode('utf-8').split(":")[1]
                        print(user)
                        newdata = json.loads(self.playersInTable[user][0].recv(1024).decode())
                        if "deckAfterEBT" in newdata.keys():
                            deck = newdata["deckAfterEBT"]
                            self.temporaryDeck = self.doTheEBT(deck)
                    if "senddecktoclient" in data.decode('utf-8'):
                        user = data.decode('utf-8').split(":")[1]
                        deckJson = json.dumps({"deckAfterEBT": self.temporaryDeck})
                        self.playersInTable[user][0].send(deckJson.encode())
                    if "senddecktoserver" in data.decode('utf-8'):
                        deckJson = json.dumps({"deckAfterEBT": self.temporaryDeck})
                        self.serverSocket.send(deckJson.encode())
                    if not data:
                        continue
                else:
                    data = json.loads(data.decode())
                    if "deckShuffle" in data.keys():
                        deck = data["deckShuffle"]
                        deck = self.shuffle(deck)
                        deckJson = json.dumps({"deckShuffled": deck})
                        self.serverSocket.send(deckJson.encode())
                    elif "deckEBT" in data.keys():
                        print("here2")
                        # Pode escolher e pode trocar e baralha sempre
                        deck = data["deckEBT"]
                        action = random.randint(1, 100)
                        # print("A:"+str(action) + " E:" + str(self.probEscolha) + " T:" + str(self.probTroca) +
                        # " B:" + str(self.probBaralha))
                        # Escolher uma carta
                        if action <= self.probChoice:
                            if len(self.hand) < 13:
                                card = random.randint(0, 51)
                                while deck[card] == [0, 0]:
                                    card = random.randint(0, 51)
                                self.hand.append(deck[card])
                                deck[card] = (0, 0)
                                # deckJson = json.dumps({"deckAfterEBT": deck})
                                # self.clientSocket.send(deckJson.encode())
                        # Troca de cartas
                        change = True
                        while change:
                            change = False
                            action = random.randint(1, 100)
                            if action <= self.probSwitch:
                                if len(self.hand) != 0:
                                    switch = random.randint(0, len(self.hand))
                                    card = random.randint(0, 51)
                                    while deck[card] == [0, 0]:
                                        card = random.randint(0, 51)
                                    self.hand.append(deck[card])
                                    deck[card] = self.hand[switch]
                                    del self.hand[switch]
                                    # deckJson = json.dumps({"deckAfterEBT": deck})
                                    # self.clientSocket.send(deckJson.encode())
                                    change = True
                        # BARALHAR
                        deck = self.shuffle(deck)
                        deckJson = json.dumps({"deckAfterEBT": deck})
                        self.serverSocket.send(deckJson.encode())
            #except Exception as e:
            #    print("Exception: "+str(e))
            #    self.clientDisconnect = True
            #    self.serverSocket.close()

    def doTheEBT(self, deck):
        print("Deck: "+str(deck))
        action = random.randint(1, 100)
        # print("A:"+str(action) + " E:" + str(self.probEscolha) + " T:" + str(self.probTroca) +
        # " B:" + str(self.probBaralha))
        # Escolher uma carta
        print("Action:"+str(action))
        if action <= self.probChoice:
            print("Escolha")
            if len(self.hand) < 13:
                card = random.randint(0, 51)
                while deck[card] == [0, 0]:
                    card = random.randint(0, 51)

                print("Card"+str(deck[card]))
                self.hand.append(deck[card])
                deck[card] = (0, 0)
                # deckJson = json.dumps({"deckAfterEBT": deck})
                # self.clientSocket.send(deckJson.encode())
        # Troca de cartas
        change = True
        while change:
            change = False
            action = random.randint(1, 100)
            if action <= self.probSwitch:
                if len(self.hand) != 0 and not all(card == deck[0] for card in deck):
                    switch = random.randint(0, len(self.hand))
                    card = random.randint(0, 51)
                    while deck[card] == [0, 0]:
                        card = random.randint(0, 51)
                    self.hand.append(deck[card])
                    deck[card] = self.hand[switch]
                    del self.hand[switch]
                    # deckJson = json.dumps({"deckAfterEBT": deck})
                    # self.clientSocket.send(deckJson.encode())
                    change = True
        # BARALHAR
        deck = self.shuffle(deck)
        return deck

    def validateSignature(self, clientPubKey, data, signature):
        try:
            clientPubKey.verify(signature, data, padding.PKCS1v15(), hashes.SHA1())
            return 'Verification succeeded'
        except:
            return 'Verification failed'

    def createClientKeys(self):
        self.rsaKeyManagement = EntityRSAKeyManagement(4096)
        self.rsaKeyManagement.generateRSAKey()
        self.clientPrivKeyRSA = self.rsaKeyManagement.getRSAPrivKey()
        self.clientPubKeyRSA = self.rsaKeyManagement.getRSAPubKey()
