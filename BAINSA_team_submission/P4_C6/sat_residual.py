"""k = 44, 48 (p = 43, 47), s = 3, Case II.  For every placement (grouped: primes
>= 17 with 2q <= p are interchangeable, as are primes with 2q > p) compute the hand
bounds B1, B2 (with eps from the p >= 42 multiplicity lemma).  For placements where
min(B1,B2) >= k-3, decide with a SAT solver whether a compatible weighted tuple
multiset of total size >= k-3 exists (the 'code' relaxation).  UNSAT => closed."""
import sys, time
from itertools import product
from math import prod
from pysat.solvers import Cadical153
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool

def primes_below(n):
    return [q for q in range(2, n) if all(q % d for d in range(2, int(q ** .5) + 1))]

def comps(n):
    for x1 in range(n + 1):
        for x2 in range(n + 1 - x1):
            for x3 in range(n + 1 - x1 - x2):
                yield (x1, x2, x3)

def eps_of(P3, p):
    T3 = [t for t in (5, 7) if t in P3 and 6 * t <= p]
    if T3 == [5]: return 10, {5: 11}, None
    if T3 == [7]: return 14, {7: 15}, None
    if T3 == [5, 7]: return 16, {5: 12, 7: 15}, 18
    return 0, {}, None

def hand(P1, P2, P3, p):
    a, b, c = len(P1), len(P2), len(P3)
    eps = eps_of(P3, p)[0]
    Lam = [(y, x) for y in P2 for x in P3 if y * x <= p]
    B1 = b * c + len(Lam) * (a - 1) + eps
    s2 = sum(1 for y in P2 if 2 * y <= p); s3 = sum(1 for x in P3 if 2 * x <= p)
    T = min(b * c, s2 * s3 + (b - s2) + (c - s3)) + eps
    L1 = [(q, x) for q in P1 if q != 2 for x in P3 if q * x <= p]
    return min(B1, T + (a - 1) * c + len(L1) * (b - 1))

def code_sat(P1, P2, P3, p, target):
    """True iff a compatible multiset of tuples of total size >= target exists."""
    tuples = list(product(P1, P2, P3))
    pool = IDPool()
    X = {t: pool.id(('x', t)) for t in tuples}
    cls = []
    for i in range(len(tuples)):
        for j in range(i + 1, len(tuples)):
            u, v = tuples[i], tuples[j]
            if prod(x for x, y in zip(u, v) if x == y) > p:
                cls.append([-X[u], -X[v]])
    _, Mmax, joint = eps_of(P3, p)
    count_lits = []
    copies_all = []
    for t in tuples:
        if t[0] == 2 and t[1] == 3 and t[2] in Mmax:
            cps = [pool.id(('c', t, i)) for i in range(Mmax[t[2]])]
            for cv in cps:
                cls.append([-cv, X[t]])          # copy -> tuple chosen
            count_lits += cps
            copies_all += cps
        else:
            count_lits.append(X[t])
    if joint is not None:
        enc = CardEnc.atmost(lits=copies_all, bound=joint, vpool=pool, encoding=EncType.seqcounter)
        cls += enc.clauses
    enc = CardEnc.atleast(lits=count_lits, bound=target, vpool=pool, encoding=EncType.seqcounter)
    cls += enc.clauses
    with Cadical153(bootstrap_with=cls) as s:
        return s.solve()

def run(k):
    p = k - 1
    Q = primes_below(p)
    special = [q for q in (5, 7, 11, 13)]
    H = [q for q in Q if q >= 17 and 2 * q <= p]
    B = [q for q in Q if 2 * q > p]
    assert sorted([2, 3] + special + H + B) == Q
    n = resid = sat = 0
    t0 = time.time()
    for sp in product(range(4), repeat=4):
        for h in comps(len(H)):
            for bb in comps(len(B)):
                P = {1: [2], 2: [3], 3: []}
                for q, j in zip(special, sp):
                    if j: P[j].append(q)
                Hs, Bs = list(H), list(B)
                for j in (1, 2, 3):
                    P[j] += [Hs.pop() for _ in range(h[j - 1])] + [Bs.pop() for _ in range(bb[j - 1])]
                if not P[3]: continue
                n += 1
                if hand(P[1], P[2], P[3], p) < k - 3: continue
                resid += 1
                if code_sat(P[1], P[2], P[3], p, k - 3):
                    sat += 1
                    print('  NOT CLOSED by code relaxation:', P, flush=True)
    print(f"k={k}: {n} grouped placements, {resid} residual after B1/B2, {sat} SAT; {time.time()-t0:.0f}s", flush=True)

if __name__ == '__main__':
    for k in map(int, sys.argv[1:]): run(k)
