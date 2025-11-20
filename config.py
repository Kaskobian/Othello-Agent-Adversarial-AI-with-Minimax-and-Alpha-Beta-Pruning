# Board configuration
BOARD_SIZE = 8
CELL_SIZE = 60
CANVAS_PADDING = 20

# Player colors (using integers for internal representation)
EMPTY = 0
BLACK = 1   # Black moves first
WHITE = -1  # White is opponent

# Character representation for display
CHAR_MAP = {
    EMPTY: '.',
    BLACK: 'B',
    WHITE: 'W'
}

# AI Configuration
DEFAULT_TIME_LIMIT = 30  # seconds (assignment requirement)
DEFAULT_DMAX = 8  # original requirement
TIME_LIMIT = 30

# Choose ONE of these:
DMAX = 9   # recommended performance mode
# DMAX = 10  # experimental deeper mode (may not finish early-game)

# Evaluation weights (from your specification)
WEIGHTS = {
    "material": 10,
    "mobility": 7,
    "corner": 40,
    "edge": 3,
    "stability": 4
}

# UI Colors
COLOR_BOARD = 'darkgreen'
COLOR_BLACK_PIECE = 'black'
COLOR_WHITE_PIECE = 'white'
COLOR_LEGAL_MOVE = 'yellow'
COLOR_GRID = 'black'

# Directions for move validation (8 directions)
DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1)
]
