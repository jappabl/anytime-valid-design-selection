#!/usr/bin/env python3
"""Query experiment progress from database."""

import sqlite3
import sys
from pathlib import Path


def list_experiments():
    """List all experiments in the results directory."""
    results_dir = Path("experiments/results")

    if not results_dir.exists():
        print("No experiments/results directory found")
        return []

    exp_dirs = [d for d in results_dir.iterdir() if d.is_dir()]

    if not exp_dirs:
        print("No experiments found")
        return []

    print(f"\nFound {len(exp_dirs)} experiment(s):\n")

    experiments = []
    for exp_dir in sorted(exp_dirs):
        db_path = exp_dir / "results.db"
        if not db_path.exists():
            continue

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get experiment metadata
        cursor.execute("SELECT experiment_id, config_json, stopped, stop_reason, final_n_samples FROM experiments")
        row = cursor.fetchone()

        if row:
            exp_id, config_json, stopped, stop_reason, final_n = row

            # Parse name from config if possible
            import json
            try:
                config = json.loads(config_json)
                name = config.get('name', 'unknown')
            except:
                name = 'unknown'

            # Get latest snapshot
            cursor.execute("SELECT n_samples, point_estimate, ci_width FROM statistics_snapshots ORDER BY n_samples DESC LIMIT 1")
            snapshot = cursor.fetchone()

            status = "COMPLETE" if stopped else "RUNNING"
            if snapshot:
                n, p_hat, width = snapshot
                print(f"  {exp_id[:12]}... - {name:<35} | {status:8} | n={n:4d} p̂={p_hat:.4f} width={width:.4f}")
            else:
                print(f"  {exp_id[:12]}... - {name:<35} | {status:8} | no data")

            experiments.append((exp_id, name, exp_dir))

        conn.close()

    return experiments


def query_progress(experiment_name_or_id: str):
    """Query and display experiment progress over time.

    Args:
        experiment_name_or_id: Name or ID prefix of experiment
    """
    # Find experiment directory
    results_dir = Path("experiments/results")

    # Try exact ID match first
    exp_dir = results_dir / experiment_name_or_id
    if exp_dir.exists():
        exp_dirs = [exp_dir]
    else:
        # Try name-based glob
        exp_dirs = list(results_dir.glob(f"{experiment_name_or_id}_*"))

        # Try ID prefix match
        if not exp_dirs:
            exp_dirs = [d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith(experiment_name_or_id)]

    if not exp_dirs:
        print(f"No experiment found matching: {experiment_name_or_id}")
        print("\nUse 'list' to see all experiments")
        return

    if len(exp_dirs) > 1:
        print(f"Multiple experiments found:")
        for d in exp_dirs:
            print(f"  - {d.name}")
        print(f"\nUsing most recent: {exp_dirs[-1].name}")

    exp_dir = exp_dirs[-1]
    db_path = exp_dir / "results.db"

    if not db_path.exists():
        print(f"No database found at: {db_path}")
        return

    # Query snapshots
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT n_samples, n_failures, point_estimate, lower_bound, upper_bound, ci_width, timestamp
        FROM statistics_snapshots
        ORDER BY n_samples ASC
    """)

    rows = cursor.fetchall()

    if not rows:
        print("No statistics snapshots found")
        conn.close()
        return

    print(f"\n{'n':>5} | {'Failures':>8} | {'p̂':>8} | {'Lower':>8} | {'Upper':>8} | {'Width':>8} | Timestamp")
    print("-" * 90)

    for n, failures, p_hat, lower, upper, width, ts in rows:
        print(f"{n:5d} | {failures:8d} | {p_hat:8.4f} | {lower:8.4f} | {upper:8.4f} | {width:8.4f} | {ts}")

    # Check if experiment is complete
    cursor.execute("SELECT stopped, stop_reason, final_n_samples FROM experiments")
    stopped, stop_reason, final_n = cursor.fetchone()

    print("\n" + "=" * 90)
    if stopped:
        print(f"Status: COMPLETE (n={final_n}, reason: {stop_reason})")
    else:
        print(f"Status: RUNNING (last snapshot at n={rows[-1][0]})")

    conn.close()


def compare_experiments(exp1_name: str, exp2_name: str):
    """Compare two experiments side by side.

    Args:
        exp1_name: First experiment name
        exp2_name: Second experiment name
    """
    results_dir = Path("experiments/results")

    # Find experiments
    exp1_dirs = list(results_dir.glob(f"{exp1_name}_*"))
    exp2_dirs = list(results_dir.glob(f"{exp2_name}_*"))

    if not exp1_dirs or not exp2_dirs:
        print(f"Could not find both experiments")
        return

    exp1_db = exp1_dirs[-1] / "results.db"
    exp2_db = exp2_dirs[-1] / "results.db"

    # Query both
    conn1 = sqlite3.connect(str(exp1_db))
    conn2 = sqlite3.connect(str(exp2_db))

    cursor1 = conn1.cursor()
    cursor2 = conn2.cursor()

    cursor1.execute("SELECT n_samples, point_estimate, ci_width FROM statistics_snapshots ORDER BY n_samples")
    cursor2.execute("SELECT n_samples, point_estimate, ci_width FROM statistics_snapshots ORDER BY n_samples")

    rows1 = cursor1.fetchall()
    rows2 = cursor2.fetchall()

    print(f"\n{'n':>5} | {exp1_name:^30} | {exp2_name:^30}")
    print(f"      | {'p̂':>8} {'Width':>8} {'Stratum Var':>12} | {'p̂':>8} {'Width':>8} {'Stratum Var':>12}")
    print("-" * 90)

    # Merge and display
    all_n = sorted(set([r[0] for r in rows1] + [r[0] for r in rows2]))

    rows1_dict = {n: (p, w) for n, p, w in rows1}
    rows2_dict = {n: (p, w) for n, p, w in rows2}

    for n in all_n:
        line = f"{n:5d} |"

        if n in rows1_dict:
            p1, w1 = rows1_dict[n]
            line += f" {p1:8.4f} {w1:8.4f} {'':>12} |"
        else:
            line += f" {'':>8} {'':>8} {'':>12} |"

        if n in rows2_dict:
            p2, w2 = rows2_dict[n]
            line += f" {p2:8.4f} {w2:8.4f} {'':>12}"
        else:
            line += f" {'':>8} {'':>8} {'':>12}"

        print(line)

    conn1.close()
    conn2.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 query_experiment_progress.py list")
        print("  python3 query_experiment_progress.py <experiment_name_or_id>")
        print("  python3 query_experiment_progress.py <exp1_name> <exp2_name>")
        print("\nExamples:")
        print("  python3 query_experiment_progress.py list")
        print("  python3 query_experiment_progress.py e527898b57db")
        print("  python3 query_experiment_progress.py stratified_gpt4mini_naive")
        print("  python3 query_experiment_progress.py stratified_gpt4mini_naive stratified_gpt4mini_stratified")
        sys.exit(1)

    if sys.argv[1] == "list":
        list_experiments()
    elif len(sys.argv) == 2:
        query_progress(sys.argv[1])
    else:
        compare_experiments(sys.argv[1], sys.argv[2])
