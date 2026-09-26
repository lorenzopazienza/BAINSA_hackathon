**Status: partial.** We do not have a closed form for every $n$, and we do not claim one.

Write $n=T_{k-1}+r$ with $1\le r\le k$ and $a=\lfloor(k-1)/2\rfloor$. The Griggs–Ho Conjecture 4.7 predicts $D_B(n)=(k-3-r)k+r+2$ for $r\le a-1$, $n-k+1$ for $r\in\{a,a+1\}$, and $(r-2)k+r$ for $r\ge a+2$.

**Proved, for all $k$ in range (our Cells 2–5, plus one new step here):**
- **Cells 2–5.** Columns $r=k$ ($k^2-k$), $r=k-1$ ($k^2-2k-1$), $r=1$ ($(k-1)(k-3)$) and $r=2$ ($\max\{(k-1)(k-4),T_{k-2}+2\}$), together with the general bound $D_B(n)\le k^2-2k-1$.
- **New here.** $d_B((n))=n-k$ and $d_B(1^n)=n-k+1$ for every $n\ge3$, with the exact landing point $B^{n-k}((n))=\delta_k\setminus\{k-r\}$. This comes from an explicit "staircase" description of the orbit of a single pile, and it proves the *lower* bound of the conjecture in the two middle columns.

**Computer-checked only:** $D_B(n)$ is computed exhaustively and exactly for every $n\le80$ (all ranks $k\le12$). It agrees with Conjecture 4.7 at every $n$ with $3\le n\le80$; there is **no disagreement**. The run takes 300 s on a laptop (under the 10-minute limit). It is cross-checked against a naive implementation for $n\le28$ and against the independent `bs.py` for $n\le60$.

**Open:** the columns $3\le r\le k-2$ outside the middle two, and the upper bound in the middle columns.

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
