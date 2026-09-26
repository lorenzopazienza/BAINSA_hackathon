**Status: both parts handed in.** $\mathbf{2328\le U(Q_9)\le2400}$ (and $227\le\nabla(Q_9)\le236$).

- **Upper bound.** A 20-word even code $C_9$ at pairwise distance $\ge4$ gives a labelling with $512+8\cdot236=2400$ uphill paths. The labelling is in the linked folder (`labelling/Q9.txt`), and its count was checked mechanically.
- **Lower bound (new; the counting bound only gives 2312).** Suppose a decycling set has $\le226$ vertices. Split $Q_9$ into eight $Q_6$ copies: at least 6 copies are "light" (exactly 28). Then:
  1. a SAT lemma (P6: a 28-vertex decycling set of $Q_6$ lies in one parity class);
  2. an adjacency lemma, which forces a single parity type;
  3. a 4-cycle argument, which makes the remaining even vertices almost a distance-4 code;
  4. the Delsarte LP bound $|C|\le25$, which contradicts the count.

The argument is computer-assisted only through the SAT lemmas L6 and P6 (about 1 minute; code and logs included).

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
