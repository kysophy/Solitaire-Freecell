from Utils.constants import RANK_VALUE, SUIT_COLOR, RANK_VALUES, RED_SUITS


# ── A* solver helpers ──

def _rank_value(rank):
    return RANK_VALUE[rank]

def _color(suit):
    return SUIT_COLOR[suit]

def _valid_on_tableau(card, target):
    """Check if card (rank, suit) tuple can be placed on target in A* format."""
    if target is None:
        return True
    rank, suit = card
    t_rank, t_suit = target
    return (
        _color(suit) != _color(t_suit)
        and _rank_value(rank) == _rank_value(t_rank) - 1
    )

def _valid_on_foundation(card, pile):
    """Check if card (rank, suit) tuple can be placed on foundation pile in A* format."""
    rank, suit = card
    if not pile:
        return rank == "A"
    top_rank, top_suit = pile[-1]
    return (
        suit == top_suit
        and _rank_value(rank) == _rank_value(top_rank) + 1
    )


# ── IDS solver helpers ──
# The IDS solver uses a string-based state: cards as "AH"/"10C",
# foundations as (suit_char, top_rank_int) tuples.

def card_str(card):
    """Convert a Card object to compact string via repr (e.g. "AH", "10C")."""
    return repr(card)

def get_suit(card_s):
    """Extract suit character from card string (last character)."""
    return card_s[-1]

def get_rank(card_s):
    """Extract numeric rank value from card string."""
    return RANK_VALUES[card_s[:-1]]

def get_color(card_s):
    """Get color ("red" or "black") of a card string."""
    return "red" if card_s[-1] in RED_SUITS else "black"


def game_to_state(tableau, freecells, foundations):
    """Convert GUI Card objects to IDS solver's immutable tuple state."""
    t = tuple(
        tuple(card_str(c) for c in col)
        for col in tableau
    )
    f = tuple(
        card_str(c) if c else None
        for c in freecells
    )
    fnd = []
    for pile in foundations:
        if pile:
            suit_ch = pile[0].suit[0]
            top_rank = RANK_VALUES[pile[-1].rank]
            fnd.append((suit_ch, top_rank))
        else:
            fnd.append((None, 0))
    return (t, f, tuple(fnd))


def canonical_hash(state):
    """Hash a state canonically (column/cell/foundation order-independent)."""
    tableau, freecells, foundations = state
    sorted_t = tuple(sorted(tableau))
    sorted_f = tuple(sorted(freecells, key=lambda x: x if x else ""))
    sorted_fnd = tuple(sorted(foundations, key=lambda x: x[0] if x[0] else "~"))
    return hash((sorted_t, sorted_f, sorted_fnd))


def is_goal(state):
    """Check if all four foundations have reached King (rank 13)."""
    _, _, foundations = state
    return all(rank == 13 for _, rank in foundations)


def can_place_on_foundation(card_s, foundations):
    """Return foundation index where card_s can be placed, or -1."""
    suit = get_suit(card_s)
    rank = get_rank(card_s)
    for i, (f_suit, f_rank) in enumerate(foundations):
        if f_suit == suit and f_rank == rank - 1:
            return i
    if rank == 1:
        for i, (f_suit, f_rank) in enumerate(foundations):
            if f_suit is None:
                return i
    return -1


def can_place_on_tableau(card_s, column):
    """Check if card_s can be placed on a tableau column (IDS string format)."""
    if not column:
        return True
    top = column[-1]
    return (get_color(card_s) != get_color(top) and
            get_rank(card_s) == get_rank(top) - 1)


def max_movable(state, dest_col_idx):
    """Max cards movable via supermove: (1 + empty_freecells) * 2^empty_columns."""
    tableau, freecells, _ = state
    empty_fc = sum(1 for c in freecells if c is None)
    empty_cols = sum(
        1 for i, col in enumerate(tableau)
        if not col and i != dest_col_idx
    )
    return (empty_fc + 1) * (2 ** empty_cols)


def find_sequence_length(column):
    """Length of valid descending alternating-color sequence at column bottom."""
    if not column:
        return 0
    length = 1
    for i in range(len(column) - 1, 0, -1):
        above = column[i - 1]
        below = column[i]
        if (get_color(above) != get_color(below) and
                get_rank(above) == get_rank(below) + 1):
            length += 1
        else:
            break
    return length


def is_safe_auto_move(card_s, foundations):
    """Check if auto-moving this card to foundation is safe (won't block future plays).

    Safe when no card in play could need it as a tableau target:
    Aces/2s are always safe; higher ranks require both opposite-color suits
    to have foundation progress >= rank - 1.
    """
    rank = get_rank(card_s)
    if rank <= 2:
        return True
    my_color = get_color(card_s)
    needed_suits = {"C", "S"} if my_color == "red" else {"H", "D"}
    for needed_suit in needed_suits:
        suit_progress = 0
        for f_suit, f_rank in foundations:
            if f_suit == needed_suit:
                suit_progress = f_rank
                break
        if suit_progress < rank - 1:
            return False
    return True


def auto_play_foundations(state):
    """Automatically move all safe cards to foundations. Returns (new_state, auto_moves)."""
    auto_moves = []
    changed = True
    while changed:
        changed = False
        tableau, freecells, foundations = state
        for i in range(len(tableau)):
            if not tableau[i]:
                continue
            card = tableau[i][-1]
            fnd_idx = can_place_on_foundation(card, foundations)
            if fnd_idx >= 0 and is_safe_auto_move(card, foundations):
                move = ('t', i, 'h', fnd_idx, 1)
                state = apply_move(state, move)
                auto_moves.append(move)
                changed = True
                break
        if changed:
            continue
        for i in range(len(freecells)):
            if not freecells[i]:
                continue
            card = freecells[i]
            fnd_idx = can_place_on_foundation(card, foundations)
            if fnd_idx >= 0 and is_safe_auto_move(card, foundations):
                move = ('f', i, 'h', fnd_idx, 1)
                state = apply_move(state, move)
                auto_moves.append(move)
                changed = True
                break
    return state, auto_moves


def evaluate_state(state):
    """Heuristic score for move ordering: higher = closer to winning."""
    tableau, freecells, foundations = state
    score = 0

    for _, rank in foundations:
        score += rank * 10
    score += sum(6 for c in freecells if c is None)
    score += sum(8 for col in tableau if not col)

    fnd_progress = {}
    for f_suit, f_rank in foundations:
        if f_suit:
            fnd_progress[f_suit] = f_rank

    for col in tableau:
        if not col:
            continue
        seq_len = find_sequence_length(col)
        score += seq_len * 2
        for i, card_s in enumerate(col):
            suit = get_suit(card_s)
            rank = get_rank(card_s)
            needed_rank = fnd_progress.get(suit, 0) + 1
            if rank == needed_rank and i < len(col) - 1:
                score -= (len(col) - 1 - i) * 3

    return score


def get_all_moves(state):
    """Generate all legal moves. Order: foundation, tableau-tableau, freecell-tableau, tableau-freecell."""
    tableau, freecells, foundations = state
    moves = []

    # Foundation moves (highest priority)
    for i in range(8):
        if not tableau[i]:
            continue
        card = tableau[i][-1]
        fnd_idx = can_place_on_foundation(card, foundations)
        if fnd_idx >= 0:
            moves.append(('t', i, 'h', fnd_idx, 1))

    for i in range(4):
        if not freecells[i]:
            continue
        fnd_idx = can_place_on_foundation(freecells[i], foundations)
        if fnd_idx >= 0:
            moves.append(('f', i, 'h', fnd_idx, 1))

    # Tableau-to-Tableau (including supermoves)
    for i in range(8):
        if not tableau[i]:
            continue
        col = tableau[i]
        max_seq = find_sequence_length(col)
        tried_empty = False
        for j in range(8):
            if i == j:
                continue
            is_empty_dest = (not tableau[j])
            if is_empty_dest:
                if tried_empty:
                    continue
                tried_empty = True
            max_move = max_movable(state, j)
            for seq_len in range(1, min(max_seq, max_move) + 1):
                card_idx = len(col) - seq_len
                top_card = col[card_idx]
                if is_empty_dest:
                    if seq_len == len(col):
                        continue
                    moves.append(('t', i, 't', j, seq_len))
                else:
                    target_top = tableau[j][-1]
                    if (get_color(top_card) != get_color(target_top) and
                            get_rank(top_card) == get_rank(target_top) - 1):
                        moves.append(('t', i, 't', j, seq_len))

    # Freecell-to-Tableau
    for i in range(4):
        if not freecells[i]:
            continue
        card = freecells[i]
        tried_empty = False
        for j in range(8):
            if not tableau[j]:
                if not tried_empty:
                    moves.append(('f', i, 't', j, 1))
                    tried_empty = True
            elif can_place_on_tableau(card, tableau[j]):
                moves.append(('f', i, 't', j, 1))

    # Tableau-to-Freecell (first empty slot only, all equivalent)
    first_empty_fc = None
    for i in range(4):
        if freecells[i] is None:
            first_empty_fc = i
            break
    if first_empty_fc is not None:
        for i in range(8):
            if tableau[i]:
                moves.append(('t', i, 'f', first_empty_fc, 1))

    return moves


def apply_move(state, move):
    """Apply a move to state, returning a new immutable state (pure function)."""
    tableau, freecells, foundations = state
    src_type, src_idx, dst_type, dst_idx, num_cards = move

    new_t = [list(col) for col in tableau]
    new_f = list(freecells)
    new_fnd = list(foundations)

    if src_type == 't':
        cards = new_t[src_idx][-num_cards:]
        del new_t[src_idx][-num_cards:]
    else:
        cards = [new_f[src_idx]]
        new_f[src_idx] = None

    if dst_type == 't':
        new_t[dst_idx].extend(cards)
    elif dst_type == 'f':
        new_f[dst_idx] = cards[0]
    elif dst_type == 'h':
        card = cards[0]
        new_fnd[dst_idx] = (get_suit(card), get_rank(card))

    return (
        tuple(tuple(col) for col in new_t),
        tuple(new_f),
        tuple(new_fnd)
    )
