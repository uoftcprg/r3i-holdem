from pickle import dump, load
from sys import argv, stdin, stdout

from tqdm import tqdm
import cupy as cp

CHIP_COUNTS = tuple(map(int, argv[1:]))


def main():
    transitions = load(stdin.buffer)
    icmpp = {}

    assert set(transitions) == set(range(1, 155 + 1))

    for chip_count in tqdm(CHIP_COUNTS):
        P = cp.zeros((2 * (chip_count + 1), 2 * (chip_count + 1)))
        P[0, 0] = P[1, 1] = P[-2, -2] = P[-1, -1] = 1

        for starting_stack in range(1, chip_count):
            effective_stack = min(
                starting_stack,
                chip_count - starting_stack,
                155,
            )

            for starting_position in (0, 1):
                finishing_position = not starting_position

                for payoff, probability in (
                        transitions[effective_stack].items()
                ):
                    if starting_position:
                        payoff = -payoff

                    finishing_stack = starting_stack + payoff

                    assert 0 <= finishing_stack <= chip_count
                    assert 0 <= probability

                    r = 2 * finishing_stack + finishing_position
                    c = 2 * starting_stack + starting_position
                    P[r, c] = probability

        assert cp.allclose(P.sum(0), 1)

        while not cp.allclose(P[[0, 1, -2, -1], :].sum(0), 1):
            P @= P

        icmpp[chip_count] = P[[-2, -1], :].sum(0).tolist()

    dump(icmpp, stdout.buffer)


if __name__ == '__main__':
    main()
