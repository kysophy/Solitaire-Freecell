import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import tracemalloc
from testCases import createDeckFromSeed
from Solver.bfs import solve as runBfs
from Solver.astar import solve as runAstar

TEST_SEEDS_ = [1, 100, 500, 1000, 32000]

def setupBoard(deckToUse):
    tab = [[] for _ in range(8)]
    fc = [None] * 4
    fd = [[] for _ in range(4)]
    
    for i, cardVal in enumerate(deckToUse):
        tab[i % 8].append(cardVal)
        
    return tab, fc, fd

def runEvaluation(algorithmFunc, tab, fc, fd):
    tracemalloc.start()
    startTime = time.time()
    
    actionsFound, nodesExpanded = algorithmFunc(tab, fc, fd, max_states=2000000, timeout_sec=60)
    
    endTime = time.time()
    _, peakMemory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    timeTaken = endTime - startTime
    pathLength = len(actionsFound) if actionsFound else 0
    
    return timeTaken, peakMemory, nodesExpanded, pathLength

def runAllFixedTests():
    for currentSeed in TEST_SEEDS_:
        print(f"--- RUNNING SEED: {currentSeed} ---")
        currentDeck = createDeckFromSeed(currentSeed)
        
        tab, fc, fd = setupBoard(currentDeck)
        bfsTime, bfsMem, bfsNodes, bfsLen = runEvaluation(runBfs, tab, fc, fd)
        print(f"BFS   | Time: {bfsTime:.4f}s | Mem: {bfsMem} bytes | Nodes: {bfsNodes} | Moves: {bfsLen}")
        
        tab, fc, fd = setupBoard(currentDeck)
        astarTime, astarMem, astarNodes, astarLen = runEvaluation(runAstar, tab, fc, fd)
        print(f"A* | Time: {astarTime:.4f}s | Mem: {astarMem} bytes | Nodes: {astarNodes} | Moves: {astarLen}")
        print("\n")

if __name__ == "__main__":
    runAllFixedTests()