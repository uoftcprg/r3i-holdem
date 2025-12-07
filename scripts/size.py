from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from math import perm
from sys import stdout

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


def traverse(state, card_count):
    if not state.status:
        count = 1
    elif state.can_deal_hole() or state.can_burn_card():
        if state.can_deal_hole():
            state.deal_hole()
            state.deal_hole()

            deal_count = 2
        else:
            state.burn_card()
            state.deal_board()

            deal_count = 1

        branching_factor = perm(card_count, deal_count)
        child_count = traverse(state, card_count - deal_count)
        count = 1 + branching_factor * child_count
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

                count += traverse(state, card_count)

    return count


def sub_main(starting_stack):
    state = RoyalRhodeIslandHoldem(AUTOMATIONS)(starting_stack)

    return traverse(state, 20)


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
