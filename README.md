# r3i-holdem

This repository contains code for "Repeated Poker and the Independent Chip Model".

# Instructions

Create the game.

```console
for i in {6..155}; do
    python scripts/game.py "$i" > "games/$i.json"
done
```

Solve the game.

```console
for i in {6..155}; do
    python scripts/solve.py < "games/$i.json" > "solutions/$i.npz"
done
```

Plot the exploitabilities and game values.

```console
python scripts/plot.py "solutions/{}.npz" figures/plot.pdf figures/plot2.pdf
```

Calculate the (abstracted) game size.

```console
python scripts/size.py > data/size.npy
python scripts/size2.py > data/size2.npy
```

Get strategy.

```console
python scripts/strategies.py "solutions/{}.npz" > data/strategies.pkl
```

Get transitions.

```console
python scripts/transitions.py < data/strategies.pkl > data/transitions.pkl
python scripts/transitions2.py < data/transitions.pkl > data/transitions2.pkl
```

Model as absorbing Markov chains.

```console
python scripts/markov.py 10 30 50 70 110 150 190 230 270 310 620 1550 7750 < data/transitions2.pkl > data/markov.pkl
```

Plot absorbing markov chain results and the ICM.

```console
python scripts/plot3.py figures/plot3.pdf figures/plot4.pdf 10 30 50 70 190 310 1550 7750 < data/markov.pkl
```
