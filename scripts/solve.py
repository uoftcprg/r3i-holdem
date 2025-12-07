from resource import getrusage, RUSAGE_SELF
from sys import stdin, stdout
from time import time

from gpugt.games import TwoPlayerZeroSumExtensiveFormGame
from gpugt.regret_minimizers import CounterfactualRegretMinimizationPlus
from tqdm import tqdm
import cupy as cp
import numpy as np

ITERATIONS = range(1, 1024 + 1)


def main():
    memory_pool = cp.get_default_memory_pool()
    pinned_memory_pool = cp.get_default_pinned_memory_pool()
    game = TwoPlayerZeroSumExtensiveFormGame.load(stdin)
    row_tfsdp = game.row_tree_form_sequential_decision_process
    column_tfsdp = game.column_tree_form_sequential_decision_process
    row_cfr = CounterfactualRegretMinimizationPlus(row_tfsdp)
    column_cfr = CounterfactualRegretMinimizationPlus(column_tfsdp)
    times = []
    exploitabilities = []
    values = []
    checkpoint = 1

    for iteration in tqdm(ITERATIONS, leave=False):
        begin_time = time()
        row_strategy = row_cfr.next_strategy()

        if iteration > 1:
            column_utility = game.column_utility(row_strategy)

            column_cfr.observe_utility(column_utility)

        column_strategy = column_cfr.next_strategy()
        row_utility = game.row_utility(column_strategy)

        row_cfr.observe_utility(row_utility)

        end_time = time()
        time_ = end_time - begin_time
        average_row_strategy = row_cfr.average_strategy
        average_column_strategy = column_cfr.average_strategy
        average_strategies = average_row_strategy, average_column_strategy

        if iteration == checkpoint:
            exploitability = game.exploitability(*average_strategies).item()
            checkpoint *= 2
        else:
            exploitability = np.nan

        value = game.row_value(*average_strategies).item()

        times.append(time_)
        exploitabilities.append(exploitability)
        values.append(value)

    np.savez(
        stdout.buffer,
        iterations=ITERATIONS,
        times=times,
        exploitabilities=exploitabilities,
        values=values,
        average_row_strategy=row_cfr.average_strategy,
        average_column_strategy=column_cfr.average_strategy,
        row_sequences=np.array(row_tfsdp.sequences, dtype=object),
        column_sequences=np.array(column_tfsdp.sequences, dtype=object),
        used_bytes=memory_pool.used_bytes(),
        total_bytes=memory_pool.total_bytes(),
        n_free_blocks=pinned_memory_pool.n_free_blocks(),
        ru_maxrss=getrusage(RUSAGE_SELF).ru_maxrss,
    )


if __name__ == '__main__':
    main()
