"""Brute-force sanity checks for Problem 4 (k = 3, 4). Not part of the proofs.

Disjointness is always checked LITERALLY, from the definition, never via the
criterion (*) gcd(m, n) | a - b.  Write x = a + m t; the classes a mod m and b mod n
meet iff b - a = m t (mod n) for some integer t.  For each pair (m, n) the set
{m t mod n : 0 <= t < n} is listed explicitly (it is periodic in t with period n).
The criterion (*) is only compared against this literal test, in check_criterion().
"""
from math import gcd
from itertools import combinations
import time


def disjoint_literal(m, a, n, b):
    """a mod m and b mod n share no integer (checked over one period lcm(m, n))."""
    return all((a + m * t - b) % n for t in range(n // gcd(m, n)))


def disjoint(m, a, n, b):
    """Criterion (*); used ONLY in check_criterion(), never in the searches."""
    return (a - b) % gcd(m, n) != 0


_MEET = {}


def disjoint_def(m, a, n, b):
    """Literal test from the definition: no t with a + m t = b (mod n)."""
    key = (m, n)
    if key not in _MEET:
        hit = [False] * n
        for t in range(n):
            hit[(m * t) % n] = True
        _MEET[key] = hit
    return not _MEET[key][(b - a) % n]


def check_criterion(M=40):
    for m in range(1, M + 1):
        for n in range(1, M + 1):
            for a in range(m):
                for b in range(n):
                    lit = disjoint_literal(m, a, n, b)
                    assert disjoint_def(m, a, n, b) == lit
                    assert disjoint(m, a, n, b) == lit
    print(f"literal tests agree with each other and with criterion (*) for all moduli <= {M}")


def search(k, M, literal=False):
    """Search for k pairwise disjoint classes with moduli <= M and all pairwise
    gcds < k.  Residues: a_1 = 0 (translate), others range over all of Z/m_i.
    Disjointness: disjoint_def (table from the definition), or with literal=True
    the element-by-element check over one period."""
    test = disjoint_literal if literal else disjoint_def
    found = []

    def extend(ms, chosen):
        if len(chosen) == len(ms):
            found.append(list(zip(ms, chosen)))
            return True
        i = len(chosen)
        for a in range(ms[i]) if i else [0]:
            if all(test(ms[j], chosen[j], ms[i], a) for j in range(i)):
                if extend(ms, chosen + [a]):
                    return True
        return False

    def moduli(prefix, start):
        if len(prefix) == k:
            yield prefix
            return
        for m in range(start, M + 1):
            if all(gcd(m, p) < k for p in prefix):
                yield from moduli(prefix + [m], m)

    n_tuples = 0
    for ms in moduli([], 1):
        n_tuples += 1
        extend(ms, [])
    return n_tuples, found


if __name__ == "__main__":
    check_criterion()
    for k, M, lit in [(3, 60, False), (3, 20, True), (4, 60, False), (4, 20, True)]:
        t = time.time()
        n, found = search(k, M, lit)
        print(f"k={k}, moduli<={M}, {'period-by-period check' if lit else 'definition table'}: "
              f"{n} moduli tuples, {len(found)} counterexamples ({time.time() - t:.1f}s)")
        assert not found, found[:3]
    # the bound is attained: k classes with max pairwise gcd exactly k
    for k in (3, 4):
        system = [(k, r) for r in range(k)]
        assert all(disjoint_literal(m, a, n, b) for (m, a), (n, b) in combinations(system, 2))
    print("sharpness: {r mod k : 0 <= r < k} is disjoint with all gcds = k (k = 3, 4)")
