"""Command-line interface for evaluation harness."""

from pathlib import Path

import click
import yaml

from eval_harness.core.config import ExperimentConfig
from eval_harness.core.runner import ExperimentRunner


@click.group()
def main():
    """Anytime-valid sequential evaluation harness for LLM failure rates."""
    pass


@main.command()
@click.argument("config_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="experiments/results",
    help="Output directory for results",
)
@click.option("--verbose/--quiet", default=True, help="Show progress")
def run(config_path: Path, output_dir: Path, verbose: bool):
    """Run experiment from config file.

    CONFIG_PATH: Path to YAML config file
    """
    # Load config
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    config = ExperimentConfig(**config_dict)

    # Run experiment
    runner = ExperimentRunner(config, output_dir, verbose=verbose)
    try:
        runner.run()
    finally:
        runner.cleanup()


@main.command()
@click.argument("experiment_id")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="experiments/results",
    help="Results directory",
)
def info(experiment_id: str, output_dir: Path):
    """Show experiment info and results.

    EXPERIMENT_ID: Experiment ID to query
    """
    from eval_harness.storage.store import ResultStore

    db_path = output_dir / experiment_id / "results.db"
    if not db_path.exists():
        click.echo(f"Experiment {experiment_id} not found in {output_dir}")
        return

    store = ResultStore(db_path)
    state = store.load_experiment_state(experiment_id)

    if state is None:
        click.echo(f"No state found for experiment {experiment_id}")
        return

    click.echo(f"Experiment: {experiment_id}")
    click.echo(f"Samples: {state.n_samples}")
    click.echo(f"Failures: {state.n_failures}")
    click.echo(f"Stopped: {state.stopped}")
    if state.stop_reason:
        click.echo(f"Stop reason: {state.stop_reason}")
    if state.latest_bounds:
        lower, upper = state.latest_bounds
        click.echo(f"Latest CS: [{lower:.4f}, {upper:.4f}]")

    store.close()


if __name__ == "__main__":
    main()
