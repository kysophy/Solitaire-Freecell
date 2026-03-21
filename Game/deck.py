import random
from .card import Card

#change to all solvable deals
def _ms_freecell_rng(seed):
    max_int = 2 ** 31 - 1
    seed    = seed % (max_int + 1)

    cards = list(range(52)) 
    result = []

    for i in range(51, 0, -1):
        seed   = (seed * 214013 + 2531011) & max_int
        j      = (seed >> 16) % (i + 1)
        cards[i], cards[j] = cards[j], cards[i]

    return cards


def _card_from_index(index):
    suits = ["Clubs", "Diamonds", "Hearts", "Spades"]
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    return Card(ranks[index % 13], suits[index // 13])


def create_deck(seed=None):
    import random

    if seed is None:
        seed = random.randint(1, 32000)
        while seed == 11982:          # skip the one unsolvable deal
            seed = random.randint(1, 32000)

    indices = _ms_freecell_rng(seed)
    return [_card_from_index(i) for i in indices], seed