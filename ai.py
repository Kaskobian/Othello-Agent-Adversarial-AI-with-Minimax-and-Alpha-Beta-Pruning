import time
import math
import copy
from config import WEIGHTS, DMAX, TIME_LIMIT

# Constants for board pieces
EMPTY, BLACK, WHITE = 0, 1, -1

# Directions (8-neighbors)
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1)
]


class OthelloAI:
    def __init__(self, game, color):
    
        #Initialize the Othello AI.
        self.game = game
        self.color = color
        self.start_time = None
        self.best_move = None

    def time_exceeded(self):
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) >= TIME_LIMIT

    def get_move(self):
        #Perform iterative deepening with alpha-beta pruning within time limit.
        self.start_time = time.time()
        self.best_move = None

        # Get initial legal moves to have a fallback
        initial_moves = self.game.get_legal_moves(self.game.board, self.color)
        if not initial_moves:
            return None
        
        # Set a default move in case we run out of time immediately
        self.best_move = initial_moves[0]

        for depth in range(1, DMAX + 1):
            if self.time_exceeded():
                break
            
            try:
                move, _ = self.alphabeta_search(self.game.board, depth, -math.inf, math.inf, True)
                if not self.time_exceeded() and move is not None:
                    self.best_move = move
            except Exception as e:
                print(f"Error during search at depth {depth}: {e}")
                break

        return self.best_move

    def alphabeta_search(self, board, depth, alpha, beta, maximizing_player):
        
        # Determine whose turn it is
        color = self.color if maximizing_player else -self.color
        legal_moves = self.game.get_legal_moves(board, color)

        # Terminal conditions
        if depth == 0 or not legal_moves or self.time_exceeded():
            return None, self.evaluate(board)

        best_move = None

        if maximizing_player:
            max_eval = -math.inf
            for move in legal_moves:
                if self.time_exceeded():
                    break
                    
                new_board = self.game.apply_move(copy.deepcopy(board), move, color)
                _, eval_val = self.alphabeta_search(new_board, depth - 1, alpha, beta, False)
                
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_move = move
                    
                alpha = max(alpha, eval_val)
                if beta <= alpha:  # Beta cutoff
                    break
                    
            return best_move, max_eval

        else:  # Minimizing player
            min_eval = math.inf
            for move in legal_moves:
                if self.time_exceeded():
                    break
                    
                new_board = self.game.apply_move(copy.deepcopy(board), move, color)
                _, eval_val = self.alphabeta_search(new_board, depth - 1, alpha, beta, True)
                
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_move = move
                    
                beta = min(beta, eval_val)
                if beta <= alpha:  # Alpha cutoff
                    break
                    
            return best_move, min_eval

    def evaluate(self, board):
        
        material = self.evaluate_material(board)
        mobility = self.evaluate_mobility(board)
        corners = self.evaluate_corners(board)
        edges = self.evaluate_edges(board)
        stability = self.evaluate_stability(board)

        score = (
            WEIGHTS["material"] * material +
            WEIGHTS["mobility"] * mobility +
            WEIGHTS["corner"] * corners +
            WEIGHTS["edge"] * edges +
            WEIGHTS["stability"] * stability
        )
        return score

    def evaluate_material(self, board):
        #Count disc advantage.
        black_count = sum(row.count(BLACK) for row in board)
        white_count = sum(row.count(WHITE) for row in board)
        
        if self.color == BLACK:
            return black_count - white_count
        return white_count - black_count

    def evaluate_mobility(self, board):
        #Evaluate move flexibility.
        my_moves = len(self.game.get_legal_moves(board, self.color))
        opp_moves = len(self.game.get_legal_moves(board, -self.color))
        
        if my_moves + opp_moves == 0:
            return 0
        return my_moves - opp_moves

    def evaluate_corners(self, board):
        #Evaluate corner control (corners are very valuable).
        corners = [(0, 0), (0, 7), (7, 0), (7, 7)]
        my_corners = sum(1 for i, j in corners if board[i][j] == self.color)
        opp_corners = sum(1 for i, j in corners if board[i][j] == -self.color)
        return my_corners - opp_corners

    def evaluate_edges(self, board):
        #Evaluate edge control.
        my_edges = 0
        opp_edges = 0
        
        # Top and bottom edges
        for i in [0, 7]:
            for j in range(8):
                if board[i][j] == self.color:
                    my_edges += 1
                elif board[i][j] == -self.color:
                    opp_edges += 1
        
        # Left and right edges (excluding corners to avoid double counting)
        for j in [0, 7]:
            for i in range(1, 7):
                if board[i][j] == self.color:
                    my_edges += 1
                elif board[i][j] == -self.color:
                    opp_edges += 1
                    
        return my_edges - opp_edges

    def evaluate_stability(self, board):
        #Simple stability evaluation: bonus for discs near owned corners.
        #Stable discs cannot be flipped for the rest of the game.
        stability = 0
        corners = [(0, 0), (0, 7), (7, 0), (7, 7)]
        
        for ci, cj in corners:
            if board[ci][cj] == self.color:
                # Add bonus for the corner itself
                stability += 1
                
                # Add bonus for adjacent discs
                for di in range(-1, 2):
                    for dj in range(-1, 2):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = ci + di, cj + dj
                        if 0 <= ni < 8 and 0 <= nj < 8 and board[ni][nj] == self.color:
                            stability += 1
        return stability
