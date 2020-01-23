<<<<<<< HEAD
import socket
import threading
import sys
import select
import pickle # used to serialize objects so that the sent data is an object instead of a string
import json
import random



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
    tables = {}
    decks = {}

    firstPlayer = None
    firstCard = None

    def __init__ (self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0


    ##Função que escreve o lobby
    def lobbyMeny(self, userSocket,userCc):
        userSocket.send(bytes("Lobby:\n", 'utf-8'))
        userSocket.send(bytes("SoloPlayers:\n", 'utf-8'))
        for un, ucc in self.playersConnected.values():
            if ucc != userCc:
                userSocket.send(bytes(un + "\n", 'utf-8'))
        userSocket.send(bytes("Parties:\n", 'utf-8'))
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
        return verificador

    def lobby(self, client_socket, client_address):
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

                #Pedir CC
                client_socket.send(bytes("CC: ", 'utf-8'))
                cc = client_socket.recv(1024).decode()
                connection = (client_socket,client_address)
                #Adicionar aos soloplayers
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

            #flag de ajuda com os invites
            invitationFlag = False

            while True:
                try:
                    #Caso a ultima mensagem enviada seja "ignore"
                    if invitationFlag == False:
                        self.lobbyMeny(client_socket,cc)
                    invitationFlag=False
                    invitation = client_socket.recv(1024).decode()

                    #Se o invite for para ele proprio
                    if(invitation == client_username):
                        client_socket.send(bytes("You can't invite your self",'utf-8'))
                    else:
                        checker = False
                        for (user_socket, user_address), (user_name, user_cc) in self.playersConnected.items():
                            if user_name == invitation:
                                resp = ""
                                while resp != "y" and resp != "n":
                                    #Envia convite para o player
                                    user_socket.send(bytes("Do you want to play with "+client_username+"?[y/n]", "utf-8"))
                                    resp = user_socket.recv(1024).decode()
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
                                            #Se o player convida um player que já esteja numa party
                                            if(self.verificarPartyMember(cc)):
                                                checker = True
                                                client_socket.send(bytes("You'te already in a party, you can't join another","utf-8"))
                                                break
                                            checker = True
                                            resp = ""
                                            while resp != "y" and resp != "n":
                                                user_socket.send(bytes("Do you want to play with " + client_username + "?[y/n]", "utf-8"))
                                                resp = user_socket.recv(1024).decode()
                                                #Player aceita convite
                                                if resp == "y":
                                                    client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                                    #Apagar player dos solo players
                                                    del self.playersConnected[connection]
                                                    #Adicionar player à party
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
                                                #Player recusa convite
                                                elif resp == "n":
                                                    checker = True
                                                    client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                        ##Se o player convidade não estiver no lobby, nem numa party
                        ##OU ser o utilizador quiser sair da party
                        if not checker:
                            if invitation == "LEAVE":
                                #Se o player nao estiver numa party
                                if (not self.verificarPartyMember(cc)):
                                    client_socket.send(bytes("You're not in a party",'utf-8'))
                                else:
                                    for party_num, list in self.parties.items():
                                        if(dicAux in list):
                                            #Se a party for de tamanho 2
                                            if len(list) == 2:
                                                for user in list:
                                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                        if(client_socket!=user_socket):
                                                            #Enviar informaçao para o outro membro da party
                                                            user_socket.send(bytes("\n"+client_username+" leave the party, party was deleted\n", 'utf-8'))
                                                        #Adicionar players da party aos soloplayer
                                                        self.playersConnected.update({(user_socket, user_address): (user_name, user_cc)})
                                                client_socket.send(bytes("You left the party",'utf-8'))
                                                #Apagar party
                                                del self.parties[party_num]
                                                break
                                            else:
                                                for user in list:
                                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                        if client_socket != user_socket:
                                                            #Enviar informaçao que um membro saiu da party
                                                            user_socket.send(bytes("\n"+client_username+" leave the party", 'utf-8'))
                                                #Remover player da party
                                                list.remove(dicAux)
                                                client_socket.send(bytes("You left the party", 'utf-8'))
                                                #Adicionar player à party
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
                            #Ignorar mensagem (resolver problema do duplo convite)
                            elif invitation == "ignore":
                                invitationFlag = True
                            elif invitation == "startgame":
                                break
                            else:
                                client_socket.send(bytes("\nThat players doesn't exist\n",'utf-8'))
                        #VERIFICAR SE PARTY = 4
                        party44 = False
                        for party_num, list in self.parties.items():
                            if len(list) == 4:
                                for user in list:
                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                        if user_socket == client_socket:
                                            party44 = True
                                        else:
                                            user_socket.send(bytes("\nNEW TABLE\n",'utf-8'))
                            if (party44 == True):
                                break
                        if (party44 == True):
                            client_socket.send(bytes("\nNEW TABLE\n", 'utf-8'))
                            invitationFlag = True
                            self.tables.update({party_num : self.parties[party_num]})
                            # the program is able to exit regardless of if there's any threads still running

                            diamonds = 'diamonds'
                            spades = 'spades'
                            hearts = 'hearts'
                            clubs = 'clubs'
                            self.decks.update({party_num : [(i, diamonds) for i in range(2,15)]\
                                                           +[(i, spades) for i in range(2,15)]\
                                                           +[(i, hearts) for i in range(2,15)]\
                                                           +[(i, clubs) for i in range(2,15)]})
                            connectionThread = threading.Thread(target=self.gameStart,
                                                                args=[party_num])
                            connectionThread.daemon = True
                            connectionThread.start()
                            del self.parties[party_num]
                except:
                    #Remover player do lobby
                    print("player disconnected")
                    #self.connections.remove(client_socket)
                    #Se o player estiver numa party
                    if(self.verificarPartyMember(cc)):
                        for party_num, list in self.parties.items():
                            if(dicAux in list):
                                #Se a party for de 2
                                if len(list) == 2:
                                    for user in list:
                                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                if (client_socket != user_socket):
                                                    user_socket.send(bytes("\n" + client_username + " leave the party, party was deleted\n",'utf-8'))
                                                self.playersConnected.update({(user_socket, user_address): (user_name, user_cc)})
                                    del self.parties[party_num]
                                    break
                                #Se a party for maior que 2
                                else:
                                    for user in list:
                                        for (user_socket, user_address), (user_name, user_cc) in user.items():
                                            if client_socket != user_socket:
                                                user_socket.send(bytes("\n" + client_username + " leave the party", 'utf-8'))
                                    list.remove(dicAux)
                                    self.playersConnected.update(dicAux)
                                    break
                    else:
                        #Retirar player dos solo players
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

    def organizarMesa(self, numTable):
        novaOrdem = []
        for table_num, list in self.tables.items():
            if table_num == numTable:
                for user in list:
                    for (user_socket, user_address) in user.keys():
                        if user_socket == self.firstPlayer:
                            novaOrdem.append(user)
                        elif user_socket != self.firstPlayer and len(novaOrdem) != 0:
                            novaOrdem.append(user)
        for table_num, list in self.tables.items():
            if table_num == numTable:
                for user in list:
                    if user not in novaOrdem:
                        novaOrdem.append(user)
        self.tables[numTable] = novaOrdem


    def gameStart(self, numTable):
        while True:
            #Esperar para que todas as mensagens sejam enviadas
            import time
            time.sleep(1)
            #Enviar para cada jogador o deck, este vai baralhá-lo e enviar de volta
            for table_num, list in self.tables.items():
                if table_num == numTable:
                    for user in list:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nSHUFFLE\n", 'utf-8'))
                            data = json.dumps({"deckShuffle": self.decks[table_num]})
                            user_socket.send(data.encode())
                            dataJson = user_socket.recv(1024)
                            objectJson = json.loads(dataJson.decode())
                            dataShuffled = objectJson['deckShuffled']
                            self.decks[table_num] = dataShuffled
                            user_socket.send(bytes("\nCARD DISTRIBUTION\n", 'utf-8'))
            print(self.decks[numTable])
            #Já todos os players baralharam
            #Enviar para cada jogador, este pode escolher uma carta, baralhar de novo ou trocar uma carta
            while not all(card == self.decks[numTable][0] for card in self.decks[numTable]):
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address) in user.keys():
                                if not all(card == self.decks[table_num][0] for card in self.decks[table_num]):
                                    data = json.dumps({"deckEBT": self.decks[table_num]})
                                    user_socket.send(data.encode())
                                    dataJson = user_socket.recv(1024)
                                    objectJson = json.loads(dataJson.decode())
                                    dataAfterEBT = objectJson['deckAfterEBT']
                                    self.decks[table_num] = dataAfterEBT
            #Mostrar mãos
            for table_num, list in self.tables.items():
                if table_num == numTable:
                    for user in list:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nHAND:", 'utf-8'))
                            user_socket.send(bytes("\nPlayer who has the 2 clubs starts playing", 'utf-8'))
                            connectionThread = threading.Thread(target=self.firstplay,
                                                                args=(user_socket, user_address, numTable))
                            connectionThread.daemon = True
                            connectionThread.start()
            #Enquanto nenhum jogador não jogar nada acontece
            while self.firstPlayer == None:
                pass
            ##Organizar ordem das jogadas
            self.organizarMesa(numTable)
            ronda = 1
            while ronda <= 13:
                time.sleep(1)
                cartasRonda = []
                #Jogada de cada jogador
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if(ronda==1):
                                    if user_socket != self.firstPlayer:
                                        user_socket.send(bytes("Your Turn",'utf-8'))
                                        card = user_socket.recv(1024).decode()
                                        while not self.validCard(card):
                                            user_socket.send(bytes("That is not a card", 'utf-8'))
                                            card = user_socket.recv(1024).decode()
                                        cartasRonda.append(card)
                                        #Enviar carta jogada para os restantes jogadores
                                        for table_num2, list2 in self.tables.items():
                                            if table_num2 == numTable:
                                                for user2 in list2:
                                                    for (user_socket2, user_address2) in user2.keys():
                                                        if user_socket != user_socket2:
                                                            user_socket2.send(bytes(user_name + ": " + card, 'utf-8'))
                                    else:
                                        cartasRonda.append(self.firstCard)
                                else:
                                    user_socket.send(bytes("Your Turn", 'utf-8'))
                                    card = user_socket.recv(1024).decode()
                                    while not self.validCard(card):
                                        user_socket.send(bytes("That is not a card", 'utf-8'))
                                        card = user_socket.recv(1024).decode()
                                    cartasRonda.append(card)
                                    for table_num2, list2 in self.tables.items():
                                        if table_num2 == numTable:
                                            for user2 in list2:
                                                for (user_socket2, user_address2) in user2.keys():
                                                    if user_socket != user_socket2:
                                                        user_socket2.send(bytes(user_name + ": " + card, 'utf-8'))
                #Ver quem ganhou a ronda
                vencedor = self.vencedorRonda(cartasRonda)
                cemiterio = 0
                username = ""
                #Pontos por ronda
                for card in cartasRonda:
                    if "hearts" in card:
                        cemiterio += 1
                    elif "Q spades" in card:
                        cemiterio += 13
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for (user_socket, user_address), (user_name, user_cc) in list[vencedor].items():
                            user_socket.send(bytes("You won the round", 'utf-8'))
                            time.sleep(0.1)
                            user_socket.send(bytes("\nHAND:", 'utf-8'))
                            time.sleep(0.1)
                            user_socket.send(bytes("Cemiterio "+str(cemiterio), 'utf-8'))
                            self.firstPlayer = user_socket
                            username = user_name
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address) in user.keys():
                                if user_socket != self.firstPlayer:
                                    user_socket.send(bytes(username+" won the round", 'utf-8'))
                                    time.sleep(0.1)
                                    user_socket.send(bytes("\nHAND:", 'utf-8'))
                self.organizarMesa(numTable)
                ronda += 1
            ##Fim de um jogo
            pontuacao = []
            for table_num, list in self.tables.items():
                if table_num == numTable:
                    for user in list:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("End of the game", 'utf-8'))
                            points = int(user_socket.recv(1024).decode())
                            pontuacao.append([user_socket, points])
            #Verificar se algum jogador tem 26 pontos
            maxPoints = False
            for points in pontuacao:
                if 26 == points[1]:
                    maxPoints = True
            for points in pontuacao:
                if maxPoints == True:
                    if 26 == points[1]:
                        points[1] = 0
                    else:
                        points[1] = 26
                points[0].send(bytes("You scored "+str(points[1])+" points",'utf-8'))
            #Reset do deck
            del self.decks[numTable]
            diamonds = 'diamonds'
            spades = 'spades'
            hearts = 'hearts'
            clubs = 'clubs'
            self.decks.update({numTable: [(i, diamonds) for i in range(2, 15)] \
                                          + [(i, spades) for i in range(2, 15)] \
                                          + [(i, hearts) for i in range(2, 15)] \
                                          + [(i, clubs) for i in range(2, 15)]})


    def vencedorRonda(self, cartasRonda):
        cartaMaior = cartasRonda[0].split(" ")
        index = 0
        court_n_ace = ["J", "Q", "K", "A"]
        if cartaMaior[0] == court_n_ace[0]:
            cartaMaior[0] = 11
        elif cartaMaior[0] == court_n_ace[1]:
            cartaMaior[0] = 12
        elif cartaMaior[0] == court_n_ace[2]:
            cartaMaior[0] = 13
        elif cartaMaior[0] == court_n_ace[3]:
            cartaMaior[0] = 14
        cartaMaior[0] = int(cartaMaior[0])
        i=0
        for card in cartasRonda[1:]:
            i+=1
            card = card.split(" ")
            if cartaMaior[1] == card[1]:
                if card[0] == court_n_ace[0]:
                    card[0] = 11
                elif card[0] == court_n_ace[1]:
                    card[0] = 12
                elif card[0] == court_n_ace[2]:
                    card[0] = 13
                elif card[0] == court_n_ace[3]:
                    card[0] = 14
                card[0] = int(card[0])
                if(cartaMaior[0]<card[0]):
                    index = i
                    cartaMaior = card
        return index


    def validCard(self,card):
        baralho = []
        court_n_ace = ["J", "Q", "K", "A"]
        for i in range(2, 11):
            baralho.append(str(i) + " diamonds")
            baralho.append(str(i) + " clubs")
            baralho.append(str(i) + " spades")
            baralho.append(str(i) + " hearts")
        for figure in court_n_ace:
            baralho.append(figure + " diamonds")
            baralho.append(figure + " clubs")
            baralho.append(figure + " spades")
            baralho.append(figure + " hearts")
        if card in baralho:
            return True
        else:
            return False

    def firstplay(self, client_socket, client_address, numTable):
        card = client_socket.recv(1024).decode()
        if card != "jajogado":
            username = ""
            while not self.validCard(card):
                if card == "jajogado":
                    break
                client_socket.send(bytes("That is not a card", 'utf-8'))
                card = client_socket.recv(1024).decode()
            if card != "jajogado":
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if client_socket == user_socket:
                                    username = user_name
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if user_socket != client_socket:
                                    user_socket.send(bytes(username+" started the round",'utf-8'))
                                    user_socket.send(bytes(username+": "+card, 'utf-8'))
                self.firstCard=card
                self.firstPlayer=client_socket


    def handler(self,client_socket, client_address):
        self.lobby(client_socket, client_address);

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

    probEscolha = 0
    probTroca = 0
    probBaralha = 0

    mao = []

    cemiterio = 0
    totalPoints = 0

    def sendMsg(self):
        while not self.clientDisconnect:
            try:
                if(self.flagTurn):
                    frase = input("")
                    self.clientSocket.send(bytes(frase, 'utf-8'))
                    if frase in self.printMao():
                        card = frase.split(" ")
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
                        self.mao.remove(card)
                    if(self.flagTurnStart):
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

    def shuffle(self,deck):
        random.shuffle(deck)
        return deck

    def printMao(self):
        retorno=[]
        court_n_ace = ["J", "Q", "K", "A"]
        for card in self.mao:
            if(card[0]<11):
                retorno.append(str(card[0])+" "+card[1])
            elif card[0]<15 and card[0]>=11:
                retorno.append(str(court_n_ace[card[0] - 11])+" "+card[1])
        return retorno


    def __init__(self, address):
        self.clientSocket.connect((address, 10001))

        #Probabilidade do client escolher, trocar e baralhar
        self.probEscolha = random.randint(1, 8)
        self.probTroca = random.randint(self.probEscolha+1, 9)
        self.probBaralha = random.randint(self.probTroca+1, 10)

        self.flagTurn = True
        self.flagTurnStart = False

        inputThread = threading.Thread(target=self.sendMsg)
        inputThread.daemon = True
        inputThread.start()

        while not self.clientDisconnect:
            try:
                data = self.clientSocket.recv(1024)
                if not self.is_json(data.decode()):
                    if "Do you want to play with" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("ignore",'utf-8'))
                    if data and "Cemiterio" not in data.decode('utf-8'):
                        print(str(data, 'utf-8'))
                    if "NEW TABLE" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("startgame",'utf-8'))
                    if "HAND" in data.decode('utf-8'):
                        print(self.printMao())
                    if "started the round" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("jajogado",'utf-8'))
                        self.flagTurn = False
                        self.flagTurnStart = True
                    if "Your Turn" in data.decode('utf-8'):
                        self.flagTurn = True
                    if "Cemiterio" in data.decode('utf-8'):
                        self.cemiterio += int(data.decode('utf-8').split(" ")[1])
                    if "End of the game" in data.decode('utf-8'):
                        self.clientSocket.send(bytes(str(self.cemiterio), 'utf-8'))
                        self.mao.clear()
                        self.cemiterio = 0
                    if "You scored" in data.decode('utf-8'):
                        self.totalPoints += int(data.decode('utf-8').split(" ")[2])
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
                        deck = data["deckEBT"]
                        action = random.randint(0, 10)
                        #print("A:"+str(action)+" E:"+str(self.probEscolha)+" T:"+str(self.probTroca)+" B:"+str(self.probBaralha))
                        if action <= self.probEscolha:
                            if len(self.mao) < 13:
                                card = random.randint(0, 51)
                                while deck[card] == [0, 0]:
                                    card = random.randint(0, 51)
                                self.mao.append(deck[card])
                                deck[card] = (0, 0)
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
                            else:
                                deck = self.shuffle(deck)
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
                        elif action >= self.probBaralha:
                            deck = self.shuffle(deck)
                            deckJson = json.dumps({"deckAfterEBT": deck})
                            self.clientSocket.send(deckJson.encode())
                        else:
                            if len(self.mao) != 0:
                                troca = random.randint(0, len(self.mao))
                                card = random.randint(0, 51)
                                while deck[card] == [0, 0]:
                                    card = random.randint(0, 51)
                                self.mao.append(deck[card])
                                deck[card] = self.mao[troca]
                                del self.mao[troca]
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
                            else:
                                deck = self.shuffle(deck)
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
            except:
                self.clientDisconnect=True
                self.clientSocket.close()

if(len(sys.argv) > 1):
    client = Client(sys.argv[1])
else:
    server = Server()
=======
import socket
import threading
import sys
import select
import pickle # used to serialize objects so that the sent data is an object instead of a string
import json
import random



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
    tables = {}
    decks = {}

    firstPlayer = None
    firstCard = None

    def __init__ (self):
        self.serverSocket.bind(('0.0.0.0', 10001))
        self.serverSocket.listen(1)
        print("Waiting for a connection, Server Started")
        self.numberOfClients = 0


    ##Função que escreve o lobby
    def lobbyMeny(self, userSocket,userCc):
        userSocket.send(bytes("Lobby:\n", 'utf-8'))
        userSocket.send(bytes("SoloPlayers:\n", 'utf-8'))
        for un, ucc in self.playersConnected.values():
            if ucc != userCc:
                userSocket.send(bytes(un + "\n", 'utf-8'))
        userSocket.send(bytes("Parties:\n", 'utf-8'))
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
        return verificador

    def lobby(self, client_socket, client_address):
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

                #Pedir CC
                client_socket.send(bytes("CC: ", 'utf-8'))
                cc = client_socket.recv(1024).decode()
                connection = (client_socket,client_address)
                #Adicionar aos soloplayers
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

            #flag de ajuda com os invites
            invitationFlag = False

            while True:
                try:
                    #Caso a ultima mensagem enviada seja "ignore"
                    if invitationFlag == False:
                        self.lobbyMeny(client_socket,cc)
                    invitationFlag=False
                    invitation = client_socket.recv(1024).decode()

                    #Se o invite for para ele proprio
                    if(invitation == client_username):
                        client_socket.send(bytes("You can't invite your self",'utf-8'))
                    else:
                        checker = False
                        for (user_socket, user_address), (user_name, user_cc) in self.playersConnected.items():
                            if user_name == invitation:
                                resp = ""
                                while resp != "y" and resp != "n":
                                    #Envia convite para o player
                                    user_socket.send(bytes("Do you want to play with "+client_username+"?[y/n]", "utf-8"))
                                    resp = user_socket.recv(1024).decode()
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
                                            #Se o player convida um player que já esteja numa party
                                            if(self.verificarPartyMember(cc)):
                                                checker = True
                                                client_socket.send(bytes("You'te already in a party, you can't join another","utf-8"))
                                                break
                                            checker = True
                                            resp = ""
                                            while resp != "y" and resp != "n":
                                                user_socket.send(bytes("Do you want to play with " + client_username + "?[y/n]", "utf-8"))
                                                resp = user_socket.recv(1024).decode()
                                                #Player aceita convite
                                                if resp == "y":
                                                    client_socket.send(bytes(user_name + " accepted the invite", 'utf-8'))
                                                    #Apagar player dos solo players
                                                    del self.playersConnected[connection]
                                                    #Adicionar player à party
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
                                                #Player recusa convite
                                                elif resp == "n":
                                                    checker = True
                                                    client_socket.send(bytes(user_name + " refused the invite", 'utf-8'))
                        ##Se o player convidade não estiver no lobby, nem numa party
                        ##OU ser o utilizador quiser sair da party
                        if not checker:
                            if invitation == "LEAVE":
                                #Se o player nao estiver numa party
                                if (not self.verificarPartyMember(cc)):
                                    client_socket.send(bytes("You're not in a party",'utf-8'))
                                else:
                                    for party_num, list in self.parties.items():
                                        if(dicAux in list):
                                            #Se a party for de tamanho 2
                                            if len(list) == 2:
                                                for user in list:
                                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                        if(client_socket!=user_socket):
                                                            #Enviar informaçao para o outro membro da party
                                                            user_socket.send(bytes("\n"+client_username+" leave the party, party was deleted\n", 'utf-8'))
                                                        #Adicionar players da party aos soloplayer
                                                        self.playersConnected.update({(user_socket, user_address): (user_name, user_cc)})
                                                client_socket.send(bytes("You left the party",'utf-8'))
                                                #Apagar party
                                                del self.parties[party_num]
                                                break
                                            else:
                                                for user in list:
                                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                        if client_socket != user_socket:
                                                            #Enviar informaçao que um membro saiu da party
                                                            user_socket.send(bytes("\n"+client_username+" leave the party", 'utf-8'))
                                                #Remover player da party
                                                list.remove(dicAux)
                                                client_socket.send(bytes("You left the party", 'utf-8'))
                                                #Adicionar player à party
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
                            #Ignorar mensagem (resolver problema do duplo convite)
                            elif invitation == "ignore":
                                invitationFlag = True
                            elif invitation == "startgame":
                                break
                            else:
                                client_socket.send(bytes("\nThat players doesn't exist\n",'utf-8'))
                        #VERIFICAR SE PARTY = 4
                        party44 = False
                        for party_num, list in self.parties.items():
                            if len(list) == 4:
                                for user in list:
                                    for (user_socket, user_address), (user_name, user_cc) in user.items():
                                        if user_socket == client_socket:
                                            party44 = True
                                        else:
                                            user_socket.send(bytes("\nNEW TABLE\n",'utf-8'))
                            if (party44 == True):
                                break
                        if (party44 == True):
                            client_socket.send(bytes("\nNEW TABLE\n", 'utf-8'))
                            invitationFlag = True
                            self.tables.update({party_num : self.parties[party_num]})
                            # the program is able to exit regardless of if there's any threads still running

                            diamonds = 'diamonds'
                            spades = 'spades'
                            hearts = 'hearts'
                            clubs = 'clubs'
                            self.decks.update({party_num : [(i, diamonds) for i in range(2,15)]\
                                                           +[(i, spades) for i in range(2,15)]\
                                                           +[(i, hearts) for i in range(2,15)]\
                                                           +[(i, clubs) for i in range(2,15)]})
                            connectionThread = threading.Thread(target=self.gameStart,
                                                                args=[party_num])
                            connectionThread.daemon = True
                            connectionThread.start()
                            del self.parties[party_num]
                except:
                    #Remover player do lobby
                    print("player disconnected")
                    #self.connections.remove(client_socket)
                    #Se o player estiver numa party
                    if(self.verificarPartyMember(cc)):
                        for party_num, list in self.parties.items():
                            if(dicAux in list):
                                #Se a party for de 2
                                if len(list) == 2:
                                    for user in list:
                                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                                if (client_socket != user_socket):
                                                    user_socket.send(bytes("\n" + client_username + " leave the party, party was deleted\n",'utf-8'))
                                                self.playersConnected.update({(user_socket, user_address): (user_name, user_cc)})
                                    del self.parties[party_num]
                                    break
                                #Se a party for maior que 2
                                else:
                                    for user in list:
                                        for (user_socket, user_address), (user_name, user_cc) in user.items():
                                            if client_socket != user_socket:
                                                user_socket.send(bytes("\n" + client_username + " leave the party", 'utf-8'))
                                    list.remove(dicAux)
                                    self.playersConnected.update(dicAux)
                                    break
                    else:
                        #Retirar player dos solo players
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

    def organizarMesa(self, numTable):
        novaOrdem = []
        for table_num, list in self.tables.items():
            if table_num == numTable:
                for user in list:
                    for (user_socket, user_address) in user.keys():
                        if user_socket == self.firstPlayer:
                            novaOrdem.append(user)
                        elif user_socket != self.firstPlayer and len(novaOrdem) != 0:
                            novaOrdem.append(user)
        for table_num, list in self.tables.items():
            if table_num == numTable:
                for user in list:
                    if user not in novaOrdem:
                        novaOrdem.append(user)
        self.tables[numTable] = novaOrdem


    def gameStart(self, numTable):
        while True:
            #Esperar para que todas as mensagens sejam enviadas
            import time
            time.sleep(1)
            #Enviar para cada jogador o deck, este vai baralhá-lo e enviar de volta
            for table_num, list in self.tables.items():
                if table_num == numTable:
                    for user in list:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nSHUFFLE\n", 'utf-8'))
                            data = json.dumps({"deckShuffle": self.decks[table_num]})
                            user_socket.send(data.encode())
                            dataJson = user_socket.recv(1024)
                            objectJson = json.loads(dataJson.decode())
                            dataShuffled = objectJson['deckShuffled']
                            self.decks[table_num] = dataShuffled
                            user_socket.send(bytes("\nCARD DISTRIBUTION\n", 'utf-8'))
            print(self.decks[numTable])
            #Já todos os players baralharam
            #Enviar para cada jogador, este pode escolher uma carta, baralhar de novo ou trocar uma carta
            while not all(card == self.decks[numTable][0] for card in self.decks[numTable]):
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address) in user.keys():
                                if not all(card == self.decks[table_num][0] for card in self.decks[table_num]):
                                    data = json.dumps({"deckEBT": self.decks[table_num]})
                                    user_socket.send(data.encode())
                                    dataJson = user_socket.recv(1024)
                                    objectJson = json.loads(dataJson.decode())
                                    dataAfterEBT = objectJson['deckAfterEBT']
                                    self.decks[table_num] = dataAfterEBT
            #Mostrar mãos
            for table_num, list in self.tables.items():
                if table_num == numTable:
                    for user in list:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("\nHAND:", 'utf-8'))
                            user_socket.send(bytes("\nPlayer who has the 2 clubs starts playing", 'utf-8'))
                            connectionThread = threading.Thread(target=self.firstplay,
                                                                args=(user_socket, user_address, numTable))
                            connectionThread.daemon = True
                            connectionThread.start()
            #Enquanto nenhum jogador não jogar nada acontece
            while self.firstPlayer == None:
                pass
            ##Organizar ordem das jogadas
            self.organizarMesa(numTable)
            ronda = 1
            while ronda <= 13:
                time.sleep(1)
                cartasRonda = []
                #Jogada de cada jogador
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if(ronda==1):
                                    if user_socket != self.firstPlayer:
                                        user_socket.send(bytes("Your Turn",'utf-8'))
                                        card = user_socket.recv(1024).decode()
                                        while not self.validCard(card):
                                            user_socket.send(bytes("That is not a card", 'utf-8'))
                                            card = user_socket.recv(1024).decode()
                                        cartasRonda.append(card)
                                        #Enviar carta jogada para os restantes jogadores
                                        for table_num2, list2 in self.tables.items():
                                            if table_num2 == numTable:
                                                for user2 in list2:
                                                    for (user_socket2, user_address2) in user2.keys():
                                                        if user_socket != user_socket2:
                                                            user_socket2.send(bytes(user_name + ": " + card, 'utf-8'))
                                    else:
                                        cartasRonda.append(self.firstCard)
                                else:
                                    user_socket.send(bytes("Your Turn", 'utf-8'))
                                    card = user_socket.recv(1024).decode()
                                    while not self.validCard(card):
                                        user_socket.send(bytes("That is not a card", 'utf-8'))
                                        card = user_socket.recv(1024).decode()
                                    cartasRonda.append(card)
                                    for table_num2, list2 in self.tables.items():
                                        if table_num2 == numTable:
                                            for user2 in list2:
                                                for (user_socket2, user_address2) in user2.keys():
                                                    if user_socket != user_socket2:
                                                        user_socket2.send(bytes(user_name + ": " + card, 'utf-8'))
                #Ver quem ganhou a ronda
                vencedor = self.vencedorRonda(cartasRonda)
                cemiterio = 0
                username = ""
                #Pontos por ronda
                for card in cartasRonda:
                    if "hearts" in card:
                        cemiterio += 1
                    elif "Q spades" in card:
                        cemiterio += 13
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for (user_socket, user_address), (user_name, user_cc) in list[vencedor].items():
                            user_socket.send(bytes("You won the round", 'utf-8'))
                            time.sleep(0.1)
                            user_socket.send(bytes("\nHAND:", 'utf-8'))
                            time.sleep(0.1)
                            user_socket.send(bytes("Cemiterio "+str(cemiterio), 'utf-8'))
                            self.firstPlayer = user_socket
                            username = user_name
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address) in user.keys():
                                if user_socket != self.firstPlayer:
                                    user_socket.send(bytes(username+" won the round", 'utf-8'))
                                    time.sleep(0.1)
                                    user_socket.send(bytes("\nHAND:", 'utf-8'))
                self.organizarMesa(numTable)
                ronda += 1
            ##Fim de um jogo
            pontuacao = []
            for table_num, list in self.tables.items():
                if table_num == numTable:
                    for user in list:
                        for (user_socket, user_address) in user.keys():
                            user_socket.send(bytes("End of the game", 'utf-8'))
                            points = int(user_socket.recv(1024).decode())
                            pontuacao.append([user_socket, points])
            #Verificar se algum jogador tem 26 pontos
            maxPoints = False
            for points in pontuacao:
                if 26 == points[1]:
                    maxPoints = True
            for points in pontuacao:
                if maxPoints == True:
                    if 26 == points[1]:
                        points[1] = 0
                    else:
                        points[1] = 26
                points[0].send(bytes("You scored "+str(points[1])+" points",'utf-8'))
            #Reset do deck
            del self.decks[numTable]
            diamonds = 'diamonds'
            spades = 'spades'
            hearts = 'hearts'
            clubs = 'clubs'
            self.decks.update({numTable: [(i, diamonds) for i in range(2, 15)] \
                                          + [(i, spades) for i in range(2, 15)] \
                                          + [(i, hearts) for i in range(2, 15)] \
                                          + [(i, clubs) for i in range(2, 15)]})


    def vencedorRonda(self, cartasRonda):
        cartaMaior = cartasRonda[0].split(" ")
        index = 0
        court_n_ace = ["J", "Q", "K", "A"]
        if cartaMaior[0] == court_n_ace[0]:
            cartaMaior[0] = 11
        elif cartaMaior[0] == court_n_ace[1]:
            cartaMaior[0] = 12
        elif cartaMaior[0] == court_n_ace[2]:
            cartaMaior[0] = 13
        elif cartaMaior[0] == court_n_ace[3]:
            cartaMaior[0] = 14
        cartaMaior[0] = int(cartaMaior[0])
        i=0
        for card in cartasRonda[1:]:
            i+=1
            card = card.split(" ")
            if cartaMaior[1] == card[1]:
                if card[0] == court_n_ace[0]:
                    card[0] = 11
                elif card[0] == court_n_ace[1]:
                    card[0] = 12
                elif card[0] == court_n_ace[2]:
                    card[0] = 13
                elif card[0] == court_n_ace[3]:
                    card[0] = 14
                card[0] = int(card[0])
                if(cartaMaior[0]<card[0]):
                    index = i
                    cartaMaior = card
        return index


    def validCard(self,card):
        baralho = []
        court_n_ace = ["J", "Q", "K", "A"]
        for i in range(2, 11):
            baralho.append(str(i) + " diamonds")
            baralho.append(str(i) + " clubs")
            baralho.append(str(i) + " spades")
            baralho.append(str(i) + " hearts")
        for figure in court_n_ace:
            baralho.append(figure + " diamonds")
            baralho.append(figure + " clubs")
            baralho.append(figure + " spades")
            baralho.append(figure + " hearts")
        if card in baralho:
            return True
        else:
            return False

    def firstplay(self, client_socket, client_address, numTable):
        card = client_socket.recv(1024).decode()
        if card != "jajogado":
            username = ""
            while not self.validCard(card):
                if card == "jajogado":
                    break
                client_socket.send(bytes("That is not a card", 'utf-8'))
                card = client_socket.recv(1024).decode()
            if card != "jajogado":
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if client_socket == user_socket:
                                    username = user_name
                for table_num, list in self.tables.items():
                    if table_num == numTable:
                        for user in list:
                            for (user_socket, user_address), (user_name, user_cc) in user.items():
                                if user_socket != client_socket:
                                    user_socket.send(bytes(username+" started the round",'utf-8'))
                                    user_socket.send(bytes(username+": "+card, 'utf-8'))
                self.firstCard=card
                self.firstPlayer=client_socket


    def handler(self,client_socket, client_address):
        self.lobby(client_socket, client_address);

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

    probEscolha = 0
    probTroca = 0
    probBaralha = 0

    mao = []

    cemiterio = 0
    totalPoints = 0

    def sendMsg(self):
        while not self.clientDisconnect:
            try:
                if(self.flagTurn):
                    frase = input("")
                    self.clientSocket.send(bytes(frase, 'utf-8'))
                    if frase in self.printMao():
                        card = frase.split(" ")
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
                        self.mao.remove(card)
                    if(self.flagTurnStart):
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

    def shuffle(self,deck):
        random.shuffle(deck)
        return deck

    def printMao(self):
        retorno=[]
        court_n_ace = ["J", "Q", "K", "A"]
        for card in self.mao:
            if(card[0]<11):
                retorno.append(str(card[0])+" "+card[1])
            elif card[0]<15 and card[0]>=11:
                retorno.append(str(court_n_ace[card[0] - 11])+" "+card[1])
        return retorno


    def __init__(self, address):
        self.clientSocket.connect((address, 10001))

        #Probabilidade do client escolher, trocar e baralhar
        self.probEscolha = random.randint(1, 8)
        self.probTroca = random.randint(self.probEscolha+1, 9)
        self.probBaralha = random.randint(self.probTroca+1, 10)

        self.flagTurn = True
        self.flagTurnStart = False

        inputThread = threading.Thread(target=self.sendMsg)
        inputThread.daemon = True
        inputThread.start()

        while not self.clientDisconnect:
            try:
                data = self.clientSocket.recv(1024)
                if not self.is_json(data.decode()):
                    if "Do you want to play with" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("ignore",'utf-8'))
                    if data and "Cemiterio" not in data.decode('utf-8'):
                        print(str(data, 'utf-8'))
                    if "NEW TABLE" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("startgame",'utf-8'))
                    if "HAND" in data.decode('utf-8'):
                        print(self.printMao())
                    if "started the round" in data.decode('utf-8'):
                        self.clientSocket.send(bytes("jajogado",'utf-8'))
                        self.flagTurn = False
                        self.flagTurnStart = True
                    if "Your Turn" in data.decode('utf-8'):
                        self.flagTurn = True
                    if "Cemiterio" in data.decode('utf-8'):
                        self.cemiterio += int(data.decode('utf-8').split(" ")[1])
                    if "End of the game" in data.decode('utf-8'):
                        self.clientSocket.send(bytes(str(self.cemiterio), 'utf-8'))
                        self.mao.clear()
                        self.cemiterio = 0
                    if "You scored" in data.decode('utf-8'):
                        self.totalPoints += int(data.decode('utf-8').split(" ")[2])
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
                        deck = data["deckEBT"]
                        action = random.randint(0, 10)
                        #print("A:"+str(action)+" E:"+str(self.probEscolha)+" T:"+str(self.probTroca)+" B:"+str(self.probBaralha))
                        if action <= self.probEscolha:
                            if len(self.mao) < 13:
                                card = random.randint(0, 51)
                                while deck[card] == [0, 0]:
                                    card = random.randint(0, 51)
                                self.mao.append(deck[card])
                                deck[card] = (0, 0)
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
                            else:
                                deck = self.shuffle(deck)
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
                        elif action >= self.probBaralha:
                            deck = self.shuffle(deck)
                            deckJson = json.dumps({"deckAfterEBT": deck})
                            self.clientSocket.send(deckJson.encode())
                        else:
                            if len(self.mao) != 0:
                                troca = random.randint(0, len(self.mao))
                                card = random.randint(0, 51)
                                while deck[card] == [0, 0]:
                                    card = random.randint(0, 51)
                                self.mao.append(deck[card])
                                deck[card] = self.mao[troca]
                                del self.mao[troca]
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
                            else:
                                deck = self.shuffle(deck)
                                deckJson = json.dumps({"deckAfterEBT": deck})
                                self.clientSocket.send(deckJson.encode())
            except:
                self.clientDisconnect=True
                self.clientSocket.close()

if(len(sys.argv) > 1):
    client = Client(sys.argv[1])
else:
    server = Server()
>>>>>>> 9902cafd5ae49e843b430fcf7e9a3fb37e0c2411
    server.run()