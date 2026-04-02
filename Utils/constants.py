# Rank string to numeric value
RANK_VALUE = {
    "A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13
}

RANK_VALUES = RANK_VALUE  # Alias used by IDS solver helpers

# Numeric value to rank string (reverse mapping)
VALUE_RANKS = {v: k for k, v in RANK_VALUE.items()}

# Full suit name to color
SUIT_COLOR = {
    "Hearts": "red", "Diamonds": "red",
    "Clubs": "black", "Spades": "black",
}

OPPOSITE_COLOR_SUITS = {
    "Hearts":   ("Clubs",    "Spades"),
    "Diamonds": ("Clubs",    "Spades"),
    "Clubs":    ("Hearts",   "Diamonds"),
    "Spades":   ("Hearts",   "Diamonds"),
}

ALL_SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")

# Full suit names list
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]

# All 13 ranks in order
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

# Single-character suit abbreviations for compact solver state representation
SUIT_CHAR = {"Hearts": "H", "Diamonds": "D", "Clubs": "C", "Spades": "S"}
CHAR_SUIT = {v: k for k, v in SUIT_CHAR.items()}

# Suit character sets by color (used by IDS solver)
RED_SUITS = {"H", "D"}
BLACK_SUITS = {"C", "S"}

# Board dimensions
NUM_CASCADES = 8
NUM_FREECELLS = 4
NUM_FOUNDATIONS = 4
TOTAL_CARDS = 52
