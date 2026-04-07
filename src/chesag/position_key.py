"""Helpers for building stable runtime position keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
  from chess import Board

type PositionKey = tuple[object, ...]


def build_position_key(board: Board) -> PositionKey:
  """Return a compact key that distinguishes all chess state relevant to search."""
  return cast("PositionKey", board._transposition_key())
