diamond = 'diamond'
spades = 'spades'
hearts = 'hearts'
clubs = 'clubs'
# Card rank (highest first)	A-14 K-13 Q-12 J-11 10 9 8 7 6 5 4 3 2, no trump
deck = [(diamond, i) for i in range(2,15)]\
       +[(spades, i) for i in range(2,15)]\
       +[(hearts, i) for i in range(2,15)]\
       +[(clubs, i) for i in range(2,15)]

from rank import Rank
from suit import Suit

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.img = suit + '.png'

    def higher(self, other_card):
        if self.rank > other_card.rank and self.suit.lead:
            return 1
        return 0


