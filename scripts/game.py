from collections import defaultdict
from copy import deepcopy
from functools import partial
from itertools import permutations
from json import dump
from math import perm
from sys import argv, stdout

from ordered_set import OrderedSet
from pokerkit import (
    Automation,
    BoardDealing,
    CheckingOrCalling,
    CompletionBettingOrRaisingTo,
    Folding,
    HoleDealing,
    RhodeIslandHoldemHand,
    RoyalRhodeIslandHoldem,
    State,
)
from tqdm import tqdm

STARTING_STACK = int(argv[1])


class SignalTree:
    CARDS = OrderedSet(RoyalRhodeIslandHoldem.deck)
    DEALINGS = partial(permutations, CARDS, 4)
    DEALING_COUNT = perm(len(CARDS), 4)
    NULL_SIGNALS = '', ''

    def __init__(self):
        self.next_signals = defaultdict(OrderedSet)
        self.chance_probabilities = defaultdict(int)
        self.equities = defaultdict(int)
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

            self.chance_probabilities[self.NULL_SIGNALS] += 1
            self.chance_probabilities[preflop_signals] += 1
            self.chance_probabilities[flop_signals] += 1
            self.chance_probabilities[turn_signals] += 1

            row_hand = RhodeIslandHoldemHand.from_game(
                row_card,
                (flop_card, turn_card),
            )
            column_hand = RhodeIslandHoldemHand.from_game(
                column_card,
                (flop_card, turn_card),
            )

            if row_hand > column_hand:
                equity = 1
            elif row_hand < column_hand:
                equity = 0
            else:
                equity = 0.5

            self.equities[self.NULL_SIGNALS] += equity
            self.equities[preflop_signals] += equity
            self.equities[flop_signals] += equity
            self.equities[turn_signals] += equity

        for signals in tqdm(self.equities):
            self.equities[signals] /= self.chance_probabilities[signals]

        for signals in tqdm(self.chance_probabilities):
            self.chance_probabilities[signals] /= self.DEALING_COUNT

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

    def evaluate(self, pot, signals):
        stack = STARTING_STACK - pot / 2
        expected_stack = stack + pot * self.equities[signals]
        expected_utility = expected_stack - STARTING_STACK
        rounded_expected_utility = round(expected_utility)

        if rounded_expected_utility == expected_utility:
            expected_utility = rounded_expected_utility

        return expected_utility


def infoset(state, signal):
    actions = []

    for operation in state.operations:
        if (
                isinstance(operation, BoardDealing)
                or (
                    isinstance(operation, HoleDealing)
                    and operation.player_index == state.actor_index
                )
        ):
            actions.append('')
        elif isinstance(operation, Folding):
            actions[-1] += 'f'
        elif isinstance(operation, CheckingOrCalling):
            actions[-1] += 'c'
        elif isinstance(operation, CompletionBettingOrRaisingTo):
            actions[-1] += 'r'

    action = ':'.join(actions)

    return f'{action};{signal}'


SIGNAL_TREE = SignalTree()


def traverse(state, signals, sequences, children, utilities):
    if not state.status or state.all_in_status or not any(state.stacks):
        if state.folded_status:
            utility = state.payoffs[0]
        else:
            utility = SIGNAL_TREE.evaluate(state.total_pushed_amount, signals)

        sequences = tuple(sequences)

        assert sequences not in utilities

        chance_probability = SIGNAL_TREE.chance_probabilities[signals]
        utilities[sequences] = chance_probability * utility
    elif state.can_deal_hole() or state.can_burn_card():
        next_signals = SIGNAL_TREE.next_signals[signals]

        if state.can_deal_hole():
            state.deal_hole()
            state.deal_hole()

            next_signals = tqdm(next_signals)
        else:
            state.burn_card()
            state.deal_board()

        for signals in next_signals:
            traverse(state, signals, sequences, children, utilities)
    else:
        i = state.actor_index
        j = infoset(state, signals[i])
        p_j = sequences[i]

        children[i][p_j].add(j)

        previous_state = state
        previous_sequences = sequences

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
                sequences = list(previous_sequences)
                sequence = j, a
                sequences[i] = sequence
                sequences = tuple(sequences)

                if sequence not in children[i]:
                    children[i][sequence] = OrderedSet()

                apply(state)
                traverse(state, signals, sequences, children, utilities)


def process(children, utilities):
    tfsdps = [[], []]
    count = 0

    for i, tfsdp in enumerate(tqdm(tfsdps)):
        for p_j, J in tqdm(children[i].items(), leave=False):
            if not J:
                tfsdp.append(
                    {
                        'parent_edge': p_j,
                        'node': {
                            'id': '',
                            'type': 'END_OF_THE_DECISION_PROCESS',
                        },
                    },
                )
            elif len(J) == 1:
                tfsdp.append(
                    {
                        'parent_edge': p_j,
                        'node': {'id': J[0], 'type': 'DECISION_POINT'},
                    },
                )
            else:
                k = f'o{count}'
                count += 1

                tfsdp.append(
                    {
                        'parent_edge': p_j,
                        'node': {'id': k, 'type': 'OBSERVATION_POINT'},
                    },
                )

                for e, j in enumerate(J):
                    parent_edge = k, f'e{e}'

                    tfsdp.append(
                        {
                            'parent_edge': parent_edge,
                            'node': {'id': j, 'type': 'DECISION_POINT'},
                        },
                    )

    utilities = list(
        map(
            dict,
            map(partial(zip, ('sequences', 'value')), tqdm(utilities.items())),
        ),
    )

    return {
        'tree_form_sequential_decision_processes': tfsdps,
        'utilities': utilities,
    }


def main():
    initial_state = RoyalRhodeIslandHoldem(
        (
            Automation.ANTE_POSTING,
            Automation.BET_COLLECTION,
            Automation.BLIND_OR_STRADDLE_POSTING,
            Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
            Automation.HAND_KILLING,
            Automation.CHIPS_PUSHING,
            Automation.CHIPS_PULLING,
        ),
    )(STARTING_STACK)
    children = {(): OrderedSet()}, {(): OrderedSet()}
    utilities = {}

    traverse(initial_state, ('', ''), ((), ()), children, utilities)
    dump(process(children, utilities), stdout)


if __name__ == '__main__':
    main()
