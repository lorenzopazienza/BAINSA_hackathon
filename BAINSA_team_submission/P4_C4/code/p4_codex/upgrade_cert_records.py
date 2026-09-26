#!/usr/bin/env python3
"""Add explicit core gcd matrices to existing compressed certificate records."""
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
from minimal_cert import write_gzip_lines

for k in map(int,sys.argv[1:]):
    path=Path(f'results_k{k}.json')
    result=json.loads(path.read_text())
    meta=result['minimal_parts']
    record_path=Path(meta['records_file'])
    with gzip.open(record_path,'rt') as f:
        records=[json.loads(line) for line in f]
    for rec in records:
        ms=rec['core_moduli']
        matrix=[[math.gcd(a,b) for b in ms] for a in ms]
        if 'core_gcds' in rec and rec['core_gcds']!=matrix:
            raise AssertionError('Core gcd matrix mismatch')
        rec['core_gcds']=matrix
    meta['records_sha256']=write_gzip_lines(record_path,records)
    meta.setdefault('seeded_decisions',0)
    for item in result['survivors']:
        if item['decision']=='UNSAT':
            ms=item['minimal_part']['core_moduli']
            item['minimal_part']['core_gcds']=[[math.gcd(a,b) for b in ms] for a in ms]
    canonical=json.dumps(result['survivors'],sort_keys=True,separators=(',',':')).encode()
    result['survivor_sha256']=hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(k,meta['records_sha256'])
