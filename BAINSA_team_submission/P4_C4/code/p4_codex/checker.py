#!/usr/bin/env python3
"""Finite modulus enumeration plus SAT residue feasibility for Sun's conjecture.

All integer and fraction comparisons in enumeration are exact. No search over
residue tuples occurs here; the independent small check is in brute_check.py.
"""
import argparse
import hashlib
import json
import math
import os
import time
from functools import lru_cache
from pathlib import Path

from pysat.solvers import Solver
import pysat


def lcm_upto(n):
    return math.lcm(*range(1, n + 1))


def divisors(n):
    """The candidate divisors follow from R1, proved in README.md.

    For g_ij=gcd(m_i,m_j), put m'_i=lcm_{j!=i} g_ij. Each g_ij|m_i,
    so m'_i|m_i. Also g_ij divides both m'_i and m'_j, whereas their
    gcd divides gcd(m_i,m_j)=g_ij. Thus the pairwise gcds are unchanged.
    CRT says disjointness depends only on those gcds and residue
    differences. Since all g_ij<=upper, each m'_i divides lcm(1..upper).
    """
    low = [i for i in range(1, math.isqrt(n) + 1) if n % i == 0]
    return sorted(set(low + [n // i for i in low]))


def density_ok(moduli, period):
    """R2: disjoint classes occupy disjoint residues modulo period.

    As each m_i|period, class i occupies period/m_i residues. Thus
    sum(period/m_i)<=period. Every subfamily obeys the same inequality.
    """
    return sum(period // m for m in moduli) <= period


def prime_powers(n):
    out = []
    p = 2
    while p * p <= n:
        if n % p == 0:
            e = 0
            while n % p == 0:
                e += 1
                n //= p
            out.append((p, e))
        p += 1
    if n > 1:
        out.append((n, 1))
    return out


@lru_cache(maxsize=1024)
def _periodic_mask(modulus, period):
    """Bit positions 0,m,2m,... in Z/period, with m dividing period."""
    if period % modulus:
        raise ValueError('modulus must divide period')
    # Geometric series sum_{t=0}^{period/m-1} 2^(m*t).
    return ((1 << period) - 1) // ((1 << modulus) - 1)


def direct_verify(moduli, residues, period):
    """Directly mark every occupied residue of Z/period with integer bits.

    The mask for a (mod m) has bit x set exactly when x=a+mt in
    {0,...,period-1}. Disjointness is equivalent to each new mask having
    empty intersection with the union of the preceding masks. Python's
    integer bit operations perform this explicit Z/period check in C.
    """
    seen = 0
    for m, a in zip(moduli, residues):
        mask = _periodic_mask(m, period) << (a % m)
        if seen & mask:
            return False
        seen |= mask
    return True


def sat_decide(moduli, period):
    """One-hot base-p digits and a differing-digit witness per pair.

    A witness w_{ijpt} implies unequal selected digits by clauses
    (-w OR -x_i,d OR -x_j,d) for every d. A disjunction of all pair
    witnesses is necessary and sufficient for gcd not dividing the
    residue difference. Fixing all digits of class 0 to zero is sound:
    simultaneous translation preserves all differences.
    """
    clauses = []
    next_var = 0
    def new():
        nonlocal next_var
        next_var += 1
        return next_var
    fact = [dict(prime_powers(m)) for m in moduli]
    digits = {}
    for i, fs in enumerate(fact):
        for p, e in fs.items():
            for t in range(e):
                xs = [new() for _ in range(p)]
                digits[i, p, t] = xs
                clauses.append(xs)
                for d in range(p):
                    for q in range(d + 1, p):
                        clauses.append([-xs[d], -xs[q]])
                if i == 0:
                    clauses.append([xs[0]])
    for i in range(len(moduli)):
        for j in range(i + 1, len(moduli)):
            witnesses = []
            for p in sorted(fact[i].keys() & fact[j].keys()):
                for t in range(min(fact[i][p], fact[j][p])):
                    w = new()
                    witnesses.append(w)
                    xi, xj = digits[i, p, t], digits[j, p, t]
                    for d in range(p):
                        clauses.append([-w, -xi[d], -xj[d]])
            clauses.append(witnesses)  # Empty clause correctly makes gcd=1 UNSAT.
    with Solver(name='cadical153', bootstrap_with=clauses) as solver:
        sat = solver.solve()
        if not sat:
            return {'decision': 'UNSAT'}
        model = set(x for x in solver.get_model() if x > 0)
    residues = []
    for i, fs in enumerate(fact):
        congruences = []
        for p, e in fs.items():
            a = sum(next(d for d, x in enumerate(digits[i, p, t]) if x in model) * p**t
                    for t in range(e))
            congruences.append((a, p**e))
        # The prime-power moduli are coprime; an explicit finite CRT search
        # is tiny here and avoids relying on the SAT encoding in verification.
        residue = next(a for a in range(moduli[i])
                       if all(a % q == b for b, q in congruences))
        residues.append(residue)
    if not direct_verify(moduli, residues, period):
        raise AssertionError(f'SAT witness failed independent Z/L check: {moduli}, {residues}')
    return {'decision': 'SAT', 'residues': residues, 'verified_over_Z_mod_L': True}


def normal_form(moduli, gcd_matrix, indices):
    for pos, idx in enumerate(indices):
        v = 1
        for q, jdx in enumerate(indices):
            if pos != q:
                v = math.lcm(v, gcd_matrix[idx][jdx])
        if v != moduli[idx]:
            return False
    return True


def solve_size(k, upper, limit_seconds=None, result_path=None, no_density_prefix_prune=False, max_nodes=None, first_index=None, stop_event=None):
    start = time.monotonic()
    period = lcm_upto(upper)
    moduli = [d for d in divisors(period) if d >= 2]
    n = len(moduli)
    gcd_matrix = [[math.gcd(a, b) for b in moduli] for a in moduli]
    compat = []
    for i in range(n):
        mask = 0
        for j in range(i, n):
            if 2 <= gcd_matrix[i][j] <= upper:
                mask |= 1 << j
        compat.append(mask)
    suffix = [((1 << n) - 1) ^ ((1 << i) - 1) for i in range(n)]
    weights = [period // m for m in moduli]
    counts = {'multisets_after_gcd': 0, 'multisets_after_density': 0,
              'multisets_after_normal_form': 0, 'sat_calls': 0,
              'SAT': 0, 'UNSAT': 0, 'nodes_visited': 0}
    survivors = []
    timed_out = False
    last_indices = []

    @lru_cache(maxsize=None)
    def count_gcd_completions(depth, allowed):
        """Count complete GCD-compatible descendants omitted by density pruning."""
        if depth == k:
            return 1
        total = 0
        x = allowed
        while x:
            bit = x & -x
            i = bit.bit_length() - 1
            x -= bit
            total += count_gcd_completions(depth + 1, allowed & compat[i] & suffix[i])
        return total

    def visit(depth, allowed, weight, indices):
        nonlocal timed_out, last_indices
        counts['nodes_visited'] += 1
        if max_nodes is not None and counts['nodes_visited'] >= max_nodes:
            timed_out = True
            last_indices = [moduli[i] for i in indices]
            return
        if counts['nodes_visited'] & 4095 == 0 and (limit_seconds is not None or stop_event is not None):
            if (limit_seconds is not None and time.monotonic() - start >= limit_seconds) or (stop_event is not None and stop_event.is_set()):
                timed_out = True
                last_indices = [moduli[i] for i in indices]
                return
        if depth == k:
            counts['multisets_after_gcd'] += 1
            if weight > period:
                return
            counts['multisets_after_density'] += 1
            if not normal_form(moduli, gcd_matrix, indices):
                return
            counts['multisets_after_normal_form'] += 1
            ms = [moduli[i] for i in indices]
            decision = sat_decide(ms, period)
            counts['sat_calls'] += 1
            counts[decision['decision']] += 1
            survivors.append({'moduli': ms, **decision})
            return
        if weight > period and not no_density_prefix_prune:
            counts['multisets_after_gcd'] += count_gcd_completions(depth, allowed)
            return
        x = allowed
        while x and not timed_out:
            bit = x & -x
            i = bit.bit_length() - 1
            x -= bit
            visit(depth + 1, allowed & compat[i] & suffix[i], weight + weights[i], indices + [i])

    if first_index is None:
        visit(0, (1 << n) - 1, 0, [])
    else:
        visit(1, compat[first_index] & suffix[first_index], weights[first_index], [first_index])
    canonical = json.dumps(survivors, sort_keys=True, separators=(',', ':')).encode()
    result = {'k': k, 'gcd_upper_bound': upper, 'L': period,
              'candidate_divisors': len(moduli),
              'all_divisor_multisets': math.comb(n + k - 1, k),
              'density_prefix_prune': not no_density_prefix_prune,
              'status': 'UNFINISHED' if timed_out else 'COMPLETE',
              'counts': counts, 'survivor_sha256': hashlib.sha256(canonical).hexdigest(),
              'survivors': survivors, 'last_prefix_at_timeout': last_indices if timed_out else None,
              'wall_seconds': round(time.monotonic() - start, 3),
              'solver': 'CaDiCaL 1.5.3 via python-sat ' + pysat.__version__}
    if first_index is not None:
        result['first_index'] = first_index
    if result_path:
        Path(result_path).write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('k', type=int)
    ap.add_argument('--upper', type=int, help='default k-1; use k for vacuity test')
    ap.add_argument('--limit-seconds', type=float)
    ap.add_argument('--output')
    ap.add_argument('--no-density-prefix-prune', action='store_true')
    ap.add_argument('--max-nodes', type=int)
    args = ap.parse_args()
    upper = args.upper if args.upper is not None else args.k - 1
    path = args.output or f'results_k{args.k}' + ('_vacuity' if upper == args.k else '') + '.json'
    r = solve_size(args.k, upper, args.limit_seconds, path,
                   args.no_density_prefix_prune, args.max_nodes)
    print(json.dumps({key: r[key] for key in ('k', 'gcd_upper_bound', 'status', 'counts',
                                                'survivor_sha256', 'wall_seconds')}, sort_keys=True))

if __name__ == '__main__':
    main()
