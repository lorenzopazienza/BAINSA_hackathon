#!/usr/bin/env python3
"""Selector-SAT minimal UNSAT submultisets and direct SAT witnesses.

For each normal-form candidate, test distinct submultisets in increasing
cardinality. Identical modulus submultisets are equivalent by relabeling.
At the first UNSAT cardinality s, every distinct (s-1)-submultiset has a
SAT witness, independently checked over Z/L. Since SAT is downward closed,
this proves there is no smaller UNSAT part.
"""
import argparse
import hashlib
import itertools
import json
import math
import time
from pathlib import Path
from pysat.solvers import Solver
from checker import prime_powers, direct_verify


class SelectorSAT:
    def __init__(self, moduli, period):
        self.moduli = tuple(moduli)
        self.period = period
        self.fact = [dict(prime_powers(m)) for m in moduli]
        clauses=[]
        num=0
        def new():
            nonlocal num
            num+=1
            return num
        self.selectors=[new() for _ in moduli]
        self.digits={}
        for i, fs in enumerate(self.fact):
            for p,e in fs.items():
                for t in range(e):
                    xs=[new() for _ in range(p)]
                    self.digits[i,p,t]=xs
                    clauses.append(xs)
                    for d in range(p):
                        for q in range(d+1,p):
                            clauses.append([-xs[d],-xs[q]])
                    if i==0:
                        clauses.append([xs[0]])
        for i in range(len(moduli)):
            for j in range(i+1,len(moduli)):
                ws=[]
                for p in sorted(self.fact[i].keys() & self.fact[j].keys()):
                    for t in range(min(self.fact[i][p],self.fact[j][p])):
                        w=new(); ws.append(w)
                        for d in range(p):
                            clauses.append([-w,-self.digits[i,p,t][d],-self.digits[j,p,t][d]])
                clauses.append([-self.selectors[i],-self.selectors[j]]+ws)
        self.solver=Solver(name='cadical153',bootstrap_with=clauses)
        self.calls=0
    def close(self):
        self.solver.delete()
    def decide(self, indices, witness=False):
        active=set(indices)
        assumptions=[x if i in active else -x for i,x in enumerate(self.selectors)]
        self.calls+=1
        if not self.solver.solve(assumptions=assumptions):
            return None
        if not witness:
            return True
        model=set(x for x in self.solver.get_model() if x>0)
        residues=[]
        ms=[]
        for i in indices:
            congruences=[]
            for p,e in self.fact[i].items():
                a=sum(next(d for d,x in enumerate(self.digits[i,p,t]) if x in model)*p**t
                      for t in range(e))
                congruences.append((a,p**e))
            residue=next(a for a in range(self.moduli[i])
                         if all(a%q==b for b,q in congruences))
            residues.append(residue)
            ms.append(self.moduli[i])
        if not direct_verify(ms,residues,self.period):
            raise AssertionError(f'Invalid SAT witness: {ms} {residues}')
        return residues


def distinct_subsets(moduli, size):
    """Yield unique modulus submultisets in the original lexicographic order.

    Equal moduli occupy contiguous runs. For each run, choose how many
    copies to take, preferring more copies of the smaller modulus first.
    This visits each distinct value multiset once and chooses the earliest
    indices representing it. It is exactly the order of first occurrences
    in itertools.combinations(range(k), size), without duplicate tuples.
    """
    groups=[]
    for i,m in enumerate(moduli):
        if groups and groups[-1][0]==m:
            groups[-1][1].append(i)
        else:
            groups.append((m,[i]))
    def visit(g,remaining,indices,values):
        if g==len(groups):
            if remaining==0:
                yield tuple(indices),tuple(values)
            return
        m,available=groups[g]
        for count in range(min(len(available),remaining),-1,-1):
            yield from visit(g+1,remaining-count,
                             indices+available[:count],values+[m]*count)
    yield from visit(0,size,[],[])


def certify_candidate(moduli, period):
    ss=SelectorSAT(moduli,period)
    try:
        previous=[]
        for size in range(1,len(moduli)+1):
            current=[]
            for ids,vals in distinct_subsets(moduli,size):
                decision=ss.decide(ids,witness=False)
                if decision is None:
                    # Re-solve previous cardinality with model requests and
                    # directly verify every SAT witness over the original Z/L.
                    witnesses=[]
                    for prev_ids,prev_vals in previous:
                        residues=ss.decide(prev_ids,witness=True)
                        if residues is None:
                            raise AssertionError('Minimality level changed to UNSAT')
                        witnesses.append({'moduli':list(prev_vals),'residues':residues})
                    return {'s':size,'core_indices':list(ids),
                            'core_moduli':list(vals),'witnesses_s_minus_1':witnesses,
                            'selector_sat_calls':ss.calls}
                current.append((ids,vals))
            previous=current
        raise AssertionError('Full candidate unexpectedly SAT')
    finally:
        ss.close()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('k',type=int)
    ap.add_argument('--sample',type=int)
    args=ap.parse_args()
    source=json.loads(Path(f'results_k{args.k}.json').read_text())
    if source['status']!='COMPLETE':
        raise SystemExit('Minimal-part certificate is produced only for completed sizes')
    candidates=source['survivors']
    if args.sample is not None:
        candidates=candidates[:args.sample]
    start=time.monotonic()
    report=[]
    for pos,item in enumerate(candidates):
        if item['decision']!='UNSAT':
            continue
        cert=certify_candidate(item['moduli'],source['L'])
        report.append({'candidate_index':pos,'moduli':item['moduli'],**cert})
    distribution={}
    for record in report:
        s=record['s'];distribution[s]=distribution.get(s,0)+1
    print(json.dumps({'k':args.k,'candidates':len(report),'distribution':distribution,
                      'sat_calls':sum(x['selector_sat_calls'] for x in report),
                      'wall_seconds':round(time.monotonic()-start,3)},sort_keys=True))
    if args.sample is not None:
        Path(f'work/minimal_sample_k{args.k}.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    main()
