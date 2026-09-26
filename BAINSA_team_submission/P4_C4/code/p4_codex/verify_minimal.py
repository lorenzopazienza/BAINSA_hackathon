#!/usr/bin/env python3
"""Audit every minimal-part witness directly over Z/L and every UNSAT core."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from checker import direct_verify
from minimal_parts import SelectorSAT, distinct_subsets


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_size(k, result_path=None):
    result=json.loads(Path(result_path or f'results_k{k}.json').read_text())
    meta=result.get('minimal_parts')
    if result['status']!='COMPLETE' or not meta or meta['status']!='COMPLETE':
        raise AssertionError(f'k={k}: no completed minimal-part certificate')
    witness_path=Path(meta['witness_file'])
    records_path=Path(meta['records_file'])
    if file_hash(witness_path)!=meta['witness_sha256']:
        raise AssertionError('Witness file hash mismatch')
    if file_hash(records_path)!=meta['records_sha256']:
        raise AssertionError('Record file hash mismatch')
    witnesses={}
    with gzip.open(witness_path,'rt') as f:
        for line in f:
            row=json.loads(line)
            key=tuple(row['moduli'])
            if key in witnesses:
                raise AssertionError('Duplicate witness key')
            witnesses[key]=row['residues']
    verified=set()
    checked_cores=set()
    total=0
    with gzip.open(records_path,'rt') as f:
        records=[json.loads(line) for line in f]
    if len(records)!=result['counts']['UNSAT']:
        raise AssertionError('Wrong number of minimal-part records')
    for rec in records:
        pos=rec['candidate_index']
        item=result['survivors'][pos]
        if item['decision']!='UNSAT' or item['moduli']!=rec['moduli']:
            raise AssertionError('Record/candidate mismatch')
        part=item['minimal_part']
        for field in ('s','core_indices','core_moduli','s_minus_1_witness_count'):
            if part[field]!=rec[field]:
                raise AssertionError('Per-candidate certificate mismatch')
        if part['witness_file']!=str(witness_path) or part['witness_sha256']!=meta['witness_sha256']:
            raise AssertionError('Per-candidate witness pointer mismatch')
        ids=rec['core_indices']; ms=item['moduli']
        if len(ids)!=rec['s'] or [ms[i] for i in ids]!=rec['core_moduli']:
            raise AssertionError('Core indices/moduli mismatch')
        matrix=[[math.gcd(a,b) for b in rec['core_moduli']] for a in rec['core_moduli']]
        if part.get('core_gcds',matrix)!=matrix or rec.get('core_gcds',matrix)!=matrix:
            raise AssertionError('Core gcd matrix mismatch')
        # Disjointness of this selected part depends only on its modulus
        # tuple. Check each distinct core tuple with selector SAT once;
        # relabeling and inactive classes cannot change that decision.
        core_key=tuple(rec['core_moduli'])
        if core_key not in checked_cores:
            sat=SelectorSAT(core_key,result['L'])
            try:
                if sat.decide(range(len(core_key)),witness=False) is not None:
                    raise AssertionError('Recorded UNSAT core is SAT')
            finally:
                sat.close()
            checked_cores.add(core_key)
        keys=[vals for _,vals in distinct_subsets(ms,rec['s']-1)]
        if len(keys)!=rec['s_minus_1_witness_count']:
            raise AssertionError('Incomplete size-(s-1) coverage')
        for key in keys:
            if key not in witnesses:
                raise AssertionError(f'Missing SAT witness for {key}')
            if key not in verified:
                if not direct_verify(key,witnesses[key],result['L']):
                    raise AssertionError(f'Invalid direct Z/L witness for {key}')
                verified.add(key)
        total+=1
    print(json.dumps({'k':k,'minimal_parts':total,'distinct_cores_checked':len(checked_cores),
                      'distinct_witnesses_verified':len(verified)},sort_keys=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('k',type=int,nargs='+')
    ap.add_argument('--result')
    args=ap.parse_args()
    if args.result and len(args.k)!=1:
        raise SystemExit('--result requires exactly one size')
    for k in args.k:
        verify_size(k,args.result)
