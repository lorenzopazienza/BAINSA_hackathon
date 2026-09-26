# P4_C4

- `p4_c4.tex` / `p4_c4.pdf`: the writeup. Certified theorem: **k <= 12** (Theorem 1). The sizes
  13 <= k <= 16 are a separate report (Section "Report for 9 <= k <= 16"), not part of the theorem.
- Recompile: `pdflatex p4_c4.tex` twice.

## What is attached (`code/`)

- `code/data/p4_codex/`: every `results_k*.json` for k <= 16 (gzipped for k >= 13), with the survivor
  lists, SAT decisions and per-survivor minimal-part records; all `minimal_parts_k*.jsonl.gz` and
  `minimal_witnesses_k*.jsonl.gz` (smallest UNSAT core + directly checked size-(s-1) witnesses);
  the vacuity results.
- `code/data/p4_dfs/`: the p4_dfs survivor and decision files for k <= 15 (`kXX_sun.json.gz`; for
  k = 15 the merged 24-block decisions, `k15_sun_decided.json.gz`).
- `code/p4_dfs`, `code/p4_codex`: the two independent implementations, unmodified.
- `code/p4_crosscheck`: elementwise list comparison (`compare_lists.py`, `compare_report.json`),
  chunked DFS decisions (`dfs_decide_chunk.py`, `merge_dfs_decisions.py`), and the timed rerun
  (`timed_rerun/`: `run_small.sh`, `run_sat.sh`, `run_dfs.sh`, `rerun_times.py`, logs).
- `k16status.tex` (+ `k16_status.py`) and `rerun_times.tex` (+ `rerun_times.py`): values frozen at
  compile time and read by the PDF.

## Status

- Survivor lists of the two implementations identical for every k <= 16 (elementwise, SHA-256).
- p4_codex: every survivor UNSAT for k <= 16, each with its minimal part.
- p4_dfs: every survivor UNSAT for k <= 15; k = 16 partial (17/24 blocks, 167,404
  survivors, all agree), run stopped at 2026-09-26 15:52.
- Timed rerun on this laptop (2026-09-26 16:04), wall clock in seconds: k = 3..12 SAT pipeline 3.2;
  full p4_dfs run k = 3..13 82.7; k = 13: 20.0; k = 14: 192.8;
  k = 15: 613.5 (SAT enumeration 187.1 + minimal parts 286.9 + DFS
  enumeration 139.5). All counts, lists and hashes reproduced.
- **Certified contiguous boundary K* = 14.** k=15,16: decided, beyond the certified boundary.
