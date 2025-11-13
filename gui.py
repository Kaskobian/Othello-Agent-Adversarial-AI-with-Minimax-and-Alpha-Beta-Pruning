import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Optional, Tuple
from game import OthelloGame
import config

# Dynamic AI import (attempts to be compatible with multiple ai.py versions)
_ai_mod = None
try:
    import importlib
    _ai_mod = importlib.import_module('ai')
except Exception as e:
    print(f"Warning: Could not import ai module: {e}")
    _ai_mod = None

Move = Tuple[int, int]


class OthelloGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Othello")

        # Game state
        self.game = OthelloGame()
        self.human_color: Optional[int] = None
        self.ai_color: Optional[int] = None
        self.current_player = config.BLACK
        self.time_limit = config.DEFAULT_TIME_LIMIT
        self.dmax = config.DEFAULT_DMAX
        self.ai_mode = None  # 'vs_ai' or 'both'

        # Threading & AI
        self.ai_thread: Optional[threading.Thread] = None
        self.ai_stop_event = threading.Event()
        self.ai_start_time = None

        # Game over flag
        self.game_over = False

        # GUI layout constants
        canvas_size = config.CELL_SIZE * config.BOARD_SIZE
        pad = config.CANVAS_PADDING

        # Canvas for board
        self.canvas = tk.Canvas(
            root, 
            width=canvas_size + 2*pad, 
            height=canvas_size + 2*pad, 
            bg='darkgreen'
        )
        self.canvas.grid(row=0, column=0, columnspan=4, padx=8, pady=8)
        self.canvas.bind('<Button-1>', self.on_canvas_click)

        # Info label
        self.info_label = tk.Label(
            root, 
            text='Select game mode and press "Start New Game"', 
            font=('Arial', 11, 'bold')
        )
        self.info_label.grid(row=1, column=0, columnspan=4, pady=5)

        # Game mode selection
        mode_frame = ttk.LabelFrame(root, text="Game Mode", padding=5)
        mode_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
        
        self.game_mode_var = tk.StringVar(value='AI vs AI')
        ttk.Radiobutton(
            mode_frame, 
            text='AI vs AI', 
            variable=self.game_mode_var, 
            value='AI vs AI',
            command=self.on_mode_change
        ).pack(side='left', padx=10)
        ttk.Radiobutton(
            mode_frame, 
            text='Human vs AI', 
            variable=self.game_mode_var, 
            value='Human vs AI',
            command=self.on_mode_change
        ).pack(side='left', padx=10)

        # Human player options
        self.human_options_frame = ttk.LabelFrame(root, text="Human Player", padding=5)
        self.human_player_var = tk.IntVar(value=config.BLACK)
        ttk.Radiobutton(
            self.human_options_frame, 
            text='Play as Black', 
            variable=self.human_player_var, 
            value=config.BLACK
        ).pack(side='left', padx=10)
        ttk.Radiobutton(
            self.human_options_frame, 
            text='Play as White', 
            variable=self.human_player_var, 
            value=config.WHITE
        ).pack(side='left', padx=10)
        
        # First player selection
        self.first_player_frame = ttk.LabelFrame(root, text="First Player", padding=5)
        self.first_player_var = tk.IntVar(value=config.BLACK)
        ttk.Radiobutton(
            self.first_player_frame, 
            text='Black starts (Standard)', 
            variable=self.first_player_var, 
            value=config.BLACK
        ).pack(side='left', padx=10)
        ttk.Radiobutton(
            self.first_player_frame, 
            text='White starts', 
            variable=self.first_player_var, 
            value=config.WHITE
        ).pack(side='left', padx=10)
        self.first_player_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky='ew')

        # Control buttons
        ttk.Button(
            root, text='Start New Game', command=self.start_new_game
        ).grid(row=4, column=0, sticky='ew', padx=4, pady=5)
        
        self.pause_button = ttk.Button(
            root, text='Pause/Resume', command=self.toggle_pause
        )
        self.pause_button.grid(row=4, column=1, sticky='ew', padx=4, pady=5)
        
        ttk.Button(
            root, text='Quit', command=self.on_quit
        ).grid(row=4, column=2, sticky='ew', padx=4, pady=5)

        # Settings frame
        settings_frame = ttk.LabelFrame(root, text="Game Settings", padding=5)
        settings_frame.grid(row=5, column=0, columnspan=4, padx=10, pady=5, sticky='ew')

        # Speed control
        ttk.Label(settings_frame, text='Speed (ms):').grid(row=0, column=0, sticky='e', padx=5)
        self.speed_var = tk.StringVar(value='1000')
        speed_combo = ttk.Combobox(
            settings_frame, 
            textvariable=self.speed_var, 
            width=10,
            state='readonly',
            values=['0 (Instant)', '200 (Fast)', '500 (Medium)', '1000 (Normal)', '2000 (Slow)']
        )
        speed_combo.current(3)
        speed_combo.grid(row=0, column=1, sticky='w', padx=5)

        # Time limit
        ttk.Label(settings_frame, text='Time limit (s):').grid(row=0, column=2, sticky='e', padx=5)
        self.time_entry = ttk.Entry(settings_frame, width=10)
        self.time_entry.insert(0, str(self.time_limit))
        self.time_entry.grid(row=0, column=3, sticky='w', padx=5)

        # Max depth
        ttk.Label(settings_frame, text='Max Depth:').grid(row=1, column=0, sticky='e', padx=5)
        self.dmax_entry = ttk.Entry(settings_frame, width=10)
        self.dmax_entry.insert(0, str(self.dmax))
        self.dmax_entry.grid(row=1, column=1, sticky='w', padx=5)

        # Score display
        self.score_label = tk.Label(
            settings_frame, 
            text='Black: 2  |  White: 2', 
            font=('Arial', 11, 'bold')
        )
        self.score_label.grid(row=1, column=2, columnspan=2, padx=5)

        # Move log
        log_frame = ttk.LabelFrame(root, text="Game Log", padding=5)
        log_frame.grid(row=6, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')
        
        self.move_log = tk.Text(
            log_frame, width=60, height=8, state='disabled', wrap='word'
        )
        self.move_log.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.move_log.yview)
        scrollbar.pack(side='right', fill='y')
        self.move_log.config(yscrollcommand=scrollbar.set)

        # Pause flag
        self.paused = False

        # Initial setup
        self.draw_board()
        self.on_mode_change()
        self._ai_interface = self.detect_ai_interface()
        self.append_log(f"AI interface detected: {self._ai_interface}")
        self.append_log("Configure settings and click 'Start New Game' to begin!")

    def _color_to_str(self, color: int) -> str:
        if color == config.BLACK:
            return "Black"
        elif color == config.WHITE:
            return "White"
        return "Unknown"

    def on_mode_change(self):
        if self.game_mode_var.get() == 'Human vs AI':
            self.human_options_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
            self.first_player_frame.grid_remove()
        else:
            self.human_options_frame.grid_remove()
            self.first_player_frame.grid()

    def detect_ai_interface(self) -> str:
        if _ai_mod is None: return "none"
        if hasattr(_ai_mod, 'OthelloAI'): return 'OthelloAI'
        if hasattr(_ai_mod, 'SearchAgent'): return 'SearchAgent'
        return 'unknown'

    def start_new_game(self):
        self.game = OthelloGame()
        self.game_over = False
        self.paused = False

        # Game mode
        if self.game_mode_var.get() == 'Human vs AI':
            self.ai_mode = 'vs_ai'
            self.human_color = self.human_player_var.get()
            self.ai_color = self.game.get_opponent(self.human_color)
            self.current_player = config.BLACK
        else:
            self.ai_mode = 'both'
            self.human_color = None
            self.ai_color = None
            self.current_player = self.first_player_var.get()

        # Read settings
        try:
            self.time_limit = float(self.time_entry.get())
            self.dmax = int(self.dmax_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Settings", "Time limit and max depth must be numbers.")
            return

        # Clear log and update UI
        self.move_log.config(state='normal')
        self.move_log.delete('1.0', 'end')
        self.move_log.config(state='disabled')
        
        self.append_log("=" * 60)
        self.append_log(f"NEW GAME: {self.game_mode_var.get()}")
        if self.ai_mode == 'vs_ai':
            human_str = self._color_to_str(self.human_color)
            ai_str = self._color_to_str(self.ai_color)
            self.append_log(f"Human: {human_str}, AI: {ai_str}")
        self.append_log(f"Time: {self.time_limit}s, Depth: {self.dmax}")
        self.append_log("=" * 60)

        self.draw_board()
        self.update_score()
        self.next_turn()

    def next_turn(self):
        if self.game_over: return
        self.update_info_label()
        self.draw_board() # Redraw to update legal moves highlight

        if self.current_player == self.human_color:
            self.pause_button.config(state='disabled')
            # Human's turn, wait for click
        else:
            self.pause_button.config(state='normal')
            # AI's turn
            delay = self.get_speed_delay() if self.ai_mode == 'both' else 200
            self.root.after(delay, self.start_ai_move)

    def on_canvas_click(self, event):
        if self.game_over or self.current_player != self.human_color:
            return

        pad = config.CANVAS_PADDING
        size = config.CELL_SIZE
        c = (event.x - pad) // size
        r = config.BOARD_SIZE - 1 - ((event.y - pad) // size)

        if 0 <= r < config.BOARD_SIZE and 0 <= c < config.BOARD_SIZE:
            move = (int(r), int(c))
            if move in self.game.legal_moves(self.human_color):
                self.game.make_move(move, self.human_color)
                human_str = self._color_to_str(self.human_color)
                self.append_log(f"Human ({human_str}) -> {move}")
                self.update_score()
                
                if self.check_game_over(): return
                
                self.current_player = self.game.get_opponent(self.current_player)
                self.next_turn()
            else:
                self.append_log(f"Invalid move: {move}")

    def draw_board(self):
        self.canvas.delete('all')
        size = config.CELL_SIZE
        pad = config.CANVAS_PADDING
        
        legal_moves = []
        if self.current_player == self.human_color and not self.game_over:
            legal_moves = self.game.legal_moves(self.human_color)

        for r in range(config.BOARD_SIZE):
            for c in range(config.BOARD_SIZE):
                x0, y0 = pad + c * size, pad + (config.BOARD_SIZE - 1 - r) * size
                x1, y1 = x0 + size, y0 + size
                
                fill_color = 'darkgreen'
                if (r, c) in legal_moves:
                    fill_color = 'forestgreen' # Highlight legal moves

                self.canvas.create_rectangle(x0, y0, x1, y1, outline='black', fill=fill_color)
                
                piece = self.game.board[r][c]
                if piece != config.EMPTY:
                    color = 'black' if piece == config.BLACK else 'white'
                    self.canvas.create_oval(x0+6, y0+6, x1-6, y1-6, fill=color, outline='gray', width=2)
        
        for c in range(config.BOARD_SIZE):
            x = pad + c * size + size / 2
            self.canvas.create_text(x, pad/2, text=str(c), fill='white', font=('Arial', 9, 'bold'))
        for r in range(config.BOARD_SIZE):
            y = pad + (config.BOARD_SIZE - 1 - r) * size + size / 2
            self.canvas.create_text(pad/2, y, text=str(r), fill='white', font=('Arial', 9, 'bold'))

    def toggle_pause(self):
        if self.ai_mode != 'both':
            self.append_log("Pause is only available in AI vs AI mode.")
            return
        self.paused = not self.paused
        if self.paused:
            self.append_log("Game PAUSED")
            self.info_label.config(text="Game PAUSED")
        else:
            self.append_log("Game RESUMED")
            self.next_turn()

    def start_ai_move(self):
        if self.game_over or self.paused or self.current_player == self.human_color:
            return
            
        if _ai_mod is None:
            messagebox.showerror("AI Error", "ai.py not found or failed to import.")
            return

        if self.ai_thread and self.ai_thread.is_alive(): return

        legal = self.game.legal_moves(self.current_player)
        color_name = self._color_to_str(self.current_player)
        
        if not legal:
            self.append_log(f"AI {color_name} has no legal moves - PASS")
            self.game.make_move(None, self.current_player)
            self.current_player = self.game.get_opponent(self.current_player)
            if self.check_game_over(): return
            self.next_turn()
            return

        self.append_log(f"AI {color_name} thinking... ({len(legal)} legal moves)")
        self.ai_stop_event.clear()
        self.ai_start_time = time.time()
        self.ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self.ai_thread.start()

    def get_speed_delay(self) -> int:
        try:
            return int(self.speed_var.get().split()[0])
        except:
            return 1000

    def _ai_worker(self):
        ai_color = self.current_player
        best_move, nodes_info = None, "N/A"
        start_time = time.time()

        try:
            if self._ai_interface == 'OthelloAI':
                agent = getattr(_ai_mod, 'OthelloAI')(self.game, ai_color)
                best_move = agent.get_move()
                nodes_info = getattr(agent, 'nodes_evaluated', 'N/A')
            elif self._ai_interface == 'SearchAgent':
                agent = getattr(_ai_mod, 'SearchAgent')(self.game, ai_color, self.time_limit, self.dmax)
                best_move = agent.iterative_deepening() if hasattr(agent, 'iterative_deepening') else agent.get_move()
                nodes_info = getattr(agent, 'nodes', 'N/A')
            else:
                self.append_log(f"Unknown AI interface: {self._ai_interface}")
        except Exception as ex:
            self.append_log(f"AI error: {ex}")
            import traceback
            traceback.print_exc()

        elapsed = time.time() - start_time
        self.root.after(10, lambda: self._apply_ai_move(best_move, elapsed, nodes_info))

    def _apply_ai_move(self, best_move, elapsed, nodes_info):
        if self.game_over or self.paused: return
            
        color_name = self._color_to_str(self.current_player)
        
        if best_move is None:
            self.append_log(f"AI {color_name} passes")
            self.game.make_move(None, self.current_player)
        else:
            applied = self.game.make_move(best_move, self.current_player)
            if not applied:
                self.append_log(f"AI {color_name} suggested illegal move {best_move} - passing")
                self.game.make_move(None, self.current_player)
            else:
                self.append_log(f"AI {color_name} -> {best_move} (t={elapsed:.2f}s, n={nodes_info})")
        
        self.update_score()
        
        if self.check_game_over(): return
        
        self.current_player = self.game.get_opponent(self.current_player)
        self.ai_stop_event.set()
        self.next_turn()

    def update_score(self):
        black_count = sum(row.count(config.BLACK) for row in self.game.board)
        white_count = sum(row.count(config.WHITE) for row in self.game.board)
        self.score_label.config(text=f"Black: {black_count}  |  White: {white_count}")

    def check_game_over(self) -> bool:
        if not self.game.legal_moves(config.BLACK) and not self.game.legal_moves(config.WHITE):
            self.game_over = True
            black_count = sum(row.count(config.BLACK) for row in self.game.board)
            white_count = sum(row.count(config.WHITE) for row in self.game.board)
            
            winner_color = "Tie"
            if black_count > white_count: winner_color = self._color_to_str(config.BLACK)
            elif white_count > black_count: winner_color = self._color_to_str(config.WHITE)
            
            result_msg = f"GAME OVER!\n\nBlack: {black_count}\nWhite: {white_count}\n\nWinner: {winner_color}"
            self.append_log("=" * 60)
            self.append_log(f"GAME OVER! Winner: {winner_color}")
            self.append_log(f"Final Score - Black: {black_count}, White: {white_count}")
            self.append_log("=" * 60)
            
            self.info_label.config(text=f"GAME OVER! Winner: {winner_color}")
            messagebox.showinfo("Game Over", result_msg)
            return True
        return False

    def update_info_label(self):
        if self.game_over: return
        
        current_player_str = self._color_to_str(self.current_player)
        if self.current_player == self.human_color:
            text = f"Your turn ({current_player_str})"
        elif self.ai_mode == 'vs_ai':
            text = f"AI's turn ({current_player_str})"
        else: # AI vs AI
            text = f"Current turn: AI {current_player_str}"
        self.info_label.config(text=text)

    def on_quit(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.quit()

    def append_log(self, text: str):
        tstamp = time.strftime('%H:%M:%S')
        self.move_log.config(state='normal')
        self.move_log.insert('end', f"[{tstamp}] {text}\n")
        self.move_log.see('end')
        self.move_log.config(state='disabled')

def main():
    root = tk.Tk()
    app = OthelloGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
