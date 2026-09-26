"""Best-so-far score at one d: FunSearch loop vs anneal-only baseline.

Left: vs wall-clock minutes (loop: timestamps since its first candidate;
anneal: cumulative restart time / 8 workers). Right: vs number of candidates
(loop: programs; anneal: restarts). Loop scores are polished scores.

Usage: python plots.py [--d 9] [--target 2399] [--known 2400]
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent
BLUE, ORANGE, MUTED, INK, SURFACE = "#2a78d6", "#eb6834", "#8a8983", "#52514e", "#fcfcfb"


def read(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def loop_series(d):
    rows = sorted((r for r in read(ROOT / "results" / "results.jsonl")
                   if r.get("d") == d and "polished" in r), key=lambda r: r["timestamp"])
    if not rows:
        return None
    t = np.array([(r["timestamp"] - rows[0]["timestamp"]) / 60 for r in rows])
    return t, np.arange(1, len(rows) + 1), np.minimum.accumulate([r["polished"] for r in rows])


def anneal_series(d, workers=8):
    rows = [r for r in read(ROOT / "results" / "anneal_log.jsonl") if r["d"] == d]
    if not rows:
        return None
    t = np.cumsum([r["secs"] for r in rows]) / workers / 60
    return t, np.arange(1, len(rows) + 1), np.minimum.accumulate([r["score"] for r in rows])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--d", type=int, default=9)
    p.add_argument("--target", type=int, default=2399)
    p.add_argument("--known", type=int, default=2400)
    a = p.parse_args()

    series = {"FunSearch loop (polished)": (loop_series(a.d), BLUE),
              "Anneal only": (anneal_series(a.d), ORANGE)}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    lows = [a.target]
    for ax, (col, xlabel) in zip(axes, [(0, "wall-clock minutes"), (1, "candidates evaluated")]):
        ax.set_facecolor(SURFACE)
        for name, (s, color) in series.items():
            if s is None:
                continue
            ax.step(s[col], s[2], where="post", color=color, lw=2, label=name)
            ax.plot(s[col][-1], s[2][-1], "o", ms=8, color=color, mec=SURFACE, mew=2)
            lows.append(s[2].min())
        for y, text, dy, va in [(a.known, f"best known {a.known}", 3, "bottom"),
                                (a.target, f"target ≤ {a.target}", -3, "top")]:
            ax.axhline(y, color=MUTED, lw=1, ls="--" if y == a.target else ":")
            ax.annotate(text, (1, y), xycoords=("axes fraction", "data"), xytext=(-4, dy),
                        textcoords="offset points", ha="right", va=va, fontsize=8, color=INK)
        ax.set_xlabel(xlabel, color=INK)
        ax.grid(axis="y", color="#e6e5df", lw=0.8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=INK)
    axes[0].set_ylabel(f"best uphill paths, Q{a.d}", color=INK)
    lo = min(lows)
    axes[0].set_ylim(lo - 10, lo + max(60, 0.04 * lo))  # early scores are huge; zoom on the frontier
    axes[1].sharey(axes[0])
    axes[0].legend(frameon=False, loc="upper right", labelcolor=INK)
    fig.suptitle(f"Q{a.d}: best score so far", color=INK, x=0.07, ha="left")
    fig.tight_layout()
    out = ROOT / "results" / f"progress_Q{a.d}.png"
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
