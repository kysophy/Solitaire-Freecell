# Group 10 - Introduction to AI - FreeCell AI Solver

Welcome to Group 10's FreeCell Solver for the Introduction to AI course! 

This project features a fully playable FreeCell graphical interface built in Python, complete with a strict rule engine and four integrated Artificial Intelligence solvers: Breadth-First Search (Beam Search), Depth-First Search (IDS), Uniform Cost Search, and Weighted A-Star.

## How to Run the Game

Running the main game is very straightforward. You don't need any external libraries, everything runs on standard Python (using tkinter for the UI).

1. Open your terminal or command prompt.

2. Ensure you are in the root directory of the project folder.

3. Run the following command:
   py main.py


## Running the AI Experiments

We have built a dedicated testing script to evaluate the performance of our algorithms across 5 predefined Microsoft FreeCell seeds (1, 100, 500, 1000, 32000).

To run the automated benchmark tests and see the terminal outputs for Search Time, Memory Usage, and Expanded Nodes:

1. Open your terminal or command prompt.

2. Navigate into the testing directory:
   cd testing

3. Run the following command:
   py runExperiments.py