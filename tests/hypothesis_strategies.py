"""Hypothesis strategies for chess positions."""

from __future__ import annotations

import chess
from hypothesis import strategies as st


@st.composite
def legal_boards(draw: st.DrawFn, *, min_plies: int = 0, max_plies: int = 20) -> chess.Board:
  """Build an arbitrary legal board by replaying a bounded list of legal moves."""
  board = chess.Board()
  plies = draw(st.integers(min_value=min_plies, max_value=max_plies))

  for _ in range(plies):
    legal_moves = list(board.legal_moves)
    if not legal_moves:
      break
    move_index = draw(st.integers(min_value=0, max_value=len(legal_moves) - 1))
    board.push(legal_moves[move_index])

  return board
