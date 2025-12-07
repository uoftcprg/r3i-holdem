from pickle import dump
from sys import argv, stdout

from tqdm import tqdm
import numpy as np

SOLUTION_PATHNAME = argv[1]
EFFECTIVE_STACKS = range(6, 155 + 1)


def main():
    strategies = {effective_stack: {} for effective_stack in EFFECTIVE_STACKS}

    for effective_stack in tqdm(EFFECTIVE_STACKS):
        solution = np.load(
            SOLUTION_PATHNAME.format(effective_stack),
            allow_pickle=True,
        )
        row_sequences = solution['row_sequences'].tolist()
        average_row_strategy = solution['average_row_strategy'].tolist()
        column_sequences = solution['column_sequences'].tolist()
        average_column_strategy = solution['average_column_strategy'].tolist()

        assert len(row_sequences) == len(average_row_strategy)
        assert len(column_sequences) == len(average_column_strategy)

        strategies[effective_stack].update(
            zip(row_sequences, average_row_strategy),
        )
        strategies[effective_stack].update(
            zip(column_sequences, average_column_strategy),
        )
        strategies[effective_stack].pop(())

        assert (
            len(strategies[effective_stack])
            == len(row_sequences) + len(column_sequences) - 2
        )

    dump(strategies, stdout.buffer)


if __name__ == '__main__':
    main()
