**Status: solved (Sun's statement for every $k\le12$), plus the required report for $9\le k\le16$.**

- **Method.** The finite reduction and pruning rules, each proved.
- **Result.** Every survivor at every $k\le16$ is decided UNSAT, so nothing is left undecided. Exact counts: 6, 3, 137, 522, 4395, 19880, 155890, 236333 for $k=9..16$.
- **Second implementation.** A DFS implementation, written independently of the SAT one, produces an elementwise-identical survivor list (same SHA-256) at every $k\le16$. Survivor lists, decisions and minimal parts are attached as files (`code/data/`). Timed reruns are in the PDF.
- **Sources.** No disagreement with any source we tested.

**Full write-up, code and logs** (PDF + `code/` + logs, everything the proof relies on): <PASTE DRIVE LINK TO THIS CELL'S FOLDER>
