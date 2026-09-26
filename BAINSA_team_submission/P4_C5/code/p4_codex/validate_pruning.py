#!/usr/bin/env python3
"""Audit the density-prefix shortcut against complete unpruned searches."""
import hashlib
import json
from pathlib import Path
from checker import solve_size

report=[]
for k in range(3,13):
    baseline=json.loads(Path(f'results_k{k}.json').read_text())
    off=solve_size(k,k-1,no_density_prefix_prune=True)
    base_list=[{key:value for key,value in item.items() if key!='minimal_part'}
               for item in baseline['survivors']]
    keys=('multisets_after_gcd','multisets_after_density',
          'multisets_after_normal_form','sat_calls','SAT','UNSAT')
    same=(off['survivors']==base_list and
          all(off['counts'][key]==baseline['counts'][key] for key in keys))
    canonical=json.dumps(base_list,sort_keys=True,separators=(',',':')).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    report.append({'k':k,'same':same,'base_survivor_sha256':digest})
    print(f'{k}: density-prefix pruning off: {"MATCH" if same else "MISMATCH"}')
    if not same:
        raise AssertionError(f'pruning comparison failed at k={k}')
Path('work').mkdir(exist_ok=True)
Path('work/density_prune_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
