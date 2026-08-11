#!/usr/bin/env python3
"""Generate paper figures from cached outcome pools and result artifacts.

Outputs PNG files to paper/figures/. Deterministic.
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / "src"))

from eval_harness.stats.fast_bounds import (
    betting_bounds,
    intersection_bounds,
    wilson_interval,
)

FIGDIR = REPO / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# Palette (validated categorical slots + status colors)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e5e4e0"

STRATA = ["simple", "medium", "complex", "extreme"]

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "text.color": INK,
    "axes.edgecolor": INK2,
    "axes.labelcolor": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_rates(path):
    pools = {s: [] for s in STRATA}
    for line in open(path):
        rec = json.loads(line)
        pools[rec["stratum"]].append(0 if rec["passed"] else 1)
    return [float(np.mean(pools[s])) for s in STRATA]


def fig1_heterogeneity():
    json_pools = {
        "gpt-4o-mini": load_rates(REPO / "data" / "llm_outcomes_diverse_json.jsonl"),
        "gpt-4.1-nano": load_rates(REPO / "data" / "llm_outcomes_diverse_json_gpt-4.1-nano.jsonl"),
        "gpt-4.1-mini": load_rates(REPO / "data" / "llm_outcomes_diverse_json_gpt-4.1-mini.jsonl"),
    }
    code_rates = load_rates(REPO / "data" / "llm_outcomes_diverse_code_gpt-4o-mini.jsonl")

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4),
                             gridspec_kw={"width_ratios": [3, 1.35]})
    x = np.arange(4)
    colors = [BLUE, ORANGE, AQUA]
    w = 0.26
    ax = axes[0]
    for i, (model, rates) in enumerate(json_pools.items()):
        bars = ax.bar(x + (i - 1) * w, rates, width=w - 0.03, color=colors[i],
                      label=model, zorder=3)
        for b, r in zip(bars, rates):
            if r >= 0.02:
                ax.text(b.get_x() + b.get_width() / 2, r + 0.012, f"{r:.2f}",
                        ha="center", va="bottom", fontsize=7.5, color=INK2)
    ax.set_xticks(x, STRATA)
    ax.set_ylabel("failure rate")
    ax.set_title("JSON schema task (250 prompts/stratum)", fontsize=10)
    ax.set_ylim(0, 0.85)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    ax.legend(frameon=False, fontsize=8, loc="upper left")

    ax = axes[1]
    bars = ax.bar(x, code_rates, width=0.5, color=BLUE, zorder=3)
    for b, r in zip(bars, code_rates):
        if r >= 0.01:
            ax.text(b.get_x() + b.get_width() / 2, r + 0.004, f"{r:.2f}",
                    ha="center", va="bottom", fontsize=7.5, color=INK2)
    ax.set_xticks(x, STRATA, fontsize=8)
    ax.set_title("Code task, gpt-4o-mini\n(80 prompts/stratum)", fontsize=10)
    ax.set_ylim(0, 0.22)
    ax.yaxis.grid(True, color=GRID, zorder=0)

    fig.suptitle("Real measured difficulty heterogeneity (temperature 0, "
                 "distinct prompts)", fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig1_heterogeneity.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


def fig2_width_vs_n():
    p = 0.202
    ns = np.arange(10, 501, 5)
    widths = {"Betting CS (anytime-valid)": [],
              "Hoeffding∩Bernstein CS (anytime-valid)": [],
              "Wilson 95% (fixed-n, invalid when peeking)": []}
    for n in ns:
        f = round(p * n)
        s = n - f
        for name, fn in [("Betting CS (anytime-valid)", betting_bounds),
                         ("Hoeffding∩Bernstein CS (anytime-valid)", intersection_bounds),
                         ("Wilson 95% (fixed-n, invalid when peeking)", wilson_interval)]:
            lo, hi = fn(f, s, 0.05)
            widths[name].append(hi - lo)

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(ns, widths["Hoeffding∩Bernstein CS (anytime-valid)"],
            color=ORANGE, lw=2)
    ax.plot(ns, widths["Betting CS (anytime-valid)"], color=BLUE, lw=2)
    ax.plot(ns, widths["Wilson 95% (fixed-n, invalid when peeking)"],
            color=INK2, lw=1.5, ls="--")
    ax.annotate("Hoeffding∩Bernstein CS", xy=(150, 0.475), color=ORANGE,
                fontsize=9)
    ax.annotate("Betting CS", xy=(320, 0.175), color=BLUE, fontsize=9)
    ax.annotate("Wilson (not valid under peeking)", xy=(255, 0.045),
                color=INK2, fontsize=9)
    ax.axhline(0.35, color=GRID, lw=1)
    ax.text(15, 0.358, "width target 0.35", ha="left", fontsize=8,
            color=INK2)
    ax.set_xlabel("n (samples)")
    ax.set_ylabel("95% interval width")
    ax.set_title(f"Interval width at p̂ = {p} — the betting CS is ~2× "
                 "tighter than stitched bounds", fontsize=10)
    ax.set_ylim(0, 0.75)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig2_width_vs_n.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig3_miscoverage():
    # Numbers from results_advanced.txt (E1)
    methods = ["Wald 95%\n(fixed-n)", "Wilson 95%\n(fixed-n)",
               "Betting CS\n(anytime-valid)"]
    rates = [1.000, 0.477, 0.036]
    colors = [CRITICAL, CRITICAL, GOOD]

    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    bars = ax.barh(methods[::-1], rates[::-1], color=colors[::-1],
                   height=0.55, zorder=3)
    for b, r in zip(bars, rates[::-1]):
        ax.text(min(r + 0.02, 0.93), b.get_y() + b.get_height() / 2,
                f"{r:.1%}", va="center", fontsize=9, color=INK)
    ax.axvline(0.05, color=INK2, lw=1, ls=":")
    ax.text(0.055, -0.42, "5% guarantee", fontsize=8, color=INK2)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("P(interval excludes true p at ANY n ≤ 200)")
    ax.set_title("Peeking breaks fixed-n intervals "
                 "(real GPT-4o-mini outcomes, 2000 reps)", fontsize=10)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig3_miscoverage.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig4_certification():
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.2))

    # Panel A: allocation strategies, UNSAFE certification (gpt-4o-mini)
    ax = axes[0]
    labels = ["round-robin", "greedy\nallocation", "decision-directed\nallocation"]
    times = [588, 224, 176]
    bars = ax.bar(labels, times, width=0.5, color=[BLUE, ORANGE, AQUA],
                  zorder=3)
    for b, t in zip(bars, times):
        ax.text(b.get_x() + b.get_width() / 2, t + 10, str(t), ha="center",
                fontsize=9, color=INK)
    ax.set_ylabel("median samples to certify")
    ax.set_title("Certify UNSAFE (τ=0.15), gpt-4o-mini JSON\n"
                 "(directed allocation: 3.3× faster)", fontsize=9.5)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    ax.set_ylim(0, 700)

    # Panel B: betting vs intersection, SAFE certification (code task)
    ax = axes[1]
    labels = ["Betting CS", "Hoeffding∩Bernstein CS"]
    med = [356, 1820]
    completed = [1.0, 166 / 500]
    bars = ax.bar(labels, med, width=0.45, color=[BLUE, ORANGE], zorder=3)
    ax.text(bars[0].get_x() + bars[0].get_width() / 2, med[0] + 40,
            "356\n(100% certify)", ha="center", fontsize=8.5, color=INK)
    ax.text(bars[1].get_x() + bars[1].get_width() / 2, med[1] + 40,
            "1820\n(only 33% certify\nwithin n=2000)", ha="center",
            fontsize=8.5, color=INK)
    ax.set_ylabel("median samples to certify")
    ax.set_title("Certify SAFE (τ=0.10), gpt-4o-mini code task\n"
                 "(p* = 0.05; 500 reps; zero wrong decisions)", fontsize=9.5)
    ax.set_ylim(0, 2450)
    ax.yaxis.grid(True, color=GRID, zorder=0)

    fig.tight_layout()
    fig.savefig(FIGDIR / "fig4_certification.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


def fig5_comparison_and_blocks():
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.3))

    # Panel A: paired model comparison
    ax = axes[0]
    labels = ["4o-mini vs\n4.1-nano", "4.1-nano vs\n4.1-mini",
              "constructed\nexact tie\n(synthetic)"]
    med_prompts = [74, 335, np.nan]
    bars = ax.bar(labels[:2], med_prompts[:2], width=0.45, color=BLUE,
                  zorder=3)
    for b, t in zip(bars, med_prompts[:2]):
        ax.text(b.get_x() + b.get_width() / 2, t + 8,
                f"{int(t)} prompts\n(500/500 correct)", ha="center",
                fontsize=8.5, color=INK)
    ax.bar(labels[2], [380], width=0.45, color="#d9d8d4", zorder=3)
    ax.text(2, 392, "abstains 96%\n(false certs 4.0%\nwithin α=5%)",
            ha="center", fontsize=8.5, color=INK2)
    ax.set_ylabel("median prompts to certify")
    ax.set_ylim(0, 520)
    ax.set_title("Anytime-valid paired model comparison\n"
                 "(sequential McNemar, α=0.05)", fontsize=9.5)
    ax.yaxis.grid(True, color=GRID, zorder=0)

    # Panel B: provable validity via block reduction
    ax = axes[1]
    labels = ["WSR CS\non blocks\n(provable)", "per-sample\nbetting CS\n(empirical)",
              "binarized\nblocks\n(provable)", "stitched EB\non blocks\n(provable)"]
    times = [184, 336, 1324, np.nan]
    colors = [AQUA, BLUE, ORANGE, ORANGE]
    bars = ax.bar(labels[:3], times[:3], width=0.5, color=colors[:3], zorder=3)
    for b, t in zip(bars, times[:3]):
        ax.text(b.get_x() + b.get_width() / 2, t + 30, str(int(t)),
                ha="center", fontsize=9, color=INK)
    ax.bar(labels[3], [2000], width=0.5, color="#d9d8d4", zorder=3)
    ax.text(3, 2040, "never\n(n≤2000)", ha="center", fontsize=8.5, color=INK2)
    ax.set_ylabel("median samples, width ≤ 0.15")
    ax.set_ylim(0, 2450)
    ax.set_title("Stratify → block → bet: provably valid AND tighter\n"
                 "(real gpt-4o-mini pools, 500 reps)", fontsize=9.5)
    ax.yaxis.grid(True, color=GRID, zorder=0)

    fig.tight_layout()
    fig.savefig(FIGDIR / "fig5_comparison_blocks.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


def fig6_scoreboard():
    """Condition x method: median samples to certify; winner highlighted."""
    conditions = ["4o-mini UNSAFE\nτ=.15 (easy)", "nano SAFE\nτ=.15 (easy)",
                  "mini SAFE\nτ=.15 (easy)", "4o-mini UNSAFE\nτ=.17 (hard)",
                  "4o-mini UNSAFE\nτ=.18 (hard)", "nano SAFE\nτ=.11 (hard)"]
    methods = ["WSR blocks\n(provable)", "bonf+directed\n(provable)",
               "single-stream\n(empirical†)", "TaSC\n(ours, provable)",
               "Spertus UI-TS\n(SOTA, provable)"]
    # Spertus column: CRN censored medians where run (results_spertus_crn
    # / results_spertus_baseline); nan = not run on that condition.
    data = np.array([
        [254, 190, 596, 324, 156],
        [268, 792, 260, 448, 184],
        [160, 356, 72, 172, np.nan],
        [662, 808, 1696, 1014, 736],
        [1308, 1802, 3186, 2388, 4000],
        [748, 3108, 1288, 1874, 812],
    ], dtype=float)

    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    norm = data / np.nanmin(data, axis=1, keepdims=True)
    im = ax.imshow(np.log(norm), cmap="Blues", vmin=0, vmax=2.2,
                   aspect="auto")
    for i in range(len(conditions)):
        winner = int(np.nanargmin(data[i]))
        for j in range(len(methods)):
            if np.isnan(data[i, j]):
                ax.text(j, i, "—", ha="center", va="center", color=INK2)
                continue
            bold = j == winner
            ax.text(j, i, f"{int(data[i, j])}", ha="center", va="center",
                    fontsize=10 if bold else 9,
                    fontweight="bold" if bold else "normal",
                    color=INK if norm[i, j] < 3.5 else "#ffffff")
            if bold:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                           fill=False, edgecolor=GOOD,
                                           lw=2.5, zorder=4))
    ax.set_xticks(range(len(methods)), methods, fontsize=8.5)
    ax.set_yticks(range(len(conditions)), conditions, fontsize=8.5)
    ax.set_title("Median samples to certify (α=0.05) — winner boxed; "
                 "shading = ratio to row winner\n"
                 "three methods share the frontier; ties per results_spertus_crn; "
                 "†single-stream: empirical validity only", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig6_scoreboard.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig1_heterogeneity()
    fig2_width_vs_n()
    fig3_miscoverage()
    fig4_certification()
    fig5_comparison_and_blocks()
    fig6_scoreboard()
    for f in sorted(FIGDIR.glob("*.png")):
        print(f)
