from functools import partial
from itertools import permutations
from math import perm
from pickle import dump, load
from sys import stdin, stdout

from ordered_set import OrderedSet
from pokerkit import RhodeIslandHoldemHand, RoyalRhodeIslandHoldem
from tqdm import tqdm


class SignalTree:
    CARDS = OrderedSet(RoyalRhodeIslandHoldem.deck)
    DEALINGS = partial(permutations, CARDS, 4)
    DEALING_COUNT = perm(len(CARDS), 4)
    NULL_SIGNALS = '', ''

    def __init__(self):
        self.win_probability = 0
        self.tie_probability = 0
        self.loss_probability = 0
        dealings = tqdm(self.DEALINGS(), total=self.DEALING_COUNT)

        for row_card, column_card, flop_card, turn_card in dealings:
            row_hand = RhodeIslandHoldemHand.from_game(
                row_card,
                (flop_card, turn_card),
            )
            column_hand = RhodeIslandHoldemHand.from_game(
                column_card,
                (flop_card, turn_card),
            )

            if row_hand > column_hand:
                self.win_probability += 1
            elif row_hand < column_hand:
                self.loss_probability += 1
            else:
                self.tie_probability += 1

        self.win_probability /= self.DEALING_COUNT
        self.tie_probability /= self.DEALING_COUNT
        self.loss_probability /= self.DEALING_COUNT


SIGNAL_TREE = SignalTree()


def main():
    transitions = load(stdin.buffer)

    assert min(transitions) == 6

    for starting_stack in range(1, min(transitions)):
        transitions[starting_stack] = {
            -starting_stack: SIGNAL_TREE.loss_probability,
            0: SIGNAL_TREE.tie_probability,
            starting_stack: SIGNAL_TREE.win_probability,
        }

    dump(transitions, stdout.buffer)


if __name__ == '__main__':
    main()
