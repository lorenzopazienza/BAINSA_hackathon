#!/usr/bin/env python3
"""Minimal UNSAT part certificates with selector SAT and direct witnesses."""
import argparse
import gzip
import hashlib
import json
import math
import time
from pathlib import Path
from minimal_parts import SelectorSAT, distinct_subsets
from checker import direct_verify


def canonical_line(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()+b'\n'


def certify_candidate(moduli,period,cache,witness_db,verified_periods,used_witnesses):
    """Search increasing sizes; cache decisions for identical modulus multisets.

    A cached SAT/UNSAT decision comes from a selector-SAT call on the same
    modulus multiset. Whenever the first UNSAT size is found, solve that
    core again with this candidate's selector assumptions. All distinct
    size-(s-1) submultisets get explicit, directly verified witnesses.
    """
    selector=None
    calls=0
    def get_selector():
        nonlocal selector
        if selector is None:
            selector=SelectorSAT(moduli,period)
        return selector
    try:
        previous=[]
        for size in range(1,len(moduli)+1):
            current=[]
            for ids,vals in distinct_subsets(moduli,size):
                known=cache.get(vals)
                if known is None:
                    decision=get_selector().decide(ids,witness=False)
                    calls+=1
                    known='SAT' if decision is True else 'UNSAT'
                    cache[vals]=known
                if known=='UNSAT':
                    # The candidate-specific selector encoding must also
                    # reject the chosen core, even if its status was cached.
                    if get_selector().decide(ids,witness=False) is not None:
                        raise AssertionError('Cached UNSAT core became SAT')
                    calls+=1
                    for prev_ids,prev_vals in previous:
                        used_witnesses.add(prev_vals)
                        if cache[prev_vals]!='SAT':
                            raise AssertionError('A smaller submultiset is UNSAT')
                        if prev_vals not in witness_db:
                            residues=get_selector().decide(prev_ids,witness=True)
                            calls+=1
                            if residues is None:
                                raise AssertionError('SAT witness level became UNSAT')
                            witness_db[prev_vals]=residues
                            verified_periods.add((prev_vals,period))
                        elif (prev_vals,period) not in verified_periods:
                            if not direct_verify(prev_vals,witness_db[prev_vals],period):
                                raise AssertionError('Cached witness failed over Z/L')
                            verified_periods.add((prev_vals,period))
                    return {'s':size,'core_indices':list(ids),
                            'core_moduli':list(vals),
                            'core_gcds':[[math.gcd(a,b) for b in vals] for a in vals],
                            's_minus_1_witness_count':len(previous),
                            'selector_sat_calls':calls}
                current.append((ids,vals))
            previous=current
        raise AssertionError('Full candidate unexpectedly SAT')
    finally:
        if selector is not None:
            selector.close()


def write_gzip_lines(path,records):
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as f:
            for record in records:
                f.write(canonical_line(record))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('k',type=int)
    ap.add_argument('--sample',type=int)
    ap.add_argument('--seed-k',type=int,action='append',default=[])
    ap.add_argument('--vacuity',action='store_true')
    args=ap.parse_args()
    tag=f'k{args.k}' + ('_vacuity' if args.vacuity else '')
    source_path=Path(f'results_{tag}.json')
    source=json.loads(source_path.read_text())
    if source['status']!='COMPLETE':
        raise SystemExit('Certify completed sizes only')
    candidates=source['survivors']
    if args.sample is not None:
        candidates=candidates[:args.sample]
    cache={}
    witnesses={}
    verified=set()
    used_witnesses=set()
    for seed_k in args.seed_k:
        seed=json.loads(Path(f'results_k{seed_k}.json').read_text())
        meta=seed.get('minimal_parts')
        if not meta or meta['status']!='COMPLETE':
            raise AssertionError(f'Seed k={seed_k} has no complete certificate')
        with gzip.open(meta['witness_file'],'rt') as f:
            for line in f:
                row=json.loads(line); key=tuple(row['moduli'])
                if key in cache and cache[key]!='SAT':
                    raise AssertionError('Conflicting seed decision')
                cache[key]='SAT'; witnesses[key]=row['residues']
        with gzip.open(meta['records_file'],'rt') as f:
            for line in f:
                row=json.loads(line); key=tuple(row['core_moduli'])
                if key in cache and cache[key]!='UNSAT':
                    raise AssertionError('Conflicting seed decision')
                cache[key]='UNSAT'
    seeded_decisions=len(cache)
    records=[]
    start=time.monotonic()
    for pos,item in enumerate(candidates):
        if item['decision']!='UNSAT':
            continue
        cert=certify_candidate(item['moduli'],source['L'],cache,witnesses,verified,used_witnesses)
        records.append({'candidate_index':pos,'moduli':item['moduli'],**cert})
        if (pos+1)%10000==0:
            print(json.dumps({'k':args.k,'processed':pos+1,'wall_seconds':round(time.monotonic()-start,3)}),flush=True)
    distribution={}
    for r in records:
        distribution[r['s']]=distribution.get(r['s'],0)+1
    stats={'k':args.k,'candidate_count':len(records),'distribution':distribution,
           'unique_decisions':len(cache),'seeded_decisions':seeded_decisions,
           'unique_witnesses':len(used_witnesses),
           'selector_sat_calls':sum(r['selector_sat_calls'] for r in records),
           'wall_seconds':round(time.monotonic()-start,3)}
    print(json.dumps(stats,sort_keys=True))
    if args.sample is not None:
        Path(f'work/minimal_cached_sample_{tag}.json').write_text(json.dumps({'stats':stats,'records':records},indent=2)+'\n')
        return
    witness_path=Path(f'minimal_witnesses_{tag}.jsonl.gz')
    records_path=Path(f'minimal_parts_{tag}.jsonl.gz')
    witness_rows=({'moduli':list(ms),'residues':witnesses[ms]}
                  for ms in sorted(used_witnesses,key=lambda x:(len(x),x)))
    witness_sha=write_gzip_lines(witness_path,witness_rows)
    record_sha=write_gzip_lines(records_path,records)
    for r in records:
        item=source['survivors'][r['candidate_index']]
        item['minimal_part']={key:r[key] for key in ('s','core_indices','core_moduli','core_gcds','s_minus_1_witness_count')}
        item['minimal_part']['witness_file']=witness_path.name
        item['minimal_part']['witness_sha256']=witness_sha
    canonical=json.dumps(source['survivors'],sort_keys=True,separators=(',',':')).encode()
    source['survivor_sha256']=hashlib.sha256(canonical).hexdigest()
    source['minimal_parts']={'status':'COMPLETE','records_file':records_path.name,
                             'records_sha256':record_sha,'witness_file':witness_path.name,
                             'witness_sha256':witness_sha,**stats}
    source_path.write_text(json.dumps(source,indent=2)+'\n')

if __name__=='__main__':
    main()
