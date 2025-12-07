from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from functools import partial
from itertools import permutations
from math import perm
from sys import stdout

from ordered_set import OrderedSet
from pokerkit import Automation, RoyalRhodeIslandHoldem, State
from tqdm import tqdm
import numpy as np

STARTING_STACKS = range(1, 155 + 1)
AUTOMATIONS = (
    Automation.ANTE_POSTING,
    Automation.BET_COLLECTION,
    Automation.BLIND_OR_STRADDLE_POSTING,
    Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
    Automation.HAND_KILLING,
    Automation.CHIPS_PUSHING,
    Automation.CHIPS_PULLING,
)


class SignalTree:
    CARDS = OrderedSet(RoyalRhodeIslandHoldem.deck)
    DEALINGS = partial(permutations, CARDS, 4)
    DEALING_COUNT = perm(len(CARDS), 4)
    NULL_SIGNALS = '', ''

    def __init__(self):
        self.next_signals = defaultdict(OrderedSet)
        dealings = tqdm(self.DEALINGS(), total=self.DEALING_COUNT)

        for row_card, column_card, flop_card, turn_card in dealings:
            preflop_signals = self.filter_preflop(row_card, column_card)
            flop_signals = self.filter_flop(row_card, column_card, flop_card)
            turn_signals = self.filter_turn(
                row_card,
                column_card,
                flop_card,
                turn_card,
            )

            self.next_signals[self.NULL_SIGNALS].add(preflop_signals)
            self.next_signals[preflop_signals].add(flop_signals)
            self.next_signals[flop_signals].add(turn_signals)

    def filter_preflop(self, row_card, column_card):
        return row_card.rank, column_card.rank

    def filter_flop(self, row_card, column_card, flop_card):

        def signal(card):
            signal = f'{card.rank}{flop_card.rank}'

            if card.suit == flop_card.suit:
                signal = f'({signal})'

            return signal

        return signal(row_card), signal(column_card)

    def filter_turn(self, row_card, column_card, flop_card, turn_card):

        def signal(card):
            if card.suit == flop_card.suit == turn_card.suit:
                signal = f'({card.rank}{flop_card.rank}{turn_card.rank})'
            elif card.suit == flop_card.suit:
                signal = f'({card.rank}{flop_card.rank}){turn_card.rank}'
            elif card.suit == turn_card.suit:
                signal = f'{card.rank}){flop_card.rank}({turn_card.rank}'
            elif flop_card.suit == turn_card.suit:
                signal = f'{card.rank}({flop_card.rank}{turn_card.rank})'
            else:
                signal = f'{card.rank}{flop_card.rank}{turn_card.rank}'

            return signal

        return signal(row_card), signal(column_card)


SIGNAL_TREE = SignalTree()


def traverse(state, signals):
    if not state.status:
        count = 1
    elif state.can_deal_hole() or state.can_burn_card():
        next_signals = SIGNAL_TREE.next_signals[signals]

        if state.can_deal_hole():
            state.deal_hole()
            state.deal_hole()
        else:
            state.burn_card()
            state.deal_board()

        count = 1

        for signals in next_signals:
            count += traverse(state, signals)
    else:
        count = 1
        previous_state = state

        for a, query, apply in (
                ('f', State.can_fold, State.fold),
                ('c', State.can_check_or_call, State.check_or_call),
                (
                    'r',
                    State.can_complete_bet_or_raise_to,
                    State.complete_bet_or_raise_to,
                ),
        ):
            if query(previous_state):
                state = deepcopy(previous_state)

                apply(state)

                count += traverse(state, signals)

    return count


def sub_main(starting_stack):
    state = RoyalRhodeIslandHoldem(AUTOMATIONS)(starting_stack)

    return traverse(state, ('', ''))


def main():
    with ProcessPoolExecutor() as executor:
        sizes = list(
            tqdm(
                executor.map(sub_main, STARTING_STACKS),
                total=len(STARTING_STACKS),
            ),
        )

    np.save(stdout.buffer, sizes)


if __name__ == '__main__':
    main()
