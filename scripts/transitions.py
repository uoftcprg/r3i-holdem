from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from functools import partial
from itertools import permutations
from math import isclose, perm
from pickle import dump, load
from sys import stdin, stdout

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


class SignalTree:
    CARDS = OrderedSet(RoyalRhodeIslandHoldem.deck)
    DEALINGS = partial(permutations, CARDS, 4)
    DEALING_COUNT = perm(len(CARDS), 4)
    NULL_SIGNALS = '', ''

    def __init__(self):
        self.next_signals = defaultdict(OrderedSet)
        self.chance_probabilities = defaultdict(int)
        self.win_probabilities = defaultdict(int)
        self.tie_probabilities = defaultdict(int)
        self.loss_probabilities = defaultdict(int)
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
                probabilities = self.win_probabilities
            elif row_hand < column_hand:
                probabilities = self.loss_probabilities
            else:
                probabilities = self.tie_probabilities

            probabilities[self.NULL_SIGNALS] += 1
            probabilities[preflop_signals] += 1
            probabilities[flop_signals] += 1
            probabilities[turn_signals] += 1

        for signals in tqdm(self.chance_probabilities):
            count = self.chance_probabilities[signals]
            self.win_probabilities[signals] /= count
            self.tie_probabilities[signals] /= count
            self.loss_probabilities[signals] /= count

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


def traverse(state, signals, sequences, strategy, probabilities):
    if not state.status or state.all_in_status or not any(state.stacks):
        probability = (
            SIGNAL_TREE.chance_probabilities[signals]
            * strategy[sequences[0]]
            * strategy[sequences[1]]
        )

        if state.folded_status:
            payoff = state.payoffs[0]
            probabilities[payoff] += probability
        else:
            pot = state.total_pushed_amount

            assert pot % 2 == 0
            assert isclose(
                (
                    SIGNAL_TREE.win_probabilities[signals]
                    + SIGNAL_TREE.tie_probabilities[signals]
                    + SIGNAL_TREE.loss_probabilities[signals]
                ),
                1,
            )

            probabilities[pot // 2] += (
                SIGNAL_TREE.win_probabilities[signals] * probability
            )
            probabilities[0] += (
                SIGNAL_TREE.tie_probabilities[signals] * probability
            )
            probabilities[-pot // 2] += (
                SIGNAL_TREE.loss_probabilities[signals] * probability
            )
    elif state.can_deal_hole() or state.can_burn_card():
        next_signals = SIGNAL_TREE.next_signals[signals]

        if state.can_deal_hole():
            state.deal_hole()
            state.deal_hole()
        else:
            state.burn_card()
            state.deal_board()

        for signals in next_signals:
            traverse(state, signals, sequences, strategy, probabilities)
    else:
        i = state.actor_index
        j = infoset(state, signals[i])

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

                apply(state)
                traverse(state, signals, sequences, strategy, probabilities)


def sub_main(starting_stack_strategy):
    starting_stack, strategy = starting_stack_strategy
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
    )(starting_stack)
    probabilities = defaultdict(int)

    traverse(
        initial_state,
        ('', ''),
        ((), ()),
        strategy,
        probabilities,
    )

    return probabilities


def main():
    strategies = load(stdin.buffer)
    starting_stacks = strategies.keys()
    strategies = strategies.values()

    with ProcessPoolExecutor() as executor:
        iterator = executor.map(sub_main, zip(starting_stacks, strategies))
        probabilities = list(tqdm(iterator, total=len(strategies)))

    probabilities = dict(zip(starting_stacks, probabilities))

    dump(probabilities, stdout.buffer)


if __name__ == '__main__':
    main()
