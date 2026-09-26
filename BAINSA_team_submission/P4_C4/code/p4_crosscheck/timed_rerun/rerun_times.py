#!/usr/bin/env python3
"""Write rerun_times.tex (LaTeX macros) from the timed-rerun logs, for P4_C4 / P4_C5.

K* rule (per size k): the timed rerun of the p4_codex pipeline (enumeration + SAT decisions +
minimal parts) plus the p4_dfs enumeration must take under 600 s of wall clock in total; for
k <= 12 the whole k = 3..12 rerun counts at once. A step that has not finished is reported as
still running and makes its size fail the rule.

Usage: python rerun_times.py OUT.tex [OUT2.tex ...]
"""
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def sat_times():
    t = {}
    for line in open(os.path.join(HERE, "logs", "sat_times.txt")):
        m = re.match(r"TIME ([\d.]+)s exit=(\d+) :: .*?(checker\.py|parallel_enum\.py|minimal_cert\.py) (\d+)", line)
        if m and m.group(2) == "0":
            t[(int(m.group(4)), "min" if m.group(3) == "minimal_cert.py" else "enum")] = float(m.group(1))
    return t


def small_times():
    t = {}
    for line in open(os.path.join(HERE, "logs", "small_times.txt")):
        m = re.match(r"TIME ([\d.]+)s exit=0 :: (p4_codex|p4_dfs)", line)
        if m:
            t[m.group(2)] = float(m.group(1))
    return t


def dfs_enum(k):
    f = glob.glob(os.path.join(HERE, "dfs", f"k{k:02d}_sun*.json"))
    if not f:
        return None
    log = open(os.path.join(HERE, "logs", f"dfs_k{k}_enum.log")).read()
    m = re.search(r"real\s+([\d.]+)", log)
    return float(m.group(1)) if m else None


def main():
    sat, small = sat_times(), small_times()
    names = {13: "XIII", 14: "XIV", 15: "XV"}
    macros, totals = {}, {}
    for k, r in names.items():
        e, m, d = sat.get((k, "enum")), sat.get((k, "min")), dfs_enum(k)
        if k == 13:  # p4_dfs k=13 was rerun in full (enumeration + decisions) with k=3..12
            d = json.load(open(os.path.join(HERE, "dfs_small", "k13_sun.json")))["wall_clock_s"]["enumeration"]
        fmt = lambda x: f"{x:.1f}" if x is not None else r"\textit{running}"
        macros[f"t{r}enum"], macros[f"t{r}min"], macros[f"t{r}dfs"] = fmt(e), fmt(m), fmt(d)
        tot = e + m + d if None not in (e, m, d) else None
        totals[k] = tot
        macros[f"ok{r}"] = "yes" if tot is not None and tot < 600 else ("no" if tot is not None or (e or 0) + (m or 0) + (d or 0) >= 600 else r"\textit{running}")
        macros[f"t{r}tot"] = fmt(tot) if tot is not None else (
            rf"$>{e + (m or 0) + (d or 0):.0f}$ (running)" if e else r"\textit{running}")
    macros["tSmallSAT"] = f"{small['p4_codex']:.1f}"
    macros["tSmallDFS"] = f"{small['p4_dfs']:.1f}"
    kstar = 12
    for k in (13, 14, 15):
        if totals[k] is not None and totals[k] < 600:
            kstar = k
        else:
            break
    macros["Kstar"] = str(kstar)
    beyond = [k for k in range(kstar + 1, 17)]
    macros["Beyond"] = "$k=" + ",".join(map(str, beyond)) + "$"
    macros["tStamp"] = time.strftime("%Y-%m-%d %H:%M")
    text = "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items())
    for out in sys.argv[1:]:
        open(out, "w").write(text)
    print(text)
    print(f"K* = {kstar}; totals {totals}")


if __name__ == "__main__":
    main()
