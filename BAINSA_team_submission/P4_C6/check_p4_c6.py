"""Companion script for p4_c6.tex: checks every counting inequality exactly.

Usage:  python3 check_p4_c6.py 32 38 42 44
(for k = 44, 48 only Case I / s >= 4 here; Case II is in sat_residual.py)

For k with p = k-1 prime, 31 <= p <= 47, the proof of Theorem 1 bounds |O| = k - s
by explicit integer expressions that depend only on how the primes < p are
distributed over the blocks P_1, ..., P_s.  This script evaluates those expressions
(integers only) over EVERY admissible distribution and checks bound < k - s.
Section references are to p4_c6.tex.

  s >= 4     : Lemma 7   bound  a*b            (a + b <= r - (s-2))
               s = 4 also a*b - 1 + c          (a + b + c <= r - 1), when 35 <= p
  s = 3, (a) : Lemma 7   bound  a*b + (c - 1)  (a + b + c <= r) [c-1 only if 35 <= p]
  s = 3, (b) : Lemmas 9-10, bound min(B1, B2) where
      B1 = b*c + |Lambda|*(a-1) + eps
      B2 = min(b*c, sig2*sig3 + beta2 + beta3) + eps + (a-1)*c + |Lambda'|*(b-1)
      eps = M5 - 1 = 10 if 5 in P3, else 0            (Lemma 8, valid for p < 42)
"""
import sys
from itertools import product


def primes_below(n):
    return [q for q in range(2, n) if all(q % d for d in range(2, int(q ** .5) + 1))]


def check(k, verbose=True):
    p = k - 1
    assert p in primes_below(p + 1), "k-1 must be prime"
    assert 31 <= p <= 47, "the light-set facts (Lemma 4) are only claimed for 31 <= p <= 47"
    Q = primes_below(p)
    r = len(Q)
    # --- the arithmetic facts of Lemma 4, checked rather than assumed ------------
    odd5 = [q for q in Q if q >= 5]
    light_pairs_ge5 = {(x, y) for x in odd5 for y in odd5 if x < y and x * y <= p}
    assert light_pairs_ge5 <= {(5, 7)}
    light_triples = {(x, y, z) for x in Q for y in Q for z in Q if x < y < z and x * y * z <= p}
    assert light_triples == ({(2, 3, 5)} if p < 42 else {(2, 3, 5), (2, 3, 7)})
    assert 2 * 3 * 5 * 7 > p and 60 > p          # no light 4-set; 30 | g <= p  =>  g = 30
    ok = True
    report = []

    # ---- s >= 4 -------------------------------------------------------------
    for s in range(4, r + 1):
        t = r - (s - 2)
        best = max(a * (t - a) for a in range(1, t))
        if s == 4 and 35 <= p:
            best = max([best] + [a * b - 1 + c for a in range(1, r) for b in range(1, r)
                                 for c in range(1, r) if a + b + c <= r - 1])
        report.append((f"s={s}", best, k - s))

    # ---- s = 3, case (a) ----------------------------------------------------
    best = max(a * b + ((c - 1) if 35 <= p else 0)
               for a in range(1, r) for b in range(1, r) for c in range(1, r) if a + b + c <= r)
    report.append(("s=3 (a)", best, k - 3))

    # ---- s = 3, case (b): 2 in P1, 3 in P2 -----------------------------------
    if p >= 42:     # Case II for k = 44, 48 is checked by sat_residual.py
        return finish(k, ok, report, None, verbose)
    # Every prime q >= 5 goes to P1, P2, P3 or nowhere (0): 4^(r-2) distributions,
    # enumerated literally (no grouping).
    others = [q for q in Q if q >= 5]
    best, arg, n = -1, None, 0
    for dist in product(range(4), repeat=len(others)):
        P = {1: [2], 2: [3], 3: []}
        for q, j in zip(others, dist):
            if j:
                P[j].append(q)
        a, b, c = len(P[1]), len(P[2]), len(P[3])
        if c == 0:
            continue
        n += 1
        eps = 10 if 5 in P[3] else 0
        Lam = [(y, x) for y in P[2] for x in P[3] if y * x <= p]
        B1 = b * c + len(Lam) * (a - 1) + eps
        sig2 = sum(1 for y in P[2] if 2 * y <= p)
        sig3 = sum(1 for x in P[3] if 2 * x <= p)
        T = min(b * c, sig2 * sig3 + (b - sig2) + (c - sig3)) + eps
        Lam1 = [(q, x) for q in P[1] if q != 2 for x in P[3] if q * x <= p]
        U = (a - 1) * c + len(Lam1) * (b - 1)
        B2 = T + U
        bd = min(B1, B2)
        if bd > best:
            best, arg = bd, (P[1], P[2], P[3], B1, B2)
    report.append((f"s=3 (b) [{n} distributions]", best, k - 3))

    return finish(k, ok, report, arg, verbose)


def finish(k, ok, report, arg, verbose):
    for name, bd, need in report:
        good = bd < need
        ok &= good
        if verbose:
            print(f"k={k}  {name:32s} max bound {bd:3d}  <  k-s = {need:3d} ? {'yes' if good else 'NO'}")
    if verbose and arg:
        print(f"k={k}  worst distribution in case (b): P1={arg[0]} P2={arg[1]} P3={arg[2]} B1={arg[3]} B2={arg[4]}")
    if verbose:
        what = 'ALL INEQUALITIES HOLD' if arg else 'CASE I AND s>=4 INEQUALITIES HOLD (Case II: sat_residual.py)'
        print(f"k={k}  {what if ok else 'FAILED'}\n")
    return ok


if __name__ == '__main__':
    ks = [int(x) for x in sys.argv[1:]] or [32, 38, 42, 44]
    sys.exit(0 if all([check(k) for k in ks]) else 1)
