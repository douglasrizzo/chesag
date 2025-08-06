"""Move selection strategies for Monte Carlo Tree Search.

This module provides different strategies for selecting the best child node
from an MCTS tree, used during the final move selection phase after tree
search is complete.
"""

from abc import ABC, abstractmethod
from enum import Enum

from chesag.agents.mcts.node import Node


class MoveSelector(ABC):
  """Abstract base class for move selection strategies.

  Defines the interface for selecting the best child node from an MCTS tree
  after search completion.
  """

  @staticmethod
  @abstractmethod
  def select_best_child(node: Node) -> Node | None:
    """Select the best child node according to the selection strategy.

    Parameters
    ----------
    node : Node
        The parent node whose children to evaluate.

    Returns
    -------
    Node or None
        The selected best child node, or None if no children exist.
    """

  @staticmethod
  @abstractmethod
  def aggregate_results(results: list[tuple[str, int, float]]) -> dict[str, int]:
    """Aggregate the results of multiple simulations.

    Parameters
    ----------
    results : list[tuple[str, int, float]]
        A list of tuples containing the action, visit count, and reward for each simulation.

    Returns
    -------
    dict[str, int]
        A dictionary mapping actions to their aggregated results.
    """


class MoveSelectorByVisitCount(MoveSelector):
  """Move selector that chooses the child with the most visits.

  This strategy selects the child node that has been visited most frequently
  during the MCTS simulation phase, which is a common approach for final
  move selection.
  """

  @staticmethod
  def select_best_child(node: Node) -> Node | None:
    """Get the child with the most visits.

    Parameters
    ----------
    node : Node
        The parent node whose children to evaluate.

    Returns
    -------
    Node or None
        The child node with the highest visit count, or None if no children exist.
    """
    if not node.children:
      return None
    return max(node.children, key=lambda child: child.visits)

  @staticmethod
  def aggregate_results(results: list[tuple[str, int, float]]) -> dict[str, int]:
    """Aggregate the results of multiple simulations.

    Parameters
    ----------
    results : list[tuple[str, int, float]]
        A list of tuples containing the action, visit count, and reward for each simulation.

    Returns
    -------
    dict[str, int]
        A dictionary mapping actions to their total visit counts.
    """
    return {action: sum(visit_count for _, visit_count, _ in results if action == action) for action, _, _ in results}


class MoveSelectorByActionValue(MoveSelector):
  """Move selector that chooses the child with the highest action value.

  This strategy selects the child node with the highest estimated action value,
  which represents the expected reward from taking that action.
  """

  @staticmethod
  def select_best_child(node: Node) -> Node | None:
    """Get the child with the highest action value.

    Parameters
    ----------
    node : Node
        The parent node whose children to evaluate.

    Returns
    -------
    Node or None
        The child node with the highest action value, or None if no children exist.
    """
    if not node.children:
      return None
    return max(node.children, key=lambda child: child.action_value)

  @staticmethod
  def aggregate_results(results: list[tuple[str, int, float]]) -> dict[str, int]:
    """Aggregate the results of multiple simulations by action value.

    Combines multiple simulation results by summing visits and values for each
    move, then computing the average action value (total value / total visits)
    for each unique move.

    Parameters
    ----------
    results : list[tuple[str, int, float]]
        A list of tuples containing the move UCI notation, visit count, and
        action value for each simulation result.

    Returns
    -------
    dict[str, int]
        A dictionary mapping move UCI strings to their average action values
        across all simulations.
    """
    move_visits = {}
    move_values = {}
    for move_uci, visits, values in results:
      if move_uci and visits > 0:
        move_visits[move_uci] = move_visits.get(move_uci, 0) + visits
        move_values[move_uci] = move_values.get(move_uci, 0) + values
    return {move_uci: move_values[move_uci] / move_visits[move_uci] for move_uci in move_visits}


class MoveSelectionStrategy(Enum):
  """Enumeration of available move selection strategies."""

  VISIT = MoveSelectorByVisitCount
  ACTION = MoveSelectorByActionValue
