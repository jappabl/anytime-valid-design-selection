"""Plot cost (samples) vs achieved confidence interval width."""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def load_statistics_snapshots(db_path: Path) -> pd.DataFrame:
    """Load statistics snapshots from experiment database.

    Args:
        db_path: Path to results.db

    Returns:
        DataFrame with columns: n_samples, ci_width, lower_bound, upper_bound, etc.
    """
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT n_samples, n_failures, lower_bound, upper_bound,
               point_estimate, ci_width, timestamp
        FROM statistics_snapshots
        ORDER BY n_samples
    """,
        conn,
    )
    conn.close()
    return df


def plot_single_experiment(db_path: Path, output_path: Path):
    """Plot cost curves for a single experiment.

    Args:
        db_path: Path to results.db
        output_path: Where to save plot
    """
    df = load_statistics_snapshots(db_path)

    if len(df) == 0:
        print("No statistics snapshots found")
        return

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Plot 1: CI width over time
    ax = axes[0]
    ax.plot(df["n_samples"], df["ci_width"], marker="o", linewidth=2)
    ax.axhline(0.01, color="red", linestyle="--", label="Target width = 0.01")
    ax.axhline(0.02, color="orange", linestyle="--", label="Target width = 0.02")
    ax.set_ylabel("Confidence Interval Width", fontsize=12)
    ax.set_title("Sample Efficiency: CI Width vs. Number of Samples", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Plot 2: Confidence bounds over time
    ax = axes[1]
    ax.plot(df["n_samples"], df["point_estimate"], label="Point estimate", linewidth=2)
    ax.fill_between(
        df["n_samples"],
        df["lower_bound"],
        df["upper_bound"],
        alpha=0.3,
        label="95% Confidence Sequence",
    )
    ax.set_xlabel("Number of Samples (Cost)", fontsize=12)
    ax.set_ylabel("Failure Probability", fontsize=12)
    ax.set_title("Confidence Sequence Evolution", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved plot to {output_path}")
    plt.close()


def plot_comparison(experiment_dirs: list[Path], labels: list[str], output_path: Path):
    """Compare cost curves across multiple experiments.

    Args:
        experiment_dirs: List of experiment result directories
        labels: Labels for each experiment
        output_path: Where to save plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    for exp_dir, label in zip(experiment_dirs, labels):
        db_path = exp_dir / "results.db"
        df = load_statistics_snapshots(db_path)

        ax.plot(df["n_samples"], df["ci_width"], marker="o", label=label, linewidth=2)

    ax.axhline(0.01, color="red", linestyle="--", alpha=0.5, label="Target = 0.01")
    ax.set_xlabel("Number of Samples (Cost)", fontsize=12)
    ax.set_ylabel("CI Width", fontsize=12)
    ax.set_title("Sample Efficiency Comparison", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved comparison plot to {output_path}")
    plt.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python plot_cost_curves.py <experiment_dir>")
        sys.exit(1)

    exp_dir = Path(sys.argv[1])
    db_path = exp_dir / "results.db"

    if not db_path.exists():
        print(f"No results.db found in {exp_dir}")
        sys.exit(1)

    output_path = exp_dir / "cost_curves.png"
    plot_single_experiment(db_path, output_path)
