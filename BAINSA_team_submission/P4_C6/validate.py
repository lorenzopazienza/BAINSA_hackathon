"""Self-review: for sampled Case II placements, the exact weighted code optimum
(max clique, (2,3,5) weighted 11) must NOT exceed min(B1,B2) from check_p4_c6.py.
The code optimum is an upper bound on |O| derived only from Lemma 5 (agreement)
and Lemma 8, so a violation would reveal an error in Lemmas 9-10 or the script."""
import random, sys
from itertools import product
from exact_code import exact_bound
from check_p4_c6 import primes_below
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
k = int(sys.argv[1]); p = k - 1
Q = primes_below(p); others = [q for q in Q if q >= 5]
def hand(P):
    a, b, c = len(P[1]), len(P[2]), len(P[3])
    eps = 10 if 5 in P[3] else 0
    Lam = [(y, x) for y in P[2] for x in P[3] if y * x <= p]
    B1 = b * c + len(Lam) * (a - 1) + eps
    s2 = sum(1 for y in P[2] if 2 * y <= p); s3 = sum(1 for x in P[3] if 2 * x <= p)
    T = min(b * c, s2 * s3 + (b - s2) + (c - s3)) + eps
    L1 = [(q, x) for q in P[1] if q != 2 for x in P[3] if q * x <= p]
    return min(B1, T + (a - 1) * c + len(L1) * (b - 1))
worst_gap, n, maxex = None, 0, 0
N = int(sys.argv[3]) if len(sys.argv) > 3 else 300
while n < N:
    dist = [random.randrange(4) for _ in others]
    P = {1: [2], 2: [3], 3: []}
    for q, j in zip(others, dist):
        if j: P[j].append(q)
    if not P[3] or len(P[1]) * len(P[2]) * len(P[3]) > 80: continue
    n += 1
    Mw = {frozenset(): 0, frozenset([5]): 11}
    ex = exact_bound(P[1], P[2], P[3], p, Mw)
    h = hand(P)
    maxex = max(maxex, ex)
    assert ex <= h, (P, ex, h)
    gap = h - ex
    if worst_gap is None or gap < worst_gap[0]: worst_gap = (gap, P, ex, h)
print(f"k={k}: {n} placements, exact <= hand everywhere; max exact {maxex} (< {k-3}); tightest {worst_gap}")
