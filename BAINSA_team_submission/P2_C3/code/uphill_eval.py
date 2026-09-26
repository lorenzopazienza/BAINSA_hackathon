"""Exact evaluator for Problem 2 (uphill paths on the hypercube).

Usage:  python uphill_eval.py FILE [FILE ...]
        python uphill_eval.py --brute 3      (minimum over all labellings of Q_3)
FILE lists the 2^d vertices of Q_d in increasing label order, as 0/1 strings
(whitespace or commas as separators).  The script checks that the list is a
permutation of {0,1}^d and prints the number of uphill paths.

Counting rule (from the definition): let N(v) be the number of uphill paths
that END at v.  A path ending at v is either (v) itself, when v is a valley,
or an uphill path ending at a lower neighbour w of v, extended by v.  Hence
    N(v) = 1                            if v is a valley,
    N(v) = sum of N(w), w ~ v, f(w) < f(v)   otherwise,
and the total is sum_v N(v).  Processing vertices in label order computes
every N(v) after the N(w) it needs.  Python integers are exact.
"""
import re
import sys


def read_labelling(text):
    words = [w for w in re.split(r"[\s,;]+", text.strip()) if w]
    if not words:
        raise ValueError("empty labelling")
    d = len(words[0])
    if len(words) != 1 << d:
        raise ValueError(f"{len(words)} strings, expected 2^{d} = {1 << d}")
    if any(len(w) != d or set(w) - {"0", "1"} for w in words):
        raise ValueError("every entry must be a 0/1 string of the same length")
    if len(set(words)) != len(words):
        raise ValueError("repeated vertex")
    return d, [int(w, 2) for w in words]


def count_uphill(d, order):
    """Number of uphill paths of Q_d for the labelling f(order[i]) = i+1."""
    pos = {v: i for i, v in enumerate(order)}
    N = {}
    for v in order:
        lower = [v ^ (1 << i) for i in range(d) if pos[v ^ (1 << i)] < pos[v]]
        N[v] = sum(N[w] for w in lower) if lower else 1
    return sum(N.values())


def brute_force(d):
    """Minimum of count_uphill over all (2^d)! labellings; feasible for d <= 3."""
    from itertools import permutations
    return min(count_uphill(d, p) for p in permutations(range(1 << d)))


def main(paths):
    if paths[:1] == ["--brute"]:
        d = int(paths[1])
        print(f"minimum over all labellings of Q_{d}: {brute_force(d)}")
        return
    for p in paths:
        with open(p) as fh:
            d, order = read_labelling(fh.read())
        print(f"{p}: d = {d}, uphill paths = {count_uphill(d, order)}")


if __name__ == "__main__":
    main(sys.argv[1:])
