#!/bin/zsh
# Timed rerun of the p4_dfs enumeration (--enum-only) for k = 14, 15, unmodified code.
cd "$(dirname "$0")/dfs"
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
for k in 14 15; do
  /usr/bin/time -p ../../../.venv/bin/python "../../../review/Teo /hackaton/p4_dfs/sun_dfs.py" $k --enum-only --outdir . > ../logs/dfs_k${k}_enum.log 2>&1
done
echo "DFS rerun done" >> ../logs/dfs_k15_enum.log
