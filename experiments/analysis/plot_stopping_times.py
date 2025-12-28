"""Plot stopping time distributions across multiple runs."""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def load_final_results(experiment_dirs: list[Path]) -> pd.DataFrame:
    """Load final results from multiple experiment runs.

    Args:
        experiment_dirs: List of result directories

    Returns:
        DataFrame with final statistics from each run
    """
    records = []

    for exp_dir in experiment_dirs:
        db_path = exp_dir / "results.db"
        if not db_path.exists():
            continue

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT experiment_id, stop_reason,
                   final_n_samples, final_n_failures,
                   final_lower, final_upper, final_point_estimate
            FROM experiments
            WHERE stopped = 1
        """
        )

        row = cursor.fetchone()
        if row:
            records.append(
                {
                    "experiment_id": row[0],
                    "stop_reason": row[1],
                    "n_samples": row[2],
                    "n_failures": row[3],
                    "final_lower": row[4],
                    "final_upper": row[5],
                    "final_point_estimate": row[6],
                    "ci_width": row[5] - row[4] if row[4] and row[5] else None,
                }
            )

        conn.close()

    return pd.DataFrame(records)


def plot_stopping_time_histogram(df: pd.DataFrame, output_path: Path):
    """Plot histogram of stopping times.

    Args:
        df: DataFrame with 'n_samples' column
        output_path: Where to save plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(df["n_samples"], bins=20, edgecolor="black", alpha=0.7)
    ax.axvline(
        df["n_samples"].mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean = {df['n_samples'].mean():.0f}",
    )
    ax.axvline(
        df["n_samples"].median(),
        color="orange",
        linestyle="--",
        linewidth=2,
        label=f"Median = {df['n_samples'].median():.0f}",
    )

    ax.set_xlabel("Stopping Time (Number of Samples)", fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.set_title("Distribution of Sequential Stopping Times", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved stopping time histogram to {output_path}")
    plt.close()


def print_summary_statistics(df: pd.DataFrame):
    """Print summary statistics of experiments.

    Args:
        df: DataFrame with final results
    """
    print("\n=== Summary Statistics ===")
    print(f"Number of experiments: {len(df)}")
    print(f"\nStopping times:")
    print(f"  Mean: {df['n_samples'].mean():.1f}")
    print(f"  Median: {df['n_samples'].median():.1f}")
    print(f"  Std: {df['n_samples'].std():.1f}")
    print(f"  Min: {df['n_samples'].min()}")
    print(f"  Max: {df['n_samples'].max()}")

    print(f"\nFinal CI widths:")
    print(f"  Mean: {df['ci_width'].mean():.4f}")
    print(f"  Median: {df['ci_width'].median():.4f}")
    print(f"  Std: {df['ci_width'].std():.4f}")

    print(f"\nPoint estimates:")
    print(f"  Mean: {df['final_point_estimate'].mean():.4f}")
    print(f"  Std: {df['final_point_estimate'].std():.4f}")

    print(f"\nStop reasons:")
    print(df["stop_reason"].value_counts())


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python plot_stopping_times.py <exp_dir1> [exp_dir2 ...]")
        sys.exit(1)

    exp_dirs = [Path(p) for p in sys.argv[1:]]
    df = load_final_results(exp_dirs)

    if len(df) == 0:
        print("No completed experiments found")
        sys.exit(1)

    print_summary_statistics(df)

    output_path = Path("stopping_times.png")
    plot_stopping_time_histogram(df, output_path)
