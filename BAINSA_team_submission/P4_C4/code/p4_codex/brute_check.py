#!/usr/bin/env python3
"""Independent direct enumeration for k=3,4, with all moduli <=36.

For each unordered modulus tuple with the required gcd range, enumerate all
residue tuples modulo those moduli after fixing the first residue to zero.
This represents *all* residue tuples: subtract the original first residue
from every class. No R1, R2, or normal-form reduction is used.
"""
import hashlib
import itertools
import json
import math
import time
from pathlib import Path
from checker import sat_decide


def check(k):
    start = time.monotonic()
    counts = {'all_moduli_multisets': 0, 'gcd_eligible_multisets': 0,
              'residue_tuples_tested_after_translation': 0,
              'brute_SAT': 0, 'sat_calls': 0, 'SAT_agreements': 0,
              'UNSAT_agreements': 0}
    decisions = []
    for ms in itertools.combinations_with_replacement(range(1, 37), k):
        counts['all_moduli_multisets'] += 1
        pairs = [(i, j, math.gcd(ms[i], ms[j])) for i in range(k) for j in range(i+1, k)]
        if not all(2 <= g <= k-1 for _, _, g in pairs):
            continue
        counts['gcd_eligible_multisets'] += 1
        brute_witness = None
        for tail in itertools.product(*(range(m) for m in ms[1:])):
            counts['residue_tuples_tested_after_translation'] += 1
            aa = (0,) + tail
            if all((aa[i] - aa[j]) % g != 0 for i, j, g in pairs):
                brute_witness = aa
                counts['brute_SAT'] += 1
                break
        sat = sat_decide(ms, math.lcm(*ms))
        counts['sat_calls'] += 1
        if (brute_witness is not None) != (sat['decision'] == 'SAT'):
            raise AssertionError(f'brute/SAT mismatch: {ms}, {brute_witness}, {sat}')
        counts['SAT_agreements' if brute_witness else 'UNSAT_agreements'] += 1
        decisions.append((ms, sat['decision']))
    digest = hashlib.sha256(json.dumps(decisions, separators=(',', ':')).encode()).hexdigest()
    result = {'k': k, 'max_modulus': 36, 'status': 'COMPLETE', 'counts': counts,
              'decision_sha256': digest, 'wall_seconds': round(time.monotonic()-start, 3),
              'method': 'all residue tuples after common translation; no R1/R2 reduction'}
    Path(f'brute_k{k}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))

if __name__ == '__main__':
    for k in (3, 4):
        check(k)
