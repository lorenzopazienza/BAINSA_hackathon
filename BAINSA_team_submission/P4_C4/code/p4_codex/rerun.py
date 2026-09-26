#!/usr/bin/env python3
"""Reproduce enumeration, minimal-part certificates, controls, and hashes."""
import os
import subprocess
import sys

ENV=os.environ.copy()
ENV['OMP_NUM_THREADS']='1'
ENV['OPENBLAS_NUM_THREADS']='1'

def run(*args):
    subprocess.run([sys.executable,*map(str,args)],check=True,env=ENV)

# The small completed sizes use the original single-process checker.
for k in range(3,15):
    run('checker.py',k)
# The two large sizes use disjoint first-modulus branches and deterministic
# sorted merge. Worker counts match the saved runs; neither rerun is timed.
run('parallel_enum.py',15,'--workers',6,'--output','results_k15.json')
run('parallel_enum.py',16,'--workers',5,'--output','results_k16.json')
for k in range(3,7):
    run('checker.py',k,'--upper',k)
run('brute_check.py')
run('validate_pruning.py')
for k in range(3,15):
    run('minimal_cert.py',k)
run('minimal_cert.py',15,'--seed-k',13,'--seed-k',14)
run('minimal_cert.py',16,'--seed-k',13,'--seed-k',14)
run('augment_core_gcds.py',*range(3,17))
for k in range(3,7):
    run('minimal_cert.py',k,'--vacuity')
run('verify_minimal.py',*range(3,17))
for k in range(3,7):
    run('verify_minimal.py',k,'--result',f'results_k{k}_vacuity.json')
run('refresh_readme.py')
run('verify_results.py')
run('summary.py')
