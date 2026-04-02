"""Difficulty-based FreeCell board generator.

Builds organized base layout (valid alternating-color descending sequences),
then disrupts with random card swaps calibrated to solver difficulty:
  Easy:   1-2 swaps  -- IDS solves quickly
  Medium: 3-5 swaps  -- IDS needs significant work
  Hard:   8-15 swaps -- IDS may time out
  Expert: pure random shuffle (caller handles)
"""

import random
from Utils.constants import SUITS, SUIT_CHAR, CHAR_SUIT, VALUE_RANKS


def _build_perfect_columns():
    """Build 8 columns of valid alternating-color descending sequences using all 52 cards."""
    red = ["H", "D"]
    black = ["C", "S"]
    random.shuffle(red)
    random.shuffle(black)

    configs = [
        (red[0], black[0]),
        (red[1], black[1]),
        (black[0], red[0]),
        (black[1], red[1]),
    ]

    columns = []

    # 4 columns of 7 cards (K through 7)
    for primary, secondary in configs:
        col = []
        for j, rank in enumerate(range(13, 6, -1)):
            suit = primary if j % 2 == 0 else secondary
            col.append(f"{VALUE_RANKS[rank]}{suit}")
        columns.append(col)

    # 4 columns of 6 cards (6 through A)
    for primary, secondary in configs:
        col = []
        for j, rank in enumerate(range(6, 0, -1)):
            suit = primary if j % 2 == 0 else secondary
            col.append(f"{VALUE_RANKS[rank]}{suit}")
        columns.append(col)

    random.shuffle(columns)
    return columns


def _apply_swaps(columns, num_swaps):
    """Randomly swap card positions across columns to introduce disorder."""
    positions = []
    for ci, col in enumerate(columns):
        for ri in range(len(col)):
            positions.append((ci, ri))

    for _ in range(num_swaps):
        (c1, r1), (c2, r2) = random.sample(positions, 2)
        columns[c1][r1], columns[c2][r2] = columns[c2][r2], columns[c1][r1]


def generate_state(difficulty="Easy"):
    """Generate a FreeCell starting board for the chosen difficulty.

    Returns solver-format state (tableau, freecells, foundations),
    or None for "Expert" (caller should use random shuffle).
    """
    if difficulty == "Expert":
        return None

    columns = _build_perfect_columns()

    swap_ranges = {
        "Easy":   (1,  2),
        "Medium": (3,  5),
        "Hard":   (8,  15),
    }
    lo, hi = swap_ranges.get(difficulty, (20, 40))
    _apply_swaps(columns, num_swaps=random.randint(lo, hi))

    tableau = tuple(tuple(col) for col in columns)
    freecells = (None, None, None, None)
    foundations = ((None, 0), (None, 0), (None, 0), (None, 0))

    return (tableau, freecells, foundations)


def state_to_cards(state):
    """Convert solver-format state back to GUI Card objects.

    Returns (gui_tableau, gui_freecells, gui_foundations).
    """
    from Game.card import Card

    tableau, freecells, foundations = state

    gui_tableau = []
    for col in tableau:
        gui_col = []
        for card_s in col:
            rank = card_s[:-1]
            suit = CHAR_SUIT[card_s[-1]]
            gui_col.append(Card(rank, suit))
        gui_tableau.append(gui_col)

    gui_freecells = []
    for card_s in freecells:
        if card_s is None:
            gui_freecells.append(None)
        else:
            rank = card_s[:-1]
            suit = CHAR_SUIT[card_s[-1]]
            gui_freecells.append(Card(rank, suit))

    gui_foundations = []
    for suit_char, rank_int in foundations:
        pile = []
        if suit_char is not None and rank_int > 0:
            full_suit = CHAR_SUIT[suit_char]
            for r in range(1, rank_int + 1):
                pile.append(Card(VALUE_RANKS[r], full_suit))
        gui_foundations.append(pile)

    return gui_tableau, gui_freecells, gui_foundations
