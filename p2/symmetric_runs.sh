#!/bin/zsh
# Symmetric SAT searches for |I| (or |D|) <= 235 in Q9, one lane per core.
# For each group: positive control <= 236 first; if that is UNSAT, <= 235 is too.
# Usage: [METHOD=sat-relaxed] ./symmetric_runs.sh GROUP [GROUP ...]   (sequential)
cd "$(dirname "$0")"
PY=../.venv/bin/python
METHOD=${METHOD:-sat}
TAG=${METHOD#sat}   # "" for sat, "-relaxed" for sat-relaxed
for g in "$@"; do
  out236=results/find_I_sat${TAG}_Q9_k236_$g.out
  $PY find_I.py $METHOD --d 9 --k 236 --group $g --minutes 15 > $out236 2>&1
  echo "$g$TAG k<=236: $(grep -E 'UNSAT|FOUND|timeout|Error' $out236 | tail -1)"
  if grep -q "UNSAT" $out236; then echo "$g$TAG: skip k<=235 (implied UNSAT)"; continue; fi
  if grep -qE "FOUND.*\|(I|D)\| = 23[0-5]" $out236; then continue; fi
  out235=results/find_I_sat${TAG}_Q9_k235_$g.out
  $PY find_I.py $METHOD --d 9 --k 235 --group $g --minutes 45 > $out235 2>&1
  echo "$g$TAG k<=235: $(grep -E 'UNSAT|FOUND|timeout|Error' $out235 | tail -1)"
done
