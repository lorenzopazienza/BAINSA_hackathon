#!/usr/bin/env python3
"""Exhaustive computation of D_B(n) for Problem 3, Cell 6.

Everything is computed straight from the definitions:

    B(lambda)  = the positive numbers among lambda_1-1, ..., lambda_s-1,
                 together with one extra part equal to s = #parts;
    lambda is cyclic  <=>  B^i(lambda) = lambda for some i >= 1;
    d_B(lambda) = min{ i >= 0 : B^i(lambda) is cyclic };
    D_B(n)      = max{ d_B(lambda) : lambda a partition of n }.

For each n we build the full functional graph of B on the p(n) partitions of n,
find the cyclic vertices as the vertices lying on a cycle of that graph (no use
of Brandt's theorem), and compute d_B as the distance to the cyclic set.  This
is the same computation as bs.py, but partitions are stored as their integer
rank instead of as tuples, which makes n >= 61 feasible in time and memory.

The ranking is the standard one: partitions of m with all parts <= M are listed
by decreasing first part, and P[m][M] = #{partitions of m with parts <= M} lets
one jump over a whole block in O(1), so ranking a partition costs O(#parts).

Output: one line per n with n, k, r, p(n), D_B(n), the value predicted by the
Griggs-Ho Conjecture 4.7 formula, and whether they agree; then a summary.

Usage:  python3 p3_c6_DB.py [NMAX] [BUDGET_SECONDS]
        defaults NMAX = 70, BUDGET = 540 (the run stops after the last n that
        finishes within the budget, so that the total stays under 10 minutes).
"""
import sys
import time
from array import array


# ----------------------------------------------------------------- basics

def T(m):
    return m * (m + 1) // 2


def rank_kr(n):
    """(k, r) with n = T_{k-1} + r and 1 <= r <= k."""
    k = 1
    while T(k) < n:
        k += 1
    return k, n - T(k - 1)


def gh_value(n):
    """The value predicted by Griggs-Ho Conjecture 4.7, i.e. the lower bound of
    their Theorem 4.5, for n >= 3.  With n = T_{k-1}+r, a = floor((k-1)/2),
    b = ceil((k-1)/2) = floor((k+1)/2):
        1 <= r < a       :  (k-3-r)k + r + 2
        r in {a, b}      :  n - k + 1
        b < r <= k       :  (r-2)k + r
    """
    k, r = rank_kr(n)
    a, b = (k - 1) // 2, (k + 1) // 2
    if 1 <= r < a:
        return (k - 3 - r) * k + r + 2
    if r == a or r == b:
        return n - k + 1
    return (r - 2) * k + r


# ------------------------------------------------- partitions by integer rank

def build_P(N):
    """P[m][j] = number of partitions of m into parts <= j, for m, j <= N."""
    P = [[1] * (N + 1) for _ in range(N + 1)]      # row m = 0 is all ones
    for m in range(1, N + 1):
        row, Pm = P[m], P[m]
        row[0] = 0
        for j in range(1, N + 1):
            row[j] = row[j - 1] + (P[m - j][j] if m >= j else 0)
    return P


def gen_partitions(n):
    """All partitions of n as descending lists, in the order used by rank()."""
    lam = []
    ap, pop = lam.append, lam.pop

    def rec(m, M):
        if m == 0:
            yield lam
            return
        for p in range(M if M < m else m, 0, -1):
            ap(p)
            yield from rec(m - p, p)
            pop()

    yield from rec(n, n)


def make_rank(n, P):
    Pn = P

    def rank(lam):
        idx = 0
        m = n
        M = n
        for x in lam:
            idx += Pn[m][M] - Pn[m][x]
            m -= x
            M = x
        return idx

    return rank


# ------------------------------------------------------- the graph of B on n

def analyse(n, P):
    """Return (p(n), D_B(n)) computed exhaustively."""
    Np = P[n][n]
    rank = make_rank(n, P)
    succ = array('i', bytes(4 * Np))

    i = 0
    for lam in gen_partitions(n):
        s = len(lam)
        b = [x - 1 for x in lam if x > 1]
        j = len(b)
        while j > 0 and b[j - 1] < s:
            j -= 1
        b.insert(j, s)
        succ[i] = rank(b)
        i += 1
    assert i == Np

    # vertices on a cycle get distance 0; everybody else distance to the cycle
    state = bytearray(Np)          # 0 = unseen, 1 = on current path, 2 = settled
    dist = array('i', bytes(4 * Np))
    for s0 in range(Np):
        if state[s0]:
            continue
        path = []
        v = s0
        while state[v] == 0:
            state[v] = 1
            path.append(v)
            v = succ[v]
        if state[v] == 1:                       # closed a new cycle through v
            w = v
            while True:
                dist[w] = 0
                state[w] = 2
                w = succ[w]
                if w == v:
                    break
        while path:
            u = path.pop()
            if state[u] == 2:
                continue
            dist[u] = dist[succ[u]] + 1
            state[u] = 2
    return Np, max(dist)


# ------------------------------------------- independent naive cross-check

def B_tuple(lam):
    return tuple(sorted([len(lam)] + [x - 1 for x in lam if x > 1], reverse=True))


def d_B_naive(lam):
    """d_B from the definition: iterate B until a partition repeats; the index
    of the first occurrence of the repeated partition is d_B."""
    first = {}
    i = 0
    while lam not in first:
        first[lam] = i
        lam = B_tuple(lam)
        i += 1
    return first[lam]


def D_B_naive(n):
    best = 0
    for lam in gen_partitions(n):
        d = d_B_naive(tuple(lam))
        if d > best:
            best = d
    return best


# ----------------------------------------------------------------- driver

def main():
    NMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 70
    BUDGET = float(sys.argv[2]) if len(sys.argv) > 2 else 540.0
    t0 = time.time()

    print("Exhaustive computation of D_B(n), straight from the definition.")
    print("n = T_{k-1} + r with 1 <= r <= k;  GH = value predicted by "
          "Griggs-Ho Conjecture 4.7.\n")
    print(f"{'n':>3} {'k':>3} {'r':>3} {'p(n)':>10} {'D_B(n)':>7} {'GH':>6} "
          f"{'agree':>6} {'secs':>8}")

    P = build_P(NMAX)
    values = {}
    disagree = []
    reached = 0
    for n in range(1, NMAX + 1):
        tn = time.time()
        Np, D = analyse(n, P)
        dt = time.time() - tn
        values[n] = D
        k, r = rank_kr(n)
        if n >= 3:
            g = gh_value(n)
            ok = (D == g)
            if not ok:
                disagree.append((n, k, r, D, g))
            gs, oks = str(g), ("yes" if ok else "*** NO ***")
        else:
            gs, oks = "-", "-"
        reached = n
        print(f"{n:>3} {k:>3} {r:>3} {Np:>10} {D:>7} {gs:>6} {oks:>6} {dt:>8.1f}",
              flush=True)
        # stop before starting an n that would push the run past the budget
        # (p(n+1)/p(n) <= 1.6 in this range, so 1.6*dt over-estimates the cost)
        if time.time() - t0 + 1.6 * dt > BUDGET:
            print(f"\n[budget of {BUDGET:.0f}s would be exceeded by n = {n+1}; "
                  f"stopping after n = {n}]")
            break
    t_exh = time.time() - t0
    print(f"\n[exhaustive part: {t_exh:.1f}s wall clock, n = 1..{reached}]")

    # independent check of the fast code against the naive definition
    tc = time.time()
    CROSS = 28
    bad = [n for n in range(1, min(CROSS, reached) + 1) if D_B_naive(n) != values[n]]
    print(f"[cross-check against the naive orbit-by-orbit computation, "
          f"n <= {min(CROSS, reached)}: "
          + ("all equal" if not bad else f"MISMATCH at {bad}")
          + f", {time.time() - tc:.1f}s]")

    print("\nComparison with Griggs-Ho Conjecture 4.7:")
    if disagree:
        print(f"  *** {len(disagree)} DISAGREEMENTS ***")
        for n, k, r, D, g in disagree:
            print(f"    n={n} (k={k}, r={r}): D_B={D} but the formula gives {g}")
    else:
        print(f"  no disagreement: D_B(n) equals the Conjecture 4.7 value for "
              f"every n with 3 <= n <= {reached}.")

    print("\nTable of D_B(T_{k-1}+r) by rows k, columns r = 1..k:")
    kmax = rank_kr(reached)[0]
    for k in range(1, kmax + 1):
        row = []
        for r in range(1, k + 1):
            n = T(k - 1) + r
            row.append(f"{values[n]:>4}" if n in values else "   .")
        print(f"  k={k:>2}: " + " ".join(row))

    print(f"\n[total {time.time() - t0:.1f}s]")


if __name__ == "__main__":
    main()
