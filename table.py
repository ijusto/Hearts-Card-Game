from player import Player
from card import *

# Order of events
# set the eldest player (with 2 of clubs) and order of player in the round
# tell everyone (except the first player) what is the order (the first player)
# tell the first player to play
# receive the first play
# tell everyone (except the first player) what he played
#

from trick import Trick

class Table:
    def __init__(self, id, players):
        self.id = id
        self.trick_id = 1
        self.players = players
        self.trick = Trick(self.trick_id, self.players)
        self.dealPoints = {}
        self.generalPoints = {}
        for player in self.players:
            self.generalPoints[player] = 0
            self.dealPoints[player] = 0

        self.ready = False

    def all_points(self):
        # If one player takes all the penalty cards on one deal, that player's score remains unchanged while 26 penalty
        # points are added to the scores of each of the other players.
        if 26 in [self.dealPoints[player] for player in self.players]:
            return True
        return False


    def updateGeneralPoints(self):
        # if one deal just happened
        if(self.trick_id % 13):
            if(self.all_points()):
                for player in self.players:
                    if player != self.trick.winner:
                        self.generalPoints[player] += 26
            else:
                for player in self.players:
                    self.generalPoints[player] += self.dealPoints[player]

            # reset deal points
            for player in self.players:
                self.dealPoints[player] = 0


    def updateDealPoints(self):
        self.dealPoints[self.trick.winner] = self.trick.getWinnerScore()


    def connected(self):
        return self.ready





# ----- Passing cards --------------------------------------------------------------------------------------------------
# Before each hand begins, each player chooses three cards, and passes them to another player.
# the most common (popularized by computer versions) rotates passing through four deals; on the first deal, players pass
# to the left, the second deal to the right, the third across the table. On the fourth deal no cards are passed; the
# cycle of four deals is then repeated.
#
# ----- Gameplay -------------------------------------------------------------------------------------------------------
# Players must follow suit;
# If they are not able to do so, they can play any card
# No penalty card may be played on the first trick (hearts or spades_Q)
# Hearts cannot be led until they have been "broken" (discarded on the lead of another suit), unless the player who must
# lead has nothing but Hearts remaining in hand.
#
