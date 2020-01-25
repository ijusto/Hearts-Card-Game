import socket
import threading
import json
import random
import time
from citizencard import CitizenCard
import pickle

class Client:
    # ipv4 tcp socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientDisconnect = False

    cc = None

    sessionsNumber = 0
    pToConnect = [socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                  socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                  socket.socket(socket.AF_INET, socket.SOCK_STREAM)]
    playersInTable = []

    probChoice = 0
    probSwitch = 0
    probShuffle = 0

    hand = []

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

    def msgBetweenPlayers(self, player_socket):
        print("here1")
        data = player_socket.recv(1024).decode()
        while not data:
            data = player_socket.recv(1024).decode()
        print(data)

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
            try:
                data = self.clientSocket.recv(1024)
                if not self.is_json(data.decode()):
                    if data and "acceptNewConnection" not in data.decode('utf-8') and "Graveyard" not in \
                            data.decode('utf-8') and "newlisten" not in data.decode('utf-8') and "playersock" not in \
                            data.decode('utf-8'):
                        #if "Do you want to play with" in data.decode('utf-8'):
                            #time.sleep(2)
                        print(str(data, 'utf-8'))
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
                    #if "CitizenCard Authentication:" in data.decode('utf-8'):
                        #self.cc = CitizenCard()
                        #sign = self.cc.sign("yo")
                        #self.cc.validateSignature(sign[0], sign[1])
                        #to_send = pickle.dumps(self.cc.pubKeyDer)
                        #self.clientSocket.send(to_send)
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
            except Exception as e:
                print(str(e))
                self.clientDisconnect = True
                self.clientSocket.close()