**Status: solved.** $U(Q_3)=14$ and $U(Q_4)=34$, both optimal.

- **Lower bound.** An exact formula $P(f)=|V|+\sum_{u\in R_f}(\deg u-1)+\sum_{u\in R_f}(N(u)-2)\,\mathrm{out}(u)$, where $R_f=\{v:N(v)\ge2\}$ is a decycling set. It gives $U(G)\ge|V|+(d-1)\nabla(G)$ for every $d$-regular $G$. With $\nabla(Q_3)=3$ and $\nabla(Q_4)=6$ this yields 14 and 34.
- **Upper bound.** The code labellings below attain these values.

**$U(Q_3)=14$. Labelling of $Q_3$** (8 vertices, listed in increasing label order, one 0/1 string per line; also in the file `Q3.txt`):

```
000
001
010
100
111
011
101
110
```

**$U(Q_4)=34$. Labelling of $Q_4$** (16 vertices, listed in increasing label order, one 0/1 string per line; also in the file `Q4.txt`):

```
0000
1111
0001
0010
0100
0111
1000
1011
1101
1110
0011
0101
0110
1001
1010
1100
```

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
