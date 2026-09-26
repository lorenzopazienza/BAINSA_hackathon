**Status: solved.** $U(Q_5)=88$, optimal.

- **Lower bound.** $U(Q_d)\ge2^d+(d-1)\nabla(Q_d)$ (Cell 1), together with $\nabla(Q_5)=14$. That no decycling set of size $\le13$ exists is a SAT fact (counterexample-guided loop with cycle cuts). It is UNSAT with CaDiCaL and with Glucose, and re-verified by an independently written program; the code is included.
- **Upper bound.** The code labelling $C=\{00000,11110\}$.

**$U(Q_5)=88$. Labelling of $Q_5$** (32 vertices, listed in increasing label order, one 0/1 string per line; also in the file `Q5.txt`):

```
00000
11110
00001
00010
00100
00111
01000
01011
01101
01110
10000
10011
10101
10110
11001
11010
11100
11111
00011
00101
00110
01001
01010
01100
01111
10001
10010
10100
10111
11000
11011
11101
```

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
