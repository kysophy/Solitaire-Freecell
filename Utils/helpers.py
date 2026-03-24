from Utils.constants import RANK_VALUE, SUIT_COLOR

#card
def _rank_value(rank):
    return RANK_VALUE[rank]
 
def _color(suit):
    return SUIT_COLOR[suit]

#can u put the card there?
def _valid_on_tableau(card, target):
    if target is None:
        return True
    rank,   suit   = card
    t_rank, t_suit = target
    return (
        _color(suit) != _color(t_suit)                        # opposite color
        and _rank_value(rank) == _rank_value(t_rank) - 1      # one rank lower
    )

def _valid_on_foundation(card, pile):
    rank, suit = card
    if not pile:
        return rank == "A"
    top_rank, top_suit = pile[-1]
    return (
        suit == top_suit                                       # same suit
        and _rank_value(rank) == _rank_value(top_rank) + 1    # one rank higher
    )
