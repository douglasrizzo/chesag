import chess

from chesag.move_priority import HeuristicMovePrioritizer


def test_tt_move_is_ranked_first() -> None:
  board = chess.Board()
  moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("g1f3"), chess.Move.from_uci("d2d4")]
  prioritizer = HeuristicMovePrioritizer()

  ordered = prioritizer.order_moves(board, moves, tt_move=chess.Move.from_uci("g1f3"))

  assert ordered[0] == chess.Move.from_uci("g1f3")


def test_tactical_capture_is_ranked_ahead_of_quiet_move() -> None:
  board = chess.Board("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
  moves = [chess.Move.from_uci("e4d5"), chess.Move.from_uci("e1f2")]
  prioritizer = HeuristicMovePrioritizer()

  ordered = prioritizer.order_moves(board, moves)

  assert ordered[0] == chess.Move.from_uci("e4d5")


def test_killer_move_reorders_quiet_candidates() -> None:
  board = chess.Board()
  moves = [chess.Move.from_uci("a2a3"), chess.Move.from_uci("g1f3")]
  prioritizer = HeuristicMovePrioritizer()
  prioritizer.record_killer(chess.Move.from_uci("a2a3"), depth=2)

  ordered = prioritizer.order_moves(board, moves, depth=2)

  assert ordered[0] == chess.Move.from_uci("a2a3")


def test_history_heuristic_breaks_quiet_move_ties() -> None:
  board = chess.Board()
  moves = [chess.Move.from_uci("a2a3"), chess.Move.from_uci("h2h3")]
  prioritizer = HeuristicMovePrioritizer()
  prioritizer.record_history(chess.Move.from_uci("h2h3"), depth=3)

  ordered = prioritizer.order_moves(board, moves, depth=1)

  assert ordered[0] == chess.Move.from_uci("h2h3")
