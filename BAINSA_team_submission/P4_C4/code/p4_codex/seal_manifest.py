#!/usr/bin/env python3
"""Save only deterministic, auditable fields as expected_results.json."""
import json
from pathlib import Path

base=('k','gcd_upper_bound','L','candidate_divisors','all_divisor_multisets',
      'density_prefix_prune','status','counts','survivor_sha256',
      'last_prefix_at_timeout','solver')
minimal=('status','records_file','records_sha256','witness_file',
         'witness_sha256','candidate_count','distribution','unique_witnesses',
         'selector_sat_calls')
manifest={}
for k in range(3,17):
    path=Path(f'results_k{k}.json'); r=json.loads(path.read_text())
    entry={field:r[field] for field in base}
    if 'parallel' in r: entry['parallel']=r['parallel']
    if 'minimal_parts' in r:
        entry['minimal_parts']={field:r['minimal_parts'][field] for field in minimal}
    manifest[path.name]=entry
for k in range(3,7):
    path=Path(f'results_k{k}_vacuity.json'); r=json.loads(path.read_text())
    entry={field:r[field] for field in base}
    if 'minimal_parts' in r:
        entry['minimal_parts']={field:r['minimal_parts'][field] for field in minimal}
    manifest[path.name]=entry
for k in (3,4):
    path=Path(f'brute_k{k}.json'); r=json.loads(path.read_text())
    manifest[path.name]={field:r[field] for field in
        ('k','max_modulus','status','counts','decision_sha256')}
Path('expected_results.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('sealed',len(manifest),'result files')
