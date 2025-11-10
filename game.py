import copy
from config import BOARD_SIZE, EMPTY, BLACK, WHITE, CHAR_MAP, DIRECTIONS


class OthelloGame:
    def __init__(self):
       #Initialize the Othello game board and history.
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.history = []  # For undo functionality
        
        # Starting position (origin at bottom-left)
        # Center four squares: (3,3), (3,4), (4,3), (4,4)
        # Assignment spec: "left-upper of center is white"
        # In bottom-left coordinates:
        #   (4,3) = left-upper of center = WHITE
        #   (3,4) = right-lower of center = WHITE
        #   (3,3) = left-lower of center = BLACK
        #   (4,4) = right-upper of center = BLACK
        
        self.board[3][3] = BLACK   # Bottom-left of center
        self.board[3][4] = WHITE   # Bottom-right of center
        self.board[4][3] = WHITE   # Top-left of center
        self.board[4][4] = BLACK   # Top-right of center

    def __str__(self):
       
        lines = []
        lines.append("  " + " ".join(str(c) for c in range(BOARD_SIZE)))
        for i in range(BOARD_SIZE - 1, -1, -1):  # Print from row 7 down to 0
            row_str = str(i) + " " + " ".join(CHAR_MAP[self.board[i][j]] for j in range(BOARD_SIZE))
            lines.append(row_str)
        return "\n".join(lines)

    def is_valid_position(self, row, col):
        #Check if position is within board bounds.
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def get_opponent(self, color):
        #Return opponent's color.
        return WHITE if color == BLACK else BLACK

    def is_valid_move(self, row, col, color):
        #Check if placing a disc at (row, col) is valid.
        #Must flip at least one opponent disc.
    
        if not self.is_valid_position(row, col):
            return False
        
        if self.board[row][col] != EMPTY:
            return False
        
        opponent = self.get_opponent(color)
        
        # Check all 8 directions
        for dr, dc in DIRECTIONS:
            r, c = row + dr, col + dc
            found_opponent = False
            
            # Move in this direction
            while self.is_valid_position(r, c) and self.board[r][c] == opponent:
                found_opponent = True
                r += dr
                c += dc
            
            # Valid if we found opponent(s) and ended with our color
            if found_opponent and self.is_valid_position(r, c) and self.board[r][c] == color:
                return True
        
        return False

    def legal_moves(self, color):
       #Return list of legal moves for given color.
        moves = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.is_valid_move(i, j, color):
                    moves.append((i, j))
        return moves

    def get_legal_moves(self, board, color):
        #Return legal moves for given board state and color.
        moves = []
        opponent = self.get_opponent(color)
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if board[i][j] != EMPTY:
                    continue
                
                # Check all 8 directions
                for dr, dc in DIRECTIONS:
                    r, c = i + dr, j + dc
                    found_opponent = False
                    
                    while self.is_valid_position(r, c) and board[r][c] == opponent:
                        found_opponent = True
                        r += dr
                        c += dc
                    
                    if found_opponent and self.is_valid_position(r, c) and board[r][c] == color:
                        moves.append((i, j))
                        break  # Found valid direction, no need to check others
        
        return moves

    def flip_discs(self, row, col, color):
       #Flip opponent discs for a move at (row, col). Returns list of flipped positions.
        if not self.is_valid_move(row, col, color):
            return []
        
        opponent = self.get_opponent(color)
        flipped = []
        
        # Check all 8 directions
        for dr, dc in DIRECTIONS:
            temp_flipped = []
            r, c = row + dr, col + dc
            
            # Collect opponent discs in this direction
            while self.is_valid_position(r, c) and self.board[r][c] == opponent:
                temp_flipped.append((r, c))
                r += dr
                c += dc
            
            # If we ended with our color, flip all collected discs
            if temp_flipped and self.is_valid_position(r, c) and self.board[r][c] == color:
                flipped.extend(temp_flipped)
        
        return flipped

    def make_move(self, move, color):
        #Make a move for the given color. Returns True if successful.
        if move is None:
            # Pass - no legal moves available
            self.history.append({
                'move': None,
                'color': color,
                'flipped': []
            })
            return True
        
        row, col = move
        
        if not self.is_valid_move(row, col, color):
            return False
        
        # Get discs to flip
        flipped = self.flip_discs(row, col, color)
        
        # Save state for undo
        self.history.append({
            'move': move,
            'color': color,
            'flipped': flipped
        })
        
        # Place disc
        self.board[row][col] = color
        
        # Flip opponent discs
        for r, c in flipped:
            self.board[r][c] = color
        
        return True

    def apply_move(self, board, move, color):
        #Apply move to a board copy (for AI simulation).
        #Returns new board state.
        new_board = copy.deepcopy(board)
        
        if move is None:
            return new_board
        
        row, col = move
        opponent = self.get_opponent(color)
        
        # Place the disc
        new_board[row][col] = color
        
        # Flip discs in all valid directions
        for dr, dc in DIRECTIONS:
            temp_flipped = []
            r, c = row + dr, col + dc
            
            # Collect opponent discs
            while self.is_valid_position(r, c) and new_board[r][c] == opponent:
                temp_flipped.append((r, c))
                r += dr
                c += dc
            
            # Flip if we ended with our color
            if temp_flipped and self.is_valid_position(r, c) and new_board[r][c] == color:
                for fr, fc in temp_flipped:
                    new_board[fr][fc] = color
        
        return new_board

    def undo_last_move(self):
        #Undo the last move. Returns True if successful.
        if not self.history:
            return False
        
        last = self.history.pop()
        move = last['move']
        color = last['color']
        flipped = last['flipped']
        
        if move is None:
            # Was a pass, nothing to undo on board
            return True
        
        row, col = move
        opponent = self.get_opponent(color)
        
        # Remove the placed disc
        self.board[row][col] = EMPTY
        
        # Flip back opponent discs
        for r, c in flipped:
            self.board[r][c] = opponent
        
        return True

    def count_discs(self):
        #Count discs for each color. Returns (black_count, white_count).
        black = sum(row.count(BLACK) for row in self.board)
        white = sum(row.count(WHITE) for row in self.board)
        return black, white

    def is_game_over(self):
        #Check if game is over (no legal moves for either player).
        return not self.legal_moves(BLACK) and not self.legal_moves(WHITE)

    def get_winner(self):
        #Get game winner. Returns BLACK, WHITE, or EMPTY (tie).
        #Should only be called when game is over.
        
        black, white = self.count_discs()
        if black > white:
            return BLACK
        elif white > black:
            return WHITE
        else:
            return EMPTY