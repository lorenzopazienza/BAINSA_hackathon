"""Search for independent decycling sets I of Q_d (forest-form labellings).

Reformulation. If I is independent and G[V minus I] is a forest with c trees, labelling each
tree outward from its root (its valley) and then I on top gives U = |E| + c (see analyze.py),
and counting edges gives c = (d-1)|I| - (d-2)2^(d-1). For d = 9: U = 2304 + 8|I| - 1792 =
512 + 8|I|, a multiple of 8: |I| = 236 -> 2400 (current best), |I| = 235 -> 2392.

Our optima for d = 3..8 have |I| = 3, 6, 14, 28, 56, 112. These look like the decycling
numbers of Q_d (minimum vertex sets whose removal leaves Q_d acyclic; independence not
required) -- to be checked against the literature. An independent decycling set is a
decycling set, so |I| >= decycling number of Q_9: a known lower bound of 236 for Q_9
would close the forest-form route to 2392.

Methods (each exits after writing a verified solution, so a watcher notices immediately):
  ls   simulated annealing over sets I of fixed size k with swap moves (1 out / 1 in) and
       tabu; cost = #cycle-closing edges of G[V minus I] (union-find) + lam * #edges inside I.
       Starts from the peak set of the stored best labelling; first tries plain removals
       (drop v from I if G[V minus I] stays acyclic).
  sat  python-sat: x_v <=> v in I, independence clauses, |I| <= k (cardinality encoding),
       all 4-cycle clauses, symmetry breaking (proved below), and lazy cycle cuts: solve,
       find cycles in G[V minus I], add "some vertex of this cycle is in I", repeat.
       UNSAT is a proof that no independent decycling set of size <= k exists.

Usage:
  python find_I.py ls  --d 9 --k 235 --minutes 120
  python find_I.py sat --d 9 --k 235
  python find_I.py sat --d 6 --k 27      # validation on small d
  python find_I.py sat --d 9 --k 236 --group z9   # I invariant under a symmetry group
  python find_I.py sat-relaxed --d 9 --k 235       # Z-relaxed forest class (section 3)
"""
import argparse
import json
import random
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
from numba import njit

from evaluator import count_uphill, count_uphill_bruteforce
from store import load_best, save_if_better

ROOT = Path(__file__).parent
RESULTS = ROOT / "results" / "results.jsonl"


# ---------------------------------------------------------------- shared helpers

def log(row):
    RESULTS.parent.mkdir(exist_ok=True)
    with open(RESULTS, "a") as f:
        f.write(json.dumps({**row, "timestamp": time.time()}) + "\n")


def forest_c(d, k):
    return (d - 1) * k - (d - 2) * 2 ** (d - 1)


def peaks_of(order, d):
    label = {v: i for i, v in enumerate(order)}
    return [v for v in order if all(label[v ^ (1 << j)] < label[v] for j in range(d))]


def check_I(I, d):
    """(independent, acyclic, #trees of G[V minus I]) by plain Python union-find."""
    I = set(I)
    independent = all(v ^ (1 << j) not in I for v in I for j in range(d))
    parent = {v: v for v in range(2 ** d) if v not in I}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    acyclic = True
    for v in parent:
        for j in range(d):
            u = v ^ (1 << j)
            if u > v and u in parent:
                a, b = find(u), find(v)
                if a == b:
                    acyclic = False
                parent[a] = b
    return independent, acyclic, len({find(v) for v in parent})


def forest_labelling(I, d, Z=()):
    """Trees of G[V minus (I + Z)] in BFS order, then Z, then I on top. With Z empty this is
    the helper in loop.py."""
    I, Z = set(I), set(Z)
    order, seen = [], I | Z
    for r in range(2 ** d):
        if r in seen:
            continue
        seen.add(r)
        queue = deque([r])
        while queue:
            v = queue.popleft()
            order.append(v)
            for j in range(d):
                u = v ^ (1 << j)
                if u not in seen:
                    seen.add(u)
                    queue.append(u)
    return order + sorted(Z) + sorted(I)


def check_relaxed(P, Z, d):
    """Z-relaxed forest class (see section 3): P, Z independent and disjoint, every z has
    exactly d-2 neighbours in P (so, Z being independent, exactly 2 in T = V minus (P + Z)),
    G[T] acyclic. Returns (ok, c = #trees of G[T])."""
    P, Z = set(P), set(Z)
    nbrs = lambda v: [v ^ (1 << j) for j in range(d)]
    ok = (not P & Z and all(u not in P for v in P for u in nbrs(v))
          and all(u not in Z for v in Z for u in nbrs(v))
          and all(sum(u in P for u in nbrs(z)) == d - 2 for z in Z))
    _, acyclic, c = check_I(P | Z, d)
    return ok and acyclic, c


def found(I, d, source, Z=()):
    """Verify (I = P, Z), build and verify the labelling, store it, export + commit if it is a
    new best. U must equal |E| + c + (d-2)|Z| = 2^d + (d-1)(|I| + |Z|)."""
    I, Z = sorted(int(v) for v in I), sorted(int(v) for v in Z)
    ok, c = check_relaxed(I, Z, d)
    assert ok, "not a valid (P, Z) configuration / independent decycling set"
    order = forest_labelling(I, d, Z)
    U, bf = count_uphill(order, d), count_uphill_bruteforce(order, d)
    assert U == bf == d * 2 ** (d - 1) + c + (d - 2) * len(Z) == 2 ** d + (d - 1) * (len(I) + len(Z)), \
        (U, bf, c, len(Z))
    k = len(I) + len(Z)
    path = ROOT / "results" / f"I_Q{d}_k{k}{'_Z' + str(len(Z)) if Z else ''}_{int(time.time())}.json"
    path.write_text(json.dumps({"d": d, "k": k, "P": len(I), "Z_size": len(Z), "c": c, "U": U,
                                "source": source, "I": I, "Z": Z}))
    stored = save_if_better(d, order, f"find_I {source} |D|={k} |Z|={len(Z)}")
    log({"source": f"find_I {source}", "d": d, "k": k, "Z": len(Z), "score": U, "file": path.name})
    print(f"!!! FOUND Q{d}: |P| = {len(I)}, |Z| = {len(Z)}, |D| = {k}, c = {c}, U = {U} "
          f"(DP == brute force == formula), saved {path.name}; store best = {load_best(d)['score']}",
          flush=True)
    if stored == U and load_best(d)["score"] == U:
        try:
            from promote import promote
            promote(d)
        except Exception as e:  # the promote.py watcher will retry
            print(f"promote failed: {e!r}", flush=True)
    return U


# ---------------------------------------------------------------- (1) local search

@njit(cache=True)
def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


@njit(cache=True)
def _cost(inI, d, parent, closing):
    """Returns (beta, eII, m): beta = #cycle-closing edges of G[V minus I] (its cyclomatic
    number), eII = #edges inside I; closing[:m] holds endpoints of cycle-closing edges."""
    n = inI.shape[0]
    for v in range(n):
        parent[v] = v
    beta, eII, m = 0, 0, 0
    for v in range(n):
        for j in range(d):
            u = v ^ (1 << j)
            if u < v:
                continue
            if inI[v] and inI[u]:
                eII += 1
            elif not inI[v] and not inI[u]:
                a, b = _find(parent, v), _find(parent, u)
                if a == b:
                    beta += 1
                    closing[m] = v
                    closing[m + 1] = u
                    m += 2
                else:
                    parent[a] = b
    return beta, eII, m


@njit(cache=True)
def anneal_I(inI, d, iters, T0, T1, lam, tabu, seed):
    """SA over sets of fixed size with 1-out/1-in swaps. Stops early at cost 0."""
    np.random.seed(seed)
    n = inI.shape[0]
    inI = inI.copy()
    parent = np.empty(n, np.int64)
    closing = np.empty(d * n, np.int64)
    closing2 = np.empty(d * n, np.int64)
    inlist = np.empty(n, np.int64)
    outlist = np.empty(n, np.int64)
    idx = np.empty(n, np.int64)
    n_in, n_out = 0, 0
    for v in range(n):
        if inI[v]:
            inlist[n_in] = v
            idx[v] = n_in
            n_in += 1
        else:
            outlist[n_out] = v
            idx[v] = n_out
            n_out += 1
    beta, eII, m = _cost(inI, d, parent, closing)
    cur = beta + lam * eII
    best, best_I = cur, inI.copy()
    last = np.full(n, -(tabu + 1), np.int64)
    ratio = T1 / T0
    for it in range(iters):
        if best == 0:
            break
        T = T0 * ratio ** (it / iters)
        # vertex to add: usually an endpoint of a cycle-closing edge (breaks a cycle)
        if m > 0 and np.random.random() < 0.8:
            v = closing[np.random.randint(m)]
        else:
            v = outlist[np.random.randint(n_out)]
        # vertex to remove: often an I-neighbour of v (restores independence)
        nb, cnt = -1, 0
        for j in range(d):
            w = v ^ (1 << j)
            if inI[w]:
                cnt += 1
                if np.random.randint(cnt) == 0:
                    nb = w
        u = nb if nb >= 0 and np.random.random() < 0.7 else inlist[np.random.randint(n_in)]
        if tabu > 0 and (it - last[u] <= tabu or it - last[v] <= tabu):
            continue
        inI[v], inI[u] = True, False
        beta2, eII2, m2 = _cost(inI, d, parent, closing2)
        new = beta2 + lam * eII2
        if new <= cur or np.random.random() < np.exp(-(new - cur) / T):
            iu, iv = idx[u], idx[v]
            inlist[iu], outlist[iv] = v, u
            idx[v], idx[u] = iu, iv
            closing, closing2 = closing2, closing
            cur, m = new, m2
            last[u] = it
            last[v] = it
            if cur < best:
                best = cur
                best_I[:] = inI
        else:
            inI[v], inI[u] = False, True
    return best_I, best


def greedy_removals(I, d):
    """Drop vertices of I while G[V minus I] stays acyclic (all neighbours of v lie in
    distinct trees). Returns the reduced set."""
    I = set(I)
    for v in sorted(I):
        trial = I - {v}
        if check_I(trial, d)[1]:
            I = trial
    return I


def shrink_to(I, d, k):
    """Remove vertices from I until |I| = k, each time the one creating the fewest cycles."""
    I = set(I)
    parent, closing = np.empty(2 ** d, np.int64), np.empty(d * 2 ** d, np.int64)
    while len(I) > k:
        def beta(v):
            arr = np.zeros(2 ** d, np.bool_)
            arr[list(I - {v})] = True
            return _cost(arr, d, parent, closing)[0]
        I.remove(min(I, key=beta))
    return I


def run_ls(d, k, minutes, seed, iters, T0, T1, lam, tabu, kick):
    rng = random.Random(seed)
    I0 = set(peaks_of(load_best(d)["order"], d))
    ind, acyc, c = check_I(I0, d)
    print(f"start: peak set of best Q{d} labelling, |I| = {len(I0)}, independent={ind}, "
          f"acyclic={acyc}, c={c}", flush=True)
    I1 = greedy_removals(I0, d)
    if len(I1) < len(I0):
        found(I1, d, "ls greedy")
        return
    deadline, restart = time.time() + 60 * minutes, 0
    while time.time() < deadline:
        I = set(I0)
        for _ in range(rng.randint(0, kick)):  # random kick: swap an I vertex with a non-I one
            I.remove(rng.choice(sorted(I)))
            I.add(rng.choice([v for v in range(2 ** d) if v not in I]))
        I = shrink_to(I, d, k)
        arr = np.zeros(2 ** d, np.bool_)
        arr[list(I)] = True
        t = time.time()
        best_I, best = anneal_I(arr, d, iters, T0, T1, lam, tabu, rng.randrange(1 << 30))
        log({"source": "find_I ls", "d": d, "k": k, "restart": restart, "cost": int(best),
             "iters": iters, "secs": time.time() - t})
        print(f"restart {restart}: best cost {best} ({time.time() - t:.1f}s)", flush=True)
        if best == 0:
            found(np.flatnonzero(best_I), d, "ls")
            return
        restart += 1


# ---------------------------------------------------------------- (2) SAT with lazy cuts

def symmetry_fixed_vertices(d):
    """Vertices that may be assumed in I without loss of generality.

    Proof. Let I be independent with G[V minus I] acyclic. I is nonempty (Q_d has cycles);
    translating by a vertex of I (an automorphism) gives 0 in I. Now suppose 0 and
    e_{2s}+e_{2s+1} (s < t) are in I, and let R = {2t, ..., d-1} with |R| >= 3. For a < b < c
    in R, the 6-cycle e_a, e_a+e_b, e_b, e_b+e_c, e_c, e_c+e_a must meet I; its weight-1
    vertices are adjacent to 0, so they are not in I; hence some e_p+e_q with p, q in R is in
    I. A coordinate permutation fixing every coordinate outside R and sending {p, q} to
    {2t, 2t+1} fixes 0 and all e_{2s}+e_{2s+1} (s < t) and maps I to a valid set of the same
    size containing e_{2t}+e_{2t+1}. Induct while |R| >= 3. For d = 9: 0, 3, 12, 48, 192.
    """
    fixed, t = [0], 0
    while d - 2 * t >= 3:
        fixed.append((1 << (2 * t)) | (1 << (2 * t + 1)))
        t += 1
    return fixed


def cycles_in_complement(I, d):
    """For each cycle-closing edge (a, b) of G[V minus I], the shortest cycle through it
    (BFS from a to b avoiding that edge). Returns a list of vertex tuples."""
    I = set(I)
    F = [v for v in range(2 ** d) if v not in I]
    parent = {v: v for v in F}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    closing = []
    for v in F:
        for j in range(d):
            u = v ^ (1 << j)
            if u > v and u in parent:
                a, b = find(u), find(v)
                if a == b:
                    closing.append((v, u))
                else:
                    parent[a] = b
    cycles = set()
    for a, b in closing:
        prev = {a: None}
        queue = deque([a])
        while queue and b not in prev:
            v = queue.popleft()
            for j in range(d):
                u = v ^ (1 << j)
                if u in parent and u not in prev and not (v == a and u == b):
                    prev[u] = v
                    queue.append(u)
        path, v = [], b
        while v is not None:
            path.append(v)
            v = prev[v]
        cycles.add(tuple(sorted(path)))
    return [list(c) for c in cycles]


# Symmetry groups for d = 9, given by generating coordinate permutations (perm[j] = image of
# coordinate j). With --group, x_v <=> x_g(v) is added for each generator g, so I is a union of
# orbits and every clause on a cycle C also covers h(C) for all h in the group (the solver
# collapses the equalities: effectively one variable per orbit).
GROUPS = {
    "z9": [[(j + 1) % 9 for j in range(9)]],                        # cyclic shift of 9 coords
    "z3blocks": [[(j + 3) % 9 for j in range(9)]],                  # shift of blocks 012,345,678
    "rot3": [[3 * (j // 3) + (j % 3 + 1) % 3 for j in range(9)]],   # (0 1 2)(3 4 5)(6 7 8)
    "inv4": [[1, 0, 3, 2, 5, 4, 7, 6, 8]],                          # (0 1)(2 3)(4 5)(6 7)
    "inv2": [[1, 0, 3, 2, 4, 5, 6, 7, 8]],                          # (0 1)(2 3)
    "inv1": [[1, 0, 2, 3, 4, 5, 6, 7, 8]],                          # (0 1)
    "inv3": [[1, 0, 3, 2, 5, 4, 6, 7, 8]],                          # (0 1)(2 3)(4 5)
    "c3x1": [[1, 2, 0, 3, 4, 5, 6, 7, 8]],                          # (0 1 2)
    "c3x2": [[1, 2, 0, 4, 5, 3, 6, 7, 8]],                          # (0 1 2)(3 4 5)
    "c5": [[1, 2, 3, 4, 0, 5, 6, 7, 8]],                            # (0 1 2 3 4)
    "c7": [[1, 2, 3, 4, 5, 6, 0, 7, 8]],                            # (0 1 2 3 4 5 6)
}
# Coverage. Every nontrivial group H of automorphisms x -> pi(x) + t contains an element g of
# prime order p in {2, 3, 5, 7} (the primes dividing 2^9 * 9!), and an H-invariant I is
# g-invariant. g^p = id means N t = 0 with N = 1 + pi + ... + pi^(p-1); g has a fixed point iff
# t is in the image of 1 + pi, and then g is conjugate (by a translation) to pi. On the cycles
# of pi, F_2^9 is a free F_2[C_p]-module, where ker N = im(1 + pi); on coordinates fixed by pi,
# N = p. So for odd p, t = 0 there and g is conjugate to a coordinate permutation; for p = 2, g
# has no fixed point iff t is nonzero on a coordinate fixed by pi, and then every orbit has size
# 2, impossible for odd |I| = 235. Hence inv1-4, c3x1, c3x2, rot3, c5, c7 cover every nontrivial
# symmetry group that a set with |I| = 235 can have.
# Up to conjugacy in Aut(Q_9), the involutions with fixed points are the coordinate involutions
# inv1..inv4 (a translation part is either conjugated away or kills all fixed points; groups
# without fixed points have only even orbits, incompatible with odd |I| = 235).
# Note: z3blocks = (0 3 6)(1 4 7)(2 5 8) is conjugate to rot3 in S_9 (both are three disjoint
# 3-cycles), hence equivalent up to an automorphism of Q_9; z9 contains z3blocks (z9^3).


def permute_coords(v, perm):
    return sum(((v >> j) & 1) << perm[j] for j in range(len(perm)))


def orbit_sizes(d, gens):
    """Sizes of the orbits of <gens> on the vertices (closure under the generators)."""
    seen, sizes = set(), []
    for v in range(2 ** d):
        if v in seen:
            continue
        orbit, stack = {v}, [v]
        while stack:
            w = stack.pop()
            for g in gens:
                u = permute_coords(w, g)
                if u not in orbit:
                    orbit.add(u)
                    stack.append(u)
        seen |= orbit
        sizes.append(len(orbit))
    return sizes


def random_automorphism(d, rng):
    perm, flip = list(range(d)), rng.randrange(2 ** d)
    rng.shuffle(perm)
    return lambda v: sum(((v >> j) & 1) << perm[j] for j in range(d)) ^ flip


def run_sat(d, k, symmetry, solver_name, encoding, images, minutes, seed, group=None):
    from pysat.card import CardEnc, EncType
    from pysat.formula import IDPool
    from pysat.solvers import Solver

    rng = random.Random(seed)
    n = 2 ** d
    x = lambda v: v + 1
    solver = Solver(name=solver_name)
    for v in range(n):
        for j in range(d):
            if v ^ (1 << j) > v:
                solver.add_clause([-x(v), -x(v ^ (1 << j))])
    card = CardEnc.atmost(lits=[x(v) for v in range(n)], bound=k,
                          vpool=IDPool(start_from=n + 1), encoding=getattr(EncType, encoding))
    solver.append_formula(card.clauses)
    n4 = 0
    for i in range(d):
        for j in range(i + 1, d):
            for v in range(n):
                if not (v >> i) & 1 and not (v >> j) & 1:
                    solver.add_clause([x(v), x(v ^ 1 << i), x(v ^ 1 << i ^ 1 << j), x(v ^ 1 << j)])
                    n4 += 1
    if group:  # I must be a union of orbits; the fixed vertices below would not be sound
        gens = GROUPS[group]
        for g in gens:
            for v in range(n):
                solver.add_clause([-x(v), x(permute_coords(v, g))])
        sizes = orbit_sizes(d, gens)
        print(f"group {group}: {len(sizes)} orbits, sizes {sorted(set(sizes))}", flush=True)
        symmetry = False
    fixed = symmetry_fixed_vertices(d) if symmetry else []
    for v in fixed:
        solver.add_clause([x(v)])
    tag = f" group={group}" if group else ""
    print(f"SAT Q{d} |I| <= {k} (c = {forest_c(d, k)}){tag}: {n4} 4-cycle clauses, fixed {fixed}, "
          f"solver {solver_name}, card {encoding}", flush=True)
    deadline, it, cuts, t0 = time.time() + 60 * minutes, 0, 0, time.time()
    seen = set()
    while time.time() < deadline:
        t = time.time()
        if not solver.solve():
            msg = (f"UNSAT: no independent decycling set of Q{d} with |I| <= {k}{tag}"
                   f"{' (with proven symmetry breaking)' if symmetry else ''}; "
                   f"{it} iterations, {cuts} cuts, {time.time() - t0:.0f}s")
            print(msg, flush=True)
            log({"source": "find_I sat", "d": d, "k": k, "group": group, "result": "UNSAT", "iters": it,
                 "cuts": cuts, "secs": time.time() - t0})
            return
        model = solver.get_model()
        I = [v for v in range(n) if model[v] > 0]
        cycles = cycles_in_complement(I, d)
        if not cycles:
            found(I, d, f"sat{tag}")
            return
        new = 0
        for cyc in cycles:
            for m in range(images + 1):  # cycle clauses hold for every valid I, so images are sound
                g = (lambda v: v) if m == 0 else random_automorphism(d, rng)
                clause = tuple(sorted(g(v) for v in cyc))
                if clause not in seen:
                    seen.add(clause)
                    solver.add_clause([x(v) for v in clause])
                    new += 1
        cuts += new
        it += 1
        if it % 10 == 0 or it < 10:
            print(f"iter {it}: |I| = {len(I)}, {len(cycles)} cycles in complement "
                  f"(lengths {sorted({len(c) for c in cycles})}), +{new} cuts, total {cuts}, "
                  f"solve {time.time() - t:.1f}s, elapsed {time.time() - t0:.0f}s", flush=True)
        if it % 50 == 0:
            log({"source": "find_I sat", "d": d, "k": k, "group": group, "iters": it, "cuts": cuts,
                 "last_cycles": len(cycles), "secs": time.time() - t0})
    print(f"timeout after {it} iterations, {cuts} cuts{tag}", flush=True)
    log({"source": "find_I sat", "d": d, "k": k, "group": group, "result": "timeout",
         "iters": it, "cuts": cuts, "secs": time.time() - t0})


# ---------------------------------------------------------------- (3) Z-relaxed forest class
#
# D = P + Z with P, Z independent, every z in Z having exactly d-2 neighbours in P and 2 in
# T = V minus D, and G[T] acyclic with c trees. Labelling: trees of T grown outward from one
# valley each, then Z, then P. N = 1 on T, N(z) = 2, P are peaks, and the excess decomposition
# gives U = |E| + c + (d-2)|Z|; counting edges, U = 2^d + (d-1)|D| (Q_9: 512 + 8|D|).
# More generally a vertex z labelled between T and P, with k (higher) P-neighbours and d-k
# (lower) T-neighbours, adds d-1 + k(d-2-k) to U = 2^d + (d-1)|P| + sum_z cost(z): the same as a
# P-vertex (d-1) iff k = d-2 (k = 0 is a P-vertex, k = d-1 a tree leaf); otherwise more.
#
# Symmetry breaking (sound, proof): P is nonempty (a z needs P-neighbours; D is nonempty since
# Q_d has cycles), so translate a vertex of P to 0. Case A: some weight-1 vertex e_a is in Z;
# a coordinate permutation (fixing 0) makes it e_0. Case B: no weight-1 vertex is in Z; none is
# in P either (adjacent to 0 in P), so all are in T, and the 6-cycle argument of
# symmetry_fixed_vertices applies verbatim with "in I" replaced by "in D" (coordinate
# permutations preserve case B). Encoded as: p_0; not z_{e_0} -> not z_{e_a} for all a; and
# not z_{e_0} -> f in D for the fixed weight-2 vertices f.

def run_sat_relaxed(d, k, symmetry, solver_name, encoding, images, minutes, seed, group=None,
                    min_z=0):
    from itertools import combinations
    from pysat.card import CardEnc, EncType
    from pysat.formula import IDPool
    from pysat.solvers import Solver

    rng = random.Random(seed)
    n = 2 ** d
    p = lambda v: v + 1
    z = lambda v: n + v + 1
    solver = Solver(name=solver_name)
    for v in range(n):
        solver.add_clause([-p(v), -z(v)])
        nb = [v ^ (1 << j) for j in range(d)]
        for u in nb:
            if u > v:
                solver.add_clause([-p(u), -p(v)])
                solver.add_clause([-z(u), -z(v)])
        for triple in combinations(nb, 3):  # z_v -> at most 2 neighbours outside P
            solver.add_clause([-z(v)] + [p(u) for u in triple])
        for sub in combinations(nb, d - 1):  # z_v -> at most d-2 neighbours in P
            solver.add_clause([-z(v)] + [-p(u) for u in sub])
    pool = IDPool(start_from=2 * n + 1)  # shared, so auxiliary variables never collide
    card = CardEnc.atmost(lits=[p(v) for v in range(n)] + [z(v) for v in range(n)], bound=k,
                          vpool=pool, encoding=getattr(EncType, encoding))
    solver.append_formula(card.clauses)
    if min_z:  # experiments / tests: force |Z| >= min_z (the symmetry fixings stay sound)
        solver.append_formula(CardEnc.atleast(lits=[z(v) for v in range(n)], bound=min_z,
                                              vpool=pool, encoding=getattr(EncType, encoding)).clauses)
    for i in range(d):
        for j in range(i + 1, d):
            for v in range(n):
                if not (v >> i) & 1 and not (v >> j) & 1:
                    cyc = [v, v ^ 1 << i, v ^ 1 << i ^ 1 << j, v ^ 1 << j]
                    solver.add_clause([p(u) for u in cyc] + [z(u) for u in cyc])
    tag = " relaxed" + (f" group={group}" if group else "")
    if group:  # P and Z unions of orbits; the fixings below would not be sound
        for g in GROUPS[group]:
            for v in range(n):
                solver.add_clause([-p(v), p(permute_coords(v, g))])
                solver.add_clause([-z(v), z(permute_coords(v, g))])
        symmetry = False
    if symmetry:
        e0 = 1
        solver.add_clause([p(0)])
        for a in range(1, d):
            solver.add_clause([z(e0), -z(1 << a)])
        for f in symmetry_fixed_vertices(d)[1:]:
            solver.add_clause([z(e0), p(f), z(f)])
    print(f"SAT Q{d} |P|+|Z| <= {k} (U = {2 ** d + (d - 1) * k}){tag}, symmetry breaking "
          f"{symmetry}, solver {solver_name}, card {encoding}", flush=True)
    deadline, it, cuts, t0, seen = time.time() + 60 * minutes, 0, 0, time.time(), set()
    while time.time() < deadline:
        t = time.time()
        if not solver.solve():
            print(f"UNSAT: no Z-relaxed configuration of Q{d} with |D| <= {k}{tag}; {it} "
                  f"iterations, {cuts} cuts, {time.time() - t0:.0f}s", flush=True)
            log({"source": "find_I sat-relaxed", "d": d, "k": k, "group": group,
                 "result": "UNSAT", "iters": it, "cuts": cuts, "secs": time.time() - t0})
            return
        model = solver.get_model()
        P = [v for v in range(n) if model[p(v) - 1] > 0]
        Z = [v for v in range(n) if model[z(v) - 1] > 0]
        cycles = cycles_in_complement(P + Z, d)
        if not cycles:
            found(P, d, f"sat{tag}", Z=Z)
            return
        new = 0
        for cyc in cycles:
            for m in range(images + 1):  # every cycle of T must meet D, for every valid (P, Z)
                g = (lambda v: v) if m == 0 else random_automorphism(d, rng)
                clause = tuple(sorted(g(v) for v in cyc))
                if clause not in seen:
                    seen.add(clause)
                    solver.add_clause([p(v) for v in clause] + [z(v) for v in clause])
                    new += 1
        cuts += new
        it += 1
        if it % 10 == 0 or it < 10:
            print(f"iter {it}: |P| = {len(P)}, |Z| = {len(Z)}, {len(cycles)} cycles in T, +{new} "
                  f"cuts, total {cuts}, solve {time.time() - t:.1f}s, elapsed {time.time() - t0:.0f}s",
                  flush=True)
    print(f"timeout after {it} iterations, {cuts} cuts{tag}", flush=True)
    log({"source": "find_I sat-relaxed", "d": d, "k": k, "group": group, "result": "timeout",
         "iters": it, "cuts": cuts, "secs": time.time() - t0})


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("method", choices=["ls", "sat", "sat-relaxed"])
    p.add_argument("--d", type=int, default=9)
    p.add_argument("--k", type=int, default=235, help="target |I|")
    p.add_argument("--minutes", type=float, default=120)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--iters", type=int, default=2_000_000, help="ls: SA iterations per restart")
    p.add_argument("--T0", type=float, default=2.0)
    p.add_argument("--T1", type=float, default=0.2)
    p.add_argument("--lam", type=float, default=2.0, help="ls: penalty per edge inside I")
    p.add_argument("--tabu", type=int, default=10)
    p.add_argument("--kick", type=int, default=10, help="ls: max random swaps before a restart")
    p.add_argument("--no-symmetry", action="store_true")
    p.add_argument("--group", choices=sorted(GROUPS), help="sat: require I invariant under this group")
    p.add_argument("--solver", default="cadical195")
    p.add_argument("--encoding", default="seqcounter")
    p.add_argument("--images", type=int, default=8, help="sat: random automorphic images per cut")
    p.add_argument("--min-z", type=int, default=0, help="sat-relaxed: require |Z| >= this")
    a = p.parse_args()
    if forest_c(a.d, a.k) < 1:
        sys.exit(f"|I| = {a.k} gives c = {forest_c(a.d, a.k)} < 1: impossible")
    if a.method == "ls":
        run_ls(a.d, a.k, a.minutes, a.seed, a.iters, a.T0, a.T1, a.lam, a.tabu, a.kick)
    elif a.method == "sat":
        run_sat(a.d, a.k, not a.no_symmetry, a.solver, a.encoding, a.images, a.minutes, a.seed,
                a.group)
    else:
        run_sat_relaxed(a.d, a.k, not a.no_symmetry, a.solver, a.encoding, a.images, a.minutes,
                        a.seed, a.group, a.min_z)
