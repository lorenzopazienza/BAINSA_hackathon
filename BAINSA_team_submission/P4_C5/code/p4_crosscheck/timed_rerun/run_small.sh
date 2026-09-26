#!/bin/zsh
# Timed rerun for k = 3..12: p4_codex pipeline (checker + minimal_cert) and full p4_dfs run.
zmodload zsh/datetime
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
PY=../../../.venv/bin/python
s=$EPOCHREALTIME
(cd codex && for k in $(seq 3 12); do $PY checker.py $k && $PY minimal_cert.py $k; done) > logs/sat_k3-12.log 2>&1
printf "TIME %.1fs exit=%d :: p4_codex checker.py + minimal_cert.py, k=3..12\n" $(( EPOCHREALTIME - s )) $? >> logs/small_times.txt
mkdir -p dfs_small; s=$EPOCHREALTIME
(cd dfs_small && $PY "../../../review/Teo /hackaton/p4_dfs/sun_dfs.py" 3 4 5 6 7 8 9 10 11 12 13 --outdir .) > logs/dfs_k3-13_full.log 2>&1
printf "TIME %.1fs exit=%d :: p4_dfs sun_dfs.py 3..13 (enumeration + decisions)\n" $(( EPOCHREALTIME - s )) $? >> logs/small_times.txt
