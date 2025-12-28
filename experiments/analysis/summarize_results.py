"""Summarize experiment results in paper-ready table format."""

import sqlite3
from pathlib import Path

import pandas as pd


def load_experiment_summary(db_path: Path) -> dict:
    """Load summary statistics for an experiment.

    Args:
        db_path: Path to results.db

    Returns:
        Dictionary with summary statistics
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get experiment metadata
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
    if not row:
        conn.close()
        return None

    experiment_id, stop_reason, n_samples, n_failures, lower, upper, p_hat = row

    # Get failure modes breakdown
    cursor.execute(
        """
        SELECT failure_mode, COUNT(*) as count
        FROM validation_results
        WHERE passed = 0 AND experiment_id = ?
        GROUP BY failure_mode
    """,
        (experiment_id,),
    )

    failure_modes = dict(cursor.fetchall())

    conn.close()

    return {
        "experiment_id": experiment_id,
        "n_samples": n_samples,
        "n_failures": n_failures,
        "p_hat": p_hat,
        "ci_lower": lower,
        "ci_upper": upper,
        "ci_width": upper - lower if (lower and upper) else None,
        "stop_reason": stop_reason,
        "failure_modes": failure_modes,
    }


def create_results_table(experiment_summaries: list[dict]) -> pd.DataFrame:
    """Create paper-ready results table.

    Args:
        experiment_summaries: List of summary dicts

    Returns:
        Formatted DataFrame
    """
    df = pd.DataFrame(experiment_summaries)

    # Format for paper
    df["p̂ [95% CS]"] = df.apply(
        lambda row: f"{row['p_hat']:.3f} [{row['ci_lower']:.3f}, {row['ci_upper']:.3f}]",
        axis=1,
    )

    df["CI Width"] = df["ci_width"].apply(lambda x: f"{x:.4f}" if x else "N/A")
    df["Samples"] = df["n_samples"]
    df["Failures"] = df["n_failures"]

    return df[["experiment_id", "Samples", "Failures", "p̂ [95% CS]", "CI Width", "stop_reason"]]


def print_latex_table(df: pd.DataFrame):
    """Print LaTeX-formatted table.

    Args:
        df: Results DataFrame
    """
    print("\n=== LaTeX Table ===")
    print(df.to_latex(index=False, escape=False))


def print_markdown_table(df: pd.DataFrame):
    """Print Markdown-formatted table.

    Args:
        df: Results DataFrame
    """
    print("\n=== Markdown Table ===")
    print(df.to_markdown(index=False))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python summarize_results.py <exp_dir1> [exp_dir2 ...]")
        sys.exit(1)

    summaries = []
    for exp_dir_str in sys.argv[1:]:
        exp_dir = Path(exp_dir_str)
        db_path = exp_dir / "results.db"

        if not db_path.exists():
            print(f"Warning: No results.db in {exp_dir}")
            continue

        summary = load_experiment_summary(db_path)
        if summary:
            summaries.append(summary)

    if not summaries:
        print("No completed experiments found")
        sys.exit(1)

    df = create_results_table(summaries)

    print("\n=== Results Summary ===")
    print(df.to_string(index=False))

    print_markdown_table(df)
    print_latex_table(df)
