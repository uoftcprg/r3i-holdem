from itertools import product
from random import choices, randint
from urllib.parse import urljoin

from js import URLSearchParams
from pokerkit import (
    Automation,
    BoardDealing,
    CheckingOrCalling,
    CompletionBettingOrRaisingTo,
    Folding,
    HoleDealing,
    RoyalRhodeIslandHoldem,
)
from pyscript import document, window
import requests

RAW_CARDS = {
    '??': '🂠',
    **{
        ''.join(key)[::-1]: value for key, value in zip(
            product('shdc', 'A23456789TJQK'),
            '🂡🂢🂣🂤🂥🂦🂧🂨🂩🂪🂫🂭🂮🂱🂲🂳🂴🂵🂶🂷🂸🂹🂺🂻🂽🂾🃁🃂🃃🃄🃅🃆🃇🃈🃉🃊🃋🃍🃎🃑🃒🃓🃔🃕🃖🃗🃘🃙🃚🃛🃝🃞',
        )
    },
}
STARTING_STACK = 155
DEAL_BUTTON = document.querySelector('#deal-button')
FOLD_BUTTON = document.querySelector('#fold-button')
CHECK_CALL_BUTTON = document.querySelector('#check-call-button')
BET_RAISE_BUTTON = document.querySelector('#bet-raise-button')
HERO_STACK = document.querySelector('#hero-stack')
VILLAIN_STACK = document.querySelector('#villain-stack')
HERO_HOLE_CARD = document.querySelector('#hero-hole-card')
VILLAIN_HOLE_CARD = document.querySelector('#villain-hole-card')
HERO_BET = document.querySelector('#hero-bet')
VILLAIN_BET = document.querySelector('#villain-bet')
HERO_BUTTON = document.querySelector('#hero-button')
VILLAIN_BUTTON = document.querySelector('#villain-button')
FLOP_CARD = document.querySelector('#flop-card')
TURN_CARD = document.querySelector('#turn-card')
POT_AMOUNT = document.querySelector('#pot-amount')
HAND_NUMBER = document.querySelector('#hand-number')
PAYOFF_SUM = document.querySelector('#payoff-sum')
PAYOFF_RATE = document.querySelector('#payoff-rate')
LAST_ACTION = document.querySelector('#last-action')
QUERY_STRING = URLSearchParams.new(window.location.search)
BACKEND_HOST = QUERY_STRING.get('backend')

while not BACKEND_HOST:
    BACKEND_HOST = window.prompt(
        'Enter the backend host (e.g., "localhost:8000"):',
    )

BACKEND_ORIGIN = (
    BACKEND_HOST if '://' in BACKEND_HOST
    else f'{window.location.protocol}//{BACKEND_HOST}'
)
QUERY_URL = urljoin(
    BACKEND_ORIGIN,
    '/api/query/?effective_stack={}&infoset={}',
)
state = None
button = None
payoff_sum = 0
hand_count = 0


def query():
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
    hole_card = state.hole_cards[state.actor_index][0]
    flop_card = state.board_cards[0][0] if state.board_cards else None
    turn_card = state.board_cards[1][0] if len(state.board_cards) > 1 else None

    if flop_card is None:
        signal = hole_card.rank
    elif turn_card is None:
        signal = f'{hole_card.rank}{flop_card.rank}'

        if hole_card.suit == flop_card.suit:
            signal = f'({signal})'
    else:
        if hole_card.suit == flop_card.suit == turn_card.suit:
            signal = f'({hole_card.rank}{flop_card.rank}{turn_card.rank})'
        elif hole_card.suit == flop_card.suit:
            signal = f'({hole_card.rank}{flop_card.rank}){turn_card.rank}'
        elif hole_card.suit == turn_card.suit:
            signal = f'{hole_card.rank}){flop_card.rank}({turn_card.rank}'
        elif flop_card.suit == turn_card.suit:
            signal = f'{hole_card.rank}({flop_card.rank}{turn_card.rank})'
        else:
            signal = f'{hole_card.rank}{flop_card.rank}{turn_card.rank}'

    effective_stack = min(*state.starting_stacks, STARTING_STACK)
    infoset = f'{action};{signal}'
    url = QUERY_URL.format(effective_stack, infoset)
    response = requests.get(url)
    data = response.json()

    return data


def update(player=None, operation=None):
    DEAL_BUTTON.hidden = state is not None and state.status
    FOLD_BUTTON.hidden = state is None or not state.can_fold()
    CHECK_CALL_BUTTON.hidden = state is None or not state.can_check_or_call()

    if not CHECK_CALL_BUTTON.hidden:
        amount = state.checking_or_calling_amount
        CHECK_CALL_BUTTON.innerHTML = f'Call {amount}' if amount else 'Check'
    else:
        CHECK_CALL_BUTTON.innerHTML = ''

    BET_RAISE_BUTTON.hidden = (
        state is None
        or not state.can_complete_bet_or_raise_to()
    )

    if not BET_RAISE_BUTTON.hidden:
        amount = state.max_completion_betting_or_raising_to_amount
        BET_RAISE_BUTTON.innerHTML = (
            f'Raise to {amount}' if any(state.bets)
            else f'Bet {amount}'
        )
    else:
        BET_RAISE_BUTTON.innerHTML = ''

    if state is not None:
        HERO_STACK.innerHTML = state.stacks[button]
        VILLAIN_STACK.innerHTML = state.stacks[not button]
        raw_hole_card = ''.join(map(repr, state.hole_cards[button]))
        HERO_HOLE_CARD.innerHTML = RAW_CARDS.get(raw_hole_card, '')

        if state.status:
            VILLAIN_HOLE_CARD.innerHTML = RAW_CARDS['??']
        else:
            raw_hole_card = ''.join(
                map(repr, state.get_censored_hole_cards(not button)),
            )
            VILLAIN_HOLE_CARD.innerHTML = RAW_CARDS.get(raw_hole_card, '')

        HERO_BET.innerHTML = state.bets[button]
        VILLAIN_BET.innerHTML = state.bets[not button]
    else:
        HERO_STACK.innerHTML = ''
        VILLAIN_STACK.innerHTML = ''
        HERO_HOLE_CARD.innerHTML = ''
        VILLAIN_HOLE_CARD.innerHTML = ''
        HERO_BET.innerHTML = ''
        VILLAIN_BET.innerHTML = ''

    HERO_BUTTON.innerHTML = 'IP' if button else 'OOP'
    VILLAIN_BUTTON.innerHTML = 'OOP' if button else 'IP'

    if state is not None and state.board_cards:
        FLOP_CARD.innerHTML = RAW_CARDS[repr(state.board_cards[0][0])]
    else:
        FLOP_CARD.innerHTML = ''

    if state is not None and len(state.board_cards) > 1:
        TURN_CARD.innerHTML = RAW_CARDS[repr(state.board_cards[1][0])]
    else:
        TURN_CARD.innerHTML = ''

    POT_AMOUNT.innerHTML = '' if state is None else state.total_pot_amount
    HAND_NUMBER.innerHTML = hand_count + 1
    PAYOFF_SUM.innerHTML = payoff_sum
    PAYOFF_RATE.innerHTML = (
        f'{payoff_sum / hand_count:.1f}' if hand_count else 0.0
    )

    if isinstance(operation, Folding):
        label = 'fold'
    elif isinstance(operation, CheckingOrCalling):
        label = 'check/call'
    elif isinstance(operation, CompletionBettingOrRaisingTo):
        label = 'bet/raise'
    else:
        label = ''

    if player is True:
        label = f'You {label}.'
    elif player is False:
        label = f'AI {label}s.'

    LAST_ACTION.innerHTML = label

    if (
            state is not None
            and state.actor_index is not None
            and state.actor_index != button
    ):
        action_probabilities = query()
        actions = list(action_probabilities.keys())
        probabilities = list(action_probabilities.values())
        action = choices(actions, probabilities)[0]

        match action:
            case 'f':
                operation = state.fold()
            case 'c':
                operation = state.check_or_call()
            case 'r':
                operation = state.complete_bet_or_raise_to()
            case _:
                raise AssertionError

        update(False, operation)


def deal(event):
    global button, hand_count, payoff_sum, state

    if state is not None and state.status:
        return

    if state is not None:
        payoff_sum += state.payoffs[button]
        hand_count += 1

    if button is None:
        button = bool(randint(0, 1))
    else:
        button = not button

    if state is None:
        stacks = STARTING_STACK, STARTING_STACK
    else:
        stacks = list(state.stacks[::-1])

        if not stacks[0]:
            stacks[0] = STARTING_STACK

        if not stacks[1]:
            stacks[1] = STARTING_STACK

    state = RoyalRhodeIslandHoldem.create_state(
        automations=tuple(Automation),
        raw_starting_stacks=stacks,
    )

    update()


def fold(event):
    if state is None or state.actor_index != button or not state.can_fold():
        return

    update(True, state.fold())


def check_call(event):
    if (
            state is None
            or state.actor_index != button
            or not state.can_check_or_call()
    ):
        return

    update(True, state.check_or_call())


def bet_raise(event):
    if (
            state is None
            or state.actor_index != button
            or not state.can_complete_bet_or_raise_to()
    ):
        return

    update(True, state.complete_bet_or_raise_to())
