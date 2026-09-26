#!/bin/zsh
# One full rerun of p4_dfs for k=14 with its own CLI (enumeration + default decider), unmodified.
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p dfs_k14_rerun logs
cd dfs_k14_rerun
/usr/bin/time -p ../../.venv/bin/python "../../review/Teo /hackaton/p4_dfs/sun_dfs.py" 14 --outdir . > ../logs/k14_rerun.log 2>&1
