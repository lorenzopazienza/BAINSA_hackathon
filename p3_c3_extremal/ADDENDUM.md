# P3 Cell 3: extremal partitions at $T_k-1$ — incomplete addendum

**Status: partial.** The exact value $D_B(T_k-1)=k^2-2k-1$ is proved in `final/P3_C3/p3_c3.tex`. I did **not** find or prove a static if-and-only-if description of every attaining partition. The rule below is a proved **necessary** static rule, not the requested classification. The data are not a proof that no closed form exists. This addendum does not cure the judge's objection and must not be presented as a solved Cell 3.

## A proved static necessary rule

Let $k\ge5$, $n=T_k-1$, and let $\lambda\vdash n$ attain $D_B(n)$. Write $\lambda'_i=\#\{j:\lambda_j\ge i\}$ and

$\operatorname{lo}_k=(\lceil(k+2-j)/2\rceil)_{j=1}^{k+1}$.

Then the stronger bounds

$\lambda_1\le k-1,\qquad \ell(\lambda)\ge k+1,\qquad \lambda'_i\ge k+3-2i\quad(i\ge1)$

hold. In fact, the **first ramp alone** is equivalent to the static pair of conditions

$\operatorname{lo}_k\subseteq\lambda,\qquad \lambda_1\le k-1.$

This sharpens Proposition “a proved direct necessary condition” in the rejected write-up, which gave only $\lambda_1\le k+1$. It does **not** characterize full extremality; the later ramps still matter.

**Proof.** The equality case of the ramp bound, as used in the proved extremality theorem, gives the first ramp $(k,k+2,k)$: with $c_i=\ell(B^{i-1}(\lambda))$, one has $c_k=k-1$, $c_{k+1}=k$, and $c_{k+2}=k+1$. The pile lemma says that no pile dies in either of these two increasing moves. Its gap lemma then forces all newly created piles $N_1,\ldots,N_{k+1}$ to be present just before move $k+2$: if the last missing $N_i$ existed, $N_{i+1}$ would also be absent, a contradiction. Thus $N_1,\ldots,N_{k-1}$ were already present just before move $k$. Since $c_k=k-1$, no original pile remains then; hence $\lambda_1\le k-1$. The survival of $N_i$ gives $c_i\ge k+2-i$. For $j<i$, these bounds ensure $N_j$ is still present just before move $i$. Thus the remaining $\lambda'_i$ original piles satisfy $c_i=\lambda'_i+(i-1)$, and $\lambda'_i\ge k+3-2i$. At $i=1$ this gives $\ell(\lambda)\ge k+1$. The conjugate of $\operatorname{lo}_k$ has parts $k+1,k-1,k-3,\ldots$, so the inequalities are exactly $\lambda\supseteq\operatorname{lo}_k$.

Conversely, assume $\lambda_1\le k-1$ and $\lambda'_i\ge k+3-2i$. We show by induction for $1\le i\le k+1$ that $N_1,\ldots,N_{i-1}$ are alive before move $i$ and $c_i=\lambda'_i+i-1\ge k+2-i$. The base case is $c_1=\lambda'_1\ge k+1$. If the assertion holds at all earlier indices $j<i$, then $c_j\ge k+2-j\ge i-j$, exactly the pile-lifetime condition for $N_j$ to be alive before move $i$. This proves the induction. All $N_1,\ldots,N_{k+1}$ are therefore alive before move $k+2$. Because $\lambda_1\le k-1$, there are no original piles at moves $k,k+1,k+2$. Hence $c_k=k-1$, $c_{k+1}=k$, and $c_{k+2}=k+1$: the first ramp holds. $\square$

For $k=4$, the sole extremal partition is $(3,2,2,1,1)$, verified in the original exhaustive small-case proof. The preceding ramp argument is stated there only for $k\ge5$.

## Data check and failed static hypotheses

The script `explore.py` reads the supplied complete lists in `review/seby/bs_extremal.txt`; it does **not** use the Bulgarian-solitaire trajectory to classify a partition. It enumerates ordinary partitions of $T_k-1$ for $4\le k\le10$ and checks the following shape tests. It also independently checks the proved first-ramp equivalence on every partition in that range, with zero discrepancies. In the table, “first bounds” means $\lambda_1\le k+1$ and $\ell(\lambda)\ge k+1$; “short bounds” means $\lambda_1\le k-1$ and $k+1\le\ell(\lambda)\le2k-3$. The interval is $\operatorname{lo}_k\subseteq\lambda\subseteq\operatorname{hi}_k$, where $\operatorname{hi}_k'$ has parts $(2k-3,2k-5,\ldots,1)$. Its upper inclusion is **observed only**, not proved.

| $k$ | $T_k-1$ | Extremals | Extremals containing $\delta_{k-1}$ | First bounds: all candidates | Short bounds: all candidates | Interval: all candidates | Interval false positives |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 9 | 1 | 1 | 12 | 3 | 1 | 0 |
| 5 | 14 | 6 | 3 | 58 | 16 | 6 | 0 |
| 6 | 20 | 34 | 9 | 270 | 75 | 35 | 1 |
| 7 | 27 | 175 | 24 | 1242 | 340 | 175 | 0 |
| 8 | 35 | 831 | 64 | 5713 | 1527 | 834 | 3 |
| 9 | 44 | 3911 | 172 | 26363 | 6839 | 3935 | 24 |
| 10 | 54 | 18163 | 461 | 122297 | 30709 | 18330 | 167 |

The tests give concrete failures:

- **Staircase plus extra cells.** Since $|\lambda|=|\delta_{k-1}|+(k-1)$, every proposal “$\delta_{k-1}$ plus $k-1$ extra cells in allowed positions” requires $\lambda\supseteq\delta_{k-1}$. Already at $k=5$, the extremal $(3,3,3,2,2,1)$ has first part $3<4$; only 3 of 6 extremals contain $\delta_4$. For $k=10$, only 461 of 18,163 contain $\delta_9$. Conversely, $\lambda\subseteq\delta_k$ fails for **every** extremal in this range; for $k\ge5$ the proved length bound $\ell(\lambda)\ge k+1$ already makes that containment impossible.
- **Largest-part and length bounds.** All listed extremals satisfy $\lambda_1\le k-1$ and $k+1\le\ell(\lambda)\le2k-3$, but this admits 75 partitions at $k=6$ against 34 extremals. The weaker first bounds admit 270. The upper length bound $\ell(\lambda)\le2k-3$ remains unproved in general; the largest-part bound is proved above. Even their conjunction is not sufficient in the data.
- **First-ramp static family.** The proved conditions $\operatorname{lo}_k\subseteq\lambda$ and $\lambda_1\le k-1$ admit respectively $1,10,47,248,1182,5822,28030$ partitions for $k=4,\ldots,10$, versus $1,6,34,175,831,3911,18163$ extremals. Thus even an exact static test for the first ramp is far from the all-ramp condition.
- **Conjugate bounds.** The interval between $\operatorname{lo}_k$ and $\operatorname{hi}_k$ captures all listed extremals but has false positives at $k=6,8,9,10$. At $k=6$ the extra partition is $(4,4,3,3,2,2,1,1)$; direct iteration gives it $d_B=11$, whereas the extremal distance is $23$. At $k=8$ the three extras are $(7,6,6,5,5,2,2,1,1)$, $(7,6,6,3,3,2,2,1,1,1,1,1,1)$, and $(7,4,4,3,3,2,2,2,2,2,2,1,1)$. A union of the interval's slices indexed only by $\lambda_1$ still contains these extras. No explicit additional family exclusion that works for all $k$ was found.
- **Conjugation symmetry.** No extremal for $k\ge5$ can have an extremal conjugate: its conjugate has largest part $\ell(\lambda)\ge k+1$, contradicting the proved upper bound $k-1$ for an extremal partition. The unique $k=4$ example also has a nonextremal conjugate. Thus a conjugation-invariant criterion cannot be correct.
- **Multiset of NW–SE diagonal lengths.** Even *inside* the interval this statistic cannot separate extremals: at $k=6$, $(5,4,3,3,2,2,1)$ is extremal and $(4,4,3,3,2,2,1,1)$ is not, yet their unindexed diagonal-length multisets agree. The script finds analogous collisions for $k=8,9,10$.
- **Counts.** The sequence is $1,6,34,175,831,3911,18163$; successive ratios are $6,5.667,5.147,4.749,4.706,4.644$ (rounded). These rule out a constant-ratio product, and the terms do not match the elementary Catalan candidate $C_{k-2}$ (already $k=5$: $6\ne5$). No binomial or product formula was established. A numerical fit to seven terms would not classify the partitions or prove the result.

The only exact condition currently proved for all $k\ge5$ remains the **dynamical** one in `final/P3_C3/p3_c3.tex`: $B^{k^2-2k-3}(\lambda)$ has at least $k+1$ parts. I did not repackage that iteration as a supposed static formula. Because no candidate static equivalence emerged, I did not attempt a $k=11$ run; the supplied complete lists stop at $n=60$, below $T_{11}-1=65$.

**Reproduction:** from the hackathon directory, run `OMP_NUM_THREADS=1 python3 p3_c3_extremal/explore.py`. It uses only the Python standard library, one core, and completed in about 5.7 seconds here. It prints the table counts, the explicit interval exceptions at $k=6,8$, the first-ramp equivalence check, diagonal collisions, and the count ratios.
