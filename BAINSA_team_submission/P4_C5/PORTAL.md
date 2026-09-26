**Status: certified boundary $K^*=14$; $k=24$ and $k=30$ decided.**

- (i) **Vacuity.** With the bound relaxed to $[2,k]$, the same code finds the genuine systems (e.g. $(3,3,3)$, $(6,6,6,6,6,6)$).
- (ii) **Decisions.** An individual decision for every survivor, with its smallest forcing part; the files are attached in `code/data/`.
- (iii) **Exact lists.** The exact survivor lists, with SHA-256.
- (iv) **Pruning.** The extra pruning rule is proved, and switching it off leaves the lists unchanged ($k\le12$).
- (v) **Second implementation.** SAT vs DFS, elementwise identical for all $k\le16$.

We claim $K^*=14$. For every $k\le14$, the survivor lists of both implementations, every decision with its minimal part, and a timed rerun under the 10-minute limit are attached (for $k=14$: 193 s in total). At $k=15$ the full rerun takes 613 s, just over the limit, so $k=15$ and $k=16$ are reported as *decided, beyond the certified boundary*: every survivor is UNSAT, with no disagreement. $k=24$ and $k=30$ ($k-1$ prime) are decided by hand, following O'Bryant's Lemma 6 argument, checked in full.

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
