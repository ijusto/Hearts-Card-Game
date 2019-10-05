from card import Card
from rank import Rank
from suit import Suit

class Trick:
    def __init__(self, id, players):
        self.id = id

        self.eldestPlayer = None
        self.youngestPlayer = None

        self.players = players

        self.lead = Suit('clubs', True)

        # cards on the table
        self.card_moves = [None, None, None, None]
        self.winner = None

        self.nextPlayer = None
        self.plays = {}

        # modifies self.eldestPlayer, self.youngestPlayer, self.players
        self.setPlayerOrder()


    def setPlayerOrder(self):
        # first trick
        if self.eldestPlayer == None:
            for i in range(len(self.players)):
                for card in self.players[i].hand:
                    # The player holding clubs_2 must lead it to begin the first trick
                    if card.rank == Rank(2) and card.suit.name == 'clubs':
                        self.players = self.players[i:] + self.players[:i]
                        self.eldestPlayer = self.players[i]
                        self.youngestPlayer = self.players[len(self.players) - 1]
        # other trick
        else:
            for i in range(len(self.players)):
                if self.players[i] == self.eldestPlayer:
                    self.players = self.players[i:] + self.players[:i]
                    self.youngestPlayer = self.players[len(self.players) - 1]


    def getRoundScorer(self):
        higher_card = self.card_moves[0]
        win = (higher_card, 0)
        for i in range(len(self.card_moves[1:])):
            if not higher_card.higher(self.card_moves[i]):
                higher_card = self.card_moves[i]
                win = (higher_card, i)
        self.winner = self.players[win[1]]

    # There are thus 26 penalty points in each deal. The game usually ends when one player reaches
    # or exceeds 100 points, or, in some variations, after a predetermined number of deals or period of time. In any of
    # these cases, the winning player is the one with the fewest penalty points
    def getWinnerScore(self):
        points = 0
        for card in self.card_moves:
            # Each Heart taken in a trick scores one penalty point against the player winning the trick
            if card.suit.name == 'hearts':
                points += 1
            # Taking spades_Q costs 13 penalty points.
            elif card.suit.name == 'spades' and card.rank.num == 12:
                points += 13
        return points


    def get_player_move(self, p):
        """
        :param p: [0,1,2,3]
        :return: Card
        """
        return self.card_moves[p]


    def play(self, player, move):
        self.card_moves[player] = move


    def start(self):
        """
        :return: Round id
        """
        while True:
            if None not in self.card_moves and self.winner != None:
                return self.id