"""Computer-assisted lemmas on decycling sets of Q_5 and Q_6 (Problem 2, cells 2-5).

Usage:  python uphill_lower.py            (needs python-sat and networkx)

Claims checked (a decycling set R is a vertex set whose complement induces a forest):
  (L5)  Q_5 has no decycling set of size <= 13;
  (L6)  Q_6 has no decycling set of size <= 27;
  (P6)  every decycling set of Q_6 of size <= 28 lies inside one parity class
        (no such set contains both an even-weight and an odd-weight vertex);
  (D9)  exact arithmetic behind the Delsarte bound |C| <= 25 of cell 5 (no SAT).

Method (counterexample-guided SAT).  Variable x_v means "v in R".  The formula
F contains
  (a) sum_v x_v <= r                    (cardinality, sequential counter);
  (b) one clause OR_{v in K} x_v for every 4-cycle K of Q_d;
  (c) clauses OR_{v in K} x_v for cycles K added during the loop;
  (d) for (P6) only: OR_{v odd} x_v and OR_{v even} x_v.
Every clause of type (b), (c) says "R meets the cycle K", which every
decycling set satisfies.  So every decycling set of size <= r (and, for (P6),
containing vertices of both parities) is a model of F at every stage.
Loop: ask the solver for a model R; if Q_d - R has a cycle, add the clauses of
a cycle basis of each cyclic component (type (c)) and repeat; if Q_d - R is a
forest, R is a decycling set (reported; never happens here).  The loop stops,
because each round adds a clause violated by the current model and there are
finitely many models.  When the solver answers UNSAT, F has no model, so no
set of the kind described exists.

(L5), (L6) are run with two independent SAT solvers (CaDiCaL and Glucose),
(P6) with CaDiCaL.  Wall clock on a laptop: about 2-3 minutes in total.
"""
import time

import networkx as nx
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical153, Glucose4


def hypercube(d):
    n = 1 << d
    edges = [(v, v ^ (1 << i)) for v in range(n) for i in range(d) if v < v ^ (1 << i)]
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)
    return G


def squares(d):
    for v in range(1 << d):
        for i in range(d):
            for j in range(i + 1, d):
                if not (v >> i) & 1 and not (v >> j) & 1:
                    yield [v, v | 1 << i, v | 1 << j, v | 1 << i | 1 << j]


def search(d, r, Solver, mixed_parity=False):
    """Return a decycling set of Q_d of size <= r (containing both parities if
    mixed_parity), or None if the solver proves that there is none."""
    n = 1 << d
    G = hypercube(d)
    x = lambda v: v + 1
    pool = IDPool(start_from=n + 1)
    clauses = CardEnc.atmost([x(v) for v in range(n)], bound=r, vpool=pool,
                             encoding=EncType.seqcounter).clauses
    clauses += [[x(v) for v in K] for K in squares(d)]
    if mixed_parity:
        clauses.append([x(v) for v in range(n) if bin(v).count("1") % 2 == 1])
        clauses.append([x(v) for v in range(n) if bin(v).count("1") % 2 == 0])
    rounds = 0
    with Solver(bootstrap_with=clauses) as s:
        while s.solve():
            rounds += 1
            model = s.get_model()
            R = {v for v in range(n) if model[v] > 0}
            H = G.subgraph(v for v in range(n) if v not in R)
            cycles = nx.cycle_basis(H)
            if not cycles:
                return R, rounds
            for K in cycles:
                s.add_clause([x(v) for v in K])
    return None, rounds


def delsarte_certificate():
    """(D9): exact check of the Krawtchouk values and of the dual certificate
    (6 K_1 + 3 K_2 + K_3)/10 used in Lemma "Delsarte bound" (n = 9, distances 4, 6, 8)."""
    from fractions import Fraction
    from math import comb
    n = 9
    K = lambda k, i: sum((-1) ** j * comb(i, j) * comb(n - i, k - j) for j in range(k + 1))
    # K_k(i) must equal sum over |w| = k of (-1)^{x.w} for any x of weight i
    for i in range(n + 1):
        x = (1 << i) - 1
        for k in range(n + 1):
            direct = sum((-1) ** bin(x & w).count("1")
                         for w in range(1 << n) if bin(w).count("1") == k)
            assert direct == K(k, i)
    lam = lambda i: Fraction(6 * K(1, i) + 3 * K(2, i) + K(3, i), 10)
    assert lam(0) == Fraction(246, 10) and all(lam(i) == -1 for i in (4, 6, 8))
    print("(D9) Krawtchouk table and certificate verified: Lambda(0) = 24.6, "
          "Lambda(4) = Lambda(6) = Lambda(8) = -1, so |C| <= 25", flush=True)


def main():
    delsarte_certificate()
    runs = [("L5", 5, 13, False, (Cadical153, Glucose4)),
            ("L6", 6, 27, False, (Cadical153, Glucose4)),
            ("P6", 6, 28, True, (Cadical153,))]
    for name, d, r, mixed, solvers in runs:
        for Solver in solvers:
            t = time.time()
            R, rounds = search(d, r, Solver, mixed)
            what = "mixed-parity " if mixed else ""
            verdict = f"UNSAT: no {what}decycling set" if R is None else f"FOUND {sorted(R)}"
            print(f"({name}) Q_{d}, |R| <= {r}, {Solver.__name__}: {verdict} "
                  f"({rounds} rounds, {time.time() - t:.1f} s)", flush=True)
            assert R is None


if __name__ == "__main__":
    main()
