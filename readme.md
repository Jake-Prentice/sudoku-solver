**The approach:**

There are quite a few different approaches you could take to create a sudoku solver. From my research, the most common and efficient approach was to treat it as a constraint satisfaction problem. Each cell of the sudoku is a variable; empty cells have a domain of {1,2,3,4,5,6,7,8,9} and prefilled cells have a domain of its singular value. The CSP uses alldifferent constraints for the nine rows, columns, and boxes.

I started by creating a simple recursive backtracking function. A total brute force approach, going systematically over each cell trying every value and recursing the new sudoku if the value was valid. This solution worked well up until the hard sudokus, where it would take minutes to complete each sudoku. I realised that it needed some heuristics to simplify the problem and stop it going down long, unnecessary, and computational paths.

This is when I researched into how humans solve sudokus as I had next to no experience on solving them by hand. The general approach being to somehow reduce the domains of cells as much as possible, leading to naked singles which are cells that only have one possible value left in their domain. Of course, brute force is still part of the approach, but the goal is to narrow down the search space as much as possible first.

These domain reductions are exactly what constraint propagation techniques are for and so naturally lead me to the arc-consistency algorithm AC-3. In some cases, this algorithm can even solve the sudoku without any backtracking. It's also used to identify whether the CSP is solvable. The algorithm requires binary or unary constraints so all the constraints of the sudoku need to be transformed.

Heuristics can also be applied during the backtracking process to try and take the branches that'll solve the sudoku quickest and not take branches that are doomed to fail:

- Most Constrained Value (MCV) – choose the variable with the least number of values in its domain. The idea being that if this branch is doomed to fail, it will fail faster than the other branches. But the same also goes for it succeeding.
- Least Constrained Value (LCV) – pick the value in the variable's domain that'll rule out the least number of values in its neighbour's domains. In essence, it assigns values that leave maximal flexibility for the remaining variables.
- Forward checking – once a partial assignment is made, look one-step ahead and remove inconsistent values from the domains of neighbouring variables. Not only does this prune neighbouring variables, reducing the number of domain values to search, and leading to naked singles, but it also flags if the assignment will cause an inconsistency further on.

**Code structure:**

I chose an OOP approach as