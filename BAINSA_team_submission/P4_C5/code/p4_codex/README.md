# Disjoint congruence classes: independent SAT checker

This program searches for a counterexample of size `k`: `k` pairwise disjoint integer congruence classes for which every pairwise modulus gcd is at most `k-1`. It reports each size separately; a completed UNSAT result is a finite exhaustive certificate, while an interrupted run is explicitly `UNFINISHED`.

## Finite reduction

**R1 (normal form).** Put `g_ij = gcd(m_i,m_j)` and `m'_i = lcm_{j != i} g_ij`. Every `g_ij` divides `m_i`, hence `m'_i | m_i`. Also `g_ij` divides both `m'_i` and `m'_j`, so `g_ij | gcd(m'_i,m'_j)`. Conversely, `m'_i | m_i` and `m'_j | m_j`, so `gcd(m'_i,m'_j) | gcd(m_i,m_j) = g_ij`. Thus the gcd is unchanged. By the generalized CRT, two classes intersect exactly when their modulus gcd divides their residue difference. Replacing all `m_i` with `m'_i`, without changing residues, therefore preserves every pairwise disjointness relation. In a counterexample every `g_ij` belongs to `{2,...,k-1}`. Consequently each normal-form modulus is an lcm of numbers in this set, and divides `L_k = lcm(1,...,k-1)`. We may search only normal-form moduli dividing `L_k`.

**R2 (density).** When all moduli divide `L_k`, each class occupies exactly `L_k/m_i` residues modulo `L_k`. Pairwise disjoint classes occupy disjoint residues, so `sum_i L_k/m_i <= L_k`, equivalently `sum_i 1/m_i <= 1`. The same argument applies to any subfamily. All fractions are compared exactly as integers using `L_k/m_i`.

## Exact candidate set and filter order

For each `k`, list every divisor of `L_k` in increasing order. Enumerate every nondecreasing length-`k` sequence from this list; it represents one modulus multiset, since relabeling classes cannot affect existence. Filter in this order:

1. **GCD:** every pair has gcd in `[2, k-1]` (or `[2,k]` in the vacuity mode). The upper bound defines the target, and the lower bound follows from CRT: gcd 1 always makes a pair intersect. Compatible prefixes are generated recursively. A candidate modulus equal to an earlier modulus is allowed only when that self-gcd satisfies the same bound.
2. **Density:** `sum_i L_k/m_i <= L_k`. Positive summands mean that a prefix already above `L_k` has no feasible extension; this pruning is exact by R2.
3. **Normal form:** for each `i`, `m_i = lcm_{j != i} gcd(m_i,m_j)`. R1 proves this is necessary after reduction.

The vacuity mode replaces the upper bound by `k` *throughout*, including `L = lcm(1,...,k)`, and otherwise runs the same code. Its witness test checks disjointness directly over `Z/L`.

The program records the number of completed multisets passing each filter. Density-prefix pruning may avoid constructing GCD-compatible completed multisets that fail density; this is tracked separately as a subtree count so the GCD-stage count is exact. No residue search is used in enumeration.

## SAT decision

For each class `i`, each prime power `p^e || m_i`, and each digit position `t=0,...,e-1`, one-hot Boolean variables encode the base-`p` digit of its residue. Exactly one value is selected at each position. A common translation lets us set `a_1=0`: subtracting `a_1` from all residues preserves every residue difference. For a pair `i,j`, let `h=gcd(m_i,m_j)`. They are disjoint iff some prime `p|h` and digit `t < v_p(h)` differs. For every such position, a witness variable implies that the two selected digits differ, and one clause requires at least one witness. If the digits are equal, exactly-one forces the corresponding witness false. If they differ, its witness can be true. Thus SAT is equivalent to pairwise disjointness. A SAT model is decoded to explicit residues and checked independently by computing occupied residues modulo `L`; the direct check is repeated for the vacuity mode. UNSAT is the solver's decision for that finite modulus multiset. Results include the solver name and version, as well as exact survivor lists and a SHA-256 digest of their canonical JSON serialization.

## Reproduction

Set `OMP_NUM_THREADS=1` and run `./run_all.sh`. The script uses the supplied Python 3.12 environment; reruns the completed single-process and parallel enumerations, relaxed-bound controls, and small brute-force check; regenerates every minimal-part certificate; audits the direct witnesses; and checks counts and hashes against `expected_results.json`. Per-size JSON files contain counts, decisions, wall time, and survivor lists. The brute-force check enumerates all modulus tuples with entries at most 36 and all residue tuples after translation for `k=3,4`.


### Why the enumeration and its counters are exhaustive

If a pair has gcd 1, its classes intersect by CRT, whatever residues are chosen. The gcd lower bound 2 is therefore necessary. The upper bound is the definition of a counterexample. Sorting the moduli loses no configuration because indices are labels only. At each recursion node, `allowed` contains exactly the divisors no smaller than the last choice that satisfy the gcd condition with every chosen modulus. Choosing each allowed divisor once gives each GCD-compatible multiset exactly once. If a prefix already exceeds the density bound, every descendant fails density because all new contributions are positive. The `count_gcd_completions` recurrence counts those skipped GCD-compatible descendants exactly: it sums the completion counts for each allowed next choice, with one completion at depth `k`. It changes no survivor. The optional `--no-density-prefix-prune` switch disables this shortcut; `validate_pruning.py` compares full counts and survivor hashes for sizes 3–12.

The `all_divisor_multisets` field is `binomial(D+k-1,k)`, where `D` is the number of divisors of `L` at least 2. `multisets_after_gcd` counts the entire GCD-compatible subset, including branches counted by the exact recurrence. The subsequent counters are nested, so `multisets_after_normal_form` equals `sat_calls` in completed runs. A `UNFINISHED` file records only completed traversal work and its last visited prefix; its counters do not assert absence of candidates in the unexplored portion.

The brute-force check does not use R1, R2, or normal-form filtering. It tests all nondecreasing modulus tuples with entries from 1 through 36 and the necessary gcd bound, and all residue tuples for those moduli after translation fixes the first residue to zero. The translation proof above makes this a complete residue check for each tuple. Its result is compared with the SAT encoding on the same tuple.

## Search budgets and deterministic reruns

The initial single-process searches for sizes 15 and 16 each stopped at a 600-second wall limit and were marked `UNFINISHED`; those exploratory files are retained under `work/`. The first-modulus parallel retries used six and five worker processes respectively and completed every branch within their own ten-minute wall budgets. The final `results_k15.json` and `results_k16.json` are therefore `COMPLETE`. Each file records its branch partition, branch counters, and branch survivor hashes. `run_all.sh` repeats the complete branches without a wall cutoff, merges them in first-modulus order, regenerates the minimal-part certificates, and checks the deterministic manifest. Wall time is measured anew and need not match.

A future time-limited parallel run would remain `UNFINISHED` unless every branch completed. A partial branch records an exact node count for deterministic fixed-node replay; its counters never assert absence of candidates in unexplored branches.

## Measured results

The `GCD`, `density`, and `normal` columns are nested filter counts. `SAT calls` equals `normal` because every retained multiset was decided. Wall times are from the saved run and vary on rerun.

| k | Status | GCD | Density | Normal | SAT calls | SAT / UNSAT | Wall seconds |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 3 | COMPLETE | 1 | 0 | 0 | 0 | 0 / 0 | 0.000 |
| 4 | COMPLETE | 4 | 0 | 0 | 0 | 0 / 0 | 0.000 |
| 5 | COMPLETE | 19 | 0 | 0 | 0 | 0 / 0 | 0.000 |
| 6 | COMPLETE | 79 | 2 | 0 | 0 | 0 / 0 | 0.000 |
| 7 | COMPLETE | 294 | 7 | 2 | 2 | 0 / 2 | 0.002 |
| 8 | COMPLETE | 1,668 | 46 | 7 | 7 | 0 / 7 | 0.003 |
| 9 | COMPLETE | 13,477 | 200 | 6 | 6 | 0 / 6 | 0.007 |
| 10 | COMPLETE | 59,092 | 547 | 3 | 3 | 0 / 3 | 0.022 |
| 11 | COMPLETE | 294,730 | 4,463 | 137 | 137 | 0 / 137 | 0.149 |
| 12 | COMPLETE | 2,952,861 | 26,861 | 522 | 522 | 0 / 522 | 0.972 |
| 13 | COMPLETE | 14,850,581 | 223,883 | 4,395 | 4,395 | 0 / 4,395 | 8.126 |
| 14 | COMPLETE | 180,318,844 | 1,806,664 | 19,880 | 19,880 | 0 / 19,880 | 60.082 |
| 15 | COMPLETE | 1,555,698,169 | 25,300,584 | 155,890 | 155,890 | 0 / 155,890 | 199.510 |
| 16 | COMPLETE | 2,477,063,373 | 19,205,992 | 236,333 | 236,333 | 0 / 236,333 | 223.907 |

The total checker wall time reported for sizes 3–12 was 1.155 seconds, well below ten minutes. The completed searches found no counterexample. This computation agrees with O'Bryant (2007), Theorem 3, for every k we completed; we tested this, we did not assume it. The computation does not address sizes 17–20.

| k | Minimal parts | Minimum-size distribution `s:count` | Distinct direct witnesses |
|---:|---:|:---|---:|
| 3 | 0 | — | 0 |
| 4 | 0 | — | 0 |
| 5 | 0 | — | 0 |
| 6 | 0 | — | 0 |
| 7 | 2 | 5:2 | 10 |
| 8 | 7 | 3:2, 5:5 | 54 |
| 9 | 6 | 3:1, 5:5 | 65 |
| 10 | 3 | 5:3 | 73 |
| 11 | 137 | 3:84, 5:1, 6:1, 7:51 | 454 |
| 12 | 522 | 3:380, 4:10, 7:132 | 1,344 |
| 13 | 4,395 | 3:2,178, 4:334, 5:363, 6:669, 7:547, 8:193, 9:108, 10:1, 11:2 | 18,060 |
| 14 | 19,880 | 3:11,007, 4:2,405, 5:1,325, 6:2,369, 7:1,842, 8:638, 9:294 | 76,108 |
| 15 | 155,890 | 3:132,232, 4:5,478, 5:2,030, 6:9,153, 7:3,007, 8:872, 9:3,113, 10:1, 12:4 | 164,041 |
| 16 | 236,333 | 3:153,452, 4:19,118, 5:16,279, 6:25,914, 7:8,557, 8:7,396, 9:4,190, 10:834, 11:581, 12:12 | 401,312 |

The vacuity runs with upper gcd bound `k` found verified classes modulo `k` for each `k=3,4,5,6`. Their exact decisions and residues are in `results_k{K}_vacuity.json`. The brute-force comparison over moduli at most 36 checked 8,436 modulus multisets at `k=3` and 82,251 at `k=4`. Of these, 295 and 651 respectively met the necessary gcd range. It checked 148,504 and 5,418,823 residue tuples after translation and agreed with SAT on every eligible modulus multiset. Those exact figures are in `brute_k3.json` and `brute_k4.json`.

Every normal-form candidate and its exact decision is in its `results_k{K}.json` file. A certified candidate also has a `minimal_part` object containing its smallest UNSAT core, its induced gcd matrix, and a hash and filename for all size-`s-1` witnesses. `expected_results.json` captures the exact counts and hashes for reproducibility.

## Minimal UNSAT part certificate

For each UNSAT normal-form candidate at a **completed** size, `minimal_cert.py` searches sub-multisets by increasing cardinality using selector SAT. It adds a Boolean selector `y_i` for each class. Every pair's disjointness clause is guarded by `¬y_i ∨ ¬y_j`; assumptions set exactly the selected classes active. Digit clauses are unchanged, so this SAT query is equivalent to disjointness of the selected subfamily. Fixing the first class's residue to zero remains sound when it is selected by common translation; when it is not selected, it constrains only an inactive class.

The first UNSAT sub-multiset has size `s`; its indices, moduli, and induced gcd matrix (computable from those moduli) identify the core. At size `s-1`, every sub-multiset is SAT and has an explicit residue witness in the witness file. Each distinct witness is checked by marking all occupied residues of `Z/L` and rejecting any overlap. Sub-multisets with the same sorted moduli are equivalent by relabeling, including their pairwise gcds, so one witness applies to each corresponding index choice. Checking `s-1` suffices to prove minimality: every subfamily of a SAT family is SAT. If a smaller UNSAT subfamily existed, it could be extended within the candidate to size `s-1`, contradicting that every such subfamily is SAT.

The per-candidate `minimal_part` object points to a SHA-256 hashed witness file. To inspect its complete minimality certificate, enumerate the distinct size-`s-1` sub-multisets of that candidate's moduli and look up their explicit residues by modulus tuple in the witness file. `verify_minimal.py` repeats this coverage and direct `Z/L` check, and re-solves each distinct core modulus tuple with selector assumptions; identical tuples give the same constraint problem by relabeling. The cache in `minimal_cert.py` only reuses decisions for identical modulus tuples; their SAT meaning is independent of labels or other inactive classes. Every chosen UNSAT core is re-solved with that candidate's own selectors.

## Parallel enumeration

`parallel_enum.py` assigns each possible first modulus to exactly one branch. Every nondecreasing modulus multiset has a unique first modulus, so the branches partition the original enumeration with no overlap or omission. Each branch runs the same GCD, density, normal-form, and SAT code as `checker.py`. Branch counters are added and survivor lists merged by first-modulus index, independent of worker completion order. Up to six worker processes run with `OMP_NUM_THREADS=1`. A time-limited parallel result records complete branch states and any stopped branch's exact node count; fixed-node branch replay reproduces its counters and survivor hash. A size is marked `COMPLETE` only when every first-modulus branch finishes.

The direct `Z/L` witness checker uses an integer bitset: bit `x` represents residue `x` for `0 ≤ x < L`. For `m | L`, the geometric sum `(2^L-1)/(2^m-1)` has bits exactly at `0,m,2m,...,L-m`; shifting by `a mod m` marks precisely `a (mod m)` in `Z/L`. A witness is accepted only when every new mask has zero intersection with the union of earlier masks. This is a direct scan of the finite cyclic residue set expressed as bit operations; the formula was cross-checked against the original bytearray scan on all small tested triples.

DRAT traces were not emitted. The UNSAT direction remains a reproducible CaDiCaL computation; the SAT witnesses used to prove minimality are checked directly over `Z/L`.
