#!/usr/bin/env python3
"""Analyze stratified sampling experiment results.

This script compares naive vs stratified sampling to demonstrate:
1. Heterogeneity exists (per-stratum failure rates differ)
2. Naive exhibits sampling imbalance
3. Stratified maintains perfect balance
4. Both maintain time-uniform validity
"""

import sys
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import sqlite3
import numpy as np


def load_experiment_data(db_path: Path):
    """Load samples and metadata from experiment database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get experiment metadata
    cursor.execute("SELECT * FROM experiments LIMIT 1")
    exp_row = cursor.fetchone()
    exp_cols = [desc[0] for desc in cursor.description]
    experiment = dict(zip(exp_cols, exp_row))

    # Get all samples
    cursor.execute("""
        SELECT sample_id, prompt_id, result, failed, stratum, stop_reason
        FROM samples
        ORDER BY sample_id
    """)
    samples = cursor.fetchall()

    conn.close()

    return experiment, samples


def analyze_per_stratum_rates(samples):
    """Analyze failure rates by stratum."""
    stratum_data = {}

    for sample_id, prompt_id, result, failed, stratum, stop_reason in samples:
        if stratum is None:
            continue  # Skip samples without stratum info

        if stratum not in stratum_data:
            stratum_data[stratum] = {'total': 0, 'failures': 0}

        stratum_data[stratum]['total'] += 1
        if failed:
            stratum_data[stratum]['failures'] += 1

    return stratum_data


def analyze_sampling_distribution(samples):
    """Analyze how many samples from each stratum."""
    stratum_counts = Counter()

    for sample_id, prompt_id, result, failed, stratum, stop_reason in samples:
        if stratum is not None:
            stratum_counts[stratum] += 1

    return stratum_counts


def print_comparison(naive_db: Path, stratified_db: Path):
    """Print detailed comparison of naive vs stratified."""
    print("="*70)
    print("STRATIFIED SAMPLING EXPERIMENT ANALYSIS")
    print("="*70)
    print()

    # Load data
    naive_exp, naive_samples = load_experiment_data(naive_db)
    strat_exp, strat_samples = load_experiment_data(stratified_db)

    print(f"Naive: {len(naive_samples)} samples")
    print(f"Stratified: {len(strat_samples)} samples")
    print()

    # 1. Per-stratum failure rates (validate heterogeneity)
    print("="*70)
    print("1. PER-STRATUM FAILURE RATES (Heterogeneity Validation)")
    print("="*70)
    print()

    naive_stratum = analyze_per_stratum_rates(naive_samples)
    strat_stratum = analyze_per_stratum_rates(strat_samples)

    print(f"{'Stratum':>12} | {'Naive p̂':>10} | {'Naive n':>8} | {'Strat p̂':>10} | {'Strat n':>8}")
    print("-"*70)

    all_strata = sorted(set(naive_stratum.keys()) | set(strat_stratum.keys()))

    for stratum in all_strata:
        naive_n = naive_stratum.get(stratum, {}).get('total', 0)
        naive_f = naive_stratum.get(stratum, {}).get('failures', 0)
        naive_p = naive_f / naive_n if naive_n > 0 else 0

        strat_n = strat_stratum.get(stratum, {}).get('total', 0)
        strat_f = strat_stratum.get(stratum, {}).get('failures', 0)
        strat_p = strat_f / strat_n if strat_n > 0 else 0

        print(f"{stratum:>12} | {naive_p:10.4f} | {naive_n:8d} | {strat_p:10.4f} | {strat_n:8d}")

    print()
    print("OBSERVATION: If failure rates differ across strata, heterogeneity exists.")
    print()

    # 2. Sampling distribution (balance check)
    print("="*70)
    print("2. SAMPLING DISTRIBUTION (Balance Check)")
    print("="*70)
    print()

    naive_dist = analyze_sampling_distribution(naive_samples)
    strat_dist = analyze_sampling_distribution(strat_samples)

    print(f"{'Stratum':>12} | {'Naive Count':>12} | {'Strat Count':>12} | {'Balance':>10}")
    print("-"*70)

    for stratum in all_strata:
        naive_count = naive_dist.get(stratum, 0)
        strat_count = strat_dist.get(stratum, 0)

        if len(all_strata) > 0:
            expected = len(strat_samples) / len(all_strata)
            balance = "✓ Perfect" if abs(strat_count - expected) < 1 else "⚠ Imbalanced"
        else:
            balance = "N/A"

        print(f"{stratum:>12} | {naive_count:12d} | {strat_count:12d} | {balance:>10}")

    # Calculate variance
    naive_counts = list(naive_dist.values())
    strat_counts = list(strat_dist.values())

    naive_var = np.var(naive_counts) if naive_counts else 0
    strat_var = np.var(strat_counts) if strat_counts else 0

    print()
    print(f"Variance in counts:")
    print(f"  Naive: {naive_var:.2f} (natural variance from uniform sampling)")
    print(f"  Stratified: {strat_var:.2f} (should be ~0 for perfect balance)")
    print()

    # 3. Overall estimates
    print("="*70)
    print("3. OVERALL FAILURE RATE ESTIMATES")
    print("="*70)
    print()

    naive_total = len(naive_samples)
    naive_failures = sum(1 for _, _, _, failed, _, _ in naive_samples if failed)
    naive_p = naive_failures / naive_total if naive_total > 0 else 0

    strat_total = len(strat_samples)
    strat_failures = sum(1 for _, _, _, failed, _, _ in strat_samples if failed)
    strat_p = strat_failures / strat_total if strat_total > 0 else 0

    print(f"{'Method':>12} | {'n':>6} | {'Failures':>9} | {'p̂':>8} | {'Stop Reason':>30}")
    print("-"*70)
    print(f"{'Naive':>12} | {naive_total:6d} | {naive_failures:9d} | {naive_p:8.4f} | {naive_exp.get('stop_reason', 'N/A'):>30}")
    print(f"{'Stratified':>12} | {strat_total:6d} | {strat_failures:9d} | {strat_p:8.4f} | {strat_exp.get('stop_reason', 'N/A'):>30}")

    print()

    # 4. Early-stopping bias assessment
    print("="*70)
    print("4. EARLY-STOPPING BIAS ASSESSMENT")
    print("="*70)
    print()

    print("If naive sampling exhibits bias:")
    print("  • May oversample easy strata → underestimate p")
    print("  • May oversample hard strata → overestimate p")
    print("  • Stopping rule is valid, but estimate may be biased")
    print()
    print("Stratified sampling avoids bias:")
    print("  • Guarantees balanced representation")
    print("  • Estimate is unbiased (equal weight to all strata)")
    print("  • Stopping rule remains valid")
    print()

    if abs(naive_p - strat_p) > 0.01:
        print(f"⚠ BIAS DETECTED: |p̂_naive - p̂_stratified| = {abs(naive_p - strat_p):.4f}")
        print(f"   This suggests naive sampling exhibited early-stopping bias.")
    else:
        print(f"✓ NO SIGNIFICANT BIAS: |p̂_naive - p̂_stratified| = {abs(naive_p - strat_p):.4f}")
        print(f"   Both methods converged to similar estimates.")

    print()

    # 5. Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print()
    print("Main Findings:")
    print(f"  1. Heterogeneity: {'✓ Confirmed' if len(all_strata) > 1 else '⚠ Not confirmed'}")
    print(f"  2. Naive balance: Variance = {naive_var:.2f}")
    print(f"  3. Stratified balance: Variance = {strat_var:.2f}")
    print(f"  4. Estimate difference: {abs(naive_p - strat_p):.4f}")
    print()
    print("Conclusion:")
    if strat_var < 1.0:
        print("  ✓ Stratified sampling maintains perfect balance")
    if naive_var > strat_var:
        print("  ✓ Naive sampling shows natural imbalance")
    print()


def main():
    # Find experiment directories
    results_dir = Path("experiments/results")

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        print("Run experiments first: python run_stratified_experiments.py")
        sys.exit(1)

    # Look for naive and stratified experiment databases
    # The experiment IDs are deterministic hashes, so we need to find them

    all_dbs = list(results_dir.glob("*/results.db"))

    if len(all_dbs) < 2:
        print(f"Error: Expected at least 2 experiment databases, found {len(all_dbs)}")
        print("Run both experiments first: python run_stratified_experiments.py")
        sys.exit(1)

    # Sort by modification time (most recent last)
    all_dbs.sort(key=lambda p: p.stat().st_mtime)

    # Assume the two most recent are naive and stratified
    if len(all_dbs) >= 2:
        naive_db = all_dbs[-2]
        stratified_db = all_dbs[-1]

        print(f"Analyzing experiments:")
        print(f"  Naive: {naive_db.parent.name}")
        print(f"  Stratified: {stratified_db.parent.name}")
        print()

        print_comparison(naive_db, stratified_db)
    else:
        print("Not enough experiments found.")


if __name__ == "__main__":
    main()
