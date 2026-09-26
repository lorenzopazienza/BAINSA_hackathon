"""Exact uphill-path counter for labellings of the hypercube Q_d.

A labelling is given as `order`: a list of the 2^d vertices (ints in [0, 2^d))
in increasing label order, i.e. order[k] is the vertex with label k.
Vertices u, v are adjacent iff u ^ v is a power of two.

An uphill path starts at a valley (a vertex with no lower neighbour) and
visits vertices with strictly increasing labels. A single valley counts.

This module is the single source of truth for scores.
"""
import random
import sys


def validate(order, d):
    """Raise ValueError unless `order` is a bijection onto {0,1}^d."""
    n = 1 << d
    if len(order) != n:
        raise ValueError(f"expected {n} vertices, got {len(order)}")
    if any(not isinstance(v, int) or isinstance(v, bool) for v in order):
        raise ValueError("vertices must be ints")
    if sorted(order) != list(range(n)):
        raise ValueError("labelling is not a bijection on {0,1}^%d" % d)


def count_uphill(order, d):
    """Exact number of uphill paths (Python ints, no overflow)."""
    validate(order, d)
    label = {v: k for k, v in enumerate(order)}
    N = {}
    for v in order:
        lower = [v ^ (1 << j) for j in range(d) if label[v ^ (1 << j)] < label[v]]
        N[v] = sum(N[u] for u in lower) if lower else 1
    return sum(N.values())


def count_uphill_bruteforce(order, d):
    """Independent check: enumerate every uphill path explicitly by DFS."""
    validate(order, d)
    label = {v: k for k, v in enumerate(order)}
    nbrs = {v: [v ^ (1 << j) for j in range(d)] for v in order}
    valleys = [v for v in order if all(label[u] > label[v] for u in nbrs[v])]
    count = 0
    stack = list(valleys)
    while stack:
        v = stack.pop()
        count += 1
        stack.extend(u for u in nbrs[v] if label[u] > label[v])
    return count


def to_strings(order, d):
    """Submission format: one d-bit 0/1 string per vertex, increasing label."""
    return [format(v, f"0{d}b") for v in order]


def from_strings(lines):
    """Inverse of to_strings. Returns (order, d)."""
    lines = [s.strip() for s in lines if s.strip()]
    d = len(lines[0])
    if any(len(s) != d or set(s) - {"0", "1"} for s in lines):
        raise ValueError("every line must be a 0/1 string of equal length")
    return [int(s, 2) for s in lines], d


def score_file(path):
    with open(path) as f:
        order, d = from_strings(f.readlines())
    return d, count_uphill(order, d)


def _self_test():
    rng = random.Random(0)
    # Path-graph sanity: labelling Q1 is a single edge -> |E|+1 = 2 paths.
    assert count_uphill([0, 1], 1) == 2
    # 4-cycle 0-1-3-2: paths 0, 0-1, 0-1-3, 0-1-3-2, 0-2.
    assert count_uphill([0, 1, 3, 2], 2) == 5
    # Weight order on Q6: N(v) = |v|!, so U = sum_k C(6,k) k! = 1957.
    assert count_uphill(sorted(range(64), key=lambda v: bin(v).count("1")), 6) == 1957
    for d in (2, 3, 4):
        for _ in range(300 if d < 4 else 100):
            order = list(range(1 << d))
            rng.shuffle(order)
            a, b = count_uphill(order, d), count_uphill_bruteforce(order, d)
            assert a == b, (d, order, a, b)
            assert a >= d * 2 ** (d - 1) + 1  # U >= |E| + 1
    for d in (5, 6):
        for _ in range(20):
            order = list(range(1 << d))
            rng.shuffle(order)
            assert count_uphill(order, d) == count_uphill_bruteforce(order, d)
    for bad in ([0, 1, 2, 2, 4, 5, 6, 7], [0, 1, 2, 3], list(range(7)) + [8]):
        try:
            validate(bad, 3)
            raise AssertionError(f"validator accepted {bad}")
        except ValueError:
            pass
    order = list(range(16))
    assert from_strings(to_strings(order, 4)) == (order, 4)
    print("evaluator self-test OK (DP == brute force on random labellings, d=2..6)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            d, u = score_file(p)
            print(f"{p}: d={d} uphill={u}")
    else:
        _self_test()
