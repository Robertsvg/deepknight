"""
gui.py

Simple Tkinter GUI for playing Tablut.

Run with:
python -m src.gui
"""

import random
import tkinter as tk
from tkinter import messagebox

from src.ai import AdvancedAI
from src.board import ATTACKER, BLACK, DEFENDER, EMPTY, KING, THRONE, WHITE
from src.fen import parse_fen, starting_position, to_fen
from src.moves import apply_move, generate_legal_moves
from src.rules import is_game_over

CELL_SIZE = 70
BOARD_SIZE = 9

LIGHT = "#f0d9b5"
DARK = "#d9b382"
THRONE_COLOR = "#b77b57"
SELECTED_COLOR = "#7ec8e3"
LEGAL_COLOR = "#a7e8a1"

ATTACKER_COLOR = "#222222"
DEFENDER_COLOR = "#f4f4f4"
KING_COLOR = "#ffd700"


def side_name(side):
    if side == WHITE:
        return "White"

    return "Black"


class TablutGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepKnight Tablut")

        self.board = starting_position()

        self.selected = None
        self.legal_moves = []

        # None means human vs human.
        # WHITE means the human plays white.
        # BLACK means the human plays black.
        self.human_side = None

        self.ai = AdvancedAI(time_limit_s=0.3, max_depth=3)
        self.ai_thinking = False

        self.canvas = tk.Canvas(
            root,
            width=CELL_SIZE * BOARD_SIZE,
            height=CELL_SIZE * BOARD_SIZE,
        )
        self.canvas.pack()

        self.info_label = tk.Label(root, text="", font=("Arial", 14))
        self.info_label.pack(pady=5)

        self.create_buttons()

        self.canvas.bind("<Button-1>", self.on_click)

        self.draw()

    def create_buttons(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        buttons = [
            ("Human vs Human", self.new_pvp_game),
            ("Play as White", self.play_as_white),
            ("Play as Black", self.play_as_black),
            ("AI Move", self.force_ai_move),
            ("Random Move", self.random_move),
            ("Test FEN", self.load_test_fen),
            ("Show FEN", self.show_fen),
        ]

        for text, command in buttons:
            button = tk.Button(button_frame, text=text, command=command)
            button.pack(side=tk.LEFT, padx=5)

    def clear_selection(self):
        self.selected = None
        self.legal_moves = []

    def reset_game(self, human_side=None):
        self.board = starting_position()
        self.human_side = human_side
        self.clear_selection()
        self.draw()

    def new_pvp_game(self):
        self.reset_game(None)

    def play_as_white(self):
        self.reset_game(WHITE)

        # Black starts, so the AI has to move first.
        self.root.after(300, self.ai_move_if_needed)

    def play_as_black(self):
        self.reset_game(BLACK)

    def load_test_fen(self):
        self.board = parse_fen("9/9/9/9/9/9/3r5/1K7/9 w 0 1")
        self.clear_selection()
        self.draw()

    def show_fen(self):
        fen = to_fen(self.board)
        messagebox.showinfo("Current FEN", fen)

    def random_move(self):
        if self.show_game_over_if_needed():
            return

        moves = list(generate_legal_moves(self.board, self.board.side_to_move))

        if not moves:
            messagebox.showinfo("Game Over", "No legal moves. Draw.")
            return

        move = random.choice(moves)
        self.board = apply_move(self.board, move)

        self.clear_selection()
        self.draw()

    def force_ai_move(self):
        self.play_ai_move()

    def ai_move_if_needed(self):
        if self.human_side is None:
            return

        if is_game_over(self.board) is not None:
            self.draw()
            return

        if self.board.side_to_move != self.human_side:
            self.play_ai_move()

    def play_ai_move(self):
        if self.ai_thinking:
            return

        if self.show_game_over_if_needed():
            return

        moves = list(generate_legal_moves(self.board, self.board.side_to_move))

        if not moves:
            messagebox.showinfo("Game Over", "No legal moves. Draw.")
            return

        self.ai_thinking = True
        self.info_label.config(
            text=f"AI thinking for {side_name(self.board.side_to_move)}..."
        )
        self.root.update_idletasks()

        move = self.ai.choose_move(self.board)

        if move is None:
            messagebox.showinfo("Game Over", "AI found no move.")
            self.ai_thinking = False
            return

        self.board = apply_move(self.board, move)

        self.ai_thinking = False
        self.clear_selection()
        self.draw()

        self.show_game_over_if_needed()

    def show_game_over_if_needed(self):
        result = is_game_over(self.board)

        if result is not None:
            messagebox.showinfo("Game Over", result)
            return True

        return False

    def on_click(self, event):
        if self.ai_thinking:
            return

        if self.show_game_over_if_needed():
            return

        # In human vs AI mode, the user can only move on their turn.
        if self.human_side is not None:
            if self.board.side_to_move != self.human_side:
                return

        row = event.y // CELL_SIZE
        col = event.x // CELL_SIZE

        if not self.is_inside_board(row, col):
            return

        if self.selected is None:
            self.select_piece(row, col)
        else:
            self.try_move(row, col)

    def select_piece(self, row, col):
        piece = self.board.get(row, col)

        if piece == EMPTY:
            return

        if not self.belongs_to_side(piece, self.board.side_to_move):
            return

        self.selected = (row, col)
        self.legal_moves = []

        for move in generate_legal_moves(self.board, self.board.side_to_move):
            if move[0] == row and move[1] == col:
                self.legal_moves.append(move)

        self.draw()

    def try_move(self, row, col):
        from_row, from_col = self.selected
        move = (from_row, from_col, row, col)

        if move not in self.legal_moves:
            self.clear_selection()
            self.draw()
            return

        self.board = apply_move(self.board, move)

        self.clear_selection()
        self.draw()

        if self.show_game_over_if_needed():
            return

        # After the human move, the AI can answer.
        self.root.after(300, self.ai_move_if_needed)

    def belongs_to_side(self, piece, side):
        if side == WHITE:
            return piece == DEFENDER or piece == KING

        if side == BLACK:
            return piece == ATTACKER

        return False

    def is_inside_board(self, row, col):
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def draw(self):
        self.canvas.delete("all")

        legal_targets = set()

        for move in self.legal_moves:
            legal_targets.add((move[2], move[3]))

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                self.draw_square(row, col, legal_targets)

                piece = self.board.get(row, col)

                if piece != EMPTY:
                    self.draw_piece(row, col, piece)

        self.draw_coordinates()
        self.update_info_text()

    def draw_square(self, row, col, legal_targets):
        x1 = col * CELL_SIZE
        y1 = row * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE

        color = LIGHT

        if (row + col) % 2 == 1:
            color = DARK

        if (row, col) == THRONE:
            color = THRONE_COLOR

        if self.selected == (row, col):
            color = SELECTED_COLOR

        if (row, col) in legal_targets:
            color = LEGAL_COLOR

        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=color,
            outline="black",
        )

    def draw_piece(self, row, col, piece):
        x = col * CELL_SIZE + CELL_SIZE // 2
        y = row * CELL_SIZE + CELL_SIZE // 2
        radius = 24

        if piece == ATTACKER:
            fill = ATTACKER_COLOR
            text = "r"
            text_color = "white"

        elif piece == DEFENDER:
            fill = DEFENDER_COLOR
            text = "R"
            text_color = "black"

        else:
            fill = KING_COLOR
            text = "K"
            text_color = "black"

        self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            outline="black",
            width=2,
        )

        self.canvas.create_text(
            x,
            y,
            text=text,
            font=("Arial", 20, "bold"),
            fill=text_color,
        )

    def draw_coordinates(self):
        for col in range(BOARD_SIZE):
            text = chr(ord("a") + col)
            x = col * CELL_SIZE + 8
            y = BOARD_SIZE * CELL_SIZE - 15

            self.canvas.create_text(
                x,
                y,
                text=text,
                font=("Arial", 10, "bold"),
            )

        for row in range(BOARD_SIZE):
            text = str(9 - row)
            x = 10
            y = row * CELL_SIZE + 12

            self.canvas.create_text(
                x,
                y,
                text=text,
                font=("Arial", 10, "bold"),
            )

    def update_info_text(self):
        result = is_game_over(self.board)

        if result is not None:
            self.info_label.config(text=f"Game Over: {result}")
            return

        mode_text = "Human vs Human"

        if self.human_side == WHITE:
            mode_text = "Human: White | AI: Black"

        elif self.human_side == BLACK:
            mode_text = "Human: Black | AI: White"

        turn_text = side_name(self.board.side_to_move)

        self.info_label.config(text=f"{mode_text} | Turn: {turn_text}")


def main():
    root = tk.Tk()
    TablutGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
