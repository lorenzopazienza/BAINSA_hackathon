#!/bin/zsh
# Timed rerun of the p4_codex SAT pipeline (enumeration + SAT decisions + minimal parts) for
# k = 13, 14, 15, in a copy of the p4_codex code (the originals write their outputs in place).
cd "$(dirname "$0")/codex"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
PY=../../../.venv/bin/python
zmodload zsh/datetime
t() { local s=$EPOCHREALTIME; "$@"; local r=$?; printf "TIME %.1fs exit=%d :: %s\n" $(( EPOCHREALTIME - s )) $r "$*" >> ../logs/sat_times.txt; }
: > ../logs/sat_times.txt
for k in 13 14; do
  t $PY checker.py $k > ../logs/sat_k${k}_enum.log 2>&1
  t $PY minimal_cert.py $k > ../logs/sat_k${k}_minimal.log 2>&1
done
t $PY parallel_enum.py 15 --workers 6 --output results_k15.json > ../logs/sat_k15_enum.log 2>&1
t $PY minimal_cert.py 15 --seed-k 13 --seed-k 14 > ../logs/sat_k15_minimal.log 2>&1
echo "SAT rerun done" >> ../logs/sat_times.txt
