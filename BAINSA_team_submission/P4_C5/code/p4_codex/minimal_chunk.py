#!/usr/bin/env python3
"""Certify one deterministic candidate-index interval for a completed size."""
import argparse
import gzip
import hashlib
import json
import time
from pathlib import Path
from minimal_cert import certify_candidate, write_gzip_lines


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('k',type=int)
    ap.add_argument('start',type=int)
    ap.add_argument('end',type=int)
    ap.add_argument('--seed-k',type=int,action='append',default=[])
    args=ap.parse_args()
    source=json.loads(Path(f'results_k{args.k}.json').read_text())
    if source['status']!='COMPLETE':
        raise AssertionError('Size is not fully enumerated')
    if not 0<=args.start<=args.end<=len(source['survivors']):
        raise ValueError('Invalid candidate interval')
    cache={}; witnesses={}; verified=set(); used=set()
    for seed_k in args.seed_k:
        seed=json.loads(Path(f'results_k{seed_k}.json').read_text())
        meta=seed['minimal_parts']
        with gzip.open(meta['witness_file'],'rt') as f:
            for line in f:
                row=json.loads(line); key=tuple(row['moduli'])
                if key in cache and cache[key]!='SAT': raise AssertionError('Seed conflict')
                cache[key]='SAT'; witnesses[key]=row['residues']
        with gzip.open(meta['records_file'],'rt') as f:
            for line in f:
                row=json.loads(line); key=tuple(row['core_moduli'])
                if key in cache and cache[key]!='UNSAT': raise AssertionError('Seed conflict')
                cache[key]='UNSAT'
    start_time=time.monotonic()
    workdir=Path('work')/f'minimal_chunks_k{args.k}'
    workdir.mkdir(parents=True,exist_ok=True)
    stem=f'{args.start:06d}_{args.end:06d}'
    progress_path=workdir/f'{stem}_progress.json'
    records=[]
    for pos in range(args.start,args.end):
        item=source['survivors'][pos]
        if item['decision']!='UNSAT':
            raise AssertionError('Chunk includes a SAT candidate')
        cert=certify_candidate(item['moduli'],source['L'],cache,witnesses,verified,used)
        records.append({'candidate_index':pos,'moduli':item['moduli'],**cert})
        if (pos-args.start+1)%5000==0:
            progress_path.write_text(json.dumps({'k':args.k,'start':args.start,'end':args.end,
                'processed':pos-args.start+1,'wall_seconds':round(time.monotonic()-start_time,3)})+'\n')
    record_path=workdir/f'{stem}_records.jsonl.gz'
    witness_path=workdir/f'{stem}_witnesses.jsonl.gz'
    record_sha=write_gzip_lines(record_path,records)
    witness_sha=write_gzip_lines(witness_path,(
        {'moduli':list(key),'residues':witnesses[key]}
        for key in sorted(used,key=lambda x:(len(x),x))))
    stats={'k':args.k,'start':args.start,'end':args.end,'candidate_count':len(records),
           'unique_decisions':len(cache),'unique_witnesses':len(used),
           'selector_sat_calls':sum(r['selector_sat_calls'] for r in records),
           'wall_seconds':round(time.monotonic()-start_time,3),
           'record_file':str(record_path),'record_sha256':record_sha,
           'witness_file':str(witness_path),'witness_sha256':witness_sha}
    (workdir/f'{stem}_stats.json').write_text(json.dumps(stats,indent=2)+'\n')
    progress_path.write_text(json.dumps({**stats,'status':'COMPLETE'})+'\n')
    print(json.dumps(stats,sort_keys=True),flush=True)

if __name__=='__main__':
    main()
