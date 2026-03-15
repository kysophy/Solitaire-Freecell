import tkinter as tk
import random
import time
import copy

class Card:

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit[0]}"

def create_deck():

    suits = ["Hearts","Diamonds","Clubs","Spades"]
    ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

    deck = [Card(r,s) for s in suits for r in ranks]

    random.shuffle(deck)

    return deck


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


class FreeCell:

    def __init__(self,root):

        self.root = root
        self.root.title("FreeCell")
        self.root.geometry("1000x650")
        self.card_images = {}
        self.load_card_images()

        self.moves = 0
        self.history = []
        self.start_time = time.time()

        # board
        self.tableau=[[] for _ in range(8)]
        self.freecells=[None]*4
        self.foundations=[[] for _ in range(4)]

        # dragging
        self.drag_stack=[]
        self.drag_source=None
        self.drag_x=0
        self.drag_y=0

        self.build_gui()
        self.new_game()

    def build_gui(self):

        self.canvas=tk.Canvas(self.root, bg="darkgreen")
        self.canvas.pack(fill="both", expand=True)

        panel=tk.Frame(self.root)
        panel.pack(fill="x")

        tk.Button(panel,text="New Game",command=self.new_game).pack(side="left")
        tk.Button(panel,text="Undo",command=self.undo).pack(side="left")

        self.move_label=tk.Label(panel,text="Moves: 0")
        self.move_label.pack(side="left",padx=20)

        self.timer_label=tk.Label(panel,text="Time: 0")
        self.timer_label.pack(side="left")

        self.canvas.bind("<Button-1>",self.click)
        self.canvas.bind("<B1-Motion>",self.drag)
        self.canvas.bind("<ButtonRelease-1>",self.drop)



    def new_game(self):

        deck=create_deck()

        self.tableau=[[] for _ in range(8)]
        self.freecells=[None]*4
        self.foundations=[[] for _ in range(4)]

        col=0

        while deck:
            self.tableau[col].append(deck.pop())
            col=(col+1)%8

        self.moves=0
        self.history=[]
        self.start_time=time.time()

        self.draw()
        self.update_timer()

    def max_movable_cards(self, target_col=None):

        empty_freecells = sum(1 for c in self.freecells if c is None)

        empty_columns = sum(1 for i,col in enumerate(self.tableau)
                            if len(col) == 0 and i != target_col)

        return (empty_freecells + 1) * (2 ** empty_columns)
    
    def load_card_images(self):

        suits = {
            "Spades":"S",
            "Hearts":"H",
            "Diamonds":"D",
            "Clubs":"C"
        }

        ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

        for suit_name, suit_letter in suits.items():
            for rank in ranks:

                filename = f"cards/{rank}{suit_letter}.png"

                img = tk.PhotoImage(file=filename)

                img = img.subsample(3,3)

                self.card_images[(rank, suit_name)] = img

    def draw(self):

        self.canvas.delete("all")

        # freecells
        for i in range(4):

            x=20+i*120
            y=20

            self.canvas.create_rectangle(x,y,x+80,y+100,outline="white")

            if self.freecells[i]:
                self.draw_card(self.freecells[i],x,y)

        # foundations
        for i in range(4):

            x=500+i*120
            y=20

            self.canvas.create_rectangle(x,y,x+80,y+100,outline="white")

            if self.foundations[i]:
                self.draw_card(self.foundations[i][-1],x,y)

        # tableau
        for c in range(8):

            x=20+c*120
            y=150

            for card in self.tableau[c]:

                self.draw_card(card,x,y)
                y+=30

        # dragging stack
        if self.drag_stack:

            x=self.drag_x
            y=self.drag_y

            for card in self.drag_stack:

                self.draw_card(card,x,y)
                y+=30


    def draw_card(self,card,x,y):

        img = self.card_images[(card.rank, card.suit)]

        self.canvas.create_image(
            x,
            y,
            image=img,
            anchor="nw"
        )


# ============================================================
# CLICK
# ============================================================

    def click(self,event):

        x = event.x
        y = event.y

        # =========================
        # CLICK FREECELL
        # =========================
        if 20 <= y <= 120:

            for i in range(4):

                fx = 20 + i*120

                if fx <= x <= fx+80 and self.freecells[i]:

                    self.drag_stack = [self.freecells[i]]
                    self.drag_source = ("freecell", i)

                    self.freecells[i] = None

                    self.drag_x = x
                    self.drag_y = y

                    self.draw()
                    return

            # =========================
            # CLICK FOUNDATION
            # =========================
            for i in range(4):

                fx = 500 + i*120

                if fx <= x <= fx+80 and self.foundations[i]:

                    card = self.foundations[i][-1]

                    self.drag_stack = [card]
                    self.drag_source = ("foundation", i)

                    self.foundations[i].pop()

                    self.drag_x = x
                    self.drag_y = y

                    self.draw()
                    return

        col = (x-20)//120

        if not (0 <= col < 8):
            return

        y_pos = 150
        index = None

        for i in range(len(self.tableau[col])):
            if y_pos <= y <= y_pos+100:
                index = i
            y_pos += 30

        if index is None:
            return

        stack = self.tableau[col][index:]

        if not self.valid_stack(stack):
            return

        max_cards = self.max_movable_cards()

        if len(stack) > max_cards:
            return

        if not self.valid_stack(stack):
            return

        self.drag_stack = stack
        self.drag_source = ("tableau", col, index)

        del self.tableau[col][index:]

        self.drag_x = x
        self.drag_y = y

        self.draw()

    def drag(self,event):

        if not self.drag_stack:
            return

        self.drag_x=event.x
        self.drag_y=event.y

        self.draw()

    def drop(self,event):

        if not self.drag_stack:
            return

        x = event.x
        y = event.y

        placed = False
        card = self.drag_stack[0]

        #Drop FREECELL
        if 10 <= y <= 140:

            for i in range(4):

                fx = 20 + i * 120

                if fx - 10 <= x <= fx + 90:

                    if self.freecells[i] is None and len(self.drag_stack) == 1:

                        self.save_state()

                        self.freecells[i] = card

                        placed = True

                        break

            #drop FOUNDATION
            for i in range(4):

                fx = 500 + i*120

                if fx <= x <= fx+80:

                    pile = self.foundations[i]

                    if not pile:

                        if card.rank == "A":

                            self.save_state()
                            pile.append(card)
                            placed = True

                    else:

                        top = pile[-1]

                        if card.suit == top.suit and rank_value(card.rank) == rank_value(top.rank)+1:

                            self.save_state()
                            pile.append(card)
                            placed = True

                    break

        #drop TABLEU
        if not placed:

            col = (x-20)//120

            if 0 <= col < 8:

                target = None

                if self.tableau[col]:
                    target = self.tableau[col][-1]

                max_cards = self.max_movable_cards(col)

                if self.valid_move(card,target) and len(self.drag_stack) <= max_cards:
                    self.save_state()

                    self.tableau[col] += self.drag_stack

                    placed = True

        #INVALID
        if not placed:

            src = self.drag_source

            if src[0] == "tableau":
                self.tableau[src[1]][src[2]:src[2]] = self.drag_stack

            elif src[0] == "freecell":
                self.freecells[src[1]] = self.drag_stack[0]

            elif src[0] == "foundation":
                self.foundations[src[1]].append(self.drag_stack[0])

        else:

            self.moves += 1
            self.update_moves()

        self.drag_stack = []
        self.drag_source = None

        self.draw()
        self.check_win()

    def valid_move(self,card,target):

        if target is None:
            return True

        if color(card)==color(target):
            return False

        if rank_value(card.rank)!=rank_value(target.rank)-1:
            return False

        return True


    def valid_stack(self,stack):

        for i in range(len(stack)-1):

            c1=stack[i]
            c2=stack[i+1]

            if color(c1)==color(c2):
                return False

            if rank_value(c1.rank)!=rank_value(c2.rank)+1:
                return False

        return True

    def save_state(self):

        state=(
            copy.deepcopy(self.tableau),
            copy.deepcopy(self.freecells),
            copy.deepcopy(self.foundations)
        )

        self.history.append(state)


    def undo(self):

        if not self.history:
            return

        state=self.history.pop()

        self.tableau,self.freecells,self.foundations=state

        self.moves=max(0,self.moves-1)

        self.update_moves()
        self.draw()

    def check_win(self):

        total=sum(len(f) for f in self.foundations)

        if total==52:

            self.canvas.create_text(
                500,300,
                text="YOU WIN!",
                fill="yellow",
                font=("Arial",40)
            )

    def update_timer(self):

        elapsed=int(time.time()-self.start_time)

        self.timer_label.config(text=f"Time: {elapsed}")

        self.root.after(1000,self.update_timer)


    def update_moves(self):

        self.move_label.config(text=f"Moves: {self.moves}")






#FIREE
root=tk.Tk()

game=FreeCell(root)

root.mainloop()