#!/usr/bin/env python3
"""Merge deterministic minimal-certificate chunks and verify coverage."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from checker import direct_verify
from minimal_parts import distinct_subsets
from minimal_cert import write_gzip_lines


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('k',type=int)
    ap.add_argument('intervals',nargs='+',help='start:end')
    ap.add_argument('--check-only',action='store_true')
    ap.add_argument('--output-result')
    ap.add_argument('--artifact-prefix')
    args=ap.parse_args()
    source_path=Path(f'results_k{args.k}.json')
    source=json.loads(source_path.read_text())
    n=len(source['survivors'])
    workdir=Path('work')/f'minimal_chunks_k{args.k}'
    records=[]; witnesses={}; stats=[]
    for interval in args.intervals:
        a,b=map(int,interval.split(':'))
        stem=f'{a:06d}_{b:06d}'
        stat=json.loads((workdir/f'{stem}_stats.json').read_text())
        if stat['start']!=a or stat['end']!=b: raise AssertionError('Chunk mismatch')
        record_path=Path(stat['record_file']); witness_path=Path(stat['witness_file'])
        if hashlib.sha256(record_path.read_bytes()).hexdigest()!=stat['record_sha256']:
            raise AssertionError('Chunk record hash mismatch')
        if hashlib.sha256(witness_path.read_bytes()).hexdigest()!=stat['witness_sha256']:
            raise AssertionError('Chunk witness hash mismatch')
        with gzip.open(record_path,'rt') as f:
            records.extend(json.loads(line) for line in f)
        with gzip.open(witness_path,'rt') as f:
            for line in f:
                row=json.loads(line); key=tuple(row['moduli'])
                if key not in witnesses or tuple(row['residues'])<tuple(witnesses[key]):
                    witnesses[key]=row['residues']
        stats.append(stat)
    records.sort(key=lambda r:r['candidate_index'])
    if [r['candidate_index'] for r in records]!=list(range(n)):
        raise AssertionError('Candidate intervals do not cover exactly once')
    verified=set()
    distribution={}
    for rec in records:
        pos=rec['candidate_index']; ms=source['survivors'][pos]['moduli']
        if rec['moduli']!=ms: raise AssertionError('Candidate mismatch')
        distribution[rec['s']]=distribution.get(rec['s'],0)+1
        lower=[vals for _,vals in distinct_subsets(ms,rec['s']-1)]
        if len(lower)!=rec['s_minus_1_witness_count']:
            raise AssertionError('Witness coverage count mismatch')
        for key in lower:
            if key not in witnesses: raise AssertionError(f'Missing witness {key}')
            if key not in verified:
                if not direct_verify(key,witnesses[key],source['L']):
                    raise AssertionError(f'Invalid witness {key}')
                verified.add(key)
    if args.check_only:
        if source.get('minimal_parts',{}).get('status')=='COMPLETE':
            for rec in records:
                part=source['survivors'][rec['candidate_index']]['minimal_part']
                if (part['s'],part['core_indices'],part['core_moduli']) != (rec['s'],rec['core_indices'],rec['core_moduli']):
                    raise AssertionError('Independent chunk core mismatch')
        print(json.dumps({'k':args.k,'candidate_count':len(records),'distribution':distribution,
                          'distinct_witnesses_checked':len(verified),'status':'MATCH'},sort_keys=True))
        return
    if args.artifact_prefix:
        witness_path=Path(f'{args.artifact_prefix}_witnesses_k{args.k}.jsonl.gz')
        record_path=Path(f'{args.artifact_prefix}_parts_k{args.k}.jsonl.gz')
    else:
        witness_path=Path(f'minimal_witnesses_k{args.k}.jsonl.gz')
        record_path=Path(f'minimal_parts_k{args.k}.jsonl.gz')
    witness_sha=write_gzip_lines(witness_path,(
        {'moduli':list(key),'residues':witnesses[key]}
        for key in sorted(verified,key=lambda x:(len(x),x))))
    record_sha=write_gzip_lines(record_path,records)
    for rec in records:
        part={key:rec[key] for key in ('s','core_indices','core_moduli','core_gcds','s_minus_1_witness_count')}
        part['witness_file']=str(witness_path)
        part['witness_sha256']=witness_sha
        source['survivors'][rec['candidate_index']]['minimal_part']=part
    canonical=json.dumps(source['survivors'],sort_keys=True,separators=(',',':')).encode()
    source['survivor_sha256']=hashlib.sha256(canonical).hexdigest()
    source['minimal_parts']={'status':'COMPLETE','records_file':str(record_path),
        'records_sha256':record_sha,'witness_file':str(witness_path),
        'witness_sha256':witness_sha,'candidate_count':n,
        'distribution':distribution,'unique_witnesses':len(verified),
        'selector_sat_calls':sum(s['selector_sat_calls'] for s in stats),
        'partition':'candidate-index intervals','chunks':stats}
    Path(args.output_result or source_path).write_text(json.dumps(source,indent=2)+'\n')
    print(json.dumps({'k':args.k,'candidates':n,'distribution':distribution,
        'witnesses':len(verified),'survivor_sha256':source['survivor_sha256']},sort_keys=True))

if __name__=='__main__':
    main()
