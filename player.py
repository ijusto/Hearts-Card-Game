import pygame
from card import Card

class Player():
    def __init__(self, hand):
        self.username = ''
        self.hand = self.redistributeHand(hand)
        # The first to play in the round
        self.isEldest = False
        # The last to play in the round
        self.youngest = False

    def redistributeHand(self, hand):
        sortedHand = sorted(hand, key=lambda card: card.rank, reverse=True)
        hearts = [card for card in sortedHand if card.suit == 'hearts']
        spades = [card for card in sortedHand if card.suit == 'spades']
        diamonds = [card for card in sortedHand if card.suit == 'diamonds']
        clubs = [card for card in sortedHand if card.suit == 'clubs']
        return hearts + spades + diamonds + clubs

    def draw(self, window):
        # window.blit(pygame.image.load(self.card), (self.rect[0], self.rect[1]))
        # pygame.draw.rect(window, self.color, self.rect)
        pass

    def play(self, card):
        if(card not in self.hand):
            print("CHEATING!!!")
        else:
            self.hand.remove(card)
            self.update(card)

    def update(self, card):
        # update interface
        pass