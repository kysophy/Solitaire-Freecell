import time
import tracemalloc

from Solver.astar import _auto_foundation
from Solver.heuristics import _heuristic
from Utils.constants import RANK_VALUE, SUIT_COLOR, OPPOSITE_COLOR_SUITS, ALL_SUITS
from Utils.helpers import _valid_on_foundation, _valid_on_tableau

# --- State Representation ---

def _to_tuple_state(tableau, freecells, foundations):
    tab = tuple(tuple((c.rank, c.suit) for c in col) for col in tableau)
    fc = tuple((c.rank, c.suit) if c is not None else None for c in freecells)
    fd = tuple(tuple((c.rank, c.suit) for c in pile) for pile in foundations)
    return tab, fc, fd

def _encode(tab, fc, fd):
    tab = tuple(sorted(tab, key=lambda col: (len(col), col)))
    tab_str = "/".join("|".join(f"{r}{s[0]}" for r, s in col) if col else "-" for col in tab)
    fc_str = ",".join(f"{c[0]}{c[1][0]}" if c else "." for c in fc)
    fd_str = "/".join(f"{pile[-1][1][0]}{len(pile)}" if pile else "-" for pile in fd)
    return f"{tab_str}#{fc_str}#{fd_str}"

# --- Game Rules & Logic ---

def _is_safe_to_foundation(card, fd):
    rank, suit = card
    r = RANK_VALUE[rank]
    
    if r <= 2:
        return True
        
    needed = r - 1
    fd_top = {}
    
    for pile in fd:
        if pile:
            top_r, top_s = pile[-1]
            fd_top[top_s] = RANK_VALUE[top_r]
            
    for opp in OPPOSITE_COLOR_SUITS[suit]:
        if fd_top.get(opp, 0) < needed:
            return False
            
    return True

def _auto_foundation(tab, fc, fd):
    auto_actions = []
    changed = True
    
    while changed:
        changed = False
        
        for fi, card in enumerate(fc):
            if card is None:
                continue
            for pi, pile in enumerate(fd):
                if _valid_on_foundation(card, pile) and _is_safe_to_foundation(card, fd):
                    fc = fc[:fi] + (None,) + fc[fi + 1:]
                    fd = fd[:pi] + (fd[pi] + (card,),) + fd[pi + 1:]
                    auto_actions.append({"from": ("freecell", fi), "to": ("foundation", pi)})
                    changed = True
                    break
                    
        for ci, col in enumerate(tab):
            if not col:
                continue
            card = col[-1]
            for pi, pile in enumerate(fd):
                if _valid_on_foundation(card, pile) and _is_safe_to_foundation(card, fd):
                    tab = tab[:ci] + (col[:-1],) + tab[ci + 1:]
                    fd = fd[:pi] + (fd[pi] + (card,),) + fd[pi + 1:]
                    auto_actions.append({"from": ("tableau", ci), "to": ("foundation", pi)})
                    changed = True
                    break
                    
    return tab, fc, fd, auto_actions

def _max_movable(fc, tab, target_col=None):
    empty_fc = sum(1 for c in fc if c is None)
    empty_cols = sum(1 for i, col in enumerate(tab) if len(col) == 0 and i != target_col)
    return (empty_fc + 1) * (2 ** empty_cols)

def _remove_t(tab, fc, fd, src):
    kind = src[0]

    if kind == "freecell":
        idx = src[1]
        return tab, fc[:idx] + (None,) + fc[idx + 1:], fd

    if kind == "tableau":
        if len(src) == 3:
            _, col_i, start_idx = src
            new_col = tab[col_i][:start_idx]
            return tab[:col_i] + (new_col,) + tab[col_i + 1:], fc, fd
        else:
            _, col_i = src
            new_col = tab[col_i][:-1]
            return tab[:col_i] + (new_col,) + tab[col_i + 1:], fc, fd

    return tab, fc, fd

def _get_movable_stacks(tab, col_i):
    col = tab[col_i]
    stacks = []

    for i in range(len(col)):
        stack = col[i:]
        valid = True
        
        for j in range(len(stack) - 1):
            r1, s1 = stack[j]
            r2, s2 = stack[j + 1]

            if RANK_VALUE[r1] != RANK_VALUE[r2] + 1 or SUIT_COLOR[s1] == SUIT_COLOR[s2]:
                valid = False
                break

        if valid:
            stacks.append((i, stack))

    return stacks

def _is_reverse_move(prev_move, new_move):
    if prev_move is None:
        return False
    return prev_move["from"] == new_move["to"] and prev_move["to"] == new_move["from"]

def _try_yield(prev_move, move, new_tab, new_fc, new_fd):
    if not _is_reverse_move(prev_move, move):
        return [(move, new_tab, new_fc, new_fd)]
    return []

# --- Node Expansion ---

def _successors(tab, fc, fd, prev_move=None):
    candidates = []
    
    for i, card in enumerate(fc):
        if card is not None:
            candidates.append((card, ("freecell", i)))
            
    for col_i, col in enumerate(tab):
        if col:
            stacks = _get_movable_stacks(tab, col_i)
            for start_idx, stack in stacks:
                candidates.append((stack, ("tableau", col_i, start_idx)))

    for stack, src in candidates:
        if isinstance(stack, tuple) and isinstance(stack[0], tuple):
            moving_cards = stack
            card = stack[0]
        else:
            moving_cards = (stack,)
            card = stack

        for fi, pile in enumerate(fd):
            if _valid_on_foundation(card, pile) and _is_safe_to_foundation(card, fd):
                move = {"from": src, "to": ("foundation", fi)}
                new_tab, new_fc, new_fd = _remove_t(tab, fc, fd, src)
                new_fd = new_fd[:fi] + (new_fd[fi] + (card,),) + new_fd[fi + 1:]

                for item in _try_yield(prev_move, move, new_tab, new_fc, new_fd):
                    yield item

        for col_i, col in enumerate(tab):
            if src[0] == "tableau" and src[1] == col_i:
                continue
                
            target = col[-1] if col else None
            
            if _valid_on_tableau(card, target) and _max_movable(fc, tab, col_i) >= len(moving_cards):
                move = {"from": src, "to": ("tableau", col_i)}
                new_tab, new_fc, new_fd = _remove_t(tab, fc, fd, src)
                new_tab = new_tab[:col_i] + (new_tab[col_i] + moving_cards,) + new_tab[col_i + 1:]

                for item in _try_yield(prev_move, move, new_tab, new_fc, new_fd):
                    yield item

        if src[0] == "tableau" and len(moving_cards) == 1:
            for fi, slot in enumerate(fc):
                if slot is None:
                    move = {"from": src, "to": ("freecell", fi)}
                    new_tab, new_fc, new_fd = _remove_t(tab, fc, fd, src)
                    new_fc = new_fc[:fi] + (card,) + new_fc[fi + 1:]

                    for item in _try_yield(prev_move, move, new_tab, new_fc, new_fd):
                        yield item

# --- Solvers & Action Execution ---

def _reconstruct_path(came_from, goal_enc):
    segments = []
    cur = goal_enc
    
    while cur in came_from:
        parent_enc, primary, auto = came_from[cur]
        segments.append((primary, auto))
        cur = parent_enc
        
    segments.reverse()
    
    flat = []
    for primary, auto in segments:
        flat.append(primary)
        flat.extend(auto)
        
    return flat

def solve(tableau, freecells, foundations, beam_width=500, max_states=2_000_000, timeout_sec=60):
    deadline = time.time() + timeout_sec
    start_time = time.time()
    tracemalloc.start()

    tab, fc, fd = _to_tuple_state(tableau, freecells, foundations)
    tab, fc, fd, init_auto = _auto_foundation(tab, fc, fd)

    start_enc = _encode(tab, fc, fd)
    beam = [(tab, fc, fd)]
    visited = {start_enc}
    came_from = {}
    expansions = 0

    while beam:
        next_level_candidates = []
        
        for current_tab, current_fc, current_fd in beam:
            expansions += 1

            if expansions % 1000 == 0:
                current_time = time.time() - start_time
                print(f"\r[BFS] Time: {current_time:.1f}s | Expanded: {expansions:,} | Beam Size: {len(beam):,}", end="", flush=True)

            if time.time() > deadline:
                elapsed = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()
                print("\n\n--- BFS Search Results ---")
                print("Status: TIMEOUT")
                print(f"Search Time: {elapsed:.3f} seconds")
                print(f"Memory Usage (Current): {current / 10**6:.2f} MB")
                print(f"Memory Usage (Peak): {peak / 10**6:.2f} MB")
                print(f"Expanded Nodes: {expansions}")
                print(f"Search Length: N/A")
                print("---------------------------\n")
                tracemalloc.stop()
                return None

            enc = _encode(current_tab, current_fc, current_fd)

            if all(len(pile) == 13 for pile in current_fd):
                elapsed = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()
                actions = init_auto + _reconstruct_path(came_from, enc)
                print("\n\n--- BFS Search Results ---")
                print("Status: SOLVED")
                print(f"Search Time: {elapsed:.3f} seconds")
                print(f"Memory Usage (Current): {current / 10**6:.2f} MB")
                print(f"Memory Usage (Peak): {peak / 10**6:.2f} MB")
                print(f"Expanded Nodes: {expansions}")
                print(f"Search Length: {len(actions)} moves")
                print("---------------------------\n")
                tracemalloc.stop()
                return actions

            prev_move = came_from[enc][1] if enc in came_from else None

            for primary, new_tab, new_fc, new_fd in _successors(current_tab, current_fc, current_fd, prev_move):
                new_tab, new_fc, new_fd, auto = _auto_foundation(new_tab, new_fc, new_fd)
                new_enc = _encode(new_tab, new_fc, new_fd)

                if new_enc not in visited:
                    visited.add(new_enc)
                    came_from[new_enc] = (enc, primary, auto)
                    
                    h_score = _heuristic(new_tab, new_fc, new_fd)
                    next_level_candidates.append((h_score, new_tab, new_fc, new_fd))

        next_level_candidates.sort(key=lambda x: x[0])
        beam = [(state[1], state[2], state[3]) for state in next_level_candidates[:beam_width]]

    elapsed = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    print("\n\n--- BFS Search Results ---")
    print("Status: BFS EMPTY (No Solution)")
    print(f"Search Time: {elapsed:.3f} seconds")
    print(f"Memory Usage (Current): {current / 10**6:.2f} MB")
    print(f"Memory Usage (Peak): {peak / 10**6:.2f} MB")
    print(f"Expanded Nodes: {expansions}")
    print(f"Search Length: N/A")
    print("---------------------------\n")
    tracemalloc.stop()
    return None

def _move_tableau_to_freecell(tableau, freecells, col_index, slot_index, card):
    tableau[col_index].pop()
    freecells[slot_index] = card

def _move_tableau_to_foundation(tableau, foundations, col_index, pile_index, card):
    tableau[col_index].pop()
    foundations[pile_index].append(card)

def _move_tableau_to_tableau(tableau, from_col, to_col, card):
    tableau[from_col].pop()
    tableau[to_col].append(card)

def _move_freecell_to_foundation(freecells, foundations, slot_index, pile_index, card):
    freecells[slot_index] = None
    foundations[pile_index].append(card)

def _move_freecell_to_tableau(freecells, tableau, slot_index, col_index, card):
    freecells[slot_index] = None
    tableau[col_index].append(card)

def _move_freecell_to_freecell(freecells, from_slot, to_slot, card):
    freecells[from_slot] = None
    freecells[to_slot] = card

def apply_solution(actions, tableau, freecells, foundations):
    for action in actions:
        src = action["from"]
        dest = action["to"]

        src_type = src[0]
        dest_type = dest[0]
        dest_idx = dest[1]

        if src_type == "tableau":
            col_idx = src[1]
            if len(src) == 3:
                start_idx = src[2]
                cards = list(tableau[col_idx][start_idx:])
            else:
                cards = [tableau[col_idx][-1]]
        elif src_type == "freecell":
            col_idx = src[1]
            cards = [freecells[col_idx]]
        else:
            raise ValueError(f"Unexpected source type: {src_type!r}")

        if src_type == "tableau" and dest_type == "freecell":
            _move_tableau_to_freecell(tableau, freecells, col_idx, dest_idx, cards[0])
        elif src_type == "tableau" and dest_type == "foundation":
            _move_tableau_to_foundation(tableau, foundations, col_idx, dest_idx, cards[0])
        elif src_type == "tableau" and dest_type == "tableau":
            if len(cards) == 1:
                _move_tableau_to_tableau(tableau, col_idx, dest_idx, cards[0])
            else:
                del tableau[col_idx][len(tableau[col_idx]) - len(cards):]
                tableau[dest_idx].extend(cards)
        elif src_type == "freecell" and dest_type == "foundation":
            _move_freecell_to_foundation(freecells, foundations, col_idx, dest_idx, cards[0])
        elif src_type == "freecell" and dest_type == "tableau":
            _move_freecell_to_tableau(freecells, tableau, col_idx, dest_idx, cards[0])
        elif src_type == "freecell" and dest_type == "freecell":
            _move_freecell_to_freecell(freecells, col_idx, dest_idx, cards[0])
        else:
            raise ValueError(f"Unknown move: {src_type!r} -> {dest_type!r}")