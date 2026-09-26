#!/usr/bin/env python3
"""Exhaustive small cases used in p3_c2/p3_c3/p3_c4/p3_c5.
Straight from the definitions: B(lambda), d_B(lambda) = number of steps before the
first partition that recurs in the orbit, D_B(n) = max over all partitions of n.
Runtime: well under one second."""


def partitions(n, maxp=None):
    maxp = n if maxp is None else maxp
    if n == 0:
        yield ()
        return
    for p in range(min(n, maxp), 0, -1):
        for rest in partitions(n - p, p):
            yield (p,) + rest


def B(lam):
    return tuple(sorted([len(lam)] + [x - 1 for x in lam if x > 1], reverse=True))


def d_B(lam):
    first = {}
    i = 0
    while lam not in first:
        first[lam] = i
        lam = B(lam)
        i += 1
    return first[lam]  # the tail length: B^i(lam) is cyclic iff i >= this


def fmt(lam):
    # compact notation: (3,3,2,1) -> 3^2 2 1
    out = []
    for v in sorted(set(lam), reverse=True):
        m = lam.count(v)
        out.append(f"{v}^{m}" if m > 1 else f"{v}")
    return "(" + " ".join(out) + ")"


for n in [1, 3, 4, 5, 6, 7, 8, 9, 12, 17]:
    parts = list(partitions(n))
    d = {lam: d_B(lam) for lam in parts}
    D = max(d.values())
    ext = [lam for lam in parts if d[lam] == D]
    print(f"n={n}: {len(parts)} partitions, D_B={D}, extremal: {', '.join(fmt(l) for l in ext)}")
