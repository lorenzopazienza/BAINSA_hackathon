# BAINSA Hackathon 2026: Track 3 "Climbing to the Frontier"

**Team:** Lorenzo Pazienza (lead), Seby, Teo, Niccolò

**The hand-in is in [`BAINSA_team_submission/`](BAINSA_team_submission/)**, with one folder per cell (`P<problem>_C<cell>`). Each folder holds the write-up PDF, its LaTeX source, and the code and logs for every computation the proof relies on.

- [`RESULTS.pdf`](BAINSA_team_submission/_TRACK3_FORM/RESULTS.pdf): all 24 cells, with what is solved and what is partial.
- [`METHODOLOGY.pdf`](BAINSA_team_submission/_TRACK3_FORM/METHODOLOGY.pdf): our game plan, how we checked correctness, how we kept compute and token use efficient, and where humans verified the work.

| Problem | Cells |
|---|---|
| P1 Angles between lines (Fejes Tóth) | C1–C5 solved (C5 for every d); C6 partial |
| P2 Uphill paths on the hypercube | C1–C4 solved, optimal (14, 34, 88, 204, 464, 1040); C5: 2328 ≤ U(Q9) ≤ 2400; C6 partial |
| P3 Bulgarian solitaire | C1, C2, C4 solved; C3, C5, C6 partial |
| P4 Disjoint congruence classes | C1–C4 solved; C5 certified K* = 14, with k = 24, 30 decided; C6 partial (k = 32, 38, 42) |

`p2/` holds the working code of our P2 search pipeline: an exact evaluator, a SAT model and local search.
