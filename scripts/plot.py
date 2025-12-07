from math import ceil, floor, log10
from sys import argv

from matplotlib import cm
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

SOLUTION_PATHNAME = argv[1]
PLOT_PATHNAME = argv[2]
PLOT2_PATHNAME = argv[3]
EFFECTIVE_STACKS = range(6, 155 + 1)
ITERATIONS = range(1, 1024 + 1)


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


def plot(exploitabilities):
    plt.clf()

    X = ITERATIONS
    Y = EFFECTIVE_STACKS
    Y_size = len(Y)
    X, Y = np.meshgrid(X, Y)
    Z = exploitabilities
    indices = ~np.isnan(Z)
    X = X[indices].reshape(Y_size, -1)
    Y = Y[indices].reshape(Y_size, -1)
    Z = Z[indices].reshape(Y_size, -1)

    plt.style.use('_mpl-gallery')

    fig = plt.figure(figsize=(8, 8))
    ax = fig.subplots(subplot_kw={'projection': '3d'})

    ax.plot_surface(
        np.log10(X),
        Y,
        np.log10(Z),
        cmap=cm.seismic,
        antialiased=False,
    )

    xticks, xticklabels = ticks(*ax.get_xlim())
    zticks, zticklabels = ticks(*ax.get_zlim())

    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Effective stack')
    ax.set_zticks(zticks)
    ax.set_zticklabels(zticklabels)
    ax.set_zlabel('Exploitability')
    ax.set_title('Exploitabilities of CFR+ in self-play', y=1.025)
    ax.set_box_aspect(None, zoom=0.95)
    fig.savefig(PLOT_PATHNAME, bbox_inches='tight')


def plot2(exploitabilities, values):
    plt.clf()
    sns.set_theme()

    data = {
        'Effective stack': EFFECTIVE_STACKS,
        'Exploitability': exploitabilities[:, -1],
        'Game value': values[:, -1],
    }
    df = pd.DataFrame(data)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    sns.lineplot(df, x='Effective stack', y='Exploitability', ax=axes[0])
    axes[0].set_yscale('log')
    axes[0].set_title('Final exploitabilities')
    sns.lineplot(df, x='Effective stack', y='Game value', ax=axes[1])
    axes[1].set_title('Final game values')
    fig.tight_layout()
    fig.savefig(PLOT2_PATHNAME)


def main():
    exploitabilities = []
    values = []

    for effective_stack in tqdm(EFFECTIVE_STACKS):
        solution = np.load(SOLUTION_PATHNAME.format(effective_stack))

        exploitabilities.append(solution['exploitabilities'])
        values.append(solution['values'])

    exploitabilities = np.array(exploitabilities)
    values = np.array(values)

    plot(exploitabilities)
    plot2(exploitabilities, values)


if __name__ == '__main__':
    main()
