from pathlib import Path

import pytest

import chesag.replay as replay_module


def test_replay_plays_pgn_with_viewer_updates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  pgn_path = tmp_path / "game.pgn"
  pgn_path.write_text(
    '[Event "Test"]\n[White "White"]\n[Black "Black"]\n\n1. e4 e5 2. Nf3 Nc6 *\n',
    encoding="utf-8",
  )

  updates: list[tuple[str, str, str]] = []

  class FakeViewer:
    def __init__(self) -> None:
      self.initialized = False

    def initialize(self) -> None:
      self.initialized = True

    def update_board(self, board, white_name: str, black_name: str) -> None:
      updates.append((board.fen(), white_name, black_name))

  monkeypatch.setattr(replay_module, "ChessViewer", FakeViewer)
  monkeypatch.setattr(replay_module.time, "sleep", lambda _: None)

  replay_module.replay(str(pgn_path), move_delay=0.0)

  assert len(updates) == 5
  assert updates[0][1:] == ("White", "Black")
