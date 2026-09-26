#!/bin/zsh
# Reproduce the p4_dfs side of the cross-check (run from this folder).
#  - k=14: one full rerun of p4_dfs's own CLI (enumeration + default decider), unmodified.
#  - k=15, 16: p4_dfs's default decider on p4_dfs's own survivor lists, 24 round-robin chunks
#    per k, at most 6 processes at a time (xargs -P 6), OMP_NUM_THREADS=1.
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
PY=../.venv/bin/python
mkdir -p dfs_k14_rerun dfs_decisions logs
{
  echo "./rerun_k14.sh"   # own script: xargs would strip the quotes around the 'Teo ' path
  for k in 15 16; do for c in $(seq 0 23); do
    echo "$PY dfs_decide_chunk.py $k $c 24 > logs/k${k}_chunk$(printf %02d $c).log 2>&1"
  done; done
} > jobs.txt
/usr/bin/time -p xargs -P 6 -I{} zsh -c '{}' < jobs.txt 2> logs/total_time.txt
echo "all jobs finished" >> logs/total_time.txt
