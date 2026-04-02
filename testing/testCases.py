import random
from Game.deck import create_deck

def createDeckFromSeed(seedValue):
    random.seed(seedValue)
    newDeck = create_deck()
    random.shuffle(newDeck)
    return newDeck