from Utils.constants import RANK_VALUE, ALL_SUITS, SUIT_COLOR

def _heuristic(tab, fc, fd):

    in_foundation  = sum(len(pile) for pile in fd)
    cards_not_home = 52 - in_foundation

    if cards_not_home == 0:
        return 0

    next_needed = {suit: 1 for suit in ALL_SUITS}
    for pile in fd:
        if pile:
            top_rank, top_suit = pile[-1]
            next_needed[top_suit] = RANK_VALUE[top_rank] + 1

    card_above = {}
    for col in tab:
        col_len = len(col)
        for depth, (rank, suit) in enumerate(col):
            card_above[(RANK_VALUE[rank], suit)] = col_len - 1 - depth
    for slot in fc:
        if slot is not None:
            rank, suit = slot
            card_above[(RANK_VALUE[rank], suit)] = 0

    blocking = 0
    for suit, needed_rv in next_needed.items():
        if needed_rv > 13:
            continue
        blocking += card_above.get((needed_rv, suit), 0)

    used_freecells = sum(1 for c in fc if c is not None)

    cascade = 0
    for col in tab:
        col_len = len(col)
        for depth, (rank, suit) in enumerate(col):
            if RANK_VALUE[rank] == next_needed[suit] and depth < col_len - 1:
                for b_depth in range(depth + 1, col_len):
                    b_rank, b_suit = col[b_depth]
                    if (RANK_VALUE[b_rank] == next_needed[b_suit]
                            and card_above.get((RANK_VALUE[b_rank], b_suit), 0) > 0):
                        cascade += 1

    return (cards_not_home * 10
            + blocking * 5
            + used_freecells * 3
            + cascade * 2)