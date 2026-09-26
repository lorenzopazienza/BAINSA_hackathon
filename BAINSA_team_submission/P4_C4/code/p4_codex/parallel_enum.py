#!/usr/bin/env python3
"""Six-process first-modulus partition of the exact checker search.

Each branch has a fixed first divisor index. Its local DFS is unchanged.
Results are merged by first index, never by worker completion order.
For partial runs, branch node cutoffs in the result file permit exact replay.
"""
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import queue
import shutil
import time
from pathlib import Path
from checker import divisors, lcm_upto, solve_size


def worker(k,upper,workdir,tasks,stopped,finished):
    os.environ['OMP_NUM_THREADS']='1'
    os.environ['OPENBLAS_NUM_THREADS']='1'
    while not stopped.is_set():
        index,max_nodes=tasks.get()
        if index is None:
            break
        path=Path(workdir)/f'branch_{index:03d}.json'
        result=solve_size(k,upper,result_path=path,first_index=index,
                          max_nodes=max_nodes,stop_event=stopped)
        finished.put((index,result['status'],result['counts']['nodes_visited']))


def run(k,upper,workers,limit_seconds=None,replay=None,output=None):
    start=time.monotonic()
    period=lcm_upto(upper)
    moduli=[d for d in divisors(period) if d>=2]
    n=len(moduli)
    if replay is None:
        # More compatible choices are scheduled first to reduce tail imbalance.
        order=sorted(range(n),key=lambda i:(-sum(2<=math.gcd(moduli[i],moduli[j])<=upper
                                              for j in range(i,n)),i))
        specs=[(i,None) for i in order]
    else:
        old=json.loads(Path(replay).read_text())
        if old['k']!=k or old['gcd_upper_bound']!=upper:
            raise ValueError('Replay size or upper bound mismatch')
        specs=[(r['first_index'],r['nodes_visited'] if r['status']=='UNFINISHED' else None)
               for r in old['parallel']['branches']]
    workdir=Path('work')/f'parallel_k{k}'
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    ctx=mp.get_context('spawn')
    tasks=ctx.Queue()
    for spec in specs:
        tasks.put(spec)
    for _ in range(min(workers,len(specs))):
        tasks.put((None,None))
    stopped=ctx.Event()
    finished=ctx.Queue()
    processes=[ctx.Process(target=worker,args=(k,upper,str(workdir),tasks,stopped,finished))
               for _ in range(min(workers,len(specs)))]
    for proc in processes:
        proc.start()
    if limit_seconds is None:
        for proc in processes:
            proc.join()
    else:
        while any(proc.is_alive() for proc in processes):
            if time.monotonic()-start>=limit_seconds:
                stopped.set()
                break
            time.sleep(0.2)
        for proc in processes:
            proc.join()
    for proc in processes:
        if proc.exitcode!=0:
            raise RuntimeError(f'Worker exited with code {proc.exitcode}')
    while True:
        try: finished.get_nowait()
        except queue.Empty: break
    branches=[]
    survivors=[]
    counts={'multisets_after_gcd':0,'multisets_after_density':0,
            'multisets_after_normal_form':0,'sat_calls':0,'SAT':0,'UNSAT':0,
            'nodes_visited':1}
    for i in range(n):
        path=workdir/f'branch_{i:03d}.json'
        if not path.exists():
            continue
        r=json.loads(path.read_text())
        branches.append({'first_index':i,'first_modulus':moduli[i],
                         'status':r['status'],'nodes_visited':r['counts']['nodes_visited'],
                         'last_prefix_at_timeout':r['last_prefix_at_timeout'],
                         'survivor_sha256':r['survivor_sha256']})
        for key in counts:
            counts[key]+=r['counts'][key]
        survivors.extend(r['survivors'])
    covered={r['first_index'] for r in branches}
    unstarted=[i for i in range(n) if i not in covered]
    status='COMPLETE' if not unstarted and all(r['status']=='COMPLETE' for r in branches) else 'UNFINISHED'
    canonical=json.dumps(survivors,sort_keys=True,separators=(',',':')).encode()
    result={'k':k,'gcd_upper_bound':upper,'L':period,'candidate_divisors':n,
            'all_divisor_multisets':math.comb(n+k-1,k),'density_prefix_prune':True,
            'status':status,'counts':counts,
            'survivor_sha256':hashlib.sha256(canonical).hexdigest(),
            'survivors':survivors,'last_prefix_at_timeout':None,
            'wall_seconds':round(time.monotonic()-start,3),
            'solver':f'CaDiCaL 1.5.3 via python-sat; {workers} processes',
            'parallel':{'workers':workers,'partition':'first modulus index',
                        'branches':branches,'unstarted_first_indices':unstarted}}
    target=Path(output or f'results_k{k}_parallel.json')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'k':k,'status':status,'counts':counts,'branches_done':len(branches),
                      'branches_total':n,'unstarted':len(unstarted),
                      'survivor_sha256':result['survivor_sha256'],
                      'wall_seconds':result['wall_seconds']},sort_keys=True))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('k',type=int)
    ap.add_argument('--upper',type=int)
    ap.add_argument('--workers',type=int,default=6)
    ap.add_argument('--limit-seconds',type=float)
    ap.add_argument('--replay')
    ap.add_argument('--output')
    args=ap.parse_args()
    if not 1<=args.workers<=6:
        raise SystemExit('workers must be between 1 and 6')
    run(args.k,args.upper or args.k-1,args.workers,args.limit_seconds,args.replay,args.output)
