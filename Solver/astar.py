import heapq
from Utils.constants import RANK_VALUE, SUIT_COLOR, OPPOSITE_COLOR_SUITS, ALL_SUITS
from Utils.helpers import _valid_on_foundation, _valid_on_tableau
from Solver.heuristics import _heuristic

def _to_tuple_state(tableau, freecells, foundations):
    tab = tuple(tuple((c.rank, c.suit) for c in col) for col in tableau)
    fc  = tuple((c.rank, c.suit) if c is not None else None for c in freecells)
    fd  = tuple(tuple((c.rank, c.suit) for c in pile) for pile in foundations)
    return tab, fc, fd


def _encode(tab, fc, fd):
    tab_str = "/".join(
        "|".join(f"{r}{s[0]}" for r, s in col) if col else "-"
        for col in tab
    )
    fc_str = ",".join(f"{c[0]}{c[1][0]}" if c else "." for c in fc)
    fd_str = "/".join(
        f"{pile[-1][1][0]}{len(pile)}" if pile else "-"
        for pile in fd
    )
    return f"{tab_str}#{fc_str}#{fd_str}"


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
                    fd  = fd[:pi] + (fd[pi] + (card,),) + fd[pi + 1:]
                    auto_actions.append({"from": ("tableau", ci), "to": ("foundation", pi)})
                    changed = True
                    break
    return tab, fc, fd, auto_actions


def _max_movable(fc, tab, target_col=None):
    empty_fc   = sum(1 for c in fc if c is None)
    empty_cols = sum(1 for i, col in enumerate(tab)
                     if len(col) == 0 and i != target_col)
    return (empty_fc + 1) * (2 ** empty_cols)


def _remove_t(tab, fc, fd, src):
    kind, idx = src
    if kind == "freecell":
        return tab, fc[:idx] + (None,) + fc[idx + 1:], fd
    if kind == "tableau":
        new_col = tab[idx][:-1]
        return tab[:idx] + (new_col,) + tab[idx + 1:], fc, fd
    if kind == "foundation":
        new_pile = fd[idx][:-1]
        return tab, fc, fd[:idx] + (new_pile,) + fd[idx + 1:]
    return tab, fc, fd


def _successors(tab, fc, fd):
    candidates = []
    for i, card in enumerate(fc):
        if card is not None:
            candidates.append((card, ("freecell", i)))
    for col_i, col in enumerate(tab):
        if col:
            candidates.append((col[-1], ("tableau", col_i)))

    for card, src in candidates:

        # to foundation
        for fi, pile in enumerate(fd):
            if _valid_on_foundation(card, pile):
                new_tab, new_fc, new_fd = _remove_t(tab, fc, fd, src)
                new_fd = new_fd[:fi] + (new_fd[fi] + (card,),) + new_fd[fi + 1:]
                yield {"from": src, "to": ("foundation", fi)}, new_tab, new_fc, new_fd

        # to tableau
        for col_i, col in enumerate(tab):
            if src[0] == "tableau" and src[1] == col_i:
                continue
            target = col[-1] if col else None
            if _valid_on_tableau(card, target) and _max_movable(fc, tab, col_i) >= 1:
                new_tab, new_fc, new_fd = _remove_t(tab, fc, fd, src)
                new_tab = (new_tab[:col_i]
                           + (new_tab[col_i] + (card,),)
                           + new_tab[col_i + 1:])
                yield {"from": src, "to": ("tableau", col_i)}, new_tab, new_fc, new_fd

        # to freecell (from tableau only; break after first empty slot)
        if src[0] == "tableau":
            for fi, slot in enumerate(fc):
                if slot is None:
                    new_tab, new_fc, new_fd = _remove_t(tab, fc, fd, src)
                    new_fc = new_fc[:fi] + (card,) + new_fc[fi + 1:]
                    yield {"from": src, "to": ("freecell", fi)}, new_tab, new_fc, new_fd
                    break


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

def solve(tableau, freecells, foundations, max_states=2_000_000, timeout_sec=30):
    import time
    deadline = time.time() + timeout_sec

    tab, fc, fd = _to_tuple_state(tableau, freecells, foundations)

    tab, fc, fd, init_auto = _auto_foundation(tab, fc, fd)

    start_enc   = _encode(tab, fc, fd)
    h0          = _heuristic(tab, fc, fd)
    print(f"h0={h0}")

    tie_counter = 0
    heap        = [(h0, 0, tie_counter, tab, fc, fd)]
    visited     = {start_enc: 0}
    came_from   = {}
    expansions  = 0

    while heap:
        if expansions % 1000 == 0 and time.time() > deadline:
            print(f"TIMEOUT at {expansions} expansions")
            return None
        if expansions >= max_states:
            print(f"MAX STATES at {expansions}")
            return None
        expansions += 1

        f, g, _, tab, fc, fd = heapq.heappop(heap)

        tab, fc, fd, popped_auto = _auto_foundation(tab, fc, fd)
        enc = _encode(tab, fc, fd)

        # Skip stale heap entries
        if visited.get(enc, float('inf')) < g:
            continue

        # Goal: all 52 cards home
        if all(len(pile) == 13 for pile in fd):
            print(f"SOLVED in {expansions} expansions")
            return init_auto + _reconstruct_path(came_from, enc)

        # Expand successors
        for primary, new_tab, new_fc, new_fd in _successors(tab, fc, fd):
            # Run auto_foundation on successor -- result is POST-auto state
            new_tab, new_fc, new_fd, auto = _auto_foundation(new_tab, new_fc, new_fd)
            new_g   = g + 1
            # Encode POST-auto state -- consistent with all other enc values
            new_enc = _encode(new_tab, new_fc, new_fd)

            if new_g < visited.get(new_enc, float('inf')):
                visited[new_enc]   = new_g
                # Parent enc is also POST-auto -- chain links correctly
                came_from[new_enc] = (enc, primary, auto)
                h     = _heuristic(new_tab, new_fc, new_fd)
                new_f = new_g + h
                tie_counter += 1
                heapq.heappush(
                    heap,
                    (new_f, new_g, tie_counter, new_tab, new_fc, new_fd)
                )

    print(f"HEAP EMPTY after {expansions} expansions")
    return None

def _get_top_card_from_tableau(tableau, col_index):
    return tableau[col_index][-1]

def _get_top_card_from_freecell(freecells, slot_index):
    return freecells[slot_index]

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
    freecells[to_slot]   = card


def apply_solution(actions, tableau, freecells, foundations):
    for action in actions:
        src_type,  src_idx  = action["from"]
        dest_type, dest_idx = action["to"]

        if src_type == "tableau":
            card = _get_top_card_from_tableau(tableau, src_idx)
        elif src_type == "freecell":
            card = _get_top_card_from_freecell(freecells, src_idx)
        else:
            raise ValueError(f"Unexpected source type: {src_type!r}")

        if   src_type == "tableau"  and dest_type == "freecell":
            _move_tableau_to_freecell(tableau, freecells, src_idx, dest_idx, card)
        elif src_type == "tableau"  and dest_type == "foundation":
            _move_tableau_to_foundation(tableau, foundations, src_idx, dest_idx, card)
        elif src_type == "tableau"  and dest_type == "tableau":
            _move_tableau_to_tableau(tableau, src_idx, dest_idx, card)
        elif src_type == "freecell" and dest_type == "foundation":
            _move_freecell_to_foundation(freecells, foundations, src_idx, dest_idx, card)
        elif src_type == "freecell" and dest_type == "tableau":
            _move_freecell_to_tableau(freecells, tableau, src_idx, dest_idx, card)
        elif src_type == "freecell" and dest_type == "freecell":
            _move_freecell_to_freecell(freecells, src_idx, dest_idx, card)
        else:
            raise ValueError(f"Unknown move: {src_type!r} -> {dest_type!r}")