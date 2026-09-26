"""Independent re-check of the SAT lemmas used by the Problem 2 writeup (Niccolo's cells 2, 3, 5).

  (L5) Q5 has no decycling set with <= 13 vertices.            -> expect UNSAT
  (L6) Q6 has no decycling set with <= 27 vertices.            -> expect UNSAT
  (P6) every decycling set of Q6 with <= 28 vertices lies in one parity class:
       no decycling set with <= 28 vertices meets both classes. -> expect UNSAT
  Sanity: sizes 14 (Q5) and 28 (Q6) without the parity clauses. -> expect SAT (a verified set)

General decycling sets (no independence assumed). Written independently of code/uphill_lower.py:
own cycle enumeration, own lazy loop, no symmetry breaking, no counting constraints.
Clauses: sum x_v <= k (sequential counter, PySAT); every 4-cycle and every chordless 6-cycle of
Q_d meets R (sound: every cycle meets a decycling set); lazy cuts: for every cycle-closing edge of
a spanning forest of Q_d - R, a shortest cycle through it. A model whose complement is acyclic is
checked from scratch (union-find) and reported as SAT. UNSAT is final. Each claim is run with two
solvers (CaDiCaL 1.9.5 and Glucose 4).

Usage: nice python3 verify_L5_L6_P6.py > verify_L5_L6_P6.log
"""
import itertools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from search import forest_cycles, short_cycles  # noqa: E402  (own code, q9_v2/search.py)

from pysat.card import CardEnc, EncType  # noqa: E402
from pysat.formula import IDPool  # noqa: E402
from pysat.solvers import Solver  # noqa: E402


def is_decycling(R, d):
    Rs = set(R)
    parent = {v: v for v in range(2 ** d) if v not in Rs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for v in parent:
        for j in range(d):
            u = v ^ (1 << j)
            if u > v and u in parent:
                a, b = find(u), find(v)
                if a == b:
                    return False
                parent[a] = b
    return True


def decide(d, k, both_parities, solver_name):
    n = 2 ** d
    x = lambda v: v + 1
    s = Solver(name=solver_name)
    s.append_formula(CardEnc.atmost([x(v) for v in range(n)], bound=k, vpool=IDPool(start_from=n + 1),
                                    encoding=EncType.seqcounter).clauses)
    cycles, n4, n6 = short_cycles(d)
    for c in cycles:
        s.add_clause([x(v) for v in c])
    if both_parities:
        s.add_clause([x(v) for v in range(n) if bin(v).count("1") % 2 == 0])
        s.add_clause([x(v) for v in range(n) if bin(v).count("1") % 2 == 1])
    t0, rounds, cuts, seen = time.time(), 0, 0, set()
    while True:
        rounds += 1
        if not s.solve():
            s.delete()
            return "UNSAT", rounds, cuts, time.time() - t0, None
        m = s.get_model()
        R = [v for v in range(n) if m[v] > 0]
        T = [v for v in range(n) if m[v] < 0]
        beta, fund, _ = forest_cycles(T, d, 0)
        if beta == 0:
            assert is_decycling(R, d) and len(R) <= k
            if both_parities:
                assert {bin(v).count("1") % 2 for v in R} == {0, 1}
            s.delete()
            return "SAT", rounds, cuts, time.time() - t0, R
        for c in fund:
            key = tuple(sorted(c))
            if key not in seen:
                seen.add(key)
                s.add_clause([x(v) for v in key])
                cuts += 1


if __name__ == "__main__":
    claims = [("L5", 5, 13, False, "UNSAT"), ("L6", 6, 27, False, "UNSAT"),
              ("P6", 6, 28, True, "UNSAT"),
              ("sanity Q5 size 14", 5, 14, False, "SAT"), ("sanity Q6 size 28", 6, 28, False, "SAT")]
    ok_all = True
    for name, d, k, both, want in claims:
        for solver in ("cadical195", "glucose4"):
            res, rounds, cuts, secs, R = decide(d, k, both, solver)
            ok = res == want
            ok_all &= ok
            extra = ""
            if R is not None:
                par = sorted({bin(v).count("1") % 2 for v in R})
                extra = f", |R| = {len(R)}, parities {par}"
            print(f"{'OK ' if ok else 'BAD'} {name}: Q{d}, |R| <= {k}{', both parities' if both else ''}: "
                  f"{res} ({solver}, {rounds} rounds, {cuts} cuts, {secs:.1f}s{extra})", flush=True)
    print("ALL OK" if ok_all else "MISMATCH", flush=True)
