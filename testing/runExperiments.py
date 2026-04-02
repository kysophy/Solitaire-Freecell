import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import tracemalloc
from testCases import createDeckFromSeed
from Solver.bfs import solve as runBfs
from Solver.dfs import solve as runDfs
from Solver.ucs import solve as runUcs
from Solver.astar import solve as runAstar

TEST_SEEDS_ = [1, 100, 500, 1000, 32000]

def setupBoard(deckToUse):
    tab = [[] for _ in range(8)]
    fc = [None] * 4
    fd = [[] for _ in range(4)]
    
    for i, cardVal in enumerate(deckToUse):
        tab[i % 8].append(cardVal)
        
    return tab, fc, fd

def runEvaluation(algoName, algorithmFunc, tab, fc, fd):
    tracemalloc.start()
    startTime = time.time()
    
    # 1. Safely handle different parameters for DFS vs the others
    if algoName == "DFS":
        result = algorithmFunc(tab, fc, fd, timeoutSec=120)
    else:
        result = algorithmFunc(tab, fc, fd, timeout_sec=120)
    
    # 2. Safely handle inconsistent return types (tuples vs lists vs None)
    if isinstance(result, tuple):
        actionsFound = result[0] # Handle the edge case where BFS returns (None, expansions) on timeout
    else:
        actionsFound = result
    
    endTime = time.time()
    _, peakMemory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    timeTaken = endTime - startTime
    pathLength = len(actionsFound) if actionsFound else 0
    
    # Solvers print nodes to console, they don't return them to this script
    nodesExpanded = "Printed Above" 
    
    return timeTaken, peakMemory, nodesExpanded, pathLength

def runAllFixedTests():
    for currentSeed in TEST_SEEDS_:
        print(f"\n======================================")
        print(f"       RUNNING SEED: {currentSeed}")
        currentDeck = createDeckFromSeed(currentSeed)
        
        tab, fc, fd = setupBoard(currentDeck)
        bfsTime, bfsMem, bfsNodes, bfsLen = runEvaluation("BFS", runBfs, tab, fc, fd)
        print(f"-> BFS   | Time: {bfsTime:.4f}s | Mem: {bfsMem} bytes | Moves: {bfsLen}\n")
        
        tab, fc, fd = setupBoard(currentDeck)
        astarTime, astarMem, astarNodes, astarLen = runEvaluation("A*", runAstar, tab, fc, fd)
        print(f"-> A* | Time: {astarTime:.4f}s | Mem: {astarMem} bytes | Moves: {astarLen}\n")
        
        tab, fc, fd = setupBoard(currentDeck)
        ucsTime, ucsMem, ucsNodes, ucsLen = runEvaluation("UCS", runUcs, tab, fc, fd)
        print(f"-> UCS   | Time: {ucsTime:.4f}s | Mem: {ucsMem} bytes | Moves: {ucsLen}\n")
        
        tab, fc, fd = setupBoard(currentDeck)
        dfsTime, dfsMem, dfsNodes, dfsLen = runEvaluation("DFS", runDfs, tab, fc, fd)
        print(f"-> DFS   | Time: {dfsTime:.4f}s | Mem: {dfsMem} bytes | Moves: {dfsLen}\n")

if __name__ == "__main__":
    runAllFixedTests()