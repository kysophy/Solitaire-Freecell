import ctypes
import random
from .card import Card

def _ms_freecell_rng(seed):
    s = ctypes.c_int(seed)
    deck = list(range(52))
    for i in range(51, -1, -1):
        s = ctypes.c_int(s.value * 214013 + 2531011)
        j = (ctypes.c_uint(s.value).value >> 16) % (i + 1)
        deck[i], deck[j] = deck[j], deck[i]
    return deck

def _card_from_index(index):
    ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
    suits = ["Clubs","Diamonds","Hearts","Spades"]
    return Card(ranks[index % 13], suits[index // 13])

def create_deck(seed=None):
    if seed is None:
        seed = random.randint(1, 32000)
        while seed == 11982:
            seed = random.randint(1, 32000)

    indices = _ms_freecell_rng(seed)
    return [_card_from_index(i) for i in indices], seed