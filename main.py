import tkinter as tk
from tkinter import messagebox
import sys
import os


def check_dependencies():
    
    missing = []
    
    # Check for required custom modules
    try:
        import gui
    except ImportError:
        missing.append("gui.py")
    
    try:
        import game
    except ImportError:
        missing.append("game.py")
    
    try:
        import config
    except ImportError:
        missing.append("config.py")
    
    try:
        import utils
    except ImportError:
        missing.append("utils.py")
    
    # Check for AI module (warn but don't fail)
    try:
        import ai
    except ImportError:
        print("Warning: ai.py not found. AI player will not be available.")
    
    if missing:
        error_msg = f"Missing required modules: {', '.join(missing)}"
        print(f"Error: {error_msg}")
        try:
            messagebox.showerror("Missing Dependencies", error_msg)
        except:
            pass
        return False
    
    return True


def main():
   
    try:
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        # Import after dependency check
        from gui import OthelloGUI
        
        # Create root window
        root = tk.Tk()
        root.title("Othello Agent - Phase 1")
        
        # Set window icon if available
        try:
            if os.path.exists("icon.ico"):
                root.iconbitmap("icon.ico")
        except:
            pass  # Icon is optional
        
        # Center window on screen
        root.update_idletasks()
        window_width = root.winfo_reqwidth()
        window_height = root.winfo_reqheight()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        x_coordinate = (screen_width // 2) - (window_width // 2)
        y_coordinate = (screen_height // 2) - (window_height // 2)
        root.geometry(f"+{x_coordinate}+{y_coordinate}")
        
        # Initialize GUI app
        app = OthelloGUI(root)
        
        # Set minimum window size (prevent too small window)
        root.minsize(600, 500)
        
        # Handle window close event
        def on_closing():
            if messagebox.askokcancel("Quit", "Do you want to quit the game?"):
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Run the Tkinter main loop
        root.mainloop()
        
    except ImportError as e:
        error_msg = f"Import Error: {e}\n\nPlease ensure all required files are in the same directory."
        print(error_msg)
        try:
            messagebox.showerror("Import Error", error_msg)
        except:
            pass
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(error_msg)
        try:
            messagebox.showerror("Error", error_msg)
        except:
            pass
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()