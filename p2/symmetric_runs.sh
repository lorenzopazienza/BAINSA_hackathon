#!/bin/zsh
# Symmetric SAT searches for |I| <= 235 in Q9, one lane per core.
# For each group: positive control |I| <= 236 first; if that is UNSAT, |I| <= 235 is too.
# Usage: ./symmetric_runs.sh GROUP [GROUP ...]     (runs the groups sequentially)
cd "$(dirname "$0")"
PY=../.venv/bin/python
for g in "$@"; do
  out236=results/find_I_sat_Q9_k236_$g.out
  $PY find_I.py sat --d 9 --k 236 --group $g --minutes 15 > $out236 2>&1
  echo "$g k<=236: $(grep -E 'UNSAT|FOUND|timeout|Error' $out236 | tail -1)"
  if grep -q "UNSAT" $out236; then echo "$g: skip k<=235 (implied UNSAT)"; continue; fi
  if grep -q "FOUND.*|I| = 23[0-5]" $out236; then continue; fi
  out235=results/find_I_sat_Q9_k235_$g.out
  $PY find_I.py sat --d 9 --k 235 --group $g --minutes 45 > $out235 2>&1
  echo "$g k<=235: $(grep -E 'UNSAT|FOUND|timeout|Error' $out235 | tail -1)"
done
