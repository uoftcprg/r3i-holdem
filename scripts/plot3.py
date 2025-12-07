from functools import partial
from itertools import starmap
from math import ceil, floor, log10
from pickle import load
from sys import argv, stdin

from matplotlib import cm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PLOT_PATHNAME = argv[1]
PLOT2_PATHNAME = argv[2]
CHIP_COUNTS = tuple(map(int, argv[3:]))


def ticks(lo, hi):
    begin = floor(lo)
    end = ceil(hi)
    ticks = []
    ticklabels = []

    def update(i, j):
        tick = j * 10 ** i

        if lo <= log10(tick) <= hi:
            ticks.append(tick)
            ticklabels.append(f'1e{i}' if j == 1 else None)

    for i in range(begin, end + 1):
        for j in range(1, 10):
            update(i, j)

    return np.log10(ticks), ticklabels


def plot(chip_counts, chip_percentages, oop_winrates, ip_winrates):
    plt.style.use('_mpl-gallery')

    fig = plt.figure(figsize=(16, 8))

    X = chip_counts
    Y = np.linspace(0, 1)
    Z = np.array(
        list(
            starmap(
                partial(np.interp, Y),
                zip(chip_percentages, oop_winrates),
            ),
        ),
    ).T
    X, Y = np.meshgrid(X, Y)
    ax = fig.add_subplot(1, 2, 1, projection='3d')

    ax.plot_surface(np.log10(X), Y, Z, cmap=cm.seismic, antialiased=False)

    xticks, xticklabels = ticks(*ax.get_xlim())

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)
    ax.set_xlabel('Chips in play')
    ax.set_ylabel('Chip percentage (OOP)')
    ax.set_zlabel('Win rate (OOP)')
    ax.set_title('Approximated poker tournament win rates (OOP)', y=1.025)
    ax.set_box_aspect(None, zoom=0.95)

    X = chip_counts
    Y = np.linspace(0, 1)
    Z = np.array(
        list(
            starmap(partial(np.interp, Y), zip(chip_percentages, ip_winrates)),
        ),
    ).T
    X, Y = np.meshgrid(X, Y)
    ax = fig.add_subplot(1, 2, 2, projection='3d')

    ax.plot_surface(np.log10(X), Y, Z, cmap=cm.seismic, antialiased=False)

    xticks, xticklabels = ticks(*ax.get_xlim())

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)
    ax.set_xlabel('Chips in play')
    ax.set_ylabel('Chip percentage (IP)')
    ax.set_zlabel('Win rate (IP)')
    ax.set_title('Approximated poker tournament win rates (IP)', y=1.025)
    ax.set_box_aspect(None, zoom=0.95)

    fig.savefig(PLOT_PATHNAME, bbox_inches='tight')


def plot2(chip_counts, chip_percentages, oop_winrates, ip_winrates):
    data = {
        'Chip percentage': [],
        'Win rate (OOP)': [],
        'Win rate (IP)': [],
        'Model': [],
    }

    for chip_count in CHIP_COUNTS:
        (index,) = np.where(chip_counts == chip_count)
        index = index.item()

        data['Chip percentage'].extend(chip_percentages[index])
        data['Win rate (OOP)'].extend(oop_winrates[index])
        data['Win rate (IP)'].extend(ip_winrates[index])
        data['Model'].extend(
            [f'{chip_count} chips in play'] * (chip_count + 1),
        )

    df = pd.DataFrame(data)

    sns.set_theme()

    fig = plt.figure(figsize=(12, 5))
    ax = fig.add_subplot(1, 2, 1)

    sns.lineplot(
        df,
        x='Chip percentage',
        y='Win rate (OOP)',
        hue='Model',
        legend=False,
        size=1,
        ax=ax,
    )
    ax.set_xlabel('Chip percentage (OOP)')
    ax.set_title('Approximated win rates (OOP) of poker tournaments')

    ax = fig.add_subplot(1, 2, 2)

    sns.lineplot(
        df,
        x='Chip percentage',
        y='Win rate (IP)',
        hue='Model',
        size=1,
        ax=ax,
    )
    ax.set_xlabel('Chip percentage (IP)')
    ax.set_title('Approximated win rates (IP) of poker tournaments')
    sns.move_legend(ax, 'center left', bbox_to_anchor=(1, 0.5))

    fig.tight_layout()
    fig.savefig(PLOT2_PATHNAME)


def main():
    icmpp = load(stdin.buffer)
    chip_counts = np.array(sorted(icmpp))
    chip_percentages = [
        np.arange(chip_count + 1) / chip_count for chip_count in chip_counts
    ]
    winrates = list(map(np.array, map(icmpp.get, chip_counts)))
    oop_winrates = [rates[::2] for rates in winrates]
    ip_winrates = [rates[1::2] for rates in winrates]

    plot(chip_counts, chip_percentages, oop_winrates, ip_winrates)
    plot2(chip_counts, chip_percentages, oop_winrates, ip_winrates)


if __name__ == '__main__':
    main()
