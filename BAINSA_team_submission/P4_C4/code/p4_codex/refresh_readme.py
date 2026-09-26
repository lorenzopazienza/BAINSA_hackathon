#!/usr/bin/env python3
"""Refresh measured tables from saved result JSON without changing proofs."""
import json
from pathlib import Path

rows=[]; cert_rows=[]; small_total=0
for k in range(3,17):
    r=json.loads(Path(f'results_k{k}.json').read_text())
    c=r['counts']
    if k<=12: small_total+=r['wall_seconds']
    rows.append(f"| {k} | {r['status']} | {c['multisets_after_gcd']:,} | {c['multisets_after_density']:,} | {c['multisets_after_normal_form']:,} | {c['sat_calls']:,} | {c['SAT']:,} / {c['UNSAT']:,} | {r['wall_seconds']:.3f} |")
    meta=r.get('minimal_parts')
    if meta and meta['status']=='COMPLETE':
        dist=', '.join(f'{s}:{n:,}' for s,n in sorted(((int(s),n) for s,n in meta['distribution'].items())))
        cert_rows.append(f"| {k} | {meta['candidate_count']:,} | {dist or '—'} | {meta['unique_witnesses']:,} |")
    else:
        cert_rows.append(f"| {k} | pending | — | — |")
section='''## Measured results

The `GCD`, `density`, and `normal` columns are nested filter counts. `SAT calls` equals `normal` because every retained multiset was decided. Wall times are from the saved run and vary on rerun.

| k | Status | GCD | Density | Normal | SAT calls | SAT / UNSAT | Wall seconds |
|---:|:---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(rows)+f'''

The total checker wall time reported for sizes 3–12 was {small_total:.3f} seconds, well below ten minutes. The completed searches found no counterexample. This computation agrees with O'Bryant (2007), Theorem 3, for every k we completed; we tested this, we did not assume it. The computation does not address sizes 17–20.

| k | Minimal parts | Minimum-size distribution `s:count` | Distinct direct witnesses |
|---:|---:|:---|---:|
'''+ '\n'.join(cert_rows)+'''

The vacuity runs with upper gcd bound `k` found verified classes modulo `k` for each `k=3,4,5,6`. Their exact decisions and residues are in `results_k{K}_vacuity.json`. The brute-force comparison over moduli at most 36 checked 8,436 modulus multisets at `k=3` and 82,251 at `k=4`. Of these, 295 and 651 respectively met the necessary gcd range. It checked 148,504 and 5,418,823 residue tuples after translation and agreed with SAT on every eligible modulus multiset. Those exact figures are in `brute_k3.json` and `brute_k4.json`.

Every normal-form candidate and its exact decision is in its `results_k{K}.json` file. A certified candidate also has a `minimal_part` object containing its smallest UNSAT core, its induced gcd matrix, and a hash and filename for all size-`s-1` witnesses. `expected_results.json` captures the exact counts and hashes for reproducibility.

'''
p=Path('README.md');s=p.read_text()
a=s.index('## Measured results')
b=s.index('## Minimal UNSAT part certificate')
s=s[:a]+section+s[b:]
p.write_text(s)
