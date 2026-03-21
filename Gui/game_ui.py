import tkinter as tk
from Game.deck import create_deck
from Game.utils import color, rank_value

from Utils import _color, _rank_value
from Solver import solve_astar as run_astar, apply_solution

import time
import copy
import threading

class FreeCell:

    def __init__(self, root):

        self.root = root
        self.root.title("FreeCell")
        self.root.geometry("1000x650")

        self.card_images = {}
        self.load_card_images()

        self._solve_thread  = None
        self._solve_actions = []
        self._solve_cache   = None

        self.moves = 0
        self.history = []
        self.start_time = time.time()

        # board
        self.tableau = [[] for _ in range(8)]
        self.freecells = [None] * 4
        self.foundations = [[] for _ in range(4)]

        self._solve_generation = 0
        self._current_replay_gen  = -1
        self._status_msg = ""
        self._status_until = 0
        self._solving = False

        # dragging
        self.drag_stack = []
        self.drag_source = None

        self.drag_x = 0
        self.drag_y = 0
        self.target_x = 0
        self.target_y = 0

        self.drag_offset_x = 40
        self.drag_offset_y = 50

        self.build_gui()
        self.new_game()

        # start animation loop
        self.smooth_move()

    # ---------------- GUI ---------------- #

    def build_gui(self):

        self.canvas = tk.Canvas(self.root, bg="darkgreen")
        self.canvas.pack(fill="both", expand=True)

        panel = tk.Frame(self.root)
        panel.place(relx=0.5, rely=0.95, anchor="center")

        tk.Button(panel, text="New Game", command=self.new_game).pack(side="left", padx=5)
        tk.Button(panel, text="Reset", command=self.reset_game).pack(side="left", padx=5)

        tk.Button(panel, text="BFS", command=self.solve_bfs).pack(side="left", padx=5)
        tk.Button(panel, text="DFS", command=self.solve_dfs).pack(side="left", padx=5)
        tk.Button(panel, text="UCS", command=self.solve_ucs).pack(side="left", padx=5)

        #gotta work with my own variable
        self.solve_btn = tk.Button(panel, text="A*", command=self.solve_astar)
        self.solve_btn.pack(side="left", padx=5)

        self.move_label = tk.Label(panel, text="Moves: 0")
        self.move_label.pack(side="left", padx=20)

        self.timer_label = tk.Label(panel, text="Time: 0")
        self.timer_label.pack(side="left")

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drop)

    # ---------------- GAME SETUP ---------------- #

    def new_game(self):
        deck = create_deck()

        self.tableau = [[] for _ in range(8)]
        self.freecells = [None] * 4
        self.foundations = [[] for _ in range(4)]

        for i, card in enumerate(deck):
            self.tableau[i % 8].append(card)

        self.moves = 0
        self.history = []
        self.start_time = time.time()

        self._solve_actions    = []
        self._solve_cache      = None
        self._solve_thread     = None
        self._solve_generation += 1   
        self._solving          = False
        self._unlock_input()

        self.update_moves()
        self.draw()
        self.update_timer()


    # ---------------- DRAW ---------------- #

    def load_card_images(self):

        suits = {"Spades":"S","Hearts":"H","Diamonds":"D","Clubs":"C"}
        ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

        for suit_name, suit_letter in suits.items():
            for rank in ranks:
                filename = f"Assets/cards/{rank}{suit_letter}.png"
                img = tk.PhotoImage(file=filename).subsample(3,3)
                self.card_images[(rank, suit_name)] = img

    def draw(self):

        self.canvas.delete("all")

        # freecells
        for i in range(4):
            x = 20 + i*120
            y = 20
            self.canvas.create_rectangle(x,y,x+80,y+100,outline="white")
            if self.freecells[i]:
                self.draw_card(self.freecells[i],x,y)

        # foundations
        for i in range(4):
            x = 500 + i*120
            y = 20
            self.canvas.create_rectangle(x,y,x+80,y+100,outline="white")
            if self.foundations[i]:
                self.draw_card(self.foundations[i][-1],x,y)

        # tableau
        for c in range(8):
            x = 20 + c*120
            y = 150
            for card in self.tableau[c]:
                self.draw_card(card,x,y)
                y += 30

        # dragging stack
        if self.drag_stack:
            x = self.drag_x
            y = self.drag_y
            for card in self.drag_stack:
                self.draw_card(card,x,y)
                y += 30

        if self._status_msg and time.time() < self._status_until:
            self.canvas.create_text(
                500, 300,
                text=self._status_msg,
                fill="red",
                font=("Arial", 20)
            )

    def draw_card(self, card, x, y):
        img = self.card_images[(card.rank, card.suit)]
        self.canvas.create_image(x, y, image=img, anchor="nw")

    # ---------------- INPUT ---------------- #

    def start_drag(self, stack, source, x, y):
        self.drag_stack = stack
        self.drag_source = source

        self.drag_x = x - self.drag_offset_x
        self.drag_y = y - self.drag_offset_y

        # CRITICAL FIX
        self.target_x = self.drag_x
        self.target_y = self.drag_y

    def click(self, event):

        x, y = event.x, event.y

        # freecell
        if 20 <= y <= 120:
            for i in range(4):
                fx = 20 + i*120
                if fx <= x <= fx+80 and self.freecells[i]:
                    card = self.freecells[i]
                    self.freecells[i] = None
                    self.start_drag([card], ("freecell", i), x, y)
                    return

            # foundation
            for i in range(4):
                fx = 500 + i*120
                if fx <= x <= fx+80 and self.foundations[i]:
                    card = self.foundations[i].pop()
                    self.start_drag([card], ("foundation", i), x, y)
                    return

        # tableau
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

        if len(stack) > self.max_movable_cards():
            return

        del self.tableau[col][index:]
        self.start_drag(stack, ("tableau", col, index), x, y)

    def drag(self, event):
        if not self.drag_stack:
            return

        self.target_x = event.x - self.drag_offset_x
        self.target_y = event.y - self.drag_offset_y
        
    def drop(self, event):

        if not self.drag_stack:
            return

        x = event.x
        y = event.y

        placed = False
        card = self.drag_stack[0]

        # FREECELL
        if 10 <= y <= 140:
            for i in range(4):
                fx = 20 + i * 120
                if fx - 10 <= x <= fx + 90:
                    if self.freecells[i] is None and len(self.drag_stack) == 1:
                        self.save_state()
                        self.freecells[i] = card
                        placed = True
                        break

        # FOUNDATION
        if not placed and 10 <= y <= 140:
            for i in range(4):
                fx = 500 + i * 120
                if fx - 10 <= x <= fx + 90:
                    pile = self.foundations[i]

                    if not pile and card.rank == "A":
                        self.save_state()
                        pile.append(card)
                        placed = True
                        break

                    elif pile:
                        top = pile[-1]
                        if card.suit == top.suit and rank_value(card.rank) == rank_value(top.rank) + 1:
                            self.save_state()
                            pile.append(card)
                            placed = True
                            break

        # TABLEAU
        if not placed:
            col = (x - 20) // 120
            if 0 <= col < 8:
                target = self.tableau[col][-1] if self.tableau[col] else None
                max_cards = self.max_movable_cards(col)

                if self.valid_move(card, target) and len(self.drag_stack) <= max_cards:
                    self.save_state()
                    self.tableau[col] += self.drag_stack
                    placed = True

        # RETURN if invalid
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
            self._invalidate_cache()

        self.drag_stack = []
        self.drag_source = None

        self.draw()
        self.check_win()

    # ---------------- SMOOTH MOTION ---------------- #

    def smooth_move(self):
        if not self._solving:
            if self.drag_stack:
                speed = 0.3
                self.drag_x += (self.target_x - self.drag_x) * speed
                self.drag_y += (self.target_y - self.drag_y) * speed
            self.draw()
        self.root.after(16, self.smooth_move)

    # ---------------- REST SAME ---------------- #

    def max_movable_cards(self, target_col=None):
        empty_freecells = sum(1 for c in self.freecells if c is None)
        empty_columns = sum(1 for i,col in enumerate(self.tableau)
                            if len(col)==0 and i!=target_col)
        return (empty_freecells+1)*(2**empty_columns)

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
            if color(stack[i])==color(stack[i+1]):
                return False
            if rank_value(stack[i].rank)!=rank_value(stack[i+1].rank)+1:
                return False
        return True

    def save_state(self):
        state=(copy.deepcopy(self.tableau),
               copy.deepcopy(self.freecells),
               copy.deepcopy(self.foundations))
        self.history.append(state)

    def reset_game(self):
        if self.history:
            self.tableau,self.freecells,self.foundations=self.history[0]
            self.history=[]
            self.moves=0
            self.update_moves()
            self._invalidate_cache()
            self.draw()

    def update_timer(self):
        elapsed=int(time.time()-self.start_time)
        self.timer_label.config(text=f"Time: {elapsed}")
        self.root.after(1000,self.update_timer)

    def update_moves(self):
        self.move_label.config(text=f"Moves: {self.moves}")

    def check_win(self):
        if sum(len(f) for f in self.foundations)==52:
            self.canvas.create_text(500,300,text="YOU WIN!",
                                    fill="yellow",font=("Arial",40))


    ############### A* helper functions#####################

    def _board_enc(self):
        from Solver.astar import _encode, _to_tuple_state
        tab, fc, fd = _to_tuple_state(self.tableau, self.freecells, self.foundations)
        return _encode(tab, fc, fd)
    
    def _invalidate_cache(self):
            self._solve_cache = None
    
    def _lock_input(self):
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.solve_btn.config(state="disabled")
 
    def _unlock_input(self):
        self.canvas.bind("<Button-1>",        self.click)
        self.canvas.bind("<B1-Motion>",       self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drop)
        self.solve_btn.config(state="normal", text="A*")
 
    def _replay_next(self):
        if self._current_replay_gen != self._solve_generation:
            return
    
        if not self._solve_actions:
            self._unlock_input()
            self.check_win()
            return
 
        action = self._solve_actions.pop(0)
        self._apply_action(action)
        self.moves += 1
        self.update_moves()
        # Tune replay speed here (milliseconds between moves)
        self.root.after(350, self._replay_next)

    def _apply_action(self, action):
        apply_solution([action], self.tableau, self.freecells, self.foundations)

    def _on_solve_done(self, enc, actions):
        self._solving = False               # resume smooth_move
        self.solve_btn.config(state="normal", text="A*")
        if actions is None:
            self._status_msg   = "Could not solve — try New Game"
            self._status_until = time.time() + 3
            return
        self._solve_cache        = (enc, list(actions))
        self._solve_actions      = actions
        self._current_replay_gen = self._solve_generation
        self._lock_input()
        self._replay_next()

    #############################
    # placeholders
    def solve_bfs(self): print("BFS")
    def solve_dfs(self): print("DFS")
    def solve_ucs(self): print("UCS")
    def solve_astar(self):
        if self._solve_thread and self._solve_thread.is_alive():
            return
 
        enc = self._board_enc()
 
        if self._solve_cache and self._solve_cache[0] == enc:
            self._solve_actions      = list(self._solve_cache[1])
            self._current_replay_gen = self._solve_generation
            self._lock_input()
            self._replay_next()
            return

        self._solving = True
        self.solve_btn.config(state="disabled", text="Solving...")
 
        tab_snap = copy.deepcopy(self.tableau)
        fc_snap  = list(self.freecells)
        fd_snap  = copy.deepcopy(self.foundations)
 
        def _run():
            actions = run_astar(
                tab_snap, fc_snap, fd_snap,
                max_states=2_000_000,
                timeout_sec=60
            )
            self.root.after(0, lambda: self._on_solve_done(enc, actions))
 
        self._solve_thread = threading.Thread(target=_run, daemon=True)
        self._solve_thread.start()
