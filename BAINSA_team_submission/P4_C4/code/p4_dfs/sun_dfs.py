#!/usr/bin/env python3
r"""
p4_dfs -- an exhaustive, SAT-free checker for Sun's conjecture for small k.

Claim checked, for a given k and gcd bound B (B = k-1 for the conjecture):

    There are no k pairwise disjoint residue classes a_1 mod m_1, ..., a_k mod m_k
    with 2 <= gcd(m_i, m_j) <= B for all i != j.

(For B = k-1 this is Sun's conjecture at k.  B = k is the "vacuity test": the
classes r mod k, 0 <= r < k, must then be found.)

============================================================================
MATHEMATICAL JUSTIFICATION (every step used by the code)
============================================================================

(0) Criterion.  a mod m and b mod n are disjoint  <=>  gcd(m, n) does not divide a - b.
    Proof: if x is in both, then a = x = b mod g.  Conversely, if g | a - b, write
    a - b = g t and um + vn = g (Bezout); then x = a - umt = b + vnt lies in both.

(1) Normal form.  Let a family be disjoint, g_ij = gcd(m_i, m_j), and put
    n_i = lcm_{j != i} g_ij.  Then n_i | m_i, since every g_ij divides m_i.  Moreover
    gcd(n_i, n_j) = g_ij: g_ij divides both n_i and n_j, and gcd(n_i, n_j) divides
    gcd(m_i, m_j) = g_ij.  By (0), a_i mod n_i (same a_i) is again a disjoint family
    with the same pairwise gcds.  It also satisfies n_i = lcm_{j != i} gcd(n_i, n_j).
    Hence WLOG every m_i is in NORMAL FORM: m_i = lcm_{j != i} gcd(m_i, m_j).

(2) Finite range.  In normal form, if every g_ij <= B then m_i | L := lcm(1..B).
    Every prime p dividing some m_i is <= B, and v_p(m_i) <= v_p(L) = floor(log_p B).

(3) Density.  Disjoint classes satisfy sum 1/m_i <= 1.  In [0, M) with
    M = lcm(m_1..m_k), class i has exactly M/m_i elements, and the classes are disjoint.

(4) Normal form, one prime at a time.  Write e_i = v_p(m_i).  Since
    v_p(lcm_j gcd(m_i, m_j)) = max_{j != i} min(e_i, e_j), normal form holds iff, for
    every prime p and every i with e_i > 0, some j != i has e_j >= e_i.  Equivalently,
    for every prime p the maximum of (e_1..e_k) is 0 or is attained at least twice.

    So the finite set to examine is
        C(k, B) = { multisets {m_1..m_k} of divisors of L :
                    2 <= gcd(m_i, m_j) <= B for all i != j,
                    normal form (4), sum 1/m_i <= 1 }.
    Its members are the SURVIVORS.  Any counterexample yields, via (1)-(3), residues
    for some survivor.  So the claim holds iff every survivor is UNSAT.

============================================================================
ENUMERATION (by prime-exponent columns, not by sorted prefixes of moduli)
============================================================================

A multiset of k moduli is a k x r matrix E of exponents; column t is the prime
primes[t], and the primes are processed in decreasing order.  Row i is the
exponent vector of m_i.

Canonical form.  We generate exactly the matrices whose rows are in
lexicographically NON-INCREASING order.  Each multiset has exactly one such
matrix (sort its rows; equal rows are interchangeable).  Suppose columns 0..t-1
are fixed and their rows are lex non-increasing.  Rows with equal prefixes then
form contiguous blocks.  The full matrix is lex non-increasing iff, inside every
block, column t is non-increasing, and so on recursively.  The code keeps a
boolean "start[i]" = row i begins a new block, and allows e_i <= e_{i-1} only
when i is not a block start.

Filters applied as the tree is built.  None changes the final output; each
can be switched off:
  (P1) gcd bound (--no-gcd-prune).  The partial gcd G_ij, i.e. the product over
       processed primes of p^min(e_i, e_j), divides the final gcd.  If
       G_ij > B, no completion satisfies gcd <= B.  When off, the bound is checked
       only at the leaves.
  (P2) coprime pairs at the last prime (--no-coprime-prune).  At the last prime
       column, if e_i = 0 and G_ij = 1 for some j != i, the pair (i, j) ends coprime
       whatever else happens.  (For j > i, G_ij does not yet include the last prime,
       but min(0, e_j) = 0 adds nothing.)  When off, gcd >= 2 is checked only at
       the leaves.
  (P3) forced-even rows (--no-forced-even-prune).  The primes are processed in
       decreasing order, so the last column is p = 2.  When column r-2 is complete,
       call row i FORCED if G_ij = 1 for some j != i.  Only the prime 2 remains, so
       a forced row must have e_i >= 1 at p = 2, or it ends coprime to j.  If two
       forced rows i != j have 2 * G_ij > B, their final gcd is >= 2 G_ij > B, and no
       completion is valid.  So the subtree is pruned.  (When off, the conflict is
       found later by P1 and P2, or at the leaves.)  The same test also runs inside
       column r-2.  Once rows a, b <= i have been set in that column, G_ab is final up
       to the prime 2.  So "a has a partner b <= i with G_ab = 1" already forces
       e_a >= 1 at p = 2, and the test applies to the rows forced so far.
  (NF) The per-prime normal-form test (4) is applied when a column is complete.
       It depends only on that column, so it is exactly the normal-form filter,
       applied early.  (--late-nf moves it to the leaves; same output.)
At each leaf all conditions of C(k, B) are re-checked in full: 2 <= gcd <= B for
all pairs, normal form recomputed from the moduli, and sum 1/m_i <= 1 with exact
Fractions.

============================================================================
DECISION (existence of residues) by backtracking; no SAT
============================================================================

Translation x -> x - a_first maps solutions to solutions, so the first chosen
class gets a = 0.  Domains D_i are subsets of Z/m_i (numpy booleans).  Placing
a_j = x removes from each unplaced D_i the values y with y = x mod g_ij.  This is
exactly the pairwise condition (0), i.e. forward checking; it is exact, not a
heuristic.  An empty domain means backtrack.

Interchangeability (--no-interchange switches it off).  Let P be the placed set and
i an unplaced class.  Put U_i = lcm{ g_ij : j unplaced, j != i }, which divides m_i.
If x, x' in D_i and x = x' mod U_i, then x can be extended to a full solution iff
x' can.  Reason: both are consistent with P (they are in D_i).  The constraint
with an unplaced j depends only on x mod g_ij, and g_ij | U_i.  So it suffices to
try one value per class of D_i mod U_i.

Variable order: the unplaced class with the fewest candidate values (after
interchangeability) goes first; ties go to the larger "gcd degree" sum_j log g_ij.
Any order is correct.  With --plain-decide the search uses none of the above: a
static order by gcd degree, a_1 = 0, then each a_i over all of Z/m_i, checked
against the placed classes.  This is used to cross-check decisions.

Every SAT answer is verified literally: for each pair, no element of one period
of class i lies in class j.  The literal check does not use (0).
"""

import argparse
import hashlib
import json
import math
import sys
import time
from fractions import Fraction
from itertools import combinations, combinations_with_replacement

import numpy as np

sys.setrecursionlimit(10000)


# ----------------------------------------------------------------- utilities
def primes_upto(n):
    return [p for p in range(2, n + 1) if all(p % q for q in range(2, int(p ** 0.5) + 1))]


def lcm_list(xs):
    out = 1
    for x in xs:
        out = out * x // math.gcd(out, x)
    return out


def canonical_json(survivors):
    """Canonical text of a survivor list: list of ascending tuples, sorted
    lexicographically, compact JSON (separators ',' ':'), no spaces."""
    return json.dumps([list(s) for s in sorted(survivors)], separators=(",", ":"))


def in_C(ms, B):
    """Full membership test for C(k, B), straight from the definition."""
    k = len(ms)
    for i, j in combinations(range(k), 2):
        g = math.gcd(ms[i], ms[j])
        if not 2 <= g <= B:
            return False
    for i in range(k):
        if ms[i] != lcm_list([math.gcd(ms[i], ms[j]) for j in range(k) if j != i]):
            return False
    return sum(Fraction(1, m) for m in ms) <= 1


# ----------------------------------------------------------------- enumeration
class _EnumTimeout(Exception):
    pass


class ColumnEnumerator:
    def __init__(self, k, B, gcd_prune=True, coprime_prune=True, late_nf=False, time_limit=None,
                 forced_even_prune=True):
        self.k, self.B = k, B
        self.L = lcm_list(range(1, B + 1))
        self.primes = sorted(primes_upto(B), reverse=True)
        self.vmax = [_vp_floor(B, p) for p in self.primes]
        self.gcd_prune, self.coprime_prune, self.late_nf = gcd_prune, coprime_prune, late_nf
        self.time_limit = time_limit
        self.forced_even_prune = forced_even_prune

    def run(self):
        k, r = self.k, len(self.primes)
        self.E = [[0] * k for _ in range(r)]
        self.G = [[1] * k for _ in range(k)]
        self.nodes = 0
        self.leaves = 0
        self.survivors = []
        self.stage_gcd_nf = 0   # leaves passing gcd in [2,B] and normal form
        self.col0_done = 0          # completed subtrees below a full first column
        self.forced = [False] * k   # P3 bookkeeping inside column r-2
        self.finished = True
        self._t0 = time.time()
        start = [True] + [False] * (k - 1)
        if r == 0:
            return []
        try:
            self._assign(0, 0, start)
        except _EnumTimeout:
            self.finished = False
        return self.survivors

    def _assign(self, t, i, start):
        k, B, G = self.k, self.B, self.G
        col = self.E[t]
        if i == k:                              # column t complete
            if not self.late_nf:
                mx = max(col)
                if mx > 0 and col.count(mx) < 2:
                    return
            if t + 1 == len(self.primes):
                self._leaf()
                if t == 0:
                    self.col0_done += 1
                return
            if self.forced_even_prune and t + 2 == len(self.primes) and self.primes[-1] == 2:
                forced = [i2 for i2 in range(k) if any(G[i2][j] == 1 for j in range(k) if j != i2)]
                for a_, b_ in combinations(forced, 2):
                    if 2 * G[a_][b_] > B:
                        if t == 0:
                            self.col0_done += 1
                        return
            newstart = [start[j] or col[j] != col[j - 1] for j in range(k)]
            newstart[0] = True
            self._assign(t + 1, 0, newstart)
            if t == 0:
                self.col0_done += 1
            return
        self.nodes += 1
        if self.time_limit is not None and self.nodes % 65536 == 0 \
                and time.time() - self._t0 > self.time_limit:
            raise _EnumTimeout
        p = self.primes[t]
        last = t + 1 == len(self.primes)
        # P3 inside column r-2: for rows a, b <= i already set in this column, G_ab is
        # final up to the prime 2, so "a has a partner b <= i with G_ab = 1" already
        # forces e_a >= 1 at p = 2; two such rows with 2 G_ab > B cannot both be valid.
        early_p3 = (self.forced_even_prune and t + 2 == len(self.primes)
                    and self.primes[-1] == 2)
        forced = self.forced
        hi = self.vmax[t] if start[i] else col[i - 1]
        Gi = G[i]
        for e in range(hi, -1, -1):
            if e == 0 and self.coprime_prune and last \
                    and any(Gi[j] == 1 for j in range(k) if j != i):
                continue
            changed = []
            ok = True
            if e:
                for j in range(i):
                    ej = col[j]
                    if ej:
                        ng = Gi[j] * p ** (e if e < ej else ej)
                        if self.gcd_prune and ng > B:
                            ok = False
                            break
                        changed.append((j, Gi[j]))
                        Gi[j] = G[j][i] = ng
            newly = []
            if ok and early_p3:
                if not forced[i] and any(Gi[j] == 1 for j in range(i)):
                    newly.append(i)
                newly.extend(j for j in range(i) if Gi[j] == 1 and not forced[j])
                for a_ in newly:
                    forced[a_] = True
                for a_ in newly:
                    Ga = G[a_]
                    if any(forced[b_] and b_ != a_ and 2 * Ga[b_] > B for b_ in range(i + 1)):
                        ok = False
                        break
            if ok:
                col[i] = e
                self._assign(t, i + 1, start)
            for a_ in newly:
                forced[a_] = False
            for j, old in changed:
                Gi[j] = G[j][i] = old
        col[i] = 0

    def _leaf(self):
        self.leaves += 1
        k, B = self.k, self.B
        ms = []
        for i in range(k):
            m = 1
            for t, p in enumerate(self.primes):
                m *= p ** self.E[t][i]
            ms.append(m)
        # full re-check of every defining condition except density
        for i, j in combinations(range(k), 2):
            g = math.gcd(ms[i], ms[j])
            assert g == self.G[i][j]
            if not 2 <= g <= B:
                return
        for i in range(k):
            if ms[i] != lcm_list([math.gcd(ms[i], ms[j]) for j in range(k) if j != i]):
                return
        self.stage_gcd_nf += 1
        # exact density test: sum 1/m_i <= 1  <=>  sum L/m_i <= L  (every m_i divides L)
        L = self.L
        if sum(L // m for m in ms) <= L:
            self.survivors.append(tuple(sorted(ms)))


def _vp_floor(B, p):
    e = 0
    while p ** (e + 1) <= B:
        e += 1
    return e


def naive_enumerate(k, B):
    """Reference oracle for small k only: all multisets of divisors >= 2 of L."""
    L = lcm_list(range(1, B + 1))
    divs = [d for d in range(2, L + 1) if L % d == 0]
    return sorted(c for c in combinations_with_replacement(divs, k) if in_C(list(c), B))


# ----------------------------------------------------------------- decision
def literal_disjoint(m, a, n, b):
    return all((a + m * t - b) % n for t in range(n // math.gcd(m, n)))


def verify_solution(ms, a, B):
    k = len(ms)
    for i, j in combinations(range(k), 2):
        g = math.gcd(ms[i], ms[j])
        if not (2 <= g <= B and literal_disjoint(ms[i], a[i], ms[j], a[j])):
            return False
    return True


class Decider:
    def __init__(self, ms, interchange=True):
        self.ms = list(ms)
        k = self.k = len(ms)
        self.g = [[math.gcd(ms[i], ms[j]) if i != j else 0 for j in range(k)] for i in range(k)]
        self.deg = [sum(math.log(self.g[i][j]) for j in range(k) if j != i) for i in range(k)]
        self.interchange = interchange
        self.nodes = 0

    def solve(self):
        k = self.k
        first = max(range(k), key=lambda i: (self.deg[i], self.ms[i]))
        doms = [np.ones(m, dtype=bool) for m in self.ms]
        a = [None] * k
        a[first] = 0
        unplaced = [i for i in range(k) if i != first]
        for j in unplaced:                       # forward-check a_first = 0
            g = self.g[first][j]
            doms[j][0::g] = False
        sol = self._rec(doms, a, unplaced)
        return sol

    def _candidates(self, i, doms, unplaced):
        m = self.ms[i]
        if self.interchange:
            U = lcm_list([self.g[i][j] for j in unplaced if j != i])
        else:
            U = m
        d = doms[i]
        if U == m:
            return np.flatnonzero(d)
        rep = d.reshape(m // U, U)           # row q, column r  <->  value qU + r
        hit = rep.any(axis=0)
        rs = np.flatnonzero(hit)
        q = rep[:, rs].argmax(axis=0)        # first q with value in domain
        return rs + q * U

    def _rec(self, doms, a, unplaced):
        self.nodes += 1
        if not unplaced:
            return list(a)
        best = None
        for i in unplaced:
            c = self._candidates(i, doms, unplaced)
            if len(c) == 0:
                return None
            key = (len(c), -self.deg[i])
            if best is None or key < best[0]:
                best = (key, i, c)
        _, i, cands = best
        rest = [j for j in unplaced if j != i]
        for x in cands:
            x = int(x)
            newdoms = list(doms)
            dead = False
            for j in rest:
                g = self.g[i][j]
                dj = doms[j].copy()
                dj[x % g::g] = False
                if not dj.any():
                    dead = True
                    break
                newdoms[j] = dj
            if dead:
                continue
            a[i] = x
            sol = self._rec(newdoms, a, rest)
            if sol is not None:
                return sol
            a[i] = None
        return None


def plain_decide(ms):
    """Cross-check decider: static order, full domains, no forward checking."""
    k = len(ms)
    g = [[math.gcd(ms[i], ms[j]) for j in range(k)] for i in range(k)]
    deg = [sum(math.log(g[i][j]) for j in range(k) if j != i) for i in range(k)]
    order = sorted(range(k), key=lambda i: (-deg[i], -ms[i]))
    a = {}

    def rec(t):
        if t == k:
            return True
        i = order[t]
        rng = [0] if t == 0 else range(ms[i])
        for x in rng:
            if all((x - a[j]) % g[i][j] for j in order[:t]):
                a[i] = x
                if rec(t + 1):
                    return True
        a.pop(i, None)
        return False

    return [a[i] for i in range(k)] if rec(0) else None


def decide(ms, B, plain=False, interchange=True):
    if plain:
        sol, nodes = plain_decide(ms), None
    else:
        d = Decider(ms, interchange=interchange)
        sol, nodes = d.solve(), d.nodes
    if sol is not None:
        assert verify_solution(ms, sol, B), ("claimed solution fails literal check", ms, sol)
    return sol, nodes


# ----------------------------------------------------------------- driver
def run_k(k, B, args):
    t0 = time.time()
    en = ColumnEnumerator(k, B, gcd_prune=not args.no_gcd_prune,
                          coprime_prune=not args.no_coprime_prune, late_nf=args.late_nf,
                          time_limit=args.enum_time_limit,
                          forced_even_prune=not args.no_forced_even_prune)
    survivors = sorted(en.run())
    t_enum = time.time() - t0
    assert len(survivors) == len(set(survivors)), "duplicate survivor: canonical form broken"
    for s in survivors:
        assert in_C(list(s), B)

    t1 = time.time()
    records, n_sat, n_undec, dec_nodes = [], 0, 0, 0
    limit = 0.0 if args.enum_only else args.decide_time_limit
    for idx, s in enumerate(survivors):
        if limit is not None and time.time() - t1 >= limit:
            records.append({"moduli": list(s), "decision": "UNDECIDED"})
            n_undec += 1
            continue
        sol, nodes = decide(s, B, plain=args.plain_decide, interchange=not args.no_interchange)
        dec_nodes += nodes or 0
        rec = {"moduli": list(s), "decision": "SAT" if sol else "UNSAT"}
        if sol:
            n_sat += 1
            rec["residues"] = sol
        records.append(rec)
        if not args.quiet and (idx + 1) % 1000 == 0:
            print(f"  [k={k}] decided {idx + 1}/{len(survivors)} ({time.time() - t1:.0f}s)",
                  file=sys.stderr, flush=True)
    t_dec = time.time() - t1

    cj = canonical_json(survivors)
    out = {
        "k": k,
        "status": "COMPLETE" if (n_undec == 0 and en.finished) else "UNFINISHED",
        "enumeration_finished": en.finished,
        "first_column_subtrees_completed": en.col0_done,
        "gcd_bound": [2, B],
        "L": en.L,
        "primes_processing_order": en.primes,
        "options": {"gcd_prune": not args.no_gcd_prune, "coprime_prune": not args.no_coprime_prune,
                    "forced_even_prune": not args.no_forced_even_prune,
                    "late_nf": args.late_nf, "plain_decide": args.plain_decide,
                    "interchange": not args.no_interchange},
        "counts": {
            "enumeration_nodes": en.nodes,
            "complete_exponent_matrices(leaves)": en.leaves,
            "gcd_in_range_and_normal_form": en.stage_gcd_nf,
            "survivors(density<=1)": len(survivors),
            "SAT": n_sat,
            "UNSAT": len(survivors) - n_sat - n_undec,
            "UNDECIDED": n_undec,
            "decision_nodes": dec_nodes if not args.plain_decide else None,
        },
        "wall_clock_s": {"enumeration": round(t_enum, 3), "decision": round(t_dec, 3),
                         "total": round(t_enum + t_dec, 3)},
        "survivors_sha256": hashlib.sha256(cj.encode()).hexdigest(),
        "survivors": records,
    }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("ks", nargs="+", type=int)
    ap.add_argument("--bound-offset", type=int, default=-1,
                    help="gcd bound B = k + offset (default -1: Sun's conjecture; 0: vacuity test)")
    ap.add_argument("--no-gcd-prune", action="store_true")
    ap.add_argument("--no-coprime-prune", action="store_true")
    ap.add_argument("--no-forced-even-prune", action="store_true")
    ap.add_argument("--late-nf", action="store_true")
    ap.add_argument("--plain-decide", action="store_true")
    ap.add_argument("--no-interchange", action="store_true")
    ap.add_argument("--decide-time-limit", type=float, default=None,
                    help="stop deciding after this many seconds; the rest is marked UNDECIDED")
    ap.add_argument("--enum-only", action="store_true", help="enumerate survivors, decide none")
    ap.add_argument("--enum-time-limit", type=float, default=None,
                    help="stop the enumeration after this many seconds (result is UNFINISHED)")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    for k in args.ks:
        B = k + args.bound_offset
        out = run_k(k, B, args)
        c = out["counts"]
        print(f"k={k:2d} B={B:2d}  nodes={c['enumeration_nodes']:>10}  leaves={c['complete_exponent_matrices(leaves)']:>8}"
              f"  gcd+NF={c['gcd_in_range_and_normal_form']:>7}  survivors={c['survivors(density<=1)']:>6}"
              f"  SAT={c['SAT']}  UNSAT={c['UNSAT']}  UNDECIDED={c['UNDECIDED']}  t_enum={out['wall_clock_s']['enumeration']}s"
              f"  t_dec={out['wall_clock_s']['decision']}s  sha256={out['survivors_sha256'][:16]}",
              flush=True)
        if args.outdir:
            tag = "sun" if args.bound_offset == -1 else f"B{args.bound_offset:+d}"
            if out["status"] != "COMPLETE":
                tag += "_UNFINISHED"
            with open(f"{args.outdir}/k{k:02d}_{tag}.json", "w") as f:
                json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
