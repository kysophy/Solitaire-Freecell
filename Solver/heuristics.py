from Utils.constants import RANK_VALUE, ALL_SUITS, SUIT_COLOR, OPPOSITE_COLOR_SUITS

def _heuristic(tab, fc, fd):
    """
    Weighted A* heuristic for FreeCell.

    Admissible base: every card not yet on a foundation needs at least 1 move.
    On top of that we add a controlled inadmissible bonus (weight W > 1) to
    guide search toward the goal faster — sacrificing optimal solution length
    for drastically fewer expansions.
    """
    W = 3   # weight — increase to solve faster but with longer solutions

    in_foundation  = sum(len(pile) for pile in fd)
    cards_not_home = 52 - in_foundation

    if cards_not_home == 0:
        return 0

    # Next rank needed per suit
    next_needed = {}
    for pile in fd:
        if pile:
            top_rank, top_suit = pile[-1]
            next_needed[top_suit] = RANK_VALUE[top_rank] + 1
    for suit in ALL_SUITS:
        if suit not in next_needed:
            next_needed[suit] = 1

    # How many cards sit ON TOP of each card in tableau
    cards_above = {}
    for col in tab:
        col_len = len(col)
        for depth, (rank, suit) in enumerate(col):
            cards_above[(RANK_VALUE[rank], suit)] = col_len - 1 - depth
    for slot in fc:
        if slot is not None:
            rank, suit = slot
            cards_above[(RANK_VALUE[rank], suit)] = 0

    # Count cards that directly block the next needed card per suit
    blocking = 0
    for suit in ALL_SUITS:
        needed_rv = next_needed[suit]
        if needed_rv > 13:
            continue
        blocking += cards_above.get((needed_rv, suit), 0)

    # Penalty for cards out of order in tableau (not in valid descending alternating sequence)
    disorder = 0
    for col in tab:
        for i in range(len(col) - 1):
            r1, s1 = col[i]
            r2, s2 = col[i + 1]
            if not (RANK_VALUE[r1] == RANK_VALUE[r2] + 1 and
                    SUIT_COLOR[s1] != SUIT_COLOR[s2]):
                disorder += 1

    h = cards_not_home + blocking + disorder
    return h * W