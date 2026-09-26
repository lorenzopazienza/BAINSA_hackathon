**Status: partial, direction (a) "decide a size $k\ge25$".**

- **Decided, computer-assisted:** $k=32$, $38$ and $42$ are not the least size at which the statement can fail. The method follows O'Bryant 2007, Lemma 6, with new ingredients for $p=k-1\ge31$. The last step is an exhaustive check over a finite set of prime distributions defined in the PDF; the check runs in 4 s, and a rerun reproduces its output exactly (`check_p4_c6.py`, logs included).
- **Not claimed:** $k=44$ is computer-assisted but the certificate is incomplete (runtime estimate about 240 CPU-hours). $k=48$ is open.

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
