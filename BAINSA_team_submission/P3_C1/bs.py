#!/usr/bin/env python3
"""Brute force for Bulgarian solitaire.

For every n <= NMAX this computes, exhaustively over all partitions of n:
  * the B-cyclic partitions and the cycles of B,
  * d_B(lambda) for every lambda, D_B(n) = max d_B, and all extremal partitions.

Output: a table on stdout, the extremal partitions in bs_extremal.txt, and a list
of sanity checks (each prints OK or FAIL) for the claims used in p3_c1..p3_c4.

Usage:  python3 bs.py [NMAX]      (default NMAX = 60; about 1-2 minutes)

Conventions (Griggs-Ho): n = T_{k-1} + r with 1 <= r <= k, T_m = m(m+1)/2.
B(lambda): subtract 1 from every part, add a part equal to the number of parts,
discard zeros.  d_B(lambda) = least i >= 0 with B^i(lambda) cyclic.
"""
import sys
import time
from itertools import combinations
from math import comb, gcd


def T(m):
    return m * (m + 1) // 2


def rank(n):
    """Return (k, r) with n = T_{k-1} + r, 1 <= r <= k."""
    k = 1
    while T(k) < n:
        k += 1
    return k, n - T(k - 1)


def partitions(n):
    """All partitions of n as non-increasing tuples."""
    out = []
    a = [0] * (n + 1)

    def rec(rem, maxp, length):
        if rem == 0:
            out.append(tuple(a[:length]))
            return
        for p in range(min(rem, maxp), 0, -1):
            a[length] = p
            rec(rem - p, p, length + 1)

    rec(n, n, 0)
    return out


def B(lam):
    s = len(lam)
    parts = [x - 1 for x in lam if x > 1]
    parts.append(s)
    parts.sort(reverse=True)
    return tuple(parts)


def d_B_single(lam, cyclic=None):
    """d_B of one partition, straight from the definition: iterate B until a
    partition repeats; the index of its first occurrence is the tail length
    d_B.  (The argument `cyclic` is ignored; it is kept for readability.)"""
    first = {}
    i = 0
    while lam not in first:
        first[lam] = i
        lam = B(lam)
        i += 1
    return first[lam]


def c_sequence(lam, length):
    """<c_1, c_2, ...>: c_i = number of parts of B^{i-1}(lam)."""
    seq = []
    for _ in range(length):
        seq.append(len(lam))
        lam = B(lam)
    return seq


def analyse(n):
    """Exhaustive analysis of the functional graph of B on partitions of n."""
    parts = partitions(n)
    index = {p: i for i, p in enumerate(parts)}
    N = len(parts)
    succ = [index[B(p)] for p in parts]

    # find cyclic nodes: colour 0 = new, 1 = on current path, 2 = done
    colour = [0] * N
    on_cycle = [False] * N
    for s0 in range(N):
        if colour[s0]:
            continue
        path = []
        v = s0
        while colour[v] == 0:
            colour[v] = 1
            path.append(v)
            v = succ[v]
        if colour[v] == 1:  # closed a new cycle, v is on it
            w = v
            while True:
                on_cycle[w] = True
                w = succ[w]
                if w == v:
                    break
        for u in path:
            colour[u] = 2

    # distances to the cycle set
    dist = [-1] * N
    for v in range(N):
        if on_cycle[v]:
            dist[v] = 0
    for s0 in range(N):
        if dist[s0] >= 0:
            continue
        path = []
        v = s0
        while dist[v] < 0:
            path.append(v)
            v = succ[v]
        d = dist[v]
        for u in reversed(path):
            d += 1
            dist[u] = d

    D = max(dist)
    extremal = [parts[i] for i in range(N) if dist[i] == D]
    cyclic = [parts[i] for i in range(N) if on_cycle[i]]

    # cycles and their lengths
    seen = set()
    cycle_lengths = []
    for i in range(N):
        if on_cycle[i] and i not in seen:
            L = 0
            w = i
            while True:
                seen.add(w)
                L += 1
                w = succ[w]
                if w == i:
                    break
            cycle_lengths.append(L)
    return dict(N=N, D=D, extremal=extremal, cyclic=cyclic,
                cycle_lengths=sorted(cycle_lengths))


# ---------------------------------------------------------------- formulas

def brandt_cyclic(n):
    """Brandt's list: (k-1+e_{k-1}, ..., 1+e_1, e_0), e_i in {0,1}, sum e_i = r."""
    k, r = rank(n)
    res = set()
    for ones in combinations(range(k), r):
        e = [1 if i in ones else 0 for i in range(k)]  # e[i] = e_i
        lam = tuple(x for x in (i + e[i] for i in range(k - 1, -1, -1)) if x > 0)
        res.add(lam)
    return res


def phi(m):
    return sum(1 for a in range(1, m + 1) if gcd(a, m) == 1)


def necklaces(k, r):
    g = gcd(k, r)
    return sum(phi(d) * comb(k // d, r // d) for d in range(1, g + 1) if g % d == 0) // k


def gh_lower_bound(n):
    """Griggs-Ho Theorem 4.5 lower bound (n >= 3)."""
    k, r = rank(n)
    a, b = (k - 1) // 2, (k + 1) // 2
    if 1 <= r < a:
        return (k - 3 - r) * k + r + 2
    if r == a or r == b:
        return n - k + 1
    return (r - 2) * k + r


def witness_triangular(k):
    """C2: (k-1, k-1, k-2, ..., 2, 1, 1), a partition of T_k."""
    return tuple([k - 1] + [k - i + 1 for i in range(2, k + 1)] + [1])


def witness_Tk_minus_1(k):
    """C3: (k-1, k-2, k-2, k-3, ..., 2, 1, 1), a partition of T_k - 1."""
    return tuple([k - 1, k - 2] + [k - i + 1 for i in range(3, k + 1)] + [1])


def witness_case1(k, r):
    """Griggs-Ho Thm 4.5 case (1): lambda_1=k-2, lambda_i=k-i (2<=i<=k-r-1),
    lambda_i=k-i+1 (k-r<=i<=k); a partition of T_{k-1}+r."""
    lam = [k - 2] + [k - i for i in range(2, k - r)] + [k - i + 1 for i in range(k - r, k + 1)]
    return tuple(sorted((x for x in lam if x > 0), reverse=True))


# ---------------------------------------------------------------- checks

FAILS = []


def check(name, ok, detail=""):
    print(("  OK   " if ok else "  FAIL ") + name + ("" if ok else "   " + detail))
    if not ok:
        FAILS.append(name)


def ramps(seq):
    """All ramps (p, q, x) of a sequence (1-indexed):
    c_p = x-1, c_{p+1} = ... = c_{q-1} = x, c_q = x+1, q >= p+2."""
    out = []
    L = len(seq)
    for p in range(L - 2):
        x = seq[p] + 1
        q = p + 1
        if seq[q] != x:
            continue
        while q < L and seq[q] == x:
            q += 1
        if q < L and seq[q] == x + 1 and q - p >= 2:
            out.append((p + 1, q + 1, x))
    return out


def main():
    NMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    t0 = time.time()
    res = {}
    print(f"{'n':>3} {'k':>3} {'r':>3} {'p(n)':>8} {'D_B':>4} {'GH4.5':>5} {'#ext':>6} "
          f"{'#cyc':>4}  cycle lengths / sample extremal")
    with open("bs_extremal.txt", "w") as f:
        for n in range(1, NMAX + 1):
            a = analyse(n)
            res[n] = a
            k, r = rank(n)
            lb = gh_lower_bound(n) if n >= 3 else None
            ext = a["extremal"]
            f.write(f"n={n} k={k} r={r} D_B={a['D']} #extremal={len(ext)}\n")
            for lam in ext:
                f.write("  " + " ".join(map(str, lam)) + "\n")
            sample = str(ext[0]) if len(ext) == 1 else f"{ext[0]} ..."
            print(f"{n:>3} {k:>3} {r:>3} {a['N']:>8} {a['D']:>4} {str(lb):>5} {len(ext):>6} "
                  f"{len(a['cycle_lengths']):>4}  {sample}", flush=True)
    print(f"[exhaustive part: {time.time() - t0:.1f}s]\n")

    print("C1  cyclic partitions and cycles")
    ok1 = all(set(res[n]["cyclic"]) == brandt_cyclic(n) for n in res)
    check("cyclic set = Brandt form, all n <= NMAX", ok1)
    ok2 = all(len(res[n]["cycle_lengths"]) == necklaces(*rank(n)) for n in res)
    check("number of cycles = (1/k) sum phi(d) C(k/d,r/d)", ok2)
    ok3 = all(max(res[n]["cycle_lengths"]) <= rank(n)[0] and
              all(rank(n)[0] % L == 0 for L in res[n]["cycle_lengths"]) for n in res)
    check("every cycle length divides k", ok3)

    print("C2  triangular n = T_k")
    for k in range(1, 12):
        if T(k) > NMAX:
            break
        n = T(k)
        check(f"D_B(T_{k}) = {k*k-k}", res[n]["D"] == k * k - k, f"got {res[n]['D']}")
    for k in range(2, 80):
        w = witness_triangular(k)
        cyc = {tuple(range(k, 0, -1))}
        if sum(w) != T(k) or d_B_single(w, cyc) != k * k - k:
            check(f"witness C2 k={k}", False)
            break
    else:
        check("witness (k-1,k-1,k-2,...,1,1) has d_B = k^2-k, 2<=k<80", True)

    print("C3  non-triangular n, Theorem 4.4")
    bad = [n for n in res if rank(n)[1] < rank(n)[0] and rank(n)[0] >= 4
           and res[n]["D"] > rank(n)[0] ** 2 - 2 * rank(n)[0] - 1]
    check("D_B(n) <= k^2-2k-1 for all non-triangular n <= NMAX with k >= 4", not bad, str(bad))
    for k in range(4, 12):
        n = T(k) - 1
        if n > NMAX:
            break
        check(f"D_B(T_{k}-1) = {k*k-2*k-1}", res[n]["D"] == k * k - 2 * k - 1, f"got {res[n]['D']}")
    for k in range(3, 80):
        w = witness_Tk_minus_1(k)
        cyc = None
        want = k * k - 2 * k - 1 if k >= 3 else None
        if sum(w) != T(k) - 1 or d_B_single(w, cyc) != want:
            check(f"witness C3 k={k}", False, f"d={d_B_single(w, cyc)}")
            break
    else:
        check("witness (k-1,k-2,k-2,k-3,...,1,1) has d_B = k^2-2k-1, 3<=k<80", True)
    for k in range(4, 12):
        n = T(k) - 1
        if n > NMAX:
            break
        ext = res[n]["extremal"]
        print(f"       T_{k}-1 = {n}: {len(ext)} extremal partitions; witness among them: "
              f"{witness_Tk_minus_1(k) in ext}  (full list in bs_extremal.txt)")

    print("C4  n = T_{k-1}+1 and T_{k-1}+2")
    for k in range(5, 12):
        n = T(k - 1) + 1
        if n > NMAX:
            break
        check(f"D_B(T_{k-1}+1) = (k-1)(k-3) = {(k-1)*(k-3)}", res[n]["D"] == (k - 1) * (k - 3),
              f"got {res[n]['D']}")
    for k in range(5, 80):
        w = witness_case1(k, 1)
        n = T(k - 1) + 1
        if sum(w) != n or d_B_single(w) != (k - 1) * (k - 3):
            check(f"witness C4 k={k}", False, f"{w} d={d_B_single(w)}")
            break
    else:
        check("witness (k-2,k-2,k-3,...,3,2,2,1) has d_B = (k-1)(k-3), 5<=k<80", True)
    for k in range(2, 12):
        n = T(k - 1) + 2
        if n > NMAX:
            break
        want = {2: 2, 3: 3, 4: 5, 5: 8, 6: 12}.get(k, (k - 1) * (k - 4))
        check(f"D_B(T_{k-1}+2) = {want}", res[n]["D"] == want, f"got {res[n]['D']}")
    for k in range(5, 12):
        n = T(k - 1) + 1
        if n > NMAX:
            break
        ext = res[n]["extremal"]
        print(f"       T_{k-1}+1 = {n}: {len(ext)} extremal partitions; witness among them: "
              f"{witness_case1(k, 1) in ext}  (full list in bs_extremal.txt)")

    print("Characterisations of the extremal partitions (proved in p3_c2/p3_c3/p3_c4)")

    def chain(c, k, x, J):
        # ramps (j x, j x + j + 1, x) for j = 1..J; c is 1-indexed (c[0] unused)
        for j in range(1, J + 1):
            p = j * x
            if c[p] != x - 1 or c[p + j + 1] != x + 1 or any(c[i] != x for i in range(p + 1, p + j + 1)):
                return False
        return True

    for k in range(4, 12):
        for label, n, D, idx, test, J, x in [
                ("T_k", T(k), k * k - k, k * k - k - 1, lambda v, k=k: v >= k + 1, k - 2, k),
                ("T_k - 1", T(k) - 1, k * k - 2 * k - 1, k * k - 2 * k - 2, lambda v, k=k: v >= k + 1, k - 3, k),
                ("T_{k-1} + 1", T(k - 1) + 1, (k - 1) * (k - 3), (k - 1) * (k - 3), lambda v, k=k: v <= k - 2, k - 3, k - 1)]:
            if n > min(NMAX, 55) or (label == "T_k - 1" and k < 5) or (label == "T_{k-1} + 1" and k < 5):
                continue
            ext = set(res[n]["extremal"])
            by_c, by_chain = set(), set()
            for lam in partitions(n):
                c = [None] + c_sequence(lam, k * k + 2)
                if test(c[idx]):
                    by_c.add(lam)
                if chain(c, k, x, J):
                    by_chain.add(lam)
            check(f"n={n} ({label}, k={k}): extremal <=> c_{idx} test <=> ramp chain  [{len(ext)} extremal]",
                  ext == by_c and ext == by_chain,
                  f"|ext|={len(ext)} |by_c|={len(by_c)} |by_chain|={len(by_chain)}")

    print("C4 entry lemma (n = T_{k-1}+1): last non-cyclic partition has k-2 parts, entry at zeta_j, j != 2, k")

    def zeta(k, j):
        lam = [k - i + (1 if i == j else 0) for i in range(1, k + 1)]
        return tuple(x for x in lam if x > 0)

    for k in range(5, 10):
        n = T(k - 1) + 1
        if n > NMAX:
            break
        z = {zeta(k, j): j for j in range(1, k + 1)}
        ok = set(z) == set(res[n]["cyclic"])
        best = {}
        for lam in partitions(n):
            d = d_B_single(lam)
            if d == 0:
                continue
            mu = lam
            for _ in range(d - 1):
                mu = B(mu)
            j = z.get(B(mu))
            if j is None or j in (2, k) or len(mu) != k - 2:
                ok = False
                continue
            best[j] = max(best.get(j, 0), d)
        want = {j: ((k - j) * (k - 1) if j >= 3 else n + 1 - k) for j in [1] + list(range(3, k))}
        check(f"k={k}: entry lemma holds; max d_B per entry column = case bound (sharp)", ok and best == want,
              f"best={best} want={want}")

    print("C3 direct necessary condition: extremal partitions of T_k - 1 contain lo_k (conjugate (k+1,k-1,...))")
    for k in range(5, 11):
        n = T(k) - 1
        if n > NMAX:
            break
        ext = res[n]["extremal"]

        def conj(l):
            return [sum(1 for x in l if x >= i) for i in range(1, (l[0] if l else 0) + 1)]
        lo_c = [k + 3 - 2 * i for i in range(1, k + 2) if k + 3 - 2 * i > 0]
        hi_c = [2 * k - 1 - 2 * i for i in range(1, k + 1) if 2 * k - 1 - 2 * i > 0]
        ok = all(len(conj(l)) >= len(lo_c) and all(conj(l)[i] >= lo_c[i] for i in range(len(lo_c)))
                 and l[0] <= k + 1 for l in ext)
        between = [l for l in partitions(n)
                   if len(conj(l)) >= len(lo_c) and all(conj(l)[i] >= lo_c[i] for i in range(len(lo_c)))
                   and len(conj(l)) <= len(hi_c) and all(conj(l)[i] <= hi_c[i] for i in range(len(conj(l))))]
        check(f"k={k}: every extremal partition of {n} has conjugate >= {lo_c} and largest part <= k+1", ok)
        print(f"       observation: {len(between)} partitions lie between lo_k and hi_k "
              f"(conjugate {hi_c}); {len(ext)} are extremal; all extremal inside: {set(ext) <= set(between)}")

    print("C5 n = T_{k-1}+2: entry classification, per-type bounds, witness, characterisation")

    def zetaE(k, E):
        lam = [k - i + (1 if i in E else 0) for i in range(1, k + 1)]
        return tuple(x for x in lam if x > 0)

    def witness_c5(k):
        return tuple([k - 2] + [k - i for i in range(2, k - 2)] + [3, 2, 1])

    for k in range(5, 12):
        n = T(k - 1) + 2
        if n > NMAX:
            break
        parts = partitions(n)
        idx = {p: i for i, p in enumerate(parts)}
        N = len(parts)
        succ = [idx[B(p)] for p in parts]
        zs = {zetaE(k, set(E)): tuple(sorted(E)) for E in combinations(range(1, k + 1), 2)}
        ok = set(zs) == set(res[n]["cyclic"])
        cyc = [p in zs for p in parts]
        dist = [0 if cyc[v] else -1 for v in range(N)]
        entry = [-1] * N
        for s0 in range(N):
            if dist[s0] >= 0:
                continue
            path, v = [], s0
            while dist[v] < 0:
                path.append(v)
                v = succ[v]
            for u in reversed(path):
                dist[u] = dist[succ[u]] + 1
                entry[u] = u if cyc[succ[u]] else entry[succ[u]]
        D = max(dist)
        best = {}
        for v in range(N):
            d = dist[v]
            if d == 0:
                continue
            mu = parts[entry[v]]
            E = zs[B(mu)]
            s = len(mu)
            if k in E:
                ok = False
                continue
            if E == (1, 2):
                typ, bound = "E12", n - k + 1
                ok &= s == k - 1 and mu == tuple([k + 1] + list(range(k - 2, 0, -1)))
            else:
                ok &= s == k - 2
                ok &= not (2 in E and 1 not in E and 3 not in E)  # E = {2,b}, b >= 4, never an entry
                if E == (1, 3):
                    typ, bound = "E13", max(k - 1, k + 3, n - k + 1)
                    ok &= mu == tuple([k + 1, k - 1] + list(range(k - 3, 1, -1)))
                    if d >= 2:
                        c = c_sequence(parts[v], d + 1)
                        cd1 = c[d - 2]
                        ok &= cd1 in (k - 3, k - 1, k + 1)
                        sub = {k - 3: k - 1, k + 1: k + 3, k - 1: n - k + 1}[cd1] if cd1 in (k - 3, k - 1, k + 1) else -1
                        ok &= d <= sub
                elif E == (2, 3):
                    typ, bound = "E23", n - k + 2
                    ok &= mu == tuple([k, k] + list(range(k - 3, 1, -1)))
                else:
                    typ, bound = f"b={max(E)}", (k - max(E)) * (k - 1)
            ok &= d <= bound
            best[typ] = max(best.get(typ, 0), d)
        w = witness_c5(k)
        ok &= sum(w) == n and d_B_single(w) == (k - 1) * (k - 4)
        want = max((k - 1) * (k - 4), T(k - 2) + 2)
        check(f"k={k} (n={n}): entry lemma, per-type bounds, witness d_B={(k-1)*(k-4)}; D_B={D} = max((k-1)(k-4), T_(k-2)+2)",
              ok and D == want, f"D={D} best={best}")
        print(f"       max d per entry type: {dict(sorted(best.items()))}")
        if k >= 7:
            ext = [parts[v] for v in range(N) if dist[v] == D]
            by_c = {parts[v] for v in range(N) if c_sequence(parts[v], D)[D - 1] <= k - 2}
            x = k - 1
            chain_ok = True
            for lam in ext:
                c = [None] + c_sequence(lam, D + k + 2)
                for j in range(1, k - 3):
                    p = j * x
                    if c[p] != x - 1 or c[p + j + 1] != x + 1 or any(c[i] != x for i in range(p + 1, p + j + 1)):
                        chain_ok = False
            ent = {zs[B(parts[entry[v]])] for v in range(N) if dist[v] == D}
            check(f"k={k}: extremal <=> c_D <= k-2 [{len(ext)} extremal]; ramp chain holds; entry sets {sorted(ent)}",
                  set(ext) == by_c and chain_ok and all(max(E) == 4 for E in ent))
    for k in range(5, 80):
        w = witness_c5(k)
        if sum(w) != T(k - 1) + 2 or d_B_single(w) != (k - 1) * (k - 4):
            check(f"C5 witness k={k}", False)
            break
    else:
        check("C5 witness (k-2,k-2,k-3,...,4,3,3,2,1) has d_B = (k-1)(k-4), 5<=k<80", True)

    print("Conjecture 4.7 (GH lower bound = D_B)")
    bad = [n for n in res if n >= 3 and res[n]["D"] != gh_lower_bound(n)]
    check("D_B(n) = GH Theorem 4.5 value for 3 <= n <= NMAX", not bad, str(bad))

    print("Lemmas on the c-sequence (all partitions, n <= 30, first 4n terms)")
    ok_ramp, ok_34, ok_32 = True, True, True
    for n in range(1, 31):
        for lam in partitions(n):
            seq = c_sequence(lam, 4 * n + 10)
            for i in range(len(seq) - 1):
                if seq[i + 1] > seq[i] + 1:
                    ok_32 = False
            for (p, q, x) in ramps(seq):
                if p > (q - p - 1) * x:
                    ok_ramp = False
                if q - p == x + 1 and x >= 2 and q > n + 1:
                    ok_34 = False
    check("c_{i+1} <= c_i + 1", ok_32)
    check("ramp lemma: every ramp (p,q,x) has p <= (q-p-1) x", ok_ramp)
    check("Lemma 3.4: ramp with q-p = x+1 (x>=2) has q <= n+1", ok_34)

    print(f"\n[total {time.time() - t0:.1f}s]  " + ("ALL CHECKS PASSED" if not FAILS else f"FAILED: {FAILS}"))


if __name__ == "__main__":
    main()
