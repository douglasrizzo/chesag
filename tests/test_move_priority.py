import chess
from hypothesis import example, given

from chesag.move_priority import HeuristicMovePrioritizer
from chesag.position_key import build_position_key
from tests.hypothesis_strategies import legal_boards


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


@given(legal_boards(min_plies=1, max_plies=24))
@example(chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"))
def test_evaluate_move_does_not_mutate_board(board: chess.Board) -> None:
  prioritizer = HeuristicMovePrioritizer()
  legal_moves = list(board.legal_moves)
  if not legal_moves:
    return

  move = legal_moves[0]
  original_fen = board.fen()
  original_key = build_position_key(board)
  original_stack = list(board.move_stack)

  prioritizer.evaluate_move(move, board)

  assert board.fen() == original_fen
  assert build_position_key(board) == original_key
  assert list(board.move_stack) == original_stack
