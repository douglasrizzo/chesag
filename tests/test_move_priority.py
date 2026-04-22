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


def test_score_move_tt_move_gets_max_bonus() -> None:
  board = chess.Board()
  prioritizer = HeuristicMovePrioritizer()
  move = chess.Move.from_uci("e2e4")

  score = prioritizer.score_move(board, move, tt_move=move)

  assert score == 1_000_000.0


def test_score_move_capture_scores_higher_than_quiet() -> None:
  board = chess.Board("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
  prioritizer = HeuristicMovePrioritizer()
  capture = chess.Move.from_uci("e4d5")
  quiet = chess.Move.from_uci("e1f2")

  capture_score = prioritizer.score_move(board, capture)
  quiet_score = prioritizer.score_move(board, quiet)

  assert capture_score > quiet_score


def test_score_move_promotion_scores_high() -> None:
  board = chess.Board("4k3/7P/8/8/8/8/8/4K3 w - - 0 1")
  prioritizer = HeuristicMovePrioritizer()
  promotion = chess.Move.from_uci("h7h8q")

  score = prioritizer.score_move(board, promotion)

  assert score > 50_000.0


def test_record_history_increments_on_repeated_calls() -> None:
  prioritizer = HeuristicMovePrioritizer()
  move = chess.Move.from_uci("e2e4")

  prioritizer.record_history(move, depth=2)
  first = prioritizer.history_heuristic[prioritizer._history_key(move)]

  prioritizer.record_history(move, depth=2)
  second = prioritizer.history_heuristic[prioritizer._history_key(move)]

  assert second > first
  assert second == 8


def test_record_history_depth_one_adds_one() -> None:
  prioritizer = HeuristicMovePrioritizer()
  move = chess.Move.from_uci("e2e4")

  prioritizer.record_history(move, depth=1)

  assert prioritizer.history_heuristic[prioritizer._history_key(move)] == 1


def test_record_killer_maintains_two_killers() -> None:
  prioritizer = HeuristicMovePrioritizer()
  move1 = chess.Move.from_uci("e2e4")
  move2 = chess.Move.from_uci("d2d4")
  move3 = chess.Move.from_uci("g1f3")

  prioritizer.record_killer(move1, depth=0)
  prioritizer.record_killer(move2, depth=0)
  prioritizer.record_killer(move3, depth=0)

  killers = prioritizer.killer_moves[0]
  assert len(killers) == 2
  assert killers[0] == move3


def test_record_killer_moves_existing_to_front() -> None:
  prioritizer = HeuristicMovePrioritizer()
  move = chess.Move.from_uci("e2e4")

  prioritizer.record_killer(move, depth=0)
  prioritizer.record_killer(chess.Move.from_uci("d2d4"), depth=0)
  prioritizer.record_killer(move, depth=0)

  killers = prioritizer.killer_moves[0]
  assert killers[0] == move
