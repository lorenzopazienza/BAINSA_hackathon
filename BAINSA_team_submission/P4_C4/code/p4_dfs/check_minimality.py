#!/usr/bin/env python3
"""Sanity check (NOT part of the proof) for the minimality argument in p4_c5.tex.

Let k-1 = p be prime and r = #primes < p.  We need: for every s with 3 <= s <= r and
every choice of positive integers x_1..x_s with sum <= r (the sizes |P_i|), the
product prod x_i is < k - s.  Equality is allowed only in the case the proof treats
separately.  We also need 2*3*5 = 30 > p, which makes the omega map injective.
This script enumerates all such (s, x) exactly, for every k <= 40 with k-1 prime.
It shows the argument closes as stated exactly for the k listed as "closes".
"""
from itertools import combinations_with_replacement
from math import prod


def primes_below(n):
    return [q for q in range(2, n) if all(q % d for d in range(2, int(q ** .5) + 1))]


for k in range(4, 41):
    p = k - 1
    if primes_below(p + 1)[-1] != p:
        continue
    r = len(primes_below(p))
    injective = 30 > p
    worst = []
    for s in range(3, r + 1):
        for xs in combinations_with_replacement(range(1, r + 1), s):
            if sum(xs) <= r and prod(xs) >= k - s:
                worst.append((s, xs, prod(xs), k - s))
    if not injective:
        verdict = "does not apply (2*3*5 <= p)"
    elif not worst:
        verdict = "closes (strict inequality for all s)"
    else:
        verdict = f"equality/excess cases: {worst}"
    print(f"k={k:2d} p={p:2d} r={r}: {verdict}")
