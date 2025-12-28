#!/usr/bin/env python3
"""Run stratified sampling experiments to validate heterogeneity bias mitigation.

This runs two paired experiments:
1. Naive (baseline): Uniform sampling - may exhibit early-stopping bias
2. Stratified (proposed): Balanced sampling - should avoid bias
"""

import os
import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import yaml
from eval_harness.core.config import ExperimentConfig
from eval_harness.core.runner import ExperimentRunner


def load_env_file(env_path: Path = Path(".env")):
    """Load environment variables from .env file."""
    if not env_path.exists():
        return

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def expand_env_vars(config_dict):
    """Recursively expand environment variables in config dict.

    Replaces ${VAR_NAME} with os.environ['VAR_NAME'].
    """
    if isinstance(config_dict, dict):
        return {k: expand_env_vars(v) for k, v in config_dict.items()}
    elif isinstance(config_dict, list):
        return [expand_env_vars(item) for item in config_dict]
    elif isinstance(config_dict, str):
        # Replace ${VAR} with environment variable value
        pattern = r'\$\{([^}]+)\}'

        def replace_env(match):
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(f"Environment variable {var_name} not set")
            return value

        return re.sub(pattern, replace_env, config_dict)
    else:
        return config_dict


def run_experiment(config_path: Path, output_dir: Path):
    """Run a single experiment."""
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"Running: {config_path.name}")
    print(f"{'='*70}\n")

    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    # Expand environment variables
    config_dict = expand_env_vars(config_dict)

    config = ExperimentConfig(**config_dict)
    runner = ExperimentRunner(config, output_dir, verbose=True)

    try:
        runner.run()
    finally:
        runner.cleanup()

    print(f"\n✓ Experiment complete: {config.name}")
    print(f"Results saved to: {runner.experiment_dir}")

    return runner.experiment_id, runner.experiment_dir


def main():
    # Load environment variables from .env file
    load_env_file()

    output_dir = Path("experiments/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define experiment configs
    configs = [
        ("configs/stratified_gpt4mini_naive.yaml", "Naive Sampling (Baseline)"),
        ("configs/stratified_gpt4mini_stratified.yaml", "Stratified Sampling (Proposed)"),
    ]

    results = {}

    for config_path_str, description in configs:
        config_path = Path(config_path_str)
        experiment_id, experiment_dir = run_experiment(config_path, output_dir)
        results[description] = {
            'config': config_path_str,
            'experiment_id': experiment_id,
            'experiment_dir': experiment_dir,
        }

    # Print summary
    print("\n" + "="*70)
    print("EXPERIMENT SUMMARY")
    print("="*70 + "\n")

    for description, info in results.items():
        print(f"{description}:")
        print(f"  Config: {info['config']}")
        print(f"  ID: {info['experiment_id']}")
        print(f"  Dir: {info['experiment_dir']}")
        print()

    print("Next steps:")
    print("  1. Run analysis: python analyze_stratified_results.py")
    print("  2. View detailed results in experiments/results/")
    print()


if __name__ == "__main__":
    main()
