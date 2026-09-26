# p4_dfs: a second, SAT-free checker for Sun's conjecture (Problem 4, Cell 5)

**Claim checked, for each k:** there are no k pairwise disjoint residue classes
`a_i mod m_i` with `2 <= gcd(m_i, m_j) <= B` for all `i != j`, where `B = k-1`.

The full proofs of every reduction and pruning rule are in the module docstring of
[`sun_dfs.py`](sun_dfs.py). In summary:

| step | statement | used for |
|---|---|---|
| (0) | `a mod m`, `b mod n` disjoint ⟺ `gcd(m,n) ∤ a−b` | decision, pruning |
| (1) | Replacing each `m_i` by `n_i = lcm_{j≠i} gcd(m_i,m_j)` keeps every pairwise gcd, hence disjointness. So WLOG `m_i = lcm_{j≠i} gcd(m_i,m_j)` (normal form) | finiteness |
| (2) | In normal form with gcds ≤ B, every `m_i` divides `L = lcm(1..B)` | finiteness |
| (3) | Disjoint classes satisfy `Σ 1/m_i ≤ 1` (count inside one period) | filter |
| (4) | Normal form ⟺ for every prime p, `max_i v_p(m_i)` is 0 or attained at least twice | enumeration |

**Finite set (the survivors).**
`C(k,B)` = multisets of k divisors of L with every pairwise gcd in `[2,B]`, in normal form,
and with `Σ 1/m_i ≤ 1` (checked with exact `Fraction`s). A counterexample exists iff some
survivor admits residues.

## Method (it differs from a sorted-prefix / SAT approach)

**Enumeration by prime-exponent columns.**
- The multiset is treated as a k × r exponent matrix, one column per prime `p ≤ B`.
  Columns are filled one prime at a time, largest prime first.
- The permutation symmetry is broken by requiring the rows to be lexicographically
  non-increasing. Rows that agree on the columns filled so far form blocks, and the next
  column must be non-increasing inside each block. This gives exactly one matrix per multiset.
- There are three pruning rules, each proved in the docstring and each switchable off:
  - `--no-gcd-prune`: a partial gcd that already exceeds B can only grow.
  - `--no-coprime-prune`: at the last prime, a pair that is still coprime stays coprime if
    this prime's exponent is set to 0.
  - `--no-forced-even-prune` (P3): only the prime 2 remains after the next-to-last column. A
    row with a still-coprime partner must be even. So two such rows with partial gcd G and
    2G > B cannot both be valid. The test runs when that column is complete, and also inside
    it: once rows a and b are set there, their gcd is final up to the factor from 2.
- The per-prime normal-form test can be moved to the leaves with `--late-nf`.
- Every leaf re-checks every defining condition of `C(k,B)` from the moduli themselves.
  Density is tested exactly in integers: `Σ L/m_i ≤ L`.

**Decision by backtracking.**
- The first class is fixed at `a = 0` (translation).
- Domains are numpy boolean arrays over `Z/m_i`. Forward checking removes the class
  `x mod gcd` from each unplaced domain, which is exactly criterion (0).
- The next class is the one with the fewest candidates; ties go to the larger gcd degree.
- Interchangeability (`--no-interchange` switches it off): two candidates that agree modulo
  `U_i = lcm{gcd(m_i,m_j) : j unplaced}` are equivalent, so only one per class is tried.
- `--plain-decide` is plain backtracking over all of `Z/m_i`, used as a cross-check.
- Every SAT witness is verified literally, element by element over one period, without
  criterion (0).

## Usage

```
python sun_dfs.py 3 4 5 6 7 8 9 10 11 12 --outdir results   # Sun, B = k-1
python sun_dfs.py 3 4 5 6 --bound-offset 0                  # vacuity test, B = k
python run_checks.py                                        # self-tests
python canonical.py                                         # write *.canonical.json, re-verify hashes
python sun_dfs.py 15 --enum-only --enum-time-limit 1800     # capped runs: status UNFINISHED
python compare.py --codex ../p4_codex --ks 3-14              # elementwise comparison with p4_codex
python check_minimality.py                                  # numeric side check for p4_c5 (k=24,30)
```
Capped runs: `--decide-time-limit T` marks the survivors not yet decided as `UNDECIDED`.
`--enum-time-limit T` stops the enumeration and records how many first-column subtrees were
completed. Either way the JSON gets `"status": "UNFINISHED"` and a `_UNFINISHED` file name.
Requirements: Python 3.12 and numpy.

## Output (`results/kXX_sun.json`)

Each file contains:
- `counts`:
  - `enumeration_nodes` and `complete_exponent_matrices(leaves)`: these depend on the
    pruning toggles.
  - `gcd_in_range_and_normal_form`, `survivors(density<=1)`, `SAT`, `UNSAT`: these do not
    depend on the toggles.
  - `decision_nodes`.
- `wall_clock_s`.
- `survivors`: each entry has `moduli` in ascending order and a `decision`, plus
  `residues` when the decision is SAT.
- `survivors_sha256`: SHA-256 of the **canonical text**. That text is the JSON list of
  survivors, each an ascending list, the whole list sorted lexicographically, serialised
  compactly with `separators=(',', ':')` and no whitespace. The exact hashed text is in
  `results/kXX_sun.canonical.json`.

## Self-tests (`run_checks.py`)

1. For k = 3..7, the survivors and the `gcd_in_range_and_normal_form` count are identical
   under all 2^4 combinations of pruning toggles. The combinations with `--no-gcd-prune` are
   only run for k ≤ 6. For k = 8..12, the results are also identical with P3 on and off.
2. For k = 3..8 with B = k−1, and for k = 3..6 with B = k, the column enumerator matches a
   naive enumeration of all multisets of divisors of L. The naive enumerator is a test
   oracle only.
3. For k = 3..10, the three deciders agree on every survivor: forward checking with
   interchangeability, forward checking without it, and plain backtracking.
4. Vacuity test (B = k, k = 3..6): SAT systems are found, including `r mod k` for all r,
   and all witnesses pass the literal check.
