"""Q9 v2: SAT search for a Z-relaxed forest configuration with |D| <= k (Q9, k = 235 -> U = 2392).

Model (same class as find_I.py sat-relaxed, independent code):
  variables p_v, z_v; D = P + Z, T = V minus D.
  * p_v -> not z_v; P independent; Z independent;
  * z_v -> exactly d-2 neighbours in P (every 3 neighbours contain a P-vertex, every d-1
    neighbours contain a non-P vertex); Z independent => its other 2 neighbours are in T;
  * every 4-cycle AND every 6-cycle of Q_d meets D, added before the first solve
    (4-cycles live in 2-dim subcubes, 6-cycles in 3-dim subcubes: 16 per Q3);
  * counting: |P| + |Z| <= k and (d-1)|P| + |Z| >= (d-2) 2^(d-1) + 1.
    Proof of the latter: e(T) = |E| - d|P| - 2|Z| (P, Z independent, each z has d-2 P- and
    2 T-neighbours), and T acyclic and nonempty gives e(T) <= |T| - 1. Encoded with a
    two-sided totalizer on P and on Z (outputs <=> "count >= i").
    For Q9, k = 235: |P| >= 223 and |Z| <= 12.
  * symmetry breaking of find_I.py (proved there): p_0; not z_{e0} -> not z_{e_a};
    not z_{e0} -> e_{2t}+e_{2t+1} in D.
  * lazy cuts: after each model, every cycle-closing edge of a spanning forest of G[T] gives
    a shortest cycle through it, plus ALL 8-cycles of G[T] (cap per round), each as
    "meets D", plus random automorphic images of the fundamental cycles (sound).
Hard deadline --until HH:MM (local time), enforced by a watchdog child process that logs a
heartbeat every 10 min and sends SIGTERM at the deadline. (An in-process timer calling
solver.interrupt() does NOT work here: pysat's cadical195 keeps the GIL and ignores it; tested.)

Usage: nice -n 10 env OMP_NUM_THREADS=1 python3 search.py --d 9 --k 235 --until 16:30
       python3 search.py --d 5 --k 13 --log /dev/stdout    # validation (expect UNSAT)
"""
import argparse
import itertools
import json
import random
import sys
import os
import subprocess
import time
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from evaluator import count_uphill, count_uphill_bruteforce, to_strings  # noqa: E402

from pysat.solvers import Solver  # noqa: E402


# ---------------------------------------------------------------- two-sided totalizer

class Totalizer:
    """Unary counter with saturation K: out[i] (i = 1..m) is equivalent to sum(lits) >= i,
    m = min(len(lits), K). Both directions are encoded."""

    def __init__(self, lits, K, newvar, clauses):
        self.out = self._build(list(lits), K, newvar, clauses)

    def _build(self, lits, K, newvar, clauses):
        if len(lits) == 1:
            return [None, lits[0]]
        h = len(lits) // 2
        a = self._build(lits[:h], K, newvar, clauses)
        b = self._build(lits[h:], K, newvar, clauses)
        na, nb = len(a) - 1, len(b) - 1  # number of outputs of the children
        m = min(na + nb, K)
        o = [None] + [newvar() for _ in range(m)]
        # a_i = "left >= i" (a_0 = true). In a down clause with i + 1 > na the literal a_{i+1}
        # is false and omitted: then i = na, and if the left child is saturated (na = K) we
        # would have s + 1 > K >= m, so that clause is never generated.
        for i in range(na + 1):
            for j in range(nb + 1):
                s = i + j
                if s >= 1:  # up: a_i & b_j -> o_min(s, m)
                    cl = [o[min(s, m)]]
                    if i:
                        cl.append(-a[i])
                    if j:
                        cl.append(-b[j])
                    clauses.append(cl)
                if s + 1 <= m:  # down: not a_{i+1} & not b_{j+1} -> not o_{s+1}
                    cl = [-o[s + 1]]
                    if i + 1 <= na:
                        cl.append(a[i + 1])
                    if j + 1 <= nb:
                        cl.append(b[j + 1])
                    clauses.append(cl)
        return o

    def ge(self, i):
        """Literal for "count >= i", or True/False when trivially decided."""
        if i <= 0:
            return True
        if i >= len(self.out):
            return False
        return self.out[i]


def _test_totalizer():
    rng = random.Random(1)
    for n in range(1, 9):
        for K in range(1, n + 2):
            top = [n]
            newvar = lambda: (top.__setitem__(0, top[0] + 1), top[0])[1]
            clauses = []
            t = Totalizer(range(1, n + 1), K, newvar, clauses)
            s = Solver(name="cadical195", bootstrap_with=clauses)
            for bits in itertools.product([0, 1], repeat=n):
                assum = [v if b else -v for v, b in zip(range(1, n + 1), bits)]
                assert s.solve(assumptions=assum)
                model = set(s.get_model())
                c = sum(bits)
                for i in range(1, len(t.out)):
                    assert (t.out[i] in model) == (c >= i), (n, K, bits, i)
            s.delete()
    del rng
    print("totalizer self-test OK")


# ---------------------------------------------------------------- cycles

def q3_six_cycles():
    """The chordless six-cycles of Q3 as vertex lists."""
    cyc = set()
    for start in range(8):
        stack = [(start, [start])]
        while stack:
            v, path = stack.pop()
            if len(path) == 6:
                if path[0] ^ v in (1, 2, 4):
                    cyc.add(frozenset(path))
                continue
            for j in range(3):
                u = v ^ (1 << j)
                if u not in path:
                    stack.append((u, path + [u]))
    assert len(cyc) == 16, len(cyc)
    # 12 of them have a chord (two faces sharing an edge): their clause is implied by the
    # 4-cycle clauses. Keep the 4 chordless ones (Q3 minus an antipodal pair).
    chordless = [c for c in cyc
                 if sum(bin(a ^ b).count("1") == 1 for a, b in itertools.combinations(c, 2)) == 6]
    assert len(chordless) == 4
    return [sorted(c) for c in chordless]


def short_cycles(d):
    """All 4-cycles and all chordless 6-cycles of Q_d (vertex lists); every other 6-cycle has a
    4-cycle inside its vertex set."""
    out = []
    for i, j in itertools.combinations(range(d), 2):
        for v in range(2 ** d):
            if not (v >> i) & 1 and not (v >> j) & 1:
                out.append([v, v ^ 1 << i, v ^ 1 << i ^ 1 << j, v ^ 1 << j])
    n4 = len(out)
    six = q3_six_cycles()
    for coords in itertools.combinations(range(d), 3):
        mask = sum(1 << c for c in coords)
        for base in range(2 ** d):
            if base & mask:
                continue
            emb = lambda x: base | sum(((x >> t) & 1) << coords[t] for t in range(3))
            for c in six:
                out.append([emb(x) for x in c])
    return out, n4, len(out) - n4


def forest_cycles(T, d, cap8):
    """(beta, cycles): beta = cyclomatic number of G[T]; cycles = a shortest cycle through each
    cycle-closing edge of a spanning forest, plus all 8-cycles of G[T] (at most cap8)."""
    Tset = set(T)
    parent = {v: v for v in T}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    closing = []
    for v in T:
        for j in range(d):
            u = v ^ (1 << j)
            if u > v and u in Tset:
                a, b = find(u), find(v)
                if a == b:
                    closing.append((v, u))
                else:
                    parent[a] = b
    fund = set()
    for a, b in closing:
        prev, q = {a: None}, deque([a])
        while q and b not in prev:
            v = q.popleft()
            for j in range(d):
                u = v ^ (1 << j)
                if u in Tset and u not in prev and not (v == a and u == b):
                    prev[u] = v
                    q.append(u)
        path, v = [], b
        while v is not None:
            path.append(v)
            v = prev[v]
        fund.add(tuple(sorted(path)))
    eight = set()
    if closing:
        cyc_vertices = set()  # only vertices in the 2-core can lie on cycles
        deg = {v: sum((v ^ (1 << j)) in Tset for j in range(d)) for v in T}
        alive, q = set(T), deque(v for v in T if deg[v] <= 1)
        while q:
            v = q.popleft()
            if v not in alive:
                continue
            alive.discard(v)
            for j in range(d):
                u = v ^ (1 << j)
                if u in alive:
                    deg[u] -= 1
                    if deg[u] == 1:
                        q.append(u)
        cyc_vertices = alive
        nb = {v: [v ^ (1 << j) for j in range(d) if (v ^ (1 << j)) in cyc_vertices] for v in cyc_vertices}
        for s in sorted(cyc_vertices):  # s = smallest vertex of the cycle
            stack = [(s, (s,))]
            while stack and len(eight) < cap8:
                v, path = stack.pop()
                for u in nb[v]:
                    if u == s and len(path) == 8 and path[1] < path[-1]:
                        eight.add(tuple(sorted(path)))
                    elif u > s and u not in path and len(path) < 8:
                        stack.append((u, path + (u,)))
            if len(eight) >= cap8:
                break
    beta = len(closing)
    return beta, [list(c) for c in fund], [list(c) for c in eight - fund]


def random_automorphism(d, rng):
    perm, flip = list(range(d)), rng.randrange(2 ** d)
    rng.shuffle(perm)
    return lambda v: sum(((v >> j) & 1) << perm[j] for j in range(d)) ^ flip


# ---------------------------------------------------------------- verification

def check_config(P, Z, d):
    P, Z = set(P), set(Z)
    nbrs = lambda v: [v ^ (1 << j) for j in range(d)]
    assert not P & Z
    assert all(u not in P for v in P for u in nbrs(v)), "P not independent"
    assert all(u not in Z for v in Z for u in nbrs(v)), "Z not independent"
    assert all(sum(u in P for u in nbrs(z)) == d - 2 for z in Z), "z without d-2 P-neighbours"
    T = [v for v in range(2 ** d) if v not in P | Z]
    beta, _, _ = forest_cycles(T, d, 0)
    assert beta == 0, "G[T] has a cycle"
    return T


def forest_labelling(P, Z, d):
    D = set(P) | set(Z)
    order, seen = [], set(D)
    for r in range(2 ** d):
        if r in seen:
            continue
        seen.add(r)
        q = deque([r])
        while q:
            v = q.popleft()
            order.append(v)
            for j in range(d):
                u = v ^ (1 << j)
                if u not in seen:
                    seen.add(u)
                    q.append(u)
    return order + sorted(Z) + sorted(P)


# ---------------------------------------------------------------- main search

def run(d, k, until, logpath, images, cap8, seed, solver_name, outdir=HERE):
    rng = random.Random(seed)
    n = 2 ** d
    E = d * 2 ** (d - 1)
    logf = open(logpath, "a", buffering=1)

    def log(msg):
        logf.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

    p = lambda v: v + 1
    z = lambda v: n + v + 1
    top = [2 * n]

    def newvar():
        top[0] += 1
        return top[0]

    cl = []
    for v in range(n):
        cl.append([-p(v), -z(v)])
        nb = [v ^ (1 << j) for j in range(d)]
        for u in nb:
            if u > v:
                cl.append([-p(u), -p(v)])
                cl.append([-z(u), -z(v)])
        for tri in itertools.combinations(nb, 3):
            cl.append([-z(v)] + [p(u) for u in tri])
        for sub in itertools.combinations(nb, d - 1):
            cl.append([-z(v)] + [-p(u) for u in sub])
    n_local = len(cl)
    cycles, n4, n6 = short_cycles(d)
    for c in cycles:
        cl.append([p(u) for u in c] + [z(u) for u in c])
    # counting constraints
    B = (d - 2) * 2 ** (d - 1) + 1  # (d-1)|P| + |Z| >= B
    pmin = max(0, -(-(B - k) // (d - 2)))
    zmax = k - pmin
    if zmax < 0:
        log(f"UNSAT (counting): (d-1)|P| + |Z| >= {B} incompatible with |D| <= {k}")
        return "UNSAT"
    n_before = len(cl)
    tp = Totalizer([p(v) for v in range(n)], k + 1, newvar, cl)
    tz = Totalizer([z(v) for v in range(n)], zmax + 1, newvar, cl)

    neg = lambda x: (not x) if isinstance(x, bool) else -x

    def lit_clause(lits):  # lits may contain True/False constants
        if any(x is True for x in lits):
            return
        cl.append([x for x in lits if x is not False])

    for j in range(0, zmax + 2):  # |Z| >= j -> |P| <= k - j
        lit_clause([neg(tz.ge(j)), neg(tp.ge(k - j + 1))])
    lit_clause([tp.ge(pmin)])
    for pv in range(pmin, k + 1):  # |P| <= pv -> |Z| >= B - (d-1) pv
        need = B - (d - 1) * pv
        if need <= 0:
            break
        lit_clause([tp.ge(pv + 1), tz.ge(need)])
    n_count = len(cl) - n_before
    # symmetry breaking (find_I.py, proved there)
    fixed = [(1 << (2 * t)) | (1 << (2 * t + 1)) for t in range(d) if d - 2 * t >= 3]
    cl.append([p(0)])
    for a in range(1, d):
        cl.append([z(1), -z(1 << a)])
    for f in fixed:
        cl.append([z(1), p(f), z(f)])
    log(f"=== Q{d} relaxed, |D| <= {k} (U <= {n + (d - 1) * k}), solver {solver_name}, until {until}")
    log(f"clauses: local {n_local}, 4-cycles {n4}, 6-cycles {n6}, counting {n_count} "
        f"(|P| >= {pmin}, |Z| <= {zmax}), symmetry fixed {fixed}; total {len(cl)}, vars {top[0]}")

    solver = Solver(name=solver_name, bootstrap_with=cl)
    total_clauses = len(cl)
    del cl
    hh, mm = map(int, until.split(":"))
    now = time.localtime()
    deadline = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hh, mm, 0, 0, 0, -1))
    if deadline <= time.time():
        log("deadline already passed")
        return "TIMEOUT"
    watchdog = subprocess.Popen(["/bin/sh", "-c", WATCHDOG, "watchdog", str(os.getpid()),
                                 str(int(deadline)), str(logpath)], start_new_session=True)
    t0, seen, rnd = time.time(), set(), 0
    try:
        while True:
            rnd += 1
            ts = time.time()
            log(f"round {rnd}: solving ({total_clauses} clauses)")
            res = solver.solve()
            dt = time.time() - ts
            if res is False:
                log(f"round {rnd}: UNSAT after {dt:.0f}s: no relaxed configuration of Q{d} with "
                    f"|D| <= {k}; total clauses {total_clauses}, elapsed {time.time() - t0:.0f}s")
                return "UNSAT"
            model = solver.get_model()
            mset = set(x for x in model if x > 0)
            P = [v for v in range(n) if p(v) in mset]
            Z = [v for v in range(n) if z(v) in mset]
            T = [v for v in range(n) if p(v) not in mset and z(v) not in mset]
            beta, fund, eight = forest_cycles(T, d, cap8)
            if beta == 0:
                log(f"round {rnd}: model with acyclic T: |P| = {len(P)}, |Z| = {len(Z)} "
                    f"({dt:.0f}s)")
                return found(P, Z, d, log, outdir)
            new = 0
            for c in fund:
                for m in range(images + 1):
                    g = (lambda v: v) if m == 0 else random_automorphism(d, rng)
                    key = tuple(sorted(g(v) for v in c))
                    if key not in seen:
                        seen.add(key)
                        solver.add_clause([p(v) for v in key] + [z(v) for v in key])
                        new += 1
            for c in eight:
                key = tuple(c)
                if key not in seen:
                    seen.add(key)
                    solver.add_clause([p(v) for v in key] + [z(v) for v in key])
                    new += 1
            total_clauses += new
            lens = sorted({len(c) for c in fund})
            log(f"round {rnd}: solve {dt:.1f}s, |P| = {len(P)}, |Z| = {len(Z)}, cycles left "
                f"(cyclomatic number of G[T]) {beta}, fundamental cycles {len(fund)} (lengths "
                f"{lens}), 8-cycles {len(eight)}, +{new} clauses, total {total_clauses}, "
                f"elapsed {time.time() - t0:.0f}s")
    finally:
        watchdog.terminate()


WATCHDOG = r"""
pid=$1; dl=$2; log=$3; n=0
while kill -0 $pid 2>/dev/null && [ $(date +%s) -lt $dl ]; do
  sleep 30; n=$((n+1))
  if [ $((n % 20)) -eq 0 ] && kill -0 $pid 2>/dev/null; then
    echo "$(date +%H:%M:%S)   ... still solving (watchdog, cpu $(ps -o time= -p $pid | tr -d ' '))" >> "$log"
  fi
done
if kill -0 $pid 2>/dev/null; then
  echo "$(date +%H:%M:%S) INTERRUPTED: hard stop reached, watchdog sent SIGTERM" >> "$log"
  kill -TERM $pid
fi
"""


def found(P, Z, d, log, outdir=HERE):
    T = check_config(P, Z, d)
    order = forest_labelling(P, Z, d)
    U, bf = count_uphill(order, d), count_uphill_bruteforce(order, d)
    k = len(P) + len(Z)
    assert U == bf == 2 ** d + (d - 1) * k, (U, bf, k)
    tag = f"Q{d}_{U}"
    (outdir / f"{tag}.txt").write_text("\n".join(to_strings(order, d)) + "\n")
    (outdir / f"{tag}_config.json").write_text(json.dumps(
        {"d": d, "U": U, "P": sorted(P), "Z": sorted(Z), "T_size": len(T)}))
    log(f"!!! FOUND Q{d}: |P| = {len(P)}, |Z| = {len(Z)}, |D| = {k}, U = {U} "
        f"(evaluator DP == brute force); saved {tag}.txt and {tag}_config.json")
    return "FOUND"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--d", type=int, default=9)
    ap.add_argument("--k", type=int, default=235)
    ap.add_argument("--until", default="16:30", help="hard stop, local HH:MM today")
    ap.add_argument("--log", default=str(HERE / "log.txt"))
    ap.add_argument("--images", type=int, default=4)
    ap.add_argument("--cap8", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--solver", default="cadical195")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--outdir", default=str(HERE), help="where a found labelling is saved")
    a = ap.parse_args()
    if a.selftest:
        _test_totalizer()
        sys.exit()
    res = run(a.d, a.k, a.until, a.log, a.images, a.cap8, a.seed, a.solver, Path(a.outdir))
    print(res)
