import random
from .card import Card

def create_deck(seed=None):

    suits = ["Hearts","Diamonds","Clubs","Spades"]
    ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

    deck = [Card(r,s) for s in suits for r in ranks]
    if seed is not None:
        random.seed(seed)
    random.shuffle(deck)

    return deck
