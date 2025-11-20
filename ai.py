import time
import math
from multiprocessing import Pool, cpu_count
from config import WEIGHTS, DMAX, TIME_LIMIT
from game import OthelloGame

# Constants for board pieces
EMPTY, BLACK, WHITE = 0, 1, -1

# Directions (8-neighbors)
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1)
]


def evaluate_board(board, color, game):
    """
    Standalone evaluation function equivalent to OthelloAI.evaluate,
    but usable inside worker processes (no dependence on self).
    """

    # --- Material ---
    black_count = sum(row.count(BLACK) for row in board)
    white_count = sum(row.count(WHITE) for row in board)
    material = black_count - white_count if color == BLACK else white_count - black_count

    # --- Mobility ---
    my_moves = len(game.get_legal_moves(board, color))
    opp_moves = len(game.get_legal_moves(board, -color))
    mobility = 0
    if my_moves + opp_moves != 0:
        mobility = my_moves - opp_moves

    # --- Corners ---
    corners_idx = [(0, 0), (0, 7), (7, 0), (7, 7)]
    my_corners = sum(1 for i, j in corners_idx if board[i][j] == color)
    opp_corners = sum(1 for i, j in corners_idx if board[i][j] == -color)
    corners = my_corners - opp_corners

    # --- Edges ---
    my_edges = 0
    opp_edges = 0

    # Top and bottom edges
    for i in [0, 7]:
        for j in range(8):
            if board[i][j] == color:
                my_edges += 1
            elif board[i][j] == -color:
                opp_edges += 1

    # Left and right edges (excluding corners)
    for j in [0, 7]:
        for i in range(1, 7):
            if board[i][j] == color:
                my_edges += 1
            elif board[i][j] == -color:
                opp_edges += 1

    edges = my_edges - opp_edges

    # --- Stability proxy (around owned corners) ---
    stability = 0
    for ci, cj in corners_idx:
        if board[ci][cj] == color:
            stability += 1  # corner itself
            for di in range(-1, 2):
                for dj in range(-1, 2):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = ci + di, cj + dj
                    if 0 <= ni < 8 and 0 <= nj < 8 and board[ni][nj] == color:
                        stability += 1

    score = (
        WEIGHTS["material"] * material +
        WEIGHTS["mobility"] * mobility +
        WEIGHTS["corner"] * corners +
        WEIGHTS["edge"] * edges +
        WEIGHTS["stability"] * stability
    )
    return score


def _parallel_worker(args):
    """
    Worker function used by multiprocessing.Pool.

    Each process:
      - applies a single candidate move at the root
      - runs alpha-beta from the resulting position
      - returns (move, score)

    NOTE: This is written without depending on OthelloAI instances
    to stay pickle-safe on Windows.
    """
    board, move, depth, color, start_time, time_limit = args

    game = OthelloGame()

    def time_exceeded() -> bool:
        return (time.time() - start_time) >= time_limit

    def alphabeta(local_board, d, alpha, beta, maximizing):
        # Determine whose turn it is in this node
        node_color = color if maximizing else -color
        legal_moves = game.get_legal_moves(local_board, node_color)

        # Terminal conditions: depth, no moves, or time up
        if d == 0 or not legal_moves or time_exceeded():
            return evaluate_board(local_board, color, game)

        if maximizing:
            value = -math.inf
            for m in legal_moves:
                child_board = game.apply_move(local_board, m, node_color)
                eval_val = alphabeta(child_board, d - 1, alpha, beta, False)
                value = max(value, eval_val)
                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break
            return value
        else:
            value = math.inf
            for m in legal_moves:
                child_board = game.apply_move(local_board, m, node_color)
                eval_val = alphabeta(child_board, d - 1, alpha, beta, True)
                value = min(value, eval_val)
                beta = min(beta, eval_val)
                if beta <= alpha:
                    break
            return value

    # Apply the root move and then search from opponent's perspective
    new_board = game.apply_move(board, move, color)
    score = alphabeta(new_board, depth - 1, -math.inf, math.inf, False)
    return move, score


class OthelloAI:
    """
    Othello AI using Minimax + Alpha-Beta pruning, iterative deepening,
    and optional parallel root search across all legal moves.

    Compatible with the existing Tkinter GUI (gui.py).
    """

    def __init__(self, game, color):
        # Initialize the Othello AI.
        self.game = game
        self.color = color
        self.start_time = None
        self.best_move = None

        # Optional: GUI looks for this; we keep it for compatibility.
        self.nodes_evaluated = 0

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------
    def time_exceeded(self) -> bool:
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) >= TIME_LIMIT

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def get_move(self):
        """
        Perform iterative deepening with alpha-beta pruning within TIME_LIMIT.

        Uses:
          - Sequential alpha-beta at shallow depths or single-move cases.
          - Parallel root search (multiprocessing) when there are multiple
            legal moves and depth >= 2.

        Returns the best move found before the time limit.
        """
        self.start_time = time.time()
        self.best_move = None
        self.nodes_evaluated = 0

        # Get initial legal moves from current position
        legal_moves = self.game.get_legal_moves(self.game.board, self.color)
        if not legal_moves:
            return None

        # Default fallback move in case we run out of time immediately
        self.best_move = legal_moves[0]

        # Iterative deepening loop
        for depth in range(1, DMAX + 1):
            if self.time_exceeded():
                break

            # If only one move, or very shallow depth, no need for parallelization
            if len(legal_moves) == 1 or depth == 1:
                move, _ = self._root_search_sequential(self.game.board, legal_moves, depth)
            else:
                move, _ = self._root_search_parallel(self.game.board, legal_moves, depth)

            # If we still have time and found a move, update best_move
            if not self.time_exceeded() and move is not None:
                self.best_move = move

        return self.best_move

    # ------------------------------------------------------------------
    # Root search helpers (sequential & parallel)
    # ------------------------------------------------------------------
    def _root_search_sequential(self, board, moves, depth):
        """
        Sequential root-level search with alpha-beta pruning.
        """
        best_move = None
        best_score = -math.inf
        alpha = -math.inf
        beta = math.inf
        color = self.color

        for move in moves:
            if self.time_exceeded():
                break

            new_board = self.game.apply_move(board, move, color)
            _, eval_val = self.alphabeta_search(
                new_board,
                depth - 1,
                alpha,
                beta,
                maximizing_player=False
            )

            if eval_val > best_score or best_move is None:
                best_score = eval_val
                best_move = move

            # Update alpha for future children (root-level alpha-beta)
            alpha = max(alpha, eval_val)

        return best_move, best_score

    def _root_search_parallel(self, board, moves, depth):
        """
        Parallel root-level search using multiprocessing.Pool.
        """
        if self.time_exceeded():
            return self.best_move, -math.inf

        # Build argument list for each worker
        tasks = [
            (board, move, depth, self.color, self.start_time, TIME_LIMIT)
            for move in moves
        ]

        n_procs = min(cpu_count(), len(moves))
        if n_procs <= 1:
            return self._root_search_sequential(board, moves, depth)

        try:
            with Pool(processes=n_procs) as pool:
                results = pool.map(_parallel_worker, tasks)
        except Exception as e:
            print(f"[OthelloAI] Parallel root search failed ({e}), falling back to sequential.")
            return self._root_search_sequential(board, moves, depth)

        best_move, best_score = max(results, key=lambda x: x[1])
        return best_move, best_score

    # ------------------------------------------------------------------
    # Alpha-Beta search (recursive, single-process)
    # ------------------------------------------------------------------
    def alphabeta_search(self, board, depth, alpha, beta, maximizing_player):
        """
        Standard recursive alpha-beta search used in the main process.
        """
        self.nodes_evaluated += 1

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

                new_board = self.game.apply_move(board, move, color)
                _, eval_val = self.alphabeta_search(
                    new_board,
                    depth - 1,
                    alpha,
                    beta,
                    False
                )

                if eval_val > max_eval or best_move is None:
                    max_eval = eval_val
                    best_move = move

                alpha = max(alpha, eval_val)
                if beta <= alpha:
                    break

            return best_move, max_eval
        else:
            min_eval = math.inf
            for move in legal_moves:
                if self.time_exceeded():
                    break

                new_board = self.game.apply_move(board, move, color)
                _, eval_val = self.alphabeta_search(
                    new_board,
                    depth - 1,
                    alpha,
                    beta,
                    True
                )

                if eval_val < min_eval or best_move is None:
                    min_eval = eval_val
                    best_move = move

                beta = min(beta, eval_val)
                if beta <= alpha:
                    break

            return best_move, min_eval

    # ------------------------------------------------------------------
    # Evaluation (main process, same heuristic as evaluate_board)
    # ------------------------------------------------------------------
    def evaluate(self, board):
        """
        Weighted evaluation of the board (same logic as evaluate_board),
        but from self.color's perspective.
        """
        # Material
        black_count = sum(row.count(BLACK) for row in board)
        white_count = sum(row.count(WHITE) for row in board)
        material = black_count - white_count if self.color == BLACK else white_count - black_count

        # Mobility
        my_moves = len(self.game.get_legal_moves(board, self.color))
        opp_moves = len(self.game.get_legal_moves(board, -self.color))
        mobility = 0
        if my_moves + opp_moves != 0:
            mobility = my_moves - opp_moves

        # Corners
        corners_idx = [(0, 0), (0, 7), (7, 0), (7, 7)]
        my_corners = sum(1 for i, j in corners_idx if board[i][j] == self.color)
        opp_corners = sum(1 for i, j in corners_idx if board[i][j] == -self.color)
        corners = my_corners - opp_corners

        # Edges
        my_edges = 0
        opp_edges = 0
        for i in [0, 7]:
            for j in range(8):
                if board[i][j] == self.color:
                    my_edges += 1
                elif board[i][j] == -self.color:
                    opp_edges += 1
        for j in [0, 7]:
            for i in range(1, 7):
                if board[i][j] == self.color:
                    my_edges += 1
                elif board[i][j] == -self.color:
                    opp_edges += 1
        edges = my_edges - opp_edges

        # Stability proxy
        stability = 0
        for ci, cj in corners_idx:
            if board[ci][cj] == self.color:
                stability += 1
                for di in range(-1, 2):
                    for dj in range(-1, 2):
                        if di == 0 and dj == 0:
                            continue
                        ni, nj = ci + di, cj + dj
                        if 0 <= ni < 8 and 0 <= nj < 8 and board[ni][nj] == self.color:
                            stability += 1

        score = (
            WEIGHTS["material"] * material +
            WEIGHTS["mobility"] * mobility +
            WEIGHTS["corner"] * corners +
            WEIGHTS["edge"] * edges +
            WEIGHTS["stability"] * stability
        )
        return score
