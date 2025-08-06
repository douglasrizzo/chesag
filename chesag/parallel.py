from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from collections.abc import Callable


class ParallelWorkerManager:
  """Manages parallel worker execution for MCTS."""

  @staticmethod
  def execute_parallel_work(worker_func: Callable, worker_args: list, max_workers: int | None = None) -> list:
    """Execute work in parallel and collect results."""
    if not worker_args:
      return []

    if len(worker_args) == 1:
      return [worker_func(worker_args[0])]

    results = []
    actual_workers = min(len(worker_args), max_workers or len(worker_args))

    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
      futures = [executor.submit(worker_func, args) for args in worker_args]
      for future in as_completed(futures):
        try:
          result = future.result()
          if result:
            results.append(result)
        except Exception:
          continue

    return results

  @staticmethod
  def distribute_simulations(total_sims: int, num_workers: int) -> list[int]:
    """Distribute simulations across workers."""
    base_sims = total_sims // num_workers
    extra_sims = total_sims % num_workers

    distribution = []
    for i in range(num_workers):
      worker_sims = base_sims + (1 if i < extra_sims else 0)
      if worker_sims > 0:
        distribution.append(worker_sims)

    return distribution
