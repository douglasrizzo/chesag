"""Board evaluation helpers."""

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from time import perf_counter_ns

import chess
from chess import Board, Move

PIECE_VALUES = {
  chess.PAWN: 1.0,
  chess.KNIGHT: 3.2,
  chess.BISHOP: 3.33,
  chess.ROOK: 5.1,
  chess.QUEEN: 9.5,
  chess.KING: 0.0,
}

BISHOP_PAIR_BONUS = 0.5
PASSED_PAWN_BONUS = 0.2
CENTER_CONTROL_WEIGHT = 0.1
KING_CASTLE_BONUS = 0.25
KING_OPEN_FILE_PENALTY = -0.2
PAWN_SHIELD_PENALTY = -0.1
MOVE_CAPTURE_WEIGHT = 0.1
MOVE_CHECK_BONUS = 0.3
MOBILITY_WEIGHT = 0.05

CENTER4 = (chess.D4, chess.E4, chess.D5, chess.E5)
EXTENDED_CENTER = {
  chess.C3,
  chess.C4,
  chess.C5,
  chess.C6,
  chess.D3,
  chess.D4,
  chess.D5,
  chess.D6,
  chess.E3,
  chess.E4,
  chess.E5,
  chess.E6,
  chess.F3,
  chess.F4,
  chess.F5,
  chess.F6,
}


@dataclass(slots=True)
class EvaluationTierStats:
  """Counters for one evaluation tier."""

  calls: int = 0
  total_ns: int = 0


@dataclass(slots=True)
class EvaluationStats:
  """Aggregate counters across evaluation tiers."""

  leaf: EvaluationTierStats = field(default_factory=EvaluationTierStats)
  order: EvaluationTierStats = field(default_factory=EvaluationTierStats)
  rollout: EvaluationTierStats = field(default_factory=EvaluationTierStats)

  def as_dict(self) -> dict[str, dict[str, int]]:
    """Return a stable dict view of the counters."""
    return {
      "leaf": asdict(self.leaf),
      "order": asdict(self.order),
      "rollout": asdict(self.rollout),
    }


_EVALUATION_STATS = EvaluationStats()


def evaluate(
  board: Board,
  perspective_color: bool,
  *,
  include_move_bonus: bool = False,
  use_material: bool = True,
  use_bishop_pair: bool = True,
  use_passed_pawns: bool = True,
  use_center_basic: bool = False,
  use_center_extended: bool = True,
  use_king_safety: bool = True,
  use_mobility: bool = True,
) -> float:
  """Evaluate a board from the requested perspective.

  The keyword toggles are preserved for compatibility, but new search code should
  prefer the explicit tiered helpers: `leaf_evaluate()`, `order_evaluate()`, and
  `rollout_evaluate()`.
  """
  terminal = terminal_evaluation(board, perspective_color)
  if terminal is not None:
    return terminal

  score = 0.0
  if use_material:
    score += material_balance(board, perspective_color)
  if use_bishop_pair:
    score += bishop_pair_bonus(board, perspective_color)
  if use_passed_pawns:
    score += passed_pawn_score(board, perspective_color)
  if use_center_extended:
    score += center_control(board, perspective_color, EXTENDED_CENTER)
  elif use_center_basic:
    score += center_control(board, perspective_color, CENTER4)
  if use_king_safety:
    score += king_safety(board, perspective_color)
  if use_mobility:
    score += mobility_score(board, perspective_color)
  if include_move_bonus and board.move_stack:
    score += move_bonus(board, perspective_color)
  return score


def leaf_evaluate(board: Board, perspective_color: bool) -> float:
  """Return the richer leaf evaluation used by minimax leaves and MCTS terminals."""
  start_ns = perf_counter_ns()
  try:
    return evaluate(board, perspective_color)
  finally:
    _record_tier_stat(_EVALUATION_STATS.leaf, start_ns)


def order_evaluate(board: Board, perspective_color: bool) -> float:
  """Return a cheap static evaluation for move ordering and quiescence."""
  start_ns = perf_counter_ns()
  try:
    return evaluate(
      board,
      perspective_color,
      include_move_bonus=False,
      use_material=True,
      use_bishop_pair=False,
      use_passed_pawns=False,
      use_center_basic=True,
      use_center_extended=False,
      use_king_safety=False,
      use_mobility=False,
    )
  finally:
    _record_tier_stat(_EVALUATION_STATS.order, start_ns)


def rollout_evaluate(board: Board, perspective_color: bool) -> float:
  """Return a very cheap evaluation for rollout weighting and cutoffs."""
  start_ns = perf_counter_ns()
  try:
    terminal = terminal_evaluation(board, perspective_color)
    if terminal is not None:
      return terminal
    return material_balance(board, perspective_color) + center_control(board, perspective_color, CENTER4)
  finally:
    _record_tier_stat(_EVALUATION_STATS.rollout, start_ns)


def quick_evaluate(board: Board, perspective_color: bool) -> float:
  """Backward-compatible alias for the ordering evaluation tier."""
  return order_evaluate(board, perspective_color)


def reset_evaluation_stats() -> None:
  """Reset all evaluation-tier counters."""
  _EVALUATION_STATS.leaf.calls = 0
  _EVALUATION_STATS.leaf.total_ns = 0
  _EVALUATION_STATS.order.calls = 0
  _EVALUATION_STATS.order.total_ns = 0
  _EVALUATION_STATS.rollout.calls = 0
  _EVALUATION_STATS.rollout.total_ns = 0


def get_evaluation_stats() -> EvaluationStats:
  """Return a snapshot of current evaluation-tier counters."""
  stats = _EVALUATION_STATS.as_dict()
  snapshot = EvaluationStats()
  snapshot.leaf.calls = stats["leaf"]["calls"]
  snapshot.leaf.total_ns = stats["leaf"]["total_ns"]
  snapshot.order.calls = stats["order"]["calls"]
  snapshot.order.total_ns = stats["order"]["total_ns"]
  snapshot.rollout.calls = stats["rollout"]["calls"]
  snapshot.rollout.total_ns = stats["rollout"]["total_ns"]
  return snapshot


def _record_tier_stat(stats: EvaluationTierStats, start_ns: int) -> None:
  """Record one evaluation call."""
  stats.calls += 1
  stats.total_ns += perf_counter_ns() - start_ns


def terminal_evaluation(board: Board, perspective_color: bool) -> float | None:
  """Return a terminal score or `None` if the game is still in progress."""
  if board.is_checkmate():
    return float("inf") if board.turn != perspective_color else -float("inf")
  if board.is_stalemate() or board.is_insufficient_material():
    return 0.0
  return None


def material_balance(board: Board, perspective_color: bool) -> float:
  """Return material balance from the requested perspective."""
  score = 0.0
  for piece_type, value in PIECE_VALUES.items():
    score += value * len(board.pieces(piece_type, chess.WHITE))
    score -= value * len(board.pieces(piece_type, chess.BLACK))
  return score if perspective_color == chess.WHITE else -score


def bishop_pair_bonus(board: Board, perspective_color: bool) -> float:
  """Return the bishop-pair bonus from the requested perspective."""
  score = 0.0
  if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
    score += BISHOP_PAIR_BONUS
  if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
    score -= BISHOP_PAIR_BONUS
  return score if perspective_color == chess.WHITE else -score


def passed_pawn_score(board: Board, perspective_color: bool) -> float:
  """Return the passed-pawn bonus from the requested perspective."""
  score = 0.0
  for pawn_square in board.pieces(chess.PAWN, chess.WHITE):
    if is_passed_pawn(board, pawn_square, chess.WHITE):
      rank = chess.square_rank(pawn_square)
      score += PASSED_PAWN_BONUS * (rank / 6)
  for pawn_square in board.pieces(chess.PAWN, chess.BLACK):
    if is_passed_pawn(board, pawn_square, chess.BLACK):
      rank = 7 - chess.square_rank(pawn_square)
      score -= PASSED_PAWN_BONUS * (rank / 6)
  return score if perspective_color == chess.WHITE else -score


def is_passed_pawn(board: Board, square: chess.Square, color: bool) -> bool:
  """Check if a pawn has no enemy pawns in front of it or on adjacent files."""
  file = chess.square_file(square)
  rank = chess.square_rank(square)
  direction = 1 if color == chess.WHITE else -1
  enemy_pawns = board.pieces(chess.PAWN, not color)

  for next_rank in range(rank + direction, 8 if color == chess.WHITE else -1, direction):
    for next_file in (file - 1, file, file + 1):
      if 0 <= next_file <= 7 and chess.square(next_file, next_rank) in enemy_pawns:
        return False
  return True


def center_control(board: Board, perspective_color: bool, squares: Iterable[chess.Square]) -> float:
  """Score control of the supplied central squares."""
  white_attackers = sum(len(board.attackers(chess.WHITE, square)) for square in squares)
  black_attackers = sum(len(board.attackers(chess.BLACK, square)) for square in squares)
  score = (white_attackers - black_attackers) * CENTER_CONTROL_WEIGHT
  return score if perspective_color == chess.WHITE else -score


def king_safety(board: Board, perspective_color: bool) -> float:
  """Score king safety from the requested perspective."""
  score = 0.0
  white_king = board.king(chess.WHITE)
  black_king = board.king(chess.BLACK)

  if board.has_kingside_castling_rights(chess.WHITE):
    score += KING_CASTLE_BONUS
  if board.has_queenside_castling_rights(chess.WHITE):
    score += KING_CASTLE_BONUS
  if board.has_kingside_castling_rights(chess.BLACK):
    score -= KING_CASTLE_BONUS
  if board.has_queenside_castling_rights(chess.BLACK):
    score -= KING_CASTLE_BONUS

  if white_king is not None:
    score += open_file_and_shield_penalty(board, white_king, chess.WHITE)
  if black_king is not None:
    score -= open_file_and_shield_penalty(board, black_king, chess.BLACK)
  return score if perspective_color == chess.WHITE else -score


def open_file_and_shield_penalty(board: Board, king_square: chess.Square, color: bool) -> float:
  """Score open files and pawn shield quality around one king."""
  score = 0.0
  king_file = chess.square_file(king_square)

  for file_idx in (king_file - 1, king_file, king_file + 1):
    if 0 <= file_idx <= 7:
      file_squares = [chess.square(file_idx, rank) for rank in range(8)]
      if not any(
        board.piece_type_at(square) == chess.PAWN and board.color_at(square) == color for square in file_squares
      ):
        score += KING_OPEN_FILE_PENALTY

  forward = 1 if color == chess.WHITE else -1
  target_rank = chess.square_rank(king_square) + forward
  if 0 <= target_rank <= 7:
    for file_idx in (king_file - 1, king_file, king_file + 1):
      if 0 <= file_idx <= 7:
        square = chess.square(file_idx, target_rank)
        if board.piece_type_at(square) != chess.PAWN or board.color_at(square) != color:
          score += PAWN_SHIELD_PENALTY
  return score


def mobility_score(board: Board, perspective_color: bool) -> float:
  """Score relative mobility from the requested perspective."""
  white_board = board.copy(stack=False)
  white_board.turn = chess.WHITE
  white_mobility = white_board.legal_moves.count()

  black_board = board.copy(stack=False)
  black_board.turn = chess.BLACK
  black_mobility = black_board.legal_moves.count()

  score = (white_mobility - black_mobility) * MOBILITY_WEIGHT
  return score if perspective_color == chess.WHITE else -score


def mvv_lva_score(board: Board, move: Move) -> float:
  """Score captures using the MVV-LVA heuristic."""
  if not board.is_capture(move):
    return 0.0

  victim_square = move.to_square
  if board.is_en_passant(move):
    direction = -8 if board.turn == chess.WHITE else 8
    victim_square = move.to_square + direction

  victim_type = board.piece_type_at(victim_square)
  attacker_type = board.piece_type_at(move.from_square)
  if victim_type is None or attacker_type is None:
    return 0.0
  return (PIECE_VALUES[victim_type] * 10) - PIECE_VALUES[attacker_type]


def move_bonus(board: Board, perspective_color: bool) -> float:
  """Return move-local tactical bonuses from the last move played."""
  if not board.move_stack:
    return 0.0

  last_move = board.peek()
  score = 0.0
  if board.is_capture(last_move):
    score += MOVE_CAPTURE_WEIGHT * mvv_lva_score(board, last_move)
  if board.is_check():
    score += MOVE_CHECK_BONUS
  if last_move.promotion is not None:
    score += PIECE_VALUES[last_move.promotion] - PIECE_VALUES[chess.PAWN]
  return score if perspective_color != board.turn else -score
