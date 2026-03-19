def color(card):
    if card.suit in ["Hearts","Diamonds"]:
        return "red"
    return "black"


def rank_value(rank):
    values = {
        "A":1,"2":2,"3":3,"4":4,"5":5,
        "6":6,"7":7,"8":8,"9":9,"10":10,
        "J":11,"Q":12,"K":13
    }
    return values[rank]