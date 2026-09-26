#!/usr/bin/env python3
"""Materialize each minimal core's induced gcd matrix in result JSON."""
import hashlib
import json
import math
import sys
from pathlib import Path

for k in map(int,sys.argv[1:]):
    path=Path(f'results_k{k}.json')
    result=json.loads(path.read_text())
    if result['status']!='COMPLETE' or result.get('minimal_parts',{}).get('status')!='COMPLETE':
        raise AssertionError(f'k={k} is not fully certified')
    for item in result['survivors']:
        if item['decision']!='UNSAT':
            continue
        part=item['minimal_part']
        ms=part['core_moduli']
        matrix=[[math.gcd(a,b) for b in ms] for a in ms]
        if 'core_gcds' in part and part['core_gcds']!=matrix:
            raise AssertionError('Stored gcd matrix mismatch')
        part['core_gcds']=matrix
    canonical=json.dumps(result['survivors'],sort_keys=True,separators=(',',':')).encode()
    result['survivor_sha256']=hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(k,result['survivor_sha256'])
