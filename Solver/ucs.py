import heapq
import time
import tracemalloc

from Utils.constants import RANK_VALUE, SUIT_COLOR, OPPOSITE_COLOR_SUITS, ALL_SUITS
from Utils.helpers import _valid_on_foundation, _valid_on_tableau

LAST_RUN_STATS = None


def _move_cost(action):
    src_kind = action["from"][0]
    dst_kind = action["to"][0]

    if dst_kind == "foundation":
        return 1

    if dst_kind == "freecell":
        return 5

    if src_kind == "freecell" and dst_kind == "tableau":
        return 3

    if src_kind == "tableau" and dst_kind == "tableau":
        return 2

    return 2


def _to_tuple_state(tableau, freecells, foundations):
    tab = tuple(tuple((c.rank, c.suit) for c in col) for col in tableau)
    fc = tuple((c.rank, c.suit) if c is not None else None for c in freecells)
    fd = tuple(tuple((c.rank, c.suit) for c in pile) for pile in foundations)
    return tab, fc, fd


def _canonical_freecells(fc):
    filled = sorted((c for c in fc if c is not None), key=lambda x: (x[1], RANK_VALUE[x[0]]))
    return tuple(filled) + (None,) * (4 - len(filled))


def _foundation_signature(fd):
    # Foundation hợp lệ luôn là A..top theo đúng suit, nên chỉ cần suit + length
    counts = {s: 0 for s in ALL_SUITS}
    for pile in fd:
        if pile:
            counts[pile[-1][1]] = len(pile)
    return tuple((s, counts[s]) for s in ALL_SUITS)


def _encode(tab, fc, fd):
    # Chuẩn hóa các cột tableau vì thứ tự cột tương đương dưới góc nhìn search
    canon_tab = tuple(sorted(tab, key=lambda col: (len(col), col)))
    canon_fc = _canonical_freecells(fc)
    canon_fd = _foundation_signature(fd)
    return (canon_tab, canon_fc, canon_fd)


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

        # freecell -> foundation
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
            if changed:
                break

        if changed:
            continue

        # tableau top -> foundation
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
            if changed:
                break

    return tab, fc, fd, auto_actions


def _max_movable(fc, tab, target_col=None):
    empty_fc = sum(1 for c in fc if c is None)
    empty_cols = sum(1 for i, col in enumerate(tab) if len(col) == 0 and i != target_col)
    return (empty_fc + 1) * (2 ** empty_cols)


def _remove_source(tab, fc, fd, src):
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


def _get_movable_stacks_from_col(col, max_len):
    """
    Chỉ sinh các suffix hợp lệ liên tiếp từ top xuống.
    Stack trả về có dạng col[start_idx:].
    """
    if not col:
        return []

    stacks = [(len(col) - 1, (col[-1],))]  # single exposed top card
    limit = min(len(col), max_len)

    for start_idx in range(len(col) - 2, len(col) - limit - 1, -1):
        upper = col[start_idx]
        lower = col[start_idx + 1]
        if (
            RANK_VALUE[upper[0]] == RANK_VALUE[lower[0]] + 1
            and SUIT_COLOR[upper[1]] != SUIT_COLOR[lower[1]]
        ):
            stacks.append((start_idx, col[start_idx:]))
        else:
            break

    return stacks


def _reconstruct_path(came_from, goal_key):
    segments = []
    cur = goal_key

    while cur in came_from:
        parent_key, primary, auto = came_from[cur]
        segments.append((primary, auto))
        cur = parent_key

    segments.reverse()

    flat = []
    for primary, auto in segments:
        flat.append(primary)
        flat.extend(auto)
    return flat

def _preview_score(tab, fc, fd, g):
    foundation_cards = sum(len(p) for p in fd)
    empty_fc = sum(1 for c in fc if c is None)
    empty_cols = sum(1 for col in tab if len(col) == 0)

    # tuple lớn hơn là tốt hơn
    return (foundation_cards, empty_cols, empty_fc, -g)


def _finish(success, actions, total_cost, expanded_nodes, states_stored, start_time, reason):
    global LAST_RUN_STATS

    elapsed = time.perf_counter() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    LAST_RUN_STATS = {
        "success": success,
        "reason": reason,
        "search_time": elapsed,
        "memory_usage_mb": peak / 10**6,
        "expanded_nodes": expanded_nodes,
        "search_length": len(actions),
        "total_cost": total_cost,
        "states_stored": states_stored,
    }

    print("=== UCS ===")
    print(f"reason: {reason}")
    print(f"success: {success}")
    print(f"search_time: {elapsed:.3f} s")
    print(f"memory_usage_mb: {peak / 10**6:.2f}")
    print(f"expanded_nodes: {expanded_nodes}")
    print(f"search_length: {len(actions)}")
    print(f"total_cost: {total_cost}")
    print(f"states_stored: {states_stored}")

    return {
        "success": success,
        "reason": reason,
        "actions": list(actions),
        "stats": LAST_RUN_STATS,
    }

def _successors(tab, fc, fd):
    empty_fc_idx = next((i for i, slot in enumerate(fc) if slot is None), None)
    empty_tableau_idx = next((i for i, col in enumerate(tab) if len(col) == 0), None)

    tableau_tops = [col[-1] if col else None for col in tab]
    target_caps = [_max_movable(fc, tab, i) for i in range(len(tab))]
    global_stack_cap = _max_movable(fc, tab)

    # 1) freecell sources: chỉ single-card
    for fi, card in enumerate(fc):
        if card is None:
            continue

        src = ("freecell", fi)

        # freecell -> foundation
        for pi, pile in enumerate(fd):
            if _valid_on_foundation(card, pile) and _is_safe_to_foundation(card, fd):
                move = {"from": src, "to": ("foundation", pi)}
                new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                new_fd = new_fd[:pi] + (new_fd[pi] + (card,),) + new_fd[pi + 1:]
                yield move, new_tab, new_fc, new_fd
                break

        # freecell -> non-empty tableau
        for dst in range(8):
            if tableau_tops[dst] is None:
                continue
            if _valid_on_tableau(card, tableau_tops[dst]):
                move = {"from": src, "to": ("tableau", dst)}
                new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                new_tab = new_tab[:dst] + (new_tab[dst] + (card,),) + new_tab[dst + 1:]
                yield move, new_tab, new_fc, new_fd

        # freecell -> one representative empty tableau
        if empty_tableau_idx is not None:
            dst = empty_tableau_idx
            move = {"from": src, "to": ("tableau", dst)}
            new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
            new_tab = new_tab[:dst] + (new_tab[dst] + (card,),) + new_tab[dst + 1:]
            yield move, new_tab, new_fc, new_fd

    # 2) tableau top single-card sources
    for src_col, col in enumerate(tab):
        if not col:
            continue

        card = col[-1]
        src = ("tableau", src_col)

        # tableau top -> foundation
        for pi, pile in enumerate(fd):
            if _valid_on_foundation(card, pile) and _is_safe_to_foundation(card, fd):
                move = {"from": src, "to": ("foundation", pi)}
                new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                new_fd = new_fd[:pi] + (new_fd[pi] + (card,),) + new_fd[pi + 1:]
                yield move, new_tab, new_fc, new_fd
                break

        # tableau top -> non-empty tableau
        for dst in range(8):
            if dst == src_col or tableau_tops[dst] is None:
                continue
            if _valid_on_tableau(card, tableau_tops[dst]):
                move = {"from": src, "to": ("tableau", dst)}
                new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                new_tab = new_tab[:dst] + (new_tab[dst] + (card,),) + new_tab[dst + 1:]
                yield move, new_tab, new_fc, new_fd

        # tableau top -> one representative empty tableau
        if empty_tableau_idx is not None and empty_tableau_idx != src_col:
            dst = empty_tableau_idx
            if target_caps[dst] >= 1:
                move = {"from": src, "to": ("tableau", dst)}
                new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                new_tab = new_tab[:dst] + (new_tab[dst] + (card,),) + new_tab[dst + 1:]
                yield move, new_tab, new_fc, new_fd

        # tableau top -> freecell
        if empty_fc_idx is not None:
            fi = empty_fc_idx
            move = {"from": src, "to": ("freecell", fi)}
            new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
            new_fc = new_fc[:fi] + (card,) + new_fc[fi + 1:]
            yield move, new_tab, new_fc, new_fd

    # 3) multi-card tableau -> tableau only
    for src_col, col in enumerate(tab):
        if len(col) <= 1:
            continue

        stacks = _get_movable_stacks_from_col(col, global_stack_cap)
        if len(stacks) <= 1:
            continue

        for start_idx, moving_cards in stacks[1:]:  # bỏ single-card; đã xử lý ở trên
            card = moving_cards[0]
            stack_len = len(moving_cards)

            # multi-card -> non-empty tableau
            for dst in range(8):
                if dst == src_col or tableau_tops[dst] is None:
                    continue
                if stack_len <= target_caps[dst] and _valid_on_tableau(card, tableau_tops[dst]):
                    src = ("tableau", src_col, start_idx)
                    move = {"from": src, "to": ("tableau", dst)}
                    new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                    new_tab = new_tab[:dst] + (new_tab[dst] + moving_cards,) + new_tab[dst + 1:]
                    yield move, new_tab, new_fc, new_fd

            # multi-card -> one representative empty tableau
            if empty_tableau_idx is not None and empty_tableau_idx != src_col:
                dst = empty_tableau_idx
                if stack_len <= target_caps[dst]:
                    src = ("tableau", src_col, start_idx)
                    move = {"from": src, "to": ("tableau", dst)}
                    new_tab, new_fc, new_fd = _remove_source(tab, fc, fd, src)
                    new_tab = new_tab[:dst] + (new_tab[dst] + moving_cards,) + new_tab[dst + 1:]
                    yield move, new_tab, new_fc, new_fd


def solve(
    tableau,
    freecells,
    foundations,
    max_states=5_000_000,
    timeout_sec=180,
    progress_cb=None,
    progress_interval=0.5,
):
    start_time = time.perf_counter()
    deadline = start_time + timeout_sec if timeout_sec is not None else float("inf")
    tracemalloc.start()

    tab, fc, fd = _to_tuple_state(tableau, freecells, foundations)
    tab, fc, fd, init_auto = _auto_foundation(tab, fc, fd)

    start_key = _encode(tab, fc, fd)
    start_cost = sum(_move_cost(a) for a in init_auto)

    tie = 0
    heap = [(start_cost, tie, tab, fc, fd)]
    best_cost = {start_key: start_cost}
    came_from = {}
    expanded_nodes = 0

    best_preview_key = start_key
    best_preview_cost = start_cost
    best_preview_score = _preview_score(tab, fc, fd, start_cost)
    last_progress_emit = start_time

    while heap:
        g, _, tab, fc, fd = heapq.heappop(heap)
        key = _encode(tab, fc, fd)

        if g > best_cost.get(key, float("inf")):
            continue

        now = time.perf_counter()
        if now > deadline:
            best_actions = init_auto + _reconstruct_path(came_from, best_preview_key)
            if progress_cb is not None and now - last_progress_emit >= progress_interval:
                preview_actions = init_auto + _reconstruct_path(came_from, best_preview_key)
                foundation_cards = best_preview_score[0]
                progress_cb({
                    "actions": preview_actions,
                    "expanded_nodes": expanded_nodes,
                    "states_stored": len(best_cost),
                    "current_cost": best_preview_cost,
                    "foundation_cards": foundation_cards,
                    "elapsed": now - start_time,
                })
                last_progress_emit = now

            return _finish(
                False,
                best_actions,
                best_preview_cost,
                expanded_nodes,
                len(best_cost),
                start_time,
                "timeout"
            )

        if len(best_cost) > max_states:
            best_actions = init_auto + _reconstruct_path(came_from, best_preview_key)

            if progress_cb is not None:
                progress_cb({
                    "actions": best_actions,
                    "expanded_nodes": expanded_nodes,
                    "states_stored": len(best_cost),
                    "current_cost": best_preview_cost,
                    "foundation_cards": best_preview_score[0],
                    "elapsed": time.perf_counter() - start_time,
                })

            return _finish(
                False,
                best_actions,
                best_preview_cost,
                expanded_nodes,
                len(best_cost),
                start_time,
                "max_states_exceeded"
            )

        expanded_nodes += 1

        score = _preview_score(tab, fc, fd, g)
        if score > best_preview_score:
            best_preview_key = key
            best_preview_score = score
            best_preview_cost = g

        if all(len(pile) == 13 for pile in fd):
            actions = init_auto + _reconstruct_path(came_from, key)
            return _finish(
                True,
                actions,
                g,
                expanded_nodes,
                len(best_cost),
                start_time,
                "solved"
            )

        if progress_cb is not None and now - last_progress_emit >= progress_interval:
            preview_actions = init_auto + _reconstruct_path(came_from, best_preview_key)
            foundation_cards = best_preview_score[0]
            progress_cb({
                "actions": preview_actions,
                "expanded_nodes": expanded_nodes,
                "states_stored": len(best_cost),
                "current_cost": best_preview_cost,
                "foundation_cards": foundation_cards,
                "elapsed": now - start_time,
            })
            last_progress_emit = now

        for primary, new_tab, new_fc, new_fd in _successors(tab, fc, fd):
            new_tab, new_fc, new_fd, auto = _auto_foundation(new_tab, new_fc, new_fd)

            step_cost = _move_cost(primary) + sum(_move_cost(a) for a in auto)
            new_g = g + step_cost
            new_key = _encode(new_tab, new_fc, new_fd)

            if new_g < best_cost.get(new_key, float("inf")):
                best_cost[new_key] = new_g
                came_from[new_key] = (key, primary, auto)
                tie += 1
                heapq.heappush(heap, (new_g, tie, new_tab, new_fc, new_fd))

    best_actions = init_auto + _reconstruct_path(came_from, best_preview_key)

    if progress_cb is not None:
        progress_cb({
            "actions": best_actions,
            "expanded_nodes": expanded_nodes,
            "states_stored": len(best_cost),
            "current_cost": best_preview_cost,
            "foundation_cards": best_preview_score[0],
            "elapsed": time.perf_counter() - start_time,
        })
        
    return _finish(
        False,
        best_actions,
        best_preview_cost,
        expanded_nodes,
        len(best_cost),
        start_time,
        "heap_empty"
    )