import tkinter as tk
from Game.deck import create_deck
from Game.utils import color, rank_value

from Utils import _color, _rank_value
from Solver import solve_astar as run_astar, apply_solution

import os
import time
import copy
import threading
import random
import csv


class FreeCell:

    def __init__(self, root):

        self.root = root
        self.root.title("Group10 - Introduction To AI - FreeCell")

        window_width = 1155
        window_height = 690

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))

        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        self.card_images = {}
        self.load_card_images()

        self._solve_thread  = None
        self._solve_actions = []
        self._solve_cache   = None
        self._cancel_event  = threading.Event()

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

        # IDS solver state
        self._ids_thread = None
        self._ids_actions = []
        self._ids_solving = False

        # dragging
        self.drag_stack = []
        self.drag_source = None

        self.drag_x = 0
        self.drag_y = 0
        self.target_x = 0
        self.target_y = 0

        self.drag_offset_x = 40
        self.drag_offset_y = 50

        # Difficulty mode
        self.game_mode = tk.StringVar(value="Easy")

        # Animation speed presets
        self.anim_speed = tk.StringVar(value="1x")
        self._speed_presets = {
            "1x":  {"interp": 0.3, "replay_ms": 350, "ids_ms": 200, "fnd_ms": 100},
            "3x":  {"interp": 0.5, "replay_ms": 120, "ids_ms": 60,  "fnd_ms": 30},
            "5x":  {"interp": 0.7, "replay_ms": 60,  "ids_ms": 30,  "fnd_ms": 15},
            "Max": {"interp": 1.0, "replay_ms": 1,   "ids_ms": 1,   "fnd_ms": 1},
        }

        self.build_gui()
        self.new_game()

        self.smooth_move()

    # ---------------- GUI ---------------- #

    def _get_speed_preset(self):
        return self._speed_presets.get(self.anim_speed.get(),
                                       self._speed_presets["1x"])

    def build_gui(self):
        panel_bg = "#2b4a2b"
        control_panel = tk.Frame(self.root, width=160, padx=10, pady=10, bg=panel_bg)
        control_panel.pack(side="left", fill="y")

        self.canvas = tk.Canvas(self.root, bg="#3b8a3b")
        self.canvas.pack(side="right", fill="both", expand=True)

        btn_opts = {"width": 15, "pady": 5}
        lbl_opts = {"bg": panel_bg, "fg": "white", "font": ("Arial", 10, "bold")}

        tk.Button(control_panel, text="New Game", command=self.new_game, **btn_opts).pack(pady=5)
        tk.Button(control_panel, text="Reset", command=self.reset_game, **btn_opts).pack(pady=5)
        tk.Button(control_panel, text="Undo", command=self.undo_move, **btn_opts).pack(pady=5)

        # ── Difficulty selector ──
        tk.Label(control_panel, text="", bg=panel_bg).pack(pady=3)
        tk.Label(control_panel, text="Difficulty:", **lbl_opts).pack(pady=(5, 0))
        mode_menu = tk.OptionMenu(
            control_panel, self.game_mode,
            "Easy", "Medium", "Hard", "Expert"
        )
        mode_menu.config(width=12, bg="#4a6a4a", fg="white", relief="flat",
                         highlightthickness=0, font=("Arial", 9))
        mode_menu["menu"].config(bg="#4a6a4a", fg="white")
        mode_menu.pack(pady=3)

        # ── Speed selector ──
        tk.Label(control_panel, text="Speed:", **lbl_opts).pack(pady=(5, 0))
        speed_menu = tk.OptionMenu(
            control_panel, self.anim_speed,
            *self._speed_presets.keys()
        )
        speed_menu.config(width=12, bg="#4a6a4a", fg="white", relief="flat",
                          highlightthickness=0, font=("Arial", 9))
        speed_menu["menu"].config(bg="#4a6a4a", fg="white")
        speed_menu.pack(pady=3)

        tk.Label(control_panel, text="", bg=panel_bg).pack(pady=3)

        # ── Solver buttons ──
        tk.Button(control_panel, text="BFS", command=self.solve_bfs, **btn_opts).pack(pady=5)
        self.dfs_btn = tk.Button(control_panel, text="DFS", command=self.solve_dfs, **btn_opts)
        self.dfs_btn.pack(pady=5)
        tk.Button(control_panel, text="UCS", command=self.solve_ucs, **btn_opts).pack(pady=5)

        self.solve_btn = tk.Button(control_panel, text="A*", command=self.solve_astar, **btn_opts)
        self.solve_btn.pack(pady=5)

        tk.Label(control_panel, text="", bg=panel_bg).pack(pady=3)

        # ── Stop button ──
        self.stop_btn = tk.Button(
            control_panel, text="Stop", command=self.stop_solving,
            width=15, pady=5,
            bg="#b71c1c", fg="white", activebackground="#d32f2f",
            activeforeground="white", relief="flat",
            state="disabled"
        )
        self.stop_btn.pack(pady=5)

        tk.Label(control_panel, text="", bg=panel_bg).pack(pady=3)

        self.move_label = tk.Label(control_panel, text="Moves: 0", **lbl_opts)
        self.move_label.pack(pady=5)

        self.timer_label = tk.Label(control_panel, text="Time: 0", **lbl_opts)
        self.timer_label.pack(pady=5)

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drop)

    # ---------------- GAME SETUP ---------------- #

    def new_game(self):
        from Utils.seed_generator import generate_state, state_to_cards

        if self._solving or self._ids_solving:
            self._do_stop()

        mode = self.game_mode.get()
        solver_state = generate_state(mode)

        self.tableau = [[] for _ in range(8)]
        self.freecells = [None] * 4
        self.foundations = [[] for _ in range(4)]

        if solver_state is None:
            deck = create_deck()
            for i, card in enumerate(deck):
                self.tableau[i % 8].append(card)
        else:
            (self.tableau,
             self.freecells,
             self.foundations) = state_to_cards(solver_state)

        self.moves = 0
        self.history = []
        self.start_time = time.time()

        self._solve_actions    = []
        self._solve_cache      = None
        self._solve_thread     = None
        self._solve_generation += 1
        self._solving          = False
        self._ids_solving      = False
        self._ids_actions      = []
        self._cancel_event.clear()
        self._unlock_input()
        self.stop_btn.config(state="disabled")

        self.update_moves()
        self.draw()
        self.update_timer()

    def undo_move(self):
        if self._ids_solving or self._solving:
            return
        if self.history:
            self.tableau, self.freecells, self.foundations = self.history.pop()
            if self.moves > 0:
                self.moves -= 1
            self.update_moves()
            self._invalidate_cache()
            self.draw()

    # ---------------- DRAW ---------------- #

    def load_card_images(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        suits = {"Spades":"S","Hearts":"H","Diamonds":"D","Clubs":"C"}
        ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

        for suit_name, suit_letter in suits.items():
            for rank in ranks:
                filename = os.path.join(base_dir, "Assets", "cards", f"{rank}{suit_letter}.png")
                img = tk.PhotoImage(file=filename).subsample(3,3)
                self.card_images[(rank, suit_name)] = img

    def draw(self):
        self.canvas.delete("all")

        self.canvas.create_rectangle(10, 10, 1010, 680, fill="#1c3b1c", outline="#1c3b1c")

        for i in range(4):
            x = 60 + i * 90
            y = 30
            self.canvas.create_rectangle(x, y, x+80, y+100, outline="white")
            if self.freecells[i]:
                self.draw_card(self.freecells[i], x, y)

        for i in range(4):
            x = 630 + i * 90
            y = 30
            self.canvas.create_rectangle(x, y, x+80, y+100, outline="white")
            if self.foundations[i]:
                self.draw_card(self.foundations[i][-1], x, y)

        for c in range(8):
            x = 60 + c * 120
            y = 160
            for card in self.tableau[c]:
                self.draw_card(card, x, y)
                y += 30

        if self.drag_stack:
            x = self.drag_x
            y = self.drag_y
            for card in self.drag_stack:
                self.draw_card(card, x, y)
                y += 30

        if self._status_msg and time.time() < self._status_until:
            self.canvas.create_text(520, 340, text=self._status_msg, fill="red", font=("Arial", 20))

    def draw_card(self, card, x, y):
        img = self.card_images[(card.rank, card.suit)]
        self.canvas.create_image(x, y, image=img, anchor="nw")

    # ---------------- INPUT ---------------- #

    def start_drag(self, stack, source, x, y):
        self.drag_stack = stack
        self.drag_source = source

        self.drag_x = x - self.drag_offset_x
        self.drag_y = y - self.drag_offset_y

        self.target_x = self.drag_x
        self.target_y = self.drag_y

    def click(self, event):
        if self._ids_solving or self._solving:
            return
        x, y = event.x, event.y

        if 30 <= y <= 130:
            for i in range(4):
                fx = 60 + i * 90
                if fx <= x <= fx + 80 and self.freecells[i]:
                    card = self.freecells[i]
                    self.freecells[i] = None
                    self.start_drag([card], ("freecell", i), x, y)
                    return

            for i in range(4):
                fx = 630 + i * 90
                if fx <= x <= fx + 80 and self.foundations[i]:
                    card = self.foundations[i].pop()
                    self.start_drag([card], ("foundation", i), x, y)
                    return

        col = (x - 60) // 120
        if not (0 <= col < 8):
            return

        y_pos = 160
        index = None
        for i in range(len(self.tableau[col])):
            if y_pos <= y <= y_pos + 100:
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
        if self._ids_solving or self._solving:
            return
        if not self.drag_stack:
            return

        self.target_x = event.x - self.drag_offset_x
        self.target_y = event.y - self.drag_offset_y

    def drop(self, event):
        if self._ids_solving or self._solving:
            return
        if not self.drag_stack:
            return

        x = event.x
        y = event.y
        placed = False
        card = self.drag_stack[0]

        if 20 <= y <= 150:
            for i in range(4):
                fx = 60 + i * 90
                if fx - 10 <= x <= fx + 90:
                    if self.freecells[i] is None and len(self.drag_stack) == 1:
                        self.save_state()
                        self.freecells[i] = card
                        placed = True
                        break

            if not placed:
                for i in range(4):
                    fx = 630 + i * 90
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

        if not placed:
            col = (x - 50) // 120
            if 0 <= col < 8:
                target = self.tableau[col][-1] if self.tableau[col] else None
                max_cards = self.max_movable_cards(col)

                if self.valid_move(card, target) and len(self.drag_stack) <= max_cards:
                    self.save_state()
                    self.tableau[col] += self.drag_stack
                    placed = True

        if not placed:
            src = self.drag_source
            if src[0] == "tableau":
                self.tableau[src[1]][src[2]:src[2]] = self.drag_stack
            elif src[0] == "freecell":
                self.freecells[src[1]] = self.drag_stack[0]
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
        if not self._solving or self._ids_solving:
            if self.drag_stack:
                if self._ids_solving or self._solving:
                    speed = self._get_speed_preset()["interp"]
                else:
                    speed = 0.3
                self.drag_x += (self.target_x - self.drag_x) * speed
                self.drag_y += (self.target_y - self.drag_y) * speed
            self.draw()
        self.root.after(16, self.smooth_move)

    # ---------------- GAME LOGIC ---------------- #

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
        if self._ids_solving or self._solving:
            return
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

    ############### A* helper functions #####################

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
        self.dfs_btn.config(state="disabled")

    def _unlock_input(self):
        self.canvas.bind("<Button-1>",        self.click)
        self.canvas.bind("<B1-Motion>",       self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.drop)
        self.solve_btn.config(state="normal", text="A*")
        self.dfs_btn.config(state="normal", text="DFS")

    def _replay_next(self):
        if self._cancel_event.is_set():
            return
        if self._current_replay_gen != self._solve_generation:
            return

        if not self._solve_actions:
            self._unlock_input()
            self.stop_btn.config(state="disabled")
            self.check_win()
            return

        action = self._solve_actions.pop(0)
        self._apply_action(action)
        self.moves += 1
        self.update_moves()
        preset = self._get_speed_preset()
        delay = preset["replay_ms"]
        self.root.after(delay, self._replay_next)

    def _apply_action(self, action):
        apply_solution([action], self.tableau, self.freecells, self.foundations)
        self.draw()

    def _on_solve_done(self, enc, result):
        self._solving = False
        self.solve_btn.config(state="normal", text="A*")
        self.dfs_btn.config(state="normal", text="DFS")

        actions, stats = result

        if self._cancel_event.is_set():
            self._status_msg   = "Solving cancelled"
            self._status_until = time.time() + 3
            self.stop_btn.config(state="disabled")
            self._unlock_input()
            self.draw()
            return

        self._save_results_csv("A*", stats)

        if actions is None:
            self._status_msg   = "Could not solve — try New Game"
            self._status_until = time.time() + 3
            self.stop_btn.config(state="disabled")
            self._unlock_input()
            return

        print(f"Total moves: {len(actions)}")
        self._solve_cache        = (enc, list(actions))
        self._solve_actions      = actions
        self._current_replay_gen = self._solve_generation
        self._lock_input()
        self.stop_btn.config(state="normal")
        self._replay_next()

    #############################
    # Solver stubs and implementations

    def solve_bfs(self): print("BFS")

    def solve_dfs(self):
        if self._solving or self._ids_solving:
            return
        if self._ids_thread and self._ids_thread.is_alive():
            return

        self._ids_solving = True
        self._cancel_event.clear()
        self._status_msg = "Solving with IDS..."
        self._status_until = time.time() + 9999
        self.stop_btn.config(state="normal")
        self.dfs_btn.config(state="disabled", text="Solving...")
        self.solve_btn.config(state="disabled")
        self.draw()

        from Utils.helpers import game_to_state
        from Solver.dfs import solve_ids

        solver_state = game_to_state(
            self.tableau, self.freecells, self.foundations
        )
        self.save_state()

        cancel = self._cancel_event

        def _run():
            result = solve_ids(solver_state, max_depth=300, time_limit=600,
                               cancel_event=cancel)
            self.root.after(0, lambda: self._on_ids_done(result))

        self._ids_thread = threading.Thread(target=_run, daemon=True)
        self._ids_thread.start()

    def _on_ids_done(self, result):
        if not self._ids_solving:
            return

        moves, stats = result
        self._status_msg = ""
        self._status_until = 0

        if self._cancel_event.is_set():
            self._ids_solving = False
            self._status_msg = "Solving cancelled"
            self._status_until = time.time() + 3
            self.stop_btn.config(state="disabled")
            self._unlock_input()
            self.draw()
            return

        self._save_results_csv("DFS", stats)

        if moves is not None:
            print(f"IDS: {stats['length']} moves in {stats['time']:.2f}s "
                  f"({stats['expanded']:,} nodes, {stats['memory']:.2f} MB)")
            self._ids_actions = list(moves)
            self.stop_btn.config(state="normal")
            self._replay_ids_next()
        else:
            self._ids_solving = False
            self._status_msg = (f"No IDS solution ({stats['time']:.1f}s, "
                                f"{stats['expanded']:,} nodes)")
            self._status_until = time.time() + 5
            self.stop_btn.config(state="disabled")
            self._unlock_input()

    def _replay_ids_next(self):
        if not self._ids_solving:
            return
        if self._cancel_event.is_set():
            self._ids_solving = False
            self._ids_actions = []
            self._status_msg = "Replay stopped"
            self._status_until = time.time() + 3
            self.stop_btn.config(state="disabled")
            self._unlock_input()
            self.draw()
            return
        if not self._ids_actions:
            self._ids_solving = False
            self.stop_btn.config(state="disabled")
            self._unlock_input()
            self.check_win()
            return

        move = self._ids_actions.pop(0)
        self._apply_ids_move(move)
        self.moves += 1
        self.update_moves()
        self.draw()
        preset = self._get_speed_preset()
        delay = preset["ids_ms"]
        self.root.after(delay, self._replay_ids_next)

    def _apply_ids_move(self, move):
        src_type, src_idx, dst_type, dst_idx, num_cards = move

        if src_type == 't':
            cards = self.tableau[src_idx][-num_cards:]
            del self.tableau[src_idx][-num_cards:]
        else:
            cards = [self.freecells[src_idx]]
            self.freecells[src_idx] = None

        if dst_type == 't':
            self.tableau[dst_idx].extend(cards)
        elif dst_type == 'f':
            self.freecells[dst_idx] = cards[0]
        elif dst_type == 'h':
            self.foundations[dst_idx].append(cards[0])

    def solve_ucs(self): print("UCS")

    def solve_astar(self):
        if self._ids_solving or self._solving:
            return
        if self._solve_thread and self._solve_thread.is_alive():
            return

        enc = self._board_enc()

        if self._solve_cache and self._solve_cache[0] == enc:
            self._solve_actions      = list(self._solve_cache[1])
            self._current_replay_gen = self._solve_generation
            self._lock_input()
            self.stop_btn.config(state="normal")
            self._replay_next()
            return

        self._solving = True
        self._cancel_event.clear()
        self.solve_btn.config(state="disabled", text="Solving...")
        self.dfs_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        tab_snap = copy.deepcopy(self.tableau)
        fc_snap  = list(self.freecells)
        fd_snap  = copy.deepcopy(self.foundations)

        cancel = self._cancel_event

        def _run():
            result = run_astar(
                tab_snap, fc_snap, fd_snap,
                max_states=2_000_000,
                timeout_sec=60,
                cancel_event=cancel
            )
            self.root.after(0, lambda: self._on_solve_done(enc, result))

        self._solve_thread = threading.Thread(target=_run, daemon=True)
        self._solve_thread.start()

    # ── CSV Export ──

    def _save_results_csv(self, solver_name, stats):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "testing", "results.csv")

        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        write_header = (not os.path.exists(csv_path)
                        or os.path.getsize(csv_path) == 0)

        solved = "Yes" if stats['length'] > 0 else "No"
        mode = self.game_mode.get()

        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow([
                    "Solver", "Mode", "Solved",
                    "Search Time", "Memory Usage",
                    "Expanded Nodes", "Solution Length"
                ])
            writer.writerow([
                solver_name,
                mode,
                solved,
                f"{stats['time']:.4f}",
                f"{stats['memory']:.4f}",
                stats['expanded'],
                stats['length']
            ])

    # ── Stop / Emergency Cancel ──

    def stop_solving(self):
        self._do_stop()

    def _do_stop(self):
        self._cancel_event.set()

        if self._solving:
            self._solving = False
            self._solve_actions = []

        if self._ids_solving:
            self._ids_solving = False
            self._ids_actions = []

        self._status_msg = "Stopped"
        self._status_until = time.time() + 3
        self.stop_btn.config(state="disabled")
        self._unlock_input()
        self.draw()
