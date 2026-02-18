import math
import multiprocessing
from functools import partial

from .board import Board


def simulate_action(action_index, state, iteration=10000):
    """Run Monte Carlo simulation for a single action."""
    board = Board()
    board.set_state(state)
    board.auto_process = True

    if board.dice_use >= 100 and not board.is_double:
        return action_index, None  # Game over

    scores = []
    for _ in range(iteration):
        sim = Board()
        sim.set_state(state)
        sim.auto_process = True
        sim.step(action_index)

        while not sim.step(sim.choose_action()):
            pass

        scores.append(sim.score)

    avg = sum(scores) / len(scores)
    min_s = min(scores)
    max_s = max(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    std = variance ** 0.5
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    if n % 2 == 0:
        median = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
    else:
        median = sorted_scores[n // 2]

    return action_index, {'avg': avg, 'min': min_s, 'max': max_s, 'std': std, 'mid': median}


def run_simulation(state, actions, iteration=10000, num_processes=6):
    """Run parallel Monte Carlo simulation for multiple actions."""
    with multiprocessing.Pool(processes=min(num_processes, len(actions))) as pool:
        func = partial(simulate_action, state=state, iteration=iteration)
        results = pool.map(func, actions)

    return {idx: stats for idx, stats in results}


def calc_loss(x):
    """Statistical penalty function."""
    if x > 999999:
        return 0
    log_x = math.log10(x)
    return 0.25 * log_x ** 2 - 3.25 * log_x + 10.5
