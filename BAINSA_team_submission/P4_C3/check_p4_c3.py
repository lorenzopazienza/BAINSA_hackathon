"""Sanity checks for Problem 4, Cell 3 (k = 5..8).  NOT part of the proof.

For each k we build the graph whose vertices are classes (m, a), 0 <= a < m <= M,
with an edge when the two classes are disjoint and gcd(m, m') < k.
Disjointness is checked LITERALLY from the definition, never via the criterion
gcd | a - b: a mod m and b mod n meet iff b - a = m t (mod n) for some t, and the
set {m t mod n : 0 <= t < n} is listed explicitly.  A counterexample to the k-case would be a k-clique.  We compute
the maximum clique size with a branch-and-bound (greedy colouring bound) and
check it equals k - 1.  No reduction from the proof is used.
"""
import sys
import time
from math import gcd


def disjoint_literal(m, a, n, b):
    return all((a + m * t - b) % n for t in range(n // gcd(m, n)))


def build(k, M):
    V = [(m, a) for m in range(2, M + 1) for a in range(m)]
    meet = {}
    for m in range(2, M + 1):
        for n in range(2, M + 1):
            hit = [False] * n
            for t in range(n):
                hit[(m * t) % n] = True
            meet[m, n] = hit
    adj = [0] * len(V)
    for i, (m, a) in enumerate(V):
        for j in range(i + 1, len(V)):
            n, b = V[j]
            g = gcd(m, n)
            if 2 <= g < k and not meet[m, n][(b - a) % n]:
                adj[i] |= 1 << j
                adj[j] |= 1 << i
    return V, adj


def max_clique(adj, n, target):
    """Largest clique size, stopping early once `target` is reached."""
    best = [0, []]
    nodes = [0]

    def colour_sort(P):
        # greedy colouring; returns vertices with colour bounds, ascending
        order, bounds = [], []
        col = 0
        Q = P
        while Q:
            col += 1
            R = Q
            while R:
                v = (R & -R).bit_length() - 1
                R &= ~adj[v] & ~(1 << v)
                Q &= ~(1 << v)
                order.append(v)
                bounds.append(col)
        return order, bounds

    def expand(C, P):
        nodes[0] += 1
        order, bounds = colour_sort(P)
        for v, b in zip(reversed(order), reversed(bounds)):
            if len(C) + b <= best[0] or best[0] >= target:
                return
            C2 = C + [v]
            P2 = P & adj[v]
            if P2:
                expand(C2, P2)
            elif len(C2) > best[0]:
                best[0], best[1] = len(C2), C2
            P &= ~(1 << v)

    expand([], (1 << n) - 1)
    return best[0], best[1], nodes[0]


if __name__ == "__main__":
    plan = [(5, 60), (6, 60), (7, 36), (8, 30)] if len(sys.argv) < 2 else \
        [tuple(map(int, s.split(":"))) for s in sys.argv[1:]]
    for k, M in plan:
        t = time.time()
        V, adj = build(k, M)
        size, clique, nodes = max_clique(adj, len(V), k)
        print(f"k={k}, moduli<={M}: {len(V)} classes, max clique = {size} "
              f"(example {[V[i] for i in clique]}), {nodes} nodes, "
              f"{time.time() - t:.1f}s", flush=True)
        assert size == k - 1, "counterexample found!" if size >= k else "unexpected"
    print("all OK")
