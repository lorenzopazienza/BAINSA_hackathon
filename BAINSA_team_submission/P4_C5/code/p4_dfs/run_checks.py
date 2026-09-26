#!/usr/bin/env python3
"""Self-tests for sun_dfs.py.

1. Toggles: survivor lists are identical with every pruning rule / speed-up
   switched off (P1 gcd prune, P2 coprime prune, P3 forced-even prune, early NF),
   for small k; and for k = 8..12 with P3 on/off (P1, P2 on).
2. Oracle: the column enumerator agrees with a naive enumeration of all
   multisets of divisors of L (k <= 8).
3. Decisions: the forward-checking decider (with and without interchangeability)
   agrees with the plain backtracking decider on every survivor (k <= 10).
4. Vacuity: with gcd bound [2, k] the checker finds SAT systems for k = 3..6,
   including the classes mod k, and every SAT witness passes the literal check.
"""
import itertools
import time
from types import SimpleNamespace

import sun_dfs as S


def opts(**kw):
    base = dict(no_gcd_prune=False, no_coprime_prune=False, late_nf=False, no_forced_even_prune=False,
                plain_decide=False, no_interchange=False)
    base.update(kw)
    return SimpleNamespace(**base)


def survivors(k, B, **kw):
    o = opts(**kw)
    en = S.ColumnEnumerator(k, B, gcd_prune=not o.no_gcd_prune,
                            coprime_prune=not o.no_coprime_prune, late_nf=o.late_nf,
                            forced_even_prune=not o.no_forced_even_prune)
    return sorted(en.run()), en


t0 = time.time()
# 1. toggles
for k in range(3, 8):
    B = k - 1
    ref, en_ref = survivors(k, B)
    for flags in itertools.product([False, True], repeat=4):
        kw = dict(no_gcd_prune=flags[0], no_coprime_prune=flags[1], late_nf=flags[2],
                  no_forced_even_prune=flags[3])
        if flags[0] and k > 6:          # no gcd pruning explodes beyond k = 6
            continue
        got, en = survivors(k, B, **kw)
        assert got == ref, (k, kw)
        assert en.stage_gcd_nf == en_ref.stage_gcd_nf, (k, kw)
    print(f"[toggles] k={k}: identical survivors and stage counts under all pruning toggles")

for k in range(8, 13):
    ref, en1 = survivors(k, k - 1)
    got, en2 = survivors(k, k - 1, no_forced_even_prune=True)
    assert got == ref and en1.stage_gcd_nf == en2.stage_gcd_nf, k
    print(f"[toggles] k={k}: P3 on/off identical ({len(ref)} survivors; nodes {en2.nodes} -> {en1.nodes})")

# 2. oracle
for k in range(3, 9):
    B = k - 1
    ref, _ = survivors(k, B)
    naive = S.naive_enumerate(k, B)
    assert ref == naive, (k, set(ref) ^ set(naive))
    print(f"[oracle]  k={k}: column enumeration == naive enumeration ({len(ref)} survivors)")
for k in range(3, 7):                    # also for the vacuity bound
    ref, _ = survivors(k, k)
    assert ref == S.naive_enumerate(k, k)
print("[oracle]  vacuity bound B=k, k=3..6: column enumeration == naive enumeration")

# 3. decisions
for k in range(3, 11):
    B = k - 1
    ref, _ = survivors(k, B)
    for s in ref:
        d1 = S.decide(s, B)[0] is not None
        d2 = S.decide(s, B, interchange=False)[0] is not None
        d3 = S.decide(s, B, plain=True)[0] is not None
        assert d1 == d2 == d3, (k, s, d1, d2, d3)
    print(f"[decide]  k={k}: three deciders agree on all {len(ref)} survivors")

# 4. vacuity
for k in range(3, 7):
    ref, _ = survivors(k, k)
    sat = []
    for s in ref:
        sol = S.decide(s, k)[0]
        if sol is not None:
            assert S.verify_solution(s, sol, k)
            sat.append(s)
        assert (sol is not None) == (S.decide(s, k, plain=True)[0] is not None)
    assert tuple([k] * k) in sat, k
    print(f"[vacuity] k={k}, B=k: {len(ref)} survivors, {len(sat)} SAT (incl. {k} classes mod {k}); "
          f"e.g. {sat[:3]}")

print(f"all self-tests passed in {time.time() - t0:.1f}s")
