"""PyQt-based chess board viewer."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import chess
import chess.svg
from PyQt6.QtCore import Qt
from PyQt6.QtSvgWidgets import QSvgWidget  # PyQt6: comes from QtSvgWidgets
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from chesag.evaluation import material_balance

if TYPE_CHECKING:
  from PyQt6.QtGui import QResizeEvent


class ChessWindow(QWidget):
  """Simple chess GUI window."""

  def __init__(self, parent: QWidget | None = None) -> None:
    """Initialize the viewer window."""
    super().__init__(parent)
    self.setWindowTitle("Chess Viewer")

    self.svg_widget = QSvgWidget()
    self.white_label = QLabel()
    self.black_label = QLabel()
    self.game_label = QLabel()
    self.setWindowFlag(Qt.WindowType.Dialog, True)
    layout = QVBoxLayout()
    layout.addWidget(self.svg_widget, stretch=1)
    layout.addWidget(self.white_label)
    layout.addWidget(self.black_label)
    layout.addWidget(self.game_label)
    self.setLayout(layout)

    # UX bits
    self.flip = False  # allow flipping the board if you want

    # Reasonable defaults
    self.resize(640, 740)

  def resizeEvent(self, a0: QResizeEvent | None) -> None:
    """Keep the window square during resize operations."""
    w = self.width()
    h = self.height()
    side = min(w, h)
    # Avoid infinite loops: only adjust when actually needed
    if w != h:
      self.resize(side, side)
    super().resizeEvent(a0)

  def set_flipped(self, flipped: bool) -> None:
    """Flip the board orientation."""
    self.flip = bool(flipped)

  # ---- helpers ---------------------------------------------------------

  def _status_text(self, board: chess.Board) -> str:
    """Build a compact status line: whose turn, move number, material, and check flag."""
    if board.is_game_over():
      result = board.result()
      if result == "1-0":
        return "Game Over: White wins"
      if result == "0-1":
        return "Game Over: Black wins"
      return "Game Over: Draw"
    # Material from White's perspective: positive => White ahead
    mat = material_balance(board, chess.WHITE)
    turn = "White" if board.turn else "Black"
    extra = " | CHECK" if board.is_check() else ""
    return f"Turn: {turn} | Move: {board.fullmove_number} | Material: {mat:+.1f}{extra}"

  # ---- rendering -------------------------------------------------------

  def update_board(self, board: chess.Board | None = None, white_info: str = "", black_info: str = "") -> None:
    """Render the board, update labels."""
    if board is None:
      board = chess.Board()

    # Last move + proper check highlight (expects the KING square in check)
    last_move = board.peek() if board.move_stack else None
    check_square = board.king(board.turn) if board.is_check() else None

    arrows = [(last_move.from_square, last_move.to_square)] if last_move else []
    svg_data = chess.svg.board(
      board=board,
      lastmove=last_move,
      check=check_square,
      arrows=arrows,
      flipped=self.flip,
    )
    self.svg_widget.load(svg_data.encode("utf-8"))

    # Labels
    self.white_label.setText(f"White: {white_info}")
    self.black_label.setText(f"Black: {black_info}")
    self.game_label.setText(self._status_text(board))

    # Let Qt schedule a repaint (avoid forcing repaint on the whole dialog)
    self.svg_widget.update()


class ChessViewer:
  """Thin wrapper managing the Qt app and top-level window.

  Game.play(...) calls:
      viewer.update_board(board, str(white_agent), str(black_agent))
      # ...per move
  """

  def __init__(self) -> None:
    """Initialize the viewer wrapper."""
    self.app: QApplication | None = None
    self.window: ChessWindow | None = None

  def initialize(self) -> None:
    """Start the Qt app and show the window (idempotent)."""
    # Reuse existing app if one already exists
    app = QApplication.instance() or QApplication([])
    self.app = cast("QApplication", app)
    if self.window is None:
      self.window = ChessWindow()
      self.window.show()

  def update_board(self, board: chess.Board, white_info: str, black_info: str) -> None:
    """Update the GUI with the current board + labels."""
    if self.window is None:
      self.initialize()
    assert self.window is not None
    self.window.update_board(board, white_info, black_info)

    # Process pending events so the UI stays responsive during the engine loop
    if self.app is not None:
      self.app.processEvents()

  def set_flipped(self, flipped: bool) -> None:
    """Flip the board orientation."""
    if self.window is None:
      self.initialize()
    assert self.window is not None
    self.window.set_flipped(flipped)

  def close(self) -> None:
    """Close the viewer window if it exists."""
    if self.window is not None:
      self.window.close()
      self.window = None
