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
        self.root.title("Othello Agent - AI vs AI")

        # Game state
        self.game = OthelloGame()
        self.human_color: Optional[str] = None
        self.ai_color: Optional[str] = None
        self.current_player = config.BLACK
        self.time_limit = config.DEFAULT_TIME_LIMIT
        self.dmax = config.DEFAULT_DMAX
        self.ai_mode = 'both'  # Always AI vs AI

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

        # Info label
        self.info_label = tk.Label(
            root, 
            text='AI vs AI Mode - Configure settings and press "Start New Game"', 
            font=('Arial', 11, 'bold')
        )
        self.info_label.grid(row=1, column=0, columnspan=4, pady=5)

        # First player selection
        first_player_frame = ttk.LabelFrame(root, text="First Player", padding=5)
        first_player_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
        
        self.first_player_var = tk.StringVar(value='BLACK')
        ttk.Radiobutton(
            first_player_frame, 
            text='Black starts (Standard)', 
            variable=self.first_player_var, 
            value='BLACK'
        ).pack(side='left', padx=10)
        ttk.Radiobutton(
            first_player_frame, 
            text='White starts', 
            variable=self.first_player_var, 
            value='WHITE'
        ).pack(side='left', padx=10)

        # Control buttons
        ttk.Button(
            root, text='Start New Game', command=self.start_new_game
        ).grid(row=3, column=0, sticky='ew', padx=4, pady=5)
        
        ttk.Button(
            root, text='Pause/Resume', command=self.toggle_pause
        ).grid(row=3, column=1, sticky='ew', padx=4, pady=5)
        
        ttk.Button(
            root, text='Quit', command=self.on_quit
        ).grid(row=3, column=2, sticky='ew', padx=4, pady=5)

        # Settings frame
        settings_frame = ttk.LabelFrame(root, text="Game Settings", padding=5)
        settings_frame.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky='ew')

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
        speed_combo.current(3)  # Default to 1000
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
        log_frame.grid(row=5, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')
        
        self.move_log = tk.Text(
            log_frame, width=60, height=12, state='disabled', wrap='word'
        )
        self.move_log.pack(fill='both', expand=True)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(log_frame, command=self.move_log.yview)
        scrollbar.pack(side='right', fill='y')
        self.move_log.config(yscrollcommand=scrollbar.set)

        # Pause flag
        self.paused = False

        # Draw initial board
        self.draw_board()

        # AI adapter detection
        self._ai_interface = self.detect_ai_interface()
        self.append_log(f"AI interface detected: {self._ai_interface}")
        self.append_log("Configure settings and click 'Start New Game' to begin!")

    def detect_ai_interface(self) -> str:
        """Detect which AI class/interface exists in ai.py."""
        if _ai_mod is None:
            return "none"
        if hasattr(_ai_mod, 'OthelloAI'):
            return 'OthelloAI'
        if hasattr(_ai_mod, 'SearchAgent'):
            return 'SearchAgent'
        return 'unknown'

    def start_new_game(self):
        """Initialize a new AI vs AI game."""
        # Always AI vs AI mode
        self.human_color = None
        self.ai_color = None
        self.ai_mode = 'both'
        
        # Reset game
        self.game = OthelloGame()
        
        # Set starting player based on selection
        if self.first_player_var.get() == 'BLACK':
            self.current_player = config.BLACK
            starting_player = "Black"
        else:
            self.current_player = config.WHITE
            starting_player = "White"
        
        self.game_over = False
        self.paused = False

        # Read settings
        try:
            self.time_limit = float(self.time_entry.get())
            if self.time_limit <= 0:
                raise ValueError("Time must be positive")
        except Exception:
            self.time_limit = config.DEFAULT_TIME_LIMIT
            self.time_entry.delete(0, 'end')
            self.time_entry.insert(0, str(self.time_limit))

        try:
            self.dmax = int(self.dmax_entry.get())
            if self.dmax <= 0:
                raise ValueError("Dmax must be positive")
        except Exception:
            self.dmax = config.DEFAULT_DMAX
            self.dmax_entry.delete(0, 'end')
            self.dmax_entry.insert(0, str(self.dmax))

        # Clear log
        self.move_log.config(state='normal')
        self.move_log.delete('1.0', 'end')
        self.move_log.config(state='disabled')

        self.append_log("=" * 60)
        self.append_log("NEW GAME STARTED: AI vs AI")
        self.append_log(f"First player: {starting_player}")
        self.append_log(f"Time limit: {self.time_limit}s | Max depth: {self.dmax}")
        speed_text = self.speed_var.get().split()[0]
        self.append_log(f"Move delay: {speed_text}ms")
        self.append_log("=" * 60)
        
        self.draw_board()
        self.update_info_label()
        self.update_score()

        # Start first AI move
        self.root.after(500, self.start_ai_move)

    def draw_board(self):
        """Draw current board state on canvas."""
        self.canvas.delete('all')
        size = config.CELL_SIZE
        pad = config.CANVAS_PADDING
        
        # Draw grid and pieces
        for r in range(config.BOARD_SIZE):
            for c in range(config.BOARD_SIZE):
                x0 = pad + c * size
                y0 = pad + (config.BOARD_SIZE - 1 - r) * size
                x1 = x0 + size
                y1 = y0 + size
                
                # Draw cell
                self.canvas.create_rectangle(
                    x0, y0, x1, y1, 
                    outline='black', 
                    fill='darkgreen'
                )
                
                # Draw piece
                piece = self.game.board[r][c]
                if piece != config.EMPTY:
                    color = 'black' if piece == config.BLACK else 'white'
                    self.canvas.create_oval(
                        x0+6, y0+6, x1-6, y1-6, 
                        fill=color, 
                        outline='gray',
                        width=2
                    )
        
        # Draw coordinate labels
        for c in range(config.BOARD_SIZE):
            x = pad + c * size + size / 2
            y_pos = pad / 2 if pad >= 10 else 10
            self.canvas.create_text(
                x, y_pos, text=str(c), 
                fill='white', font=('Arial', 9, 'bold')
            )
        
        for r in range(config.BOARD_SIZE):
            y = pad + (config.BOARD_SIZE - 1 - r) * size + size / 2
            x_pos = pad / 2 if pad >= 10 else 10
            self.canvas.create_text(
                x_pos, y, text=str(r), 
                fill='white', font=('Arial', 9, 'bold')
            )

    def toggle_pause(self):
        """Pause or resume the AI vs AI game."""
        self.paused = not self.paused
        if self.paused:
            self.append_log("Game PAUSED")
            self.info_label.config(text="Game PAUSED - Click Resume to continue")
        else:
            self.append_log("Game RESUMED")
            self.update_info_label()
            # Resume AI if it's their turn
            if not self.game_over and not (self.ai_thread and self.ai_thread.is_alive()):
                self.root.after(200, self.start_ai_move)

    def start_ai_move(self):
        """Start AI thinking in a background thread."""
        if self.game_over or self.paused:
            return
            
        if _ai_mod is None:
            messagebox.showerror("AI Error", "ai.py not found or failed to import.")
            return

        if self.ai_thread and self.ai_thread.is_alive():
            return

        ai_color_to_move = self.current_player

        # Check if AI has legal moves
        legal = self.game.legal_moves(ai_color_to_move)
        
        if not legal:
            color_name = "Black" if ai_color_to_move == config.BLACK else "White"
            self.append_log(f"AI {color_name} has no legal moves - PASS")
            self.game.make_move(None, ai_color_to_move)
            self.current_player = self.game.get_opponent(self.current_player)
            self.update_info_label()
            
            if self.check_game_over():
                return
            
            # Continue to next player
            delay = self.get_speed_delay()
            self.root.after(delay, self.start_ai_move)
            return

        color_name = "Black" if ai_color_to_move == config.BLACK else "White"
        self.append_log(f"AI {color_name} thinking... ({len(legal)} legal moves)")

        # Start AI worker thread
        self.ai_stop_event.clear()
        self.ai_start_time = time.time()
        self.ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
        self.ai_thread.start()

    def get_speed_delay(self) -> int:
        """Extract delay value from speed selection."""
        speed_text = self.speed_var.get()
        # Extract number from text like "1000 (Normal)"
        delay_str = speed_text.split()[0]
        try:
            return int(delay_str)
        except:
            return 1000  # Default

    def _ai_worker(self):
        """Background worker: compute AI move."""
        ai_color = self.current_player
        ai_interface = self._ai_interface
        best_move = None
        start_time = time.time()
        nodes_info = "N/A"

        try:
            if ai_interface == 'OthelloAI':
                AgentClass = getattr(_ai_mod, 'OthelloAI')
                agent = AgentClass(self.game, ai_color)
                
                if hasattr(agent, 'get_move'):
                    best_move = agent.get_move()
                    nodes_info = getattr(agent, 'nodes_evaluated', 'N/A')
                else:
                    self.append_log("Error: OthelloAI has no get_move method")
                    
            elif ai_interface == 'SearchAgent':
                AgentClass = getattr(_ai_mod, 'SearchAgent')
                agent = AgentClass(
                    self.game, 
                    ai_color, 
                    time_limit=self.time_limit, 
                    max_depth=self.dmax
                )
                
                if hasattr(agent, 'iterative_deepening'):
                    best_move = agent.iterative_deepening()
                elif hasattr(agent, 'get_move'):
                    best_move = agent.get_move()
                    
                nodes_info = getattr(agent, 'nodes', 'N/A')
                
            else:
                self.append_log(f"Unknown AI interface: {ai_interface}")
                best_move = None

        except TimeoutError:
            self.append_log(f"AI timed out after {self.time_limit}s")
        except Exception as ex:
            self.append_log(f"AI error: {ex}")
            print(f"AI exception: {ex}")
            import traceback
            traceback.print_exc()

        end_time = time.time()
        elapsed = end_time - start_time

        # Schedule move application
        self.root.after(10, lambda: self._apply_ai_move(best_move, elapsed, nodes_info))

    def _apply_ai_move(self, best_move, elapsed, nodes_info):
        """Apply AI's move on the main thread."""
        if self.game_over or self.paused:
            return
            
        color_name = "Black" if self.current_player == config.BLACK else "White"
        
        if best_move is None:
            self.append_log(f"AI {color_name} passes")
            self.game.make_move(None, self.current_player)
        else:
            print(f"\nBoard before AI {color_name} move {best_move}:")
            print(self.game)
            
            applied = self.game.make_move(best_move, self.current_player)
            if not applied:
                self.append_log(f"AI {color_name} suggested illegal move - passing")
                self.game.make_move(None, self.current_player)
            else:
                self.append_log(
                    f"AI {color_name} -> {best_move} "
                    f"(time={elapsed:.2f}s, nodes={nodes_info})"
                )
        
        self.draw_board()
        self.update_score()
        
        # Check for game over
        if self.check_game_over():
            return
        
        # Switch player
        self.current_player = self.game.get_opponent(self.current_player)
        self.update_info_label()
        self.ai_stop_event.set()
        
        # Schedule next AI move
        if not self.paused:
            delay = self.get_speed_delay()
            self.root.after(delay, self.start_ai_move)

    def update_score(self):
        """Update the score display."""
        black_count = sum(row.count(config.BLACK) for row in self.game.board)
        white_count = sum(row.count(config.WHITE) for row in self.game.board)
        self.score_label.config(text=f"Black: {black_count}  |  White: {white_count}")

    def check_game_over(self) -> bool:
        """Check if game is over and display results."""
        black_moves = self.game.legal_moves(config.BLACK)
        white_moves = self.game.legal_moves(config.WHITE)
        
        if not black_moves and not white_moves:
            self.game_over = True
            black_count = sum(row.count(config.BLACK) for row in self.game.board)
            white_count = sum(row.count(config.WHITE) for row in self.game.board)
            
            if black_count > white_count:
                winner = "Black"
            elif white_count > black_count:
                winner = "White"
            else:
                winner = "Tie"
            
            result_msg = (
                f"GAME OVER!\n\n"
                f"Black: {black_count}\n"
                f"White: {white_count}\n\n"
                f"Winner: {winner}"
            )
            
            self.append_log("=" * 60)
            self.append_log(f"GAME OVER! Winner: {winner}")
            self.append_log(f"Final Score - Black: {black_count}, White: {white_count}")
            self.append_log("=" * 60)
            
            self.info_label.config(text=f"GAME OVER! Winner: {winner}")
            messagebox.showinfo("Game Over", result_msg)
            return True
        
        return False

    def update_info_label(self):
        """Update the info label with current player."""
        if self.game_over:
            return
        
        if self.current_player == config.BLACK:
            self.info_label.config(text="Current turn: AI Black")
        else:
            self.info_label.config(text="Current turn: AI White")

    def on_quit(self):
        """Quit the application."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.root.quit()

    def append_log(self, text: str):
        """Append text to the move log."""
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
