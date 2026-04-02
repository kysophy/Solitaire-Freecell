## Solitaire FreeCell (AI Search Project)

This project is a playable FreeCell game with two automated solvers:

- **IDS** (Iterative Deepening Search) in `Solver/dfs.py`
- **A\*** in `Solver/astar.py`

The GUI is built with Tkinter (`Gui/game_ui.py`), and the IDS solver can be launched from the **DFS** button in the interface.

---

## Run the project

From the `Solitaire-Freecell` folder:

```bash
python main.py
```

No external dependencies are required beyond standard Python libraries used in the code.

---

## Project structure

- `main.py`: starts the Tkinter app
- `Gui/game_ui.py`: game loop, user interaction, solver threading, replay animation
- `Solver/dfs.py`: IDS solver implementation
- `Solver/astar.py`: A* solver implementation
- `Utils/helpers.py`: shared helpers (state conversion, move generation, canonical hashing, auto-foundation logic)
- `testing/results.csv`: exported solver run statistics

---

## IDS solver implementation (detailed)

### 1) State representation used by IDS

The IDS solver works on an immutable tuple state created by `game_to_state(...)` in `Utils/helpers.py`:

- `tableau`: tuple of 8 columns, each column is a tuple of card strings like `"AH"` or `"10C"`
- `freecells`: tuple of 4 slots containing either a card string or `None`
- `foundations`: tuple of 4 entries as `(suit_char, top_rank_int)`, e.g. `("H", 7)` or `(None, 0)`

This representation is compact, hashable, and safe for recursive search.

### 2) Move encoding

IDS moves are 5-tuples:

```text
(src_type, src_idx, dst_type, dst_idx, num_cards)
```

Where:

- `src_type` is `'t'` (tableau) or `'f'` (freecell)
- `dst_type` is `'t'` (tableau), `'f'` (freecell), or `'h'` (foundation)
- `num_cards` supports supermoves for tableau-to-tableau transfers

Example: `('t', 3, 't', 5, 2)` means move a 2-card stack from tableau column 3 to column 5.

### 3) Core algorithm: Iterative Deepening + Depth-Limited DFS

`solve_ids(initial_state, max_depth=300, time_limit=600, cancel_event=None)` performs:

1. Start depth limit at 1
2. Run depth-limited DFS
3. If no solution, increase limit and repeat
4. Stop on solution, timeout, cancellation, or depth bound reached

Implementation details:

- Each depth iteration creates a **fresh `visited` map**
- Search is done by `_depth_limited_dfs(...)`
- `expanded` counts expanded nodes across all depth iterations
- Runtime and memory are measured (`time`, `tracemalloc`)

This gives IDS properties:

- **Complete** under finite branching and increasing depth bounds
- **Optimal in number of moves** (first found solution is shallowest depth)
- Typical complexity: time `O(b^d)`, space `O(b*d)`

### 4) Depth-limited DFS behavior

Inside `_depth_limited_dfs(...)`:

- aborts on timeout/cancel
- checks goal state first
- enforces cutoff when `depth >= limit`
- prunes duplicate states using a depth-aware visited map
- expands legal moves (`get_all_moves`)
- applies move (`apply_move`)
- runs automatic safe foundation pushes (`auto_play_foundations`)
- recurses, then backtracks path if branch fails

The path contains both:

- the deliberate move chosen by DFS, and
- any auto-foundation moves triggered immediately after it

### 5) Duplicate detection and canonical hashing

A key part of IDS efficiency is:

- `canonical_hash(state)` from `Utils/helpers.py`

It canonicalizes logically equivalent states by sorting tableau columns, freecells, and foundation descriptors before hashing.  
Result: states that differ only by symmetric ordering map to the same key and are not expanded repeatedly.

Visited policy in DFS:

- `visited[state_hash] = min_depth_expanded`
- if state seen at an equal or shallower depth, branch is pruned
- if rediscovered at a shallower depth than before, it can still be explored

This preserves completeness for depth-limited search while reducing redundant work.

### 6) Branch reduction techniques used by IDS helpers

`get_all_moves(...)` and related helpers apply practical reductions:

- prioritize foundation moves in generation order
- treat equivalent empty destinations carefully (avoid duplicate empty-column/empty-freecell variants)
- support legal supermoves with `max_movable(...)`
- auto-play only **safe** foundation moves with `is_safe_auto_move(...)`

These choices significantly reduce branching without changing legal gameplay rules.

### 7) GUI integration (how IDS is executed)

In `Gui/game_ui.py`:

- clicking **DFS** triggers `solve_dfs()`
- current board is converted with `game_to_state(...)`
- `solve_ids(...)` runs in a background thread
- on completion, `_on_ids_done(...)` either:
  - replays moves on the board (`_replay_ids_next`), or
  - shows a "no solution / cancelled" message

Default IDS runtime settings from the GUI call:

- `max_depth=300`
- `time_limit=600` seconds

The **Stop** button sets a cancellation event checked by the solver.

### 8) Reported metrics

IDS returns:

- `moves` (or `None` if not solved in limits)
- `stats` dictionary:
  - `time` (seconds)
  - `memory` (peak MB via `tracemalloc`)
  - `expanded` (expanded nodes)
  - `length` (solution length)

Results are appended to `testing/results.csv` via `_save_results_csv(...)`.

---

## Notes

- The GUI label uses **DFS**, but the implementation is specifically **IDS** (`solve_ids`).
- A solved game means all four foundations reach rank 13 (`K`).
- If IDS does not finish within limits, you can retry with a new deal or use A* for comparison.
