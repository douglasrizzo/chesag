import sys

import chess
import chess.svg
from chess import Board
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout

from chesag.chess import ExtendedBoard


class ChessWindow(QDialog):
  """A window that displays a chess board and can be updated with new positions."""

  def __init__(self, title: str = "Chess Game"):
    super().__init__()
    self.init_ui(title)
    self.update_board()

  def init_ui(self, title: str):
    """Initialize the user interface."""
    self.setWindowTitle(title)
    self.setGeometry(100, 100, 600, 650)

    # Create layout
    layout = QVBoxLayout()

    label_font = QFont("Arial", 12)

    self.players_label = QLabel("")
    self.players_label.setFont(label_font)

    self.game_label = QLabel("Game Status: Ready")
    self.game_label.setFont(label_font)

    self.svg_widget = QSvgWidget()
    self.svg_widget.setMinimumSize(580, 580)

    layout.addWidget(self.players_label)
    layout.addWidget(self.game_label)
    layout.addWidget(self.svg_widget)

    layout.setStretchFactor(self.players_label, 0)
    layout.setStretchFactor(self.game_label, 0)
    layout.setStretchFactor(self.svg_widget, 1)

    self.setLayout(layout)

  def update_board(self, board: ExtendedBoard | None = None, white_info: str = "", black_info: str = ""):
    """Update the displayed chess board."""
    if board is None:
      board = ExtendedBoard()

    last_move = board.peek() if board.move_stack else None
    check_squares = list(board.checkers())
    check_square = check_squares[0] if check_squares else None

    # Generate SVG and display it
    svg_data = chess.svg.board(board=board, lastmove=last_move, check=check_square)
    self.svg_widget.load(svg_data.encode("utf-8"))

    # Update status
    if board.extended_game_over():
      result = board.result()
      if result == "1-0":
        status = "Game Over: White wins!"
      elif result == "0-1":
        status = "Game Over: Black wins!"
      else:
        status = "Game Over: Draw!"
    else:
      turn = "White" if board.turn else "Black"

      extra = ""
      if board.is_check():
        extra = "CHECK"
      elif board.is_checkmate():
        extra = "CHECKMATE"
      if len(extra) > 0:
        extra = " | " + extra
      status = f"Turn: {turn} | Move: {board.fullmove_number}{extra}"

    self.players_label.setText(f"White: {white_info} | Black: {black_info}")
    self.game_label.setText(status)

    # Force repaint
    self.repaint()

  def closeEvent(self, a0: QCloseEvent | None):
    """Handle window close event."""
    if a0 is not None:
      a0.accept()


class ChessViewer:
  """A manager class for the chess viewing window."""

  def __init__(self, title="Chess Game"):
    self.app = None
    self.window = None
    self.title = title

  def initialize(self):
    """Initialize the Qt application and window."""
    if self.app is None:
      # Check if QApplication already exists
      self.app = QApplication.instance()
      if self.app is None:
        self.app = QApplication(sys.argv)

    if self.window is None:
      self.window = ChessWindow(self.title)
      self.window.show()

    return self.window

  def update_board(self, board: Board, white_info: str, black_info: str):
    """Update the chess board display."""
    if self.window is not None:
      self.window.update_board(board, white_info, black_info)
      # Process events to update the display
      if self.app is not None:
        self.app.processEvents()

  def close(self):
    """Close the viewer window."""
    if self.window is not None:
      self.window.close()
      self.window = None


if __name__ == "__main__":
  # Test the viewer
  viewer = ChessViewer("Test Chess Board")
  window = viewer.initialize()

  # Create a test position
  board = chess.Board()
  board.push_san("e4")
  board.push_san("e5")
  board.push_san("Nf3")

  viewer.update_board(board)

  # Run the application
  if viewer.app:
    viewer.app.exec()
