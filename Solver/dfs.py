"""IDS (Iterative Deepening Search) solver for FreeCell.

Duplicate detection uses a depth-aware visited dict (hash -> min depth expanded),
rebuilt fresh each iteration to preserve completeness. Canonical hashing treats
equivalent board positions (same cards, different column/cell ordering) as identical.
"""

import time
import tracemalloc
import sys

from Utils.helpers import (
    canonical_hash,
    is_goal,
    get_all_moves,
    apply_move,
    auto_play_foundations,
)

sys.setrecursionlimit(5000)


def solve_ids(initial_state, max_depth=300, time_limit=600, cancel_event=None):
    """
    Returns (solution_moves, stats) or (None, stats) if unsolvable.
    Stats dict keys: 'time', 'memory' (MB), 'expanded', 'length'.
    """
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    start_time = time.time()

    if is_goal(initial_state):
        elapsed = time.time() - start_time
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return [], {
            'time': elapsed,
            'memory': peak_mem / (1024 * 1024),
            'expanded': 0,
            'length': 0
        }

    expanded = [0]

    for depth_limit in range(1, max_depth + 1):
        if time.time() - start_time > time_limit:
            break
        if cancel_event and cancel_event.is_set():
            break

        visited = {}
        path = []

        result = _depth_limited_dfs(
            initial_state, 0, depth_limit,
            path, visited, expanded,
            start_time, time_limit, cancel_event
        )

        if result is not None:
            elapsed = time.time() - start_time
            _, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return result, {
                'time': elapsed,
                'memory': peak_mem / (1024 * 1024),
                'expanded': expanded[0],
                'length': len(result)
            }

    elapsed = time.time() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return None, {
        'time': elapsed,
        'memory': peak_mem / (1024 * 1024),
        'expanded': expanded[0],
        'length': 0
    }


def _depth_limited_dfs(state, depth, limit, path, visited, expanded,
                       start_time, time_limit, cancel_event=None):
    """
    Uses a depth-aware visited dict (hash -> min_depth_expanded) so a state
    reached via a shorter path can be re-explored with more remaining budget.
    Only expanded states (not cutoff or pruned) are counted.
    """
    if time.time() - start_time > time_limit:
        return None
    if cancel_event and cancel_event.is_set():
        return None

    if is_goal(state):
        return list(path)

    if depth >= limit:
        return None

    # Skip if already expanded at equal or shallower depth
    state_hash = canonical_hash(state)
    if state_hash in visited and visited[state_hash] <= depth:
        return None

    visited[state_hash] = depth
    expanded[0] += 1

    all_moves = get_all_moves(state)

    for move in all_moves:
        new_state = apply_move(state, move)

        # Auto-play safe foundation moves (aces, 2s, etc.) to shrink search tree
        new_state, auto_moves = auto_play_foundations(new_state)

        path.append(move)
        path.extend(auto_moves)

        result = _depth_limited_dfs(
            new_state, depth + 1, limit,
            path, visited, expanded,
            start_time, time_limit, cancel_event
        )

        if result is not None:
            return result

        # Backtrack: remove deliberate move + all auto-foundation moves
        for _ in range(len(auto_moves) + 1):
            path.pop()

        if time.time() - start_time > time_limit:
            return None

    return None
