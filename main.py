import itertools
import numpy as np

sudokus = np.load(f"data/hard_puzzle.npy")
solutions = np.load(f"data/hard_solution.npy")

current=10
current_sudoku = sudokus[current]
current_solution = solutions[current]

COLUMN_CHARACTERS = 'ABCDEFGHI'
ROW_NUMBERS = '123456789'

def cartesian_product(arr1, arr2):
    return [a + b for a in arr1 for b in arr2]

'''
arc consitency algorithm (AC3) requires binary constraints.
So split each row, column and box constraint into a binary constraint (one arc) [X,Y] & [Y,X]
returns all the arcs.
'''
def build_arc_constraints():
    row_constraints = [cartesian_product(COLUMN_CHARACTERS, n) for n in ROW_NUMBERS] 
    col_constraints = [cartesian_product(character, ROW_NUMBERS) for character in COLUMN_CHARACTERS]
    box_constraints = [cartesian_product(block_cols, block_rows) for block_cols in ('ABC', 'DEF', 'GHI') for block_rows in ('123', '456', '789')]

    arc_constraints = []
    for constraints in (row_constraints, col_constraints, box_constraints):
        for constraint in constraints:
              combinations = [[combination[0], combination[1]] 
                                for combination in itertools.permutations(constraint, 2) 
                                if [combination[0], combination[1]] not in arc_constraints]
              arc_constraints += combinations
    return arc_constraints

'''
from the arc constraints, you can work out all the neighbours for each variable
returns a dictionary of all variables and their neighbours
'''
def build_neighbours(variables, arc_constraints):
    neighbours={}
    for X in variables:
        neighbours[X] = []
        for constraint in arc_constraints:
            if X == constraint[0]:
                neighbours[X].append(constraint[1])
    return neighbours
  
VARIABLES = cartesian_product(COLUMN_CHARACTERS, ROW_NUMBERS)
ARC_CONSTRAINTS = build_arc_constraints()
NEIGHBOURS = build_neighbours(VARIABLES, ARC_CONSTRAINTS)


class SudokuSolver:
    def __init__(self, sudoku, VARIABLES, ARC_CONSTRAINTS, NEIGHBOURS):
        #list of all constraints (in a binary constraint form)
        self.ARC_CONSTRAINTS = ARC_CONSTRAINTS
        #dictionary of variables and their neighbours
        self.NEIGHBOURS = NEIGHBOURS
        #list of all variables (cells on the sudoku board). A1, A2,...I9
        self.VARIABLES = VARIABLES
        
        flat_sudoku = sudoku.flatten()
        #holds the current assigned variables of the sudoku. When it has 81 assignments the sudoku is solved
        self.partial_assignments = {var: flat_sudoku[i] for i, var in enumerate(VARIABLES) if flat_sudoku[i] != 0 } 
        #the possible values (the domain) of each variable (cell) in the sudoku 
        self.domains = {var: list(range(1,10)) if flat_sudoku[i] == 0 else [flat_sudoku[i]] for i, var in enumerate(VARIABLES) }
        #prune_history
        self.prune_history = {var: list() if flat_sudoku[i] == 0 else [flat_sudoku[i]] for i, var in enumerate(VARIABLES)}
    
    '''
    checks that for every value (xk) in xi's domain,
    there is at least some value (yk) in xj's domain that differs (is consistent with).
    
    if not, remove xk from xi's domain to make it consistent,
    and return true to indicate xi's domain has changed 
    '''
    def revise(self, xi, xj): 
        revised = False
        for xk in self.domains[xi]:
            if not any([xk != yk for yk in self.domains[xj]]):
                self.domains[xi].remove(xk)
                revised = True
        return revised
    
    '''
    generic AC3 algorithm - 
    reduce the domains of the variables, which in some cases can fully solve the sudoku
    returns whether its arc-consistent (the sudoku is solvable)
    '''
    def is_arc_consistent(self):
        #make a copy
        arcs = list(self.ARC_CONSTRAINTS)
        while arcs:
            #take any of the remaining arcs
            xi, xj = arcs.pop(0)
            #if need to change the domain of xi so that it's consistent with xj
            if self.revise(xi, xj):
                #no solution to the sudoku
                if len(self.domains[xi]) == 0:
                    return False
                #need to add the neighbours' arcs back on (except the current arc),
                #to ensure they're still consistent with xi (since xi's domain changed)
                for xk in self.NEIGHBOURS[xi]:
                    if xk != xi:
                        arcs.append([xk, xi])
        return True
    
    #returns whether a value is valid at a given variable
    def meets_constraints(self, var, target_value): 
        for neighbour in self.NEIGHBOURS[var]:
            if neighbour in self.partial_assignments and target_value == self.partial_assignments[neighbour]:
                return False
        return True
    '''
    Forward check heuristic: 
    it looks one-step ahead, removing now inconsistent values from the domains 
    of neighbouring variables (similar to AC3).
    
    returns whether the target_value is valid, i.e. none of the neighbour's domains became empty
    '''
    def forward_check(self, var, target_value):
        for neighbour in self.NEIGHBOURS[var]:
            if neighbour in self.partial_assignments: continue
            if target_value in self.domains[neighbour]:
                self.domains[neighbour].remove(target_value)
                self.prune_history[var].append((neighbour, target_value))
                if len(self.domains) == 0: return False
        return True
    
    ''' 
    remove the current assignment of a variable and restore its neighbours domains
    to how they were before the assignment.
    '''
    def unassign(self, var):
        if var not in self.partial_assignments: return
        #restore domain values that were removed during forward_check
        for (neighbour, value) in self.prune_history[var]:
            self.domains[neighbour].append(value)
        self.prune_history[var] = []
        del self.partial_assignments[var]
    
    '''
    Most Constrained Variable heuristic:
    returns the next unassigned variable that has the fewest consistent values
    '''
    def get_unassigned_variable(self):
        unassigned = [v for v in self.VARIABLES if v not in self.partial_assignments]
        return min(unassigned, key=lambda var: len(self.domains[var]) )
    
    '''
    Least Constrained Value heuristic:
    returns the value in the variable's domain that yields the highest number
    of consistent values of its neighours. 
    '''
    def order_domain_values(self, var):
        #if naked single
        if len(self.domains[var]) == 1:
            return self.domains[var]
        value_to_sum = {}
        for value in self.domains[var]: 
            sum=0
            for neighbour in self.NEIGHBOURS[var]:
                sum += len(self.domains[neighbour])
                if value in self.domains[neighbour]: sum -= 1
            value_to_sum[value] = sum
        return sorted(value_to_sum, key=value_to_sum.get, reverse=True)    

    '''
    recurisve backtrack method to solve the sudoku. If solvable, the result
    will be in self.partial_assignments. To speed up backtracking It Uses:
        * MCV heuristic
        * LCV heuristic
        * forward checking
    returns whether the sudoku is solvable
    '''
    def backtrack(self):
        if len(self.partial_assignments) == len(self.VARIABLES): return True
        next_var = self.get_unassigned_variable()
        for value in self.order_domain_values(next_var):
            if not self.meets_constraints(next_var, value): continue
            if not self.forward_check(next_var, value): return False
            self.partial_assignments[next_var] = value
            if self.backtrack(): return True
            self.unassign(next_var)
        return False
    
    '''
    The main method. Once finished solving, it'll turn the partial_assignments dictionary
    into a 9x9 array. If the sudoku is unsolvable, it'll return a 9x9 array of negative ones
    '''
    def solve(self):
        if not self.is_arc_consistent(): return np.full((9,9), -1)
        if not self.backtrack(): return np.full((9,9), -1)
        #sudoku was solvable, need to turn back into 9x9 array
        result = np.empty((9,9))
        for i, var in enumerate(self.VARIABLES):
            result[i // 9][i % 9] = self.partial_assignments[var]
        return result
               

sudoku = SudokuSolver(
    current_sudoku, 
    VARIABLES, 
    ARC_CONSTRAINTS, 
    NEIGHBOURS
)

solved_sudoku = sudoku.solve()
print(solved_sudoku)
