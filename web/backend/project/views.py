from pickle import load

from django.conf import settings
from django.http import JsonResponse

with open(settings.STRATEGIES_FILEPATH, 'rb') as file:
    STRATEGIES = load(file)


def query_view(request):
    raw_effective_stack = request.GET.get('effective_stack', '')
    infoset = request.GET.get('infoset', '')

    if raw_effective_stack.isnumeric():
        effective_stack = int(raw_effective_stack)
    else:
        effective_stack = settings.DEFAULT_EFFECTIVE_STACK

    strategy = STRATEGIES.get(effective_stack, {})
    data = {}

    for action in 'fcr':
        key = infoset, action

        if key in strategy:
            data[action] = strategy[key]

    return JsonResponse(data)
