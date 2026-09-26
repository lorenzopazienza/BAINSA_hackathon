"""Exact code bound (max weighted clique) for s = 3, case (b) configurations.
A configuration is (P1, P2, P3) with 2 in P1, 3 in P2; grouped primes >= 17 are
replaced by representatives (interchangeable for the compatibility relation).
Nodes: tuples in P1 x P2 x P3.  Two tuples are compatible iff the product of the
coordinates on which they agree is <= p.  Tuples (2,3,t), t in T3, may repeat:
weights per Lemma M.  Returns an upper bound on |O|."""
from itertools import product
from math import prod

def max_clique(nodes, adj):
    best = [0]
    order = sorted(nodes, key=lambda v: bin(adj[v]).count('1'))
    def expand(R, P):
        if P == 0:
            if R > best[0]: best[0] = R
            return
        while P:
            if R + bin(P).count('1') <= best[0]: return
            v = P.bit_length() - 1
            expand(R + 1, P & adj[v])
            P &= ~(1 << v)
    mask = 0
    for v in nodes: mask |= 1 << v
    expand(0, mask)
    return best[0]

def exact_bound(P1, P2, P3, p, Mw):
    """Mw: dict frozenset(T3-subset) -> total multiplicity allowed for those tuples."""
    tuples = list(product(P1, P2, P3))
    n = len(tuples)
    adj = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            ag = [x for x, y in zip(tuples[i], tuples[j]) if x == y]
            if prod(ag) <= p:
                adj[i] |= 1 << j; adj[j] |= 1 << i
    special = {t[2]: idx for idx, t in enumerate(tuples) if t[0] == 2 and t[1] == 3 and 6 * t[2] <= p}
    others = [i for i in range(n) if i not in special.values()]
    best = 0
    T3 = list(special)
    from itertools import combinations
    for rsz in range(len(T3) + 1):
        for sub in combinations(T3, rsz):
            idxs = [special[t] for t in sub]
            # sub must be pairwise compatible
            if any(not (adj[a] >> b) & 1 for a in idxs for b in idxs if a != b):
                continue
            cand = [v for v in others if all((adj[v] >> a) & 1 for a in idxs)]
            w = Mw[frozenset(sub)]
            best = max(best, max_clique(cand, adj) + w)
    return best
