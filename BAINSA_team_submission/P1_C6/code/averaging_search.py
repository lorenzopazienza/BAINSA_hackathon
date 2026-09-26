"""Problem 1, Cell 6: which pairs (N,d) does subset averaging settle?

Proved cases used as sources (lines in R^d): N <= d (M = 0), N = d+1 (C3, M = 1),
N = d+2 (C5, M = 2), all N when d = 2 (C1), and (6,3) (Cell 6, Thm 1).
Averaging an n-line bound A >= M(n,d)*pi/2 over all n-subsets of N lines gives
    A >= N(N-1) / (n(n-1)) * M(n,d) * pi/2          (each pair lies in C(N-2,n-2) subsets).
The script lists every (N,d) with 3 <= d <= DMAX, d+3 <= N <= NMAX for which some
source gives at least M(N,d); the answer is exactly [(6, 3)] (Proposition 2).
Exact rational arithmetic.  Runs in a few seconds.
"""
from fractions import Fraction
from math import comb

DMAX, NMAX = 60, 400


def M(N, d):
    q, s = divmod(N, d)
    return s * comb(q + 1, 2) + (d - s) * comb(q, 2)


hits = []
for d in range(3, DMAX + 1):
    sources = {n: M(n, d) for n in range(2, d + 3)}
    if d == 3:
        sources[6] = M(6, 3)                      # Theorem 1 of the cell
    for N in range(d + 3, NMAX + 1):
        best = max(Fraction(N * (N - 1), n * (n - 1)) * m for n, m in sources.items() if n <= N)
        if best >= M(N, d):
            hits.append((N, d))
print("pairs settled by averaging with d >= 3, N >= d+3:", hits)
assert hits == [(6, 3)]
