**Status: partial. We do not claim a new infinite family.**

With $A=\sum_{i<j}\arcsin|\langle x_i,x_j\rangle|$, the conjecture reads $A\ge M(N,d)\frac\pi2$.

**Proved:**
1. **6 lines in $\mathbb R^3$:** $A\ge\frac32\pi$, i.e. $S\le6\pi$, with equality for three orthogonal directions each taken twice. The proof averages the 5-line bound of Cells 4/5 over the six 5-subsets; each pair lies in 4 of them.
2. **Exact reach of subset averaging.** For $d\ge3$ and $N\ge d+3$, averaging from every case proved so far gives the conjecture *only* for $(N,d)=(6,3)$. The proof uses a convexity argument on $f(k)=2(d+k)(d+k-1)-k(d+1)(d+2)$ for $N\le2d$ and a direct estimate for $N\ge2d+1$. It is also checked in exact arithmetic for $d\le60$, $N\le400$ (`averaging_search.py`, 2 s). So averaging cannot give a new infinite family.
3. **Structural reduction of $N=d+3$ for every $d$.** At a saturated minimiser, every component of the non-orthogonality graph is settled, except components of rank $\ge4$, nullity $\ge3$ and maximum degree 3 with cyclomatic number $\ge2$. The key new lemma is a PSD "forcing" argument: tree components have nullity $\le1$, and unicyclic ones have nullity $\le2$.

**Open:** the first unsettled instance is 7 lines in $\mathbb R^4$ with a connected graph. A numerical scan of all 41 admissible graph patterns finds no configuration below $\frac32\pi$; this is evidence only, not a proof.

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
