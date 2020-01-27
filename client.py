import socket
import threading
import json
import random
import time
from citizencard import CitizenCard
import pickle
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

class Client:
    # Generate a private key for use in the deck encryption
    clientPrivKey = ec.generate_private_key(ec.SECP384R1(), default_backend())
    clientPubKey = clientPrivKey.public_key()

    # ipv4 tcp socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientDisconnect = False

    cc = None
    serverPubKey = None

    sessionsNumber = 0
    pToConnect = [socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                  socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                  socket.socket(socket.AF_INET, socket.SOCK_STREAM)]
    playersInTable = []

    probChoice = 0
    probSwitch = 0
    probShuffle = 0

    hand = []

    decrypt = False

    graveyard = 0
    totalPoints = 0

    def sendMsg(self):
        while not self.clientDisconnect:
            try:
                if self.flagTurn:
                    sentence = input("")
                    self.clientSocket.send(bytes(sentence, 'utf-8'))
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
                self.clientSocket.close()

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
        cipherDeck = []
        for card in deck:
            # Encrypt the plaintext using OAEP + MGF1(SHA256) + SHA256
            cipherDeck += [self.clientPrivKey.encrypt(card, padding.OAEP(padding.MGF1(hashes.SHA256()), hashes.SHA256(),
                                                                        None))]
    def decipherDeck(self, deck, keys):
        decipherHand = []
        for key in keys: # all pub keys in order
            for card in deck:
                decipherHand += key.decrypt(card, padding.OAEP(padding.MGF1(hashes.SHA256()), hashes.SHA256(), None))
            deck = decipherHand

    def cipherMsgToServer(self, msg):
        # Calculate the maximum amount of data we can encrypt with OAEP + SHA256
        maxLenG = (self.serverPubKey.key_size // 8) - 2 * hashes.SHA256.digest_size - 2
        maxLen = maxLenG
        minLen = 0
        ciphertext = bytes()
        if maxLenG >= len(msg):
            ciphertext = self.serverPubKey.encrypt(msg, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                          hashes.SHA256(), None))
        else:
            while minLen <= len(msg):
                plaintext = msg[minLen:maxLen]
                minLen = maxLen
                if maxLen+maxLenG > len(msg):
                    maxLen += maxLenG
                else:
                    maxLen = len(msg)
                ciphertext += self.serverPubKey.encrypt(plaintext, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                                   hashes.SHA256(), None))

        return ciphertext

    def decipherMsgFromServer(self, msg):
        maxLenG = 256
        print(msg)
        print("size:"+str(len(msg)))
        maxLen = maxLenG
        minLen = 0
        plaintext = bytes()
        if maxLenG >= len(msg):
            print("here")
            plaintext = self.cc.privKey.decrypt(msg, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                     hashes.SHA256(), None))
            print("here2")
        else:
            while minLen < len(msg):
                ciphertext = msg[minLen:maxLen]
                minLen = maxLen
                if maxLen + maxLenG > len(msg):
                    maxLen += maxLenG
                else:
                    maxLen = len(msg)
                plaintext += self.cc.privKey.decrypt(ciphertext, padding.OAEP(padding.MGF1(hashes.SHA256()),
                                                                                 hashes.SHA256(), None))
        return plaintext


    def __init__(self, address):
        self.clientSocket.connect((address, 10002))

        # Probabilidade do client escolher, trocar e baralhar
        self.probChoice = random.randint(1, 20)
        self.probSwitch = random.randint(1, 50)

        self.flagTurn = True
        self.flagTurnStart = False

        inputThread = threading.Thread(target=self.sendMsg)
        inputThread.daemon = True
        inputThread.start()

        while not self.clientDisconnect:
            #try:
            if self.decrypt:
                data = self.decipherMsgFromServer(self.clientSocket.recv(1024)).decode()
                if "RandomToSign" in data:
                    sign = self.cc.sign(data.split(":")[1])
                    self.clientSocket.send(sign)
                self.decrypt = False
            else:
                data = self.clientSocket.recv(1024)
                if not self.is_json(data.decode()):
                    if data and "acceptNewConnection" not in data.decode('utf-8') and "Graveyard" not in \
                            data.decode('utf-8') and "newlisten" not in data.decode('utf-8') and "playersock" not in \
                            data.decode('utf-8') and "RandomToSign" not in data.decode('utf-8')\
                            and "ServerPublicKey" not in data.decode('utf-8'):
                        #if "Do you want to play with" in data.decode('utf-8'):
                            #time.sleep(2)
                        print(str(data, 'utf-8'))
                    if "ServerPublicKey" in data.decode('utf-8'):
                        pem = self.clientSocket.recv(1024)
                        self.serverPubKey = serialization.load_pem_public_key(pem, backend=default_backend())
                        self.cc = CitizenCard()
                        pem = self.cc.pubKey.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        self.clientSocket.send(self.cipherMsgToServer(pem))
                        self.decrypt = True
                    if "newlisten" in data.decode('utf-8'):
                        sock = data.decode('utf-8').replace("newlisten", "").replace("(", "").replace(")", "").replace(
                            "\'", "").split(",")
                        self.listener.bind((sock[0], int(sock[1])))
                        self.listener.listen(4)
                    if "playersock" in data.decode('utf-8'):
                        sock = data.decode('utf-8').replace("playersock", "").replace("(", "").replace(")", "").replace("\'", "").split(",")
                        #print(str(self.listener)+"connecting too")
                        #print("add:"+sock[0]+" port:"+sock[1])
                        self.pToConnect[self.sessionsNumber].connect((sock[0], int(sock[1])))
                        self.sessionsNumber += 1
                    if "acceptNewConnection" in data.decode(('utf-8')):
                        #print(str(self.listener) + "accepting")
                        sock, add = self.listener.accept()
                        self.pToConnect[self.sessionsNumber] = sock
                        self.sessionsNumber += 1
                    if "Do you want to play with" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("ignore", 'utf-8'))
                    if "NEW TABLE" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("startgame", 'utf-8'))
                    if "HAND" in data.decode('utf-8'):
                        print(self.printHand())
                    if "started the round" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("alreadyplayed", 'utf-8'))
                        self.flagTurn = False
                        self.flagTurnStart = True
                    if "Your Turn" in data.decode('utf-8'):
                        self.flagTurn = True
                    if "Graveyard" in data.decode('utf-8'):
                        self.graveyard += int(data.decode('utf-8').split(" ")[1])
                    if "End of the game" in data.decode('utf-8'):
                        self.clientSocket.send(bytes(str(self.graveyard), 'utf-8'))
                        self.hand.clear()
                        self.graveyard = 0
                    if "You scored" in data.decode('utf-8'):
                        self.totalPoints += int(data.decode('utf-8').split(" ")[2])
                    #if "SHUFFLE" in data.decode('utf-8'):
                    #    for i in range(0, 3):
                    #        inputThread = threading.Thread(target=self.msgBetweenPlayers, args=[self.pToConnect[i]])
                    #        inputThread.daemon = True
                    #        inputThread.start()
                        #inputThread = threading.Thread(target=self.msgBetweenPlayers, args=[self.pToConnect[0]])
                        #inputThread.daemon = True
                        #inputThread.start()
                    #if "CARD DISTRIBUTION" in data.decode('utf-8'):
                    #    for i in range(0, 3):
                    #        print("here2")
                    #        self.pToConnect[i].send(bytes("funciona", 'utf-8'))
                    if "receiving" in data.decode('utf-8'):
                        i = int(data.decode('utf-8').split(":")[1])
                        print(self.pToConnect[i].recv(1024).decode())
                    if "sending" in data.decode('utf-8'):
                        i = int(data.decode('utf-8').split(":")[1])
                        self.pToConnect[i].send(bytes("funciona", 'utf-8'))
                    if not data:
                        continue
                else:
                    data = json.loads(data.decode())
                    if "deckShuffle" in data.keys():
                        deck = data["deckShuffle"]
                        deck = self.shuffle(deck)
                        deckJson = json.dumps({"deckShuffled": deck})
                        self.clientSocket.send(deckJson.encode())
                    elif "deckEBT" in data.keys():
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
                        self.clientSocket.send(deckJson.encode())
            #except Exception as e:
            #    print("Exception: "+str(e))
            #    self.clientDisconnect = True
            #    self.clientSocket.close()
