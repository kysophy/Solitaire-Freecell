from Game.card import Card
import Solver.ucs as ucs

def make_col(cards):
    return [Card(rank, suit) for rank, suit in cards]

# Board lấy theo đúng thứ tự hiển thị từ trên xuống dưới trong ảnh
# Trong code của bạn, lá top/movable là phần tử cuối cột.
tableau = [
    make_col([
        ("5", "Hearts"),
        ("3", "Clubs"),
        ("6", "Hearts"),
        ("4", "Spades"),
        ("Q", "Hearts"),
        ("3", "Spades"),
        ("8", "Hearts"),
    ]),
    make_col([
        ("A", "Spades"),
        ("Q", "Clubs"),
        ("7", "Spades"),
        ("Q", "Spades"),
        ("2", "Spades"),
        ("4", "Hearts"),
        ("K", "Diamonds"),
    ]),
    make_col([
        ("6", "Diamonds"),
        ("9", "Clubs"),
        ("10", "Spades"),
        ("4", "Diamonds"),
        ("10", "Diamonds"),
        ("9", "Hearts"),
        ("A", "Diamonds"),
    ]),
    make_col([
        ("J", "Hearts"),
        ("9", "Diamonds"),
        ("5", "Clubs"),
        ("7", "Diamonds"),
        ("10", "Hearts"),
        ("6", "Spades"),
        ("Q", "Diamonds"),
    ]),
    make_col([
        ("7", "Clubs"),
        ("9", "Spades"),
        ("2", "Hearts"),
        ("J", "Spades"),
        ("7", "Hearts"),
        ("J", "Clubs"),
    ]),
    make_col([
        ("8", "Spades"),
        ("3", "Hearts"),
        ("4", "Clubs"),
        ("A", "Hearts"),
        ("2", "Diamonds"),
        ("8", "Diamonds"),
    ]),
    make_col([
        ("3", "Diamonds"),
        ("5", "Diamonds"),
        ("5", "Spades"),
        ("J", "Diamonds"),
        ("K", "Spades"),
        ("6", "Clubs"),
    ]),
    make_col([
        ("A", "Clubs"),
        ("K", "Hearts"),
        ("10", "Clubs"),
        ("K", "Clubs"),
        ("2", "Clubs"),
        ("8", "Clubs"),
    ]),
]

freecells = [None] * 4
foundations = [[] for _ in range(4)]

actions = ucs.solve(
    tableau,
    freecells,
    foundations,
    max_states=5_000_000,
    timeout_sec=180
)

print("\n=== RESULT ===")
print("Solved:", actions is not None)
print("Number of actions:", 0 if actions is None else len(actions))
print("Stats:", ucs.LAST_RUN_STATS)