#!/usr/bin/env python3
"""Generate figures 7-9 for paper v3 from committed result artifacts.

Numbers are hard-coded FROM the checksummed artifacts they cite (rev-2
values); regenerating after an artifact changes requires updating the
corresponding array here — each figure names its source artifact.
Outputs PNG files to paper/figures/. Deterministic.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).parent.parent
FIGDIR = REPO / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e5e4e0"


def fig7_drift():
    """Warm-start staleness budget (results_warmstart_drift.txt rev 2)."""
    deltas = [-0.10, -0.06, -0.03, -0.015, 0.0, 0.015, 0.03, 0.06, 0.10]
    medians = [1350, 836, 362, 288, 276, 460, 928, 1718, 1748]
    wsr, cold = 350, 1572

    fig, ax = plt.subplots(figsize=(7.2, 4.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.axhline(cold, color=INK2, lw=1.2, ls="--")
    ax.text(0.102, cold, "cold UI (1572)", va="bottom", ha="right",
            fontsize=8.5, color=INK2)
    ax.axhline(cold + 181, color=CRITICAL, lw=1.0, ls=":")
    ax.text(0.102, cold + 181, "contamination ceiling (cold + log(1/ε)/V)",
            va="bottom", ha="right", fontsize=8.5, color=CRITICAL)
    ax.axhline(wsr, color=ORANGE, lw=1.2, ls="--")
    ax.text(0.102, wsr, "WSR blocks (350)", va="bottom", ha="right",
            fontsize=8.5, color=ORANGE)
    ax.plot(deltas, medians, "-o", color=BLUE, lw=2, ms=5, zorder=5,
            label="warm-start UI (joint ε-contamination)")
    ax.axvspan(-0.015, 0.0, color=GOOD, alpha=0.10)
    ax.text(-0.0075, 90, "robust\nwin", ha="center", fontsize=8,
            color=GOOD)
    ax.set_xlabel("prior drift δ  (prior rates = truth + δ, clipped)")
    ax.set_ylabel("median samples to certify (τ = 0.16)")
    ax.set_title("Warm-start staleness budget is asymmetric: "
                 "overstating failure rates is the expensive mistake",
                 fontsize=10.5)
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.annotate("understated prior:\nclipped at zero-rate strata,\n"
                "nearly free", xy=(-0.06, 836), xytext=(-0.095, 1150),
                fontsize=8, color=INK2,
                arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
    ax.annotate("overstated prior:\npoisons all strata,\nsaturates at "
                "the ε floor", xy=(0.06, 1718), xytext=(0.018, 1350),
                fontsize=8, color=INK2,
                arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
    fig.savefig(FIGDIR / "fig7_drift_budget.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


def fig8_frontier():
    """Cold-start overhead by construction (results_frontier.txt rev 2),
    tau=0.16 column; arms at >=95% certification plus the censored
    split-LRT b=50 shown hatched."""
    arms = ["UI\nmixture", "epoch-\nsplit", "split-LRT\nb=100",
            "single-\nstream", "warm-start\n(recurring)"]
    overheads = [16.00, 27.46, 6.36, 2.98, 0.76]
    colors = [BLUE, INK2, AQUA, ORANGE, GOOD]
    notes = ["pays (d/2)·log n", "misses window\n(1.72× UI)",
             "escapes: 0.40× UI\n(FALSIFIES conservation)",
             "d = 1 only", "oracle-adjacent prior\n(results_warmstart)"]

    fig, ax = plt.subplots(figsize=(7.2, 4.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.bar(arms, overheads, color=colors, width=0.62)
    ax.axhline(16.00 * 0.5, color=CRITICAL, lw=1.2, ls="--")
    ax.text(4.45, 8.3, "pre-registered\nfalsification line (0.5× UI)",
            fontsize=8, color=CRITICAL, ha="right")
    for b, oh, note in zip(bars, overheads, notes):
        ax.text(b.get_x() + b.get_width() / 2, oh + 0.5, f"{oh:+.2f}",
                ha="center", fontsize=9, color=INK)
        ax.text(b.get_x() + b.get_width() / 2, oh + 2.2, note,
                ha="center", fontsize=7.5, color=INK2)
    ax.set_ylabel("overhead beyond log(1/α), nats  (τ = 0.16, V_rr)")
    ax.set_title("The learning tax and its three escapes "
                 "(gpt-4o-mini pools; ≥95%-certified arms)",
                 fontsize=10.5)
    ax.set_ylim(0, 31)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.savefig(FIGDIR / "fig8_frontier.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


def fig9_design_map():
    """The four-regime design map with per-regime winning evidence."""
    fig, ax = plt.subplots(figsize=(8.0, 4.6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    ax.axis("off")

    cells = [
        (0, 1, "EXTREME heterogeneity\nHARD margin",
         "WSR blocks",
         "662/1308/748 vs mixtures\n(results_wsr_hard)", ORANGE),
        (1, 1, "EXTREME heterogeneity\nEASY margin",
         "directed (UNSAFE)\nsingle-stream (SAFE)",
         "190 median UNSAFE\n(fig6 scoreboard)", BLUE),
        (0, 0, "MILD heterogeneity\n(e.g. MBPP)",
         "single-stream",
         "V_rr ≈ V_pool: strata buy nothing;\nUI censors, WSR d≈2 "
         "(results_mbpp_law)", AQUA),
        (1, 0, "RECURRING evaluation\n(smooth drift ≤ ~0.015)",
         "warm-start UI",
         "overhead 0.8-1.2 nats vs 16-18 cold;\nzero wrong certs "
         "(results_warmstart*)", GOOD),
    ]
    for x, y, regime, winner, ev, color in cells:
        ax.add_patch(plt.Rectangle((x + 0.02, y + 0.02), 0.96, 0.96,
                                   facecolor=color, alpha=0.10,
                                   edgecolor=color, lw=1.5))
        ax.text(x + 0.5, y + 0.82, regime, ha="center", fontsize=9,
                color=INK2)
        ax.text(x + 0.5, y + 0.52, winner, ha="center", fontsize=12,
                color=INK, fontweight="bold")
        ax.text(x + 0.5, y + 0.22, ev, ha="center", fontsize=7.5,
                color=INK2)
    ax.set_title("Design map: which anytime-valid design to use "
                 "(all cells audited; every negative result retained)",
                 fontsize=11)
    fig.savefig(FIGDIR / "fig9_design_map.png", dpi=200,
                bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig7_drift()
    fig8_frontier()
    fig9_design_map()
    print("figures 7-9 written to", FIGDIR)
