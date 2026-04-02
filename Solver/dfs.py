import time
import tracemalloc

from Utils.helpers import (
    canonical_hash,
    is_goal,
    get_all_moves,
    apply_move,
    auto_play_foundations,
    game_to_state
)

def _depthLimitedDfs(state, depth, limit, path, visited, expanded, startTime, timeoutSec):
    if time.time() - startTime > timeoutSec:
        return None

    if is_goal(state):
        return list(path)

    if depth >= limit:
        return None

    stateHash = canonical_hash(state)
    if stateHash in visited and visited[stateHash] <= depth:
        return None

    visited[stateHash] = depth
    expanded[0] += 1

    if expanded[0] % 1000 == 0:
        currentTime = time.time() - startTime
        print(f"\r[DFS] Time: {currentTime:.1f}s | Expanded: {expanded[0]:,} | Depth: {limit}", end="", flush=True)

    allMoves = get_all_moves(state)

    for move in allMoves:
        newState = apply_move(state, move)
        newState, autoMoves = auto_play_foundations(newState)

        path.append(move)
        path.extend(autoMoves)

        result = _depthLimitedDfs(
            newState, depth + 1, limit,
            path, visited, expanded,
            startTime, timeoutSec
        )

        if result is not None:
            return result

        for _ in range(len(autoMoves) + 1):
            path.pop()

    return None

def _translate_to_user_format(friend_moves, tableau, freecells):
    translated = []
    
    tab_sizes = [len(col) for col in tableau]
    fc_occupied = [c is not None for c in freecells]

    for move in friend_moves:
        src_type, src_idx, dst_type, dst_idx, num_cards = move
        
        src_str = "tableau" if src_type == 't' else "freecell"
        if dst_type == 't':
            dst_str = "tableau"
        elif dst_type == 'h':
            dst_str = "foundation"
        else:
            dst_str = "freecell"

        if src_str == "tableau":
            start_idx = tab_sizes[src_idx] - num_cards
            src_tuple = ("tableau", src_idx, start_idx)
            tab_sizes[src_idx] -= num_cards
        else:
            src_tuple = ("freecell", src_idx)
            fc_occupied[src_idx] = False

        if dst_str == "tableau":
            tab_sizes[dst_idx] += num_cards
        elif dst_str == "freecell":
            fc_occupied[dst_idx] = True

        translated.append({
            "from": src_tuple,
            "to": (dst_str, dst_idx)
        })

    return translated

def solve(tableau, freecells, foundations, maxDepth=300, timeoutSec=120):
    startTime = time.time()
    tracemalloc.start()

    initialState = game_to_state(tableau, freecells, foundations)
    initialState, initAuto = auto_play_foundations(initialState)

    expanded = [0]

    for depthLimit in range(1, maxDepth + 1):
        if time.time() - startTime > timeoutSec:
            break

        visited = {}
        path = []

        result = _depthLimitedDfs(
            initialState, 0, depthLimit,
            path, visited, expanded,
            startTime, timeoutSec
        )

        if result is not None:
            elapsed = time.time() - startTime
            currentMem, peakMem = tracemalloc.get_traced_memory()
            
            full_friend_moves = initAuto + result
            actions = _translate_to_user_format(full_friend_moves, tableau, freecells)
            
            print("\n\n--- DFS Search Results ---")
            print("Status: SOLVED")
            print(f"Search Time: {elapsed:.3f} seconds")
            print(f"Memory Usage (Current): {currentMem / 10**6:.2f} MB")
            print(f"Memory Usage (Peak): {peakMem / 10**6:.2f} MB")
            print(f"Expanded Nodes: {expanded[0]}")
            print(f"Search Length: {len(actions)} moves")
            print("---------------------------\n")
            tracemalloc.stop()
            return actions

    elapsed = time.time() - startTime
    currentMem, peakMem = tracemalloc.get_traced_memory()
    print("\n\n--- DFS Search Results ---")
    if time.time() - startTime > timeoutSec:
        print("Status: TIMEOUT")
    else:
        print("Status: DFS EMPTY (No Solution)")
    print(f"Search Time: {elapsed:.3f} seconds")
    print(f"Memory Usage (Current): {currentMem / 10**6:.2f} MB")
    print(f"Memory Usage (Peak): {peakMem / 10**6:.2f} MB")
    print(f"Expanded Nodes: {expanded[0]}")
    print(f"Search Length: N/A")
    print("---------------------------\n")
    tracemalloc.stop()
    return None