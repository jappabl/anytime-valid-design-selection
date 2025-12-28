"""Experiment orchestration with resumability."""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from tqdm import tqdm

from eval_harness.core.config import ExperimentConfig
from eval_harness.core.types import DecodingConfig, Sample
from eval_harness.prompts.base import PromptDataset
from eval_harness.prompts.json_schema_prompts import JSONSchemaPromptDataset
from eval_harness.sampling.base import Sampler
from eval_harness.sampling.toy_sampler import ToySampler
from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection
from eval_harness.stats.stopping import SequentialStopper
from eval_harness.storage.store import ResultStore
from eval_harness.validators.base import Validator
from eval_harness.validators.json_schema import JSONSchemaValidator
from eval_harness.validators.toy_validator import ToyValidator


class ExperimentRunner:
    """Orchestrates sequential evaluation experiments with resumability."""

    def __init__(
        self,
        config: ExperimentConfig,
        output_dir: Path,
        verbose: bool = True,
    ):
        """Initialize experiment runner.

        Args:
            config: Experiment configuration
            output_dir: Directory for results
            verbose: If True, show progress bars and logging
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.verbose = verbose

        # Generate deterministic experiment ID
        self.experiment_id = config.get_experiment_id()
        self.experiment_dir = self.output_dir / self.experiment_id
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        # Initialize storage
        db_path = self.experiment_dir / "results.db"
        self.store = ResultStore(db_path)

        # Initialize components
        self.sampler = self._create_sampler()
        self.validator = self._create_validator()
        self.prompts = self._create_prompts()

        # Initialize statistics (using intersection of Hoeffding + Bernstein with α-splitting)
        self.cs = BernoulliCSIntersection(
            alpha=config.statistics.alpha,
            n_max=config.stopping.max_samples,  # Pass budget cap for time-uniform validity
            method="intersection"  # Use intersection with α/2 splitting for tighter bounds
        )
        self.stopper = SequentialStopper(
            precision_target=config.stopping.precision_target,
            certification_threshold=config.stopping.certification_threshold,
            min_samples=config.stopping.min_samples,
            max_samples=config.stopping.max_samples,
        )

        # RNG for sampling
        self.rng = np.random.default_rng(config.seed)

        # Initialize stratified sampler if using stratified mode
        self.prompt_sampler = None
        if config.prompts.type == "stratified_json":
            from eval_harness.prompts.stratified_json_prompts import (
                StratifiedSampler,
                NaiveSampler,
            )
            if config.prompts.sampling_mode == "stratified":
                self.prompt_sampler = StratifiedSampler(self.prompts, self.rng)
            else:  # naive
                self.prompt_sampler = NaiveSampler(self.prompts, self.rng)

        # Track consecutive API failures (empty generations)
        self.consecutive_empty_responses = 0
        self.max_consecutive_empty_responses = config.stopping.max_consecutive_api_failures

        if self.verbose:
            print(f"Experiment ID: {self.experiment_id}")
            print(f"Results dir: {self.experiment_dir}")
            if self.prompt_sampler:
                mode = "Stratified" if isinstance(self.prompt_sampler, StratifiedSampler) else "Naive"
                print(f"Sampling mode: {mode}")

    def _create_sampler(self) -> Sampler:
        """Create sampler from config."""
        sampler_cfg = self.config.sampler

        if sampler_cfg.type == "toy":
            if sampler_cfg.failure_probability is None:
                raise ValueError("Toy sampler requires failure_probability")
            return ToySampler(
                model_id=sampler_cfg.model_id,
                failure_probability=sampler_cfg.failure_probability,
            )
        elif sampler_cfg.type == "gemini":
            from eval_harness.sampling.gemini_sampler import GeminiSampler
            return GeminiSampler(
                model_id=sampler_cfg.model_id,
                api_key=sampler_cfg.api_key,
            )
        elif sampler_cfg.type == "groq":
            from eval_harness.sampling.groq_sampler import GroqSampler
            return GroqSampler(
                model_id=sampler_cfg.model_id,
                api_key=sampler_cfg.api_key,
            )
        elif sampler_cfg.type == "openai":
            from eval_harness.sampling.openai_sampler import OpenAISampler
            return OpenAISampler(
                model_id=sampler_cfg.model_id,
                api_key=sampler_cfg.api_key,
                base_url=sampler_cfg.base_url,
            )
        else:
            raise NotImplementedError(
                f"Sampler type {sampler_cfg.type} not yet implemented"
            )

    def _create_validator(self) -> Validator:
        """Create validator from config."""
        val_cfg = self.config.validator

        if val_cfg.type == "json_schema":
            # For toy model, use ToyValidator
            if self.config.sampler.type == "toy":
                return ToyValidator()

            # For real LLMs with JSON schema prompts, we use a dynamic validator
            # that gets the schema from each prompt's metadata
            if self.config.prompts.type in ("json_schema", "stratified_json"):
                # Return a validator that will check against per-prompt schemas
                # We'll pass None here and validate dynamically in the run loop
                return JSONSchemaValidator(
                    schema=None,  # Will be set per-prompt
                    require_exact_keys=val_cfg.require_exact_keys,
                )

            if val_cfg.json_schema is None:
                raise ValueError("JSON schema validator requires schema")
            return JSONSchemaValidator(
                schema=val_cfg.json_schema,
                require_exact_keys=val_cfg.require_exact_keys,
            )
        elif val_cfg.type == "sql":
            from eval_harness.validators.sql_validator import SQLValidator
            return SQLValidator()
        else:
            raise NotImplementedError(f"Validator type {val_cfg.type} not yet implemented")

    def _create_prompts(self) -> PromptDataset:
        """Create prompt dataset from config."""
        prompt_cfg = self.config.prompts

        if prompt_cfg.type == "json_schema":
            return JSONSchemaPromptDataset(
                n_prompts=prompt_cfg.n_prompts,
                complexity=prompt_cfg.complexity,
                seed=prompt_cfg.seed,
            )
        elif prompt_cfg.type == "sql":
            from eval_harness.prompts.sql_prompts import SQLPromptDataset
            return SQLPromptDataset(
                n_prompts=prompt_cfg.n_prompts,
                seed=prompt_cfg.seed,
            )
        elif prompt_cfg.type == "stratified_json":
            from eval_harness.prompts.stratified_json_prompts import StratifiedJSONSchemaDataset
            prompts_per_stratum = prompt_cfg.prompts_per_stratum or 25
            return StratifiedJSONSchemaDataset(
                prompts_per_stratum=prompts_per_stratum,
                seed=prompt_cfg.seed,
            )
        else:
            raise NotImplementedError(f"Prompt type {prompt_cfg.type} not yet implemented")

    def run(self):
        """Run the sequential evaluation experiment."""
        # Create experiment record
        config_json = self.config.model_dump_json()
        self.store.create_experiment(self.experiment_id, config_json)

        # Load existing state if resuming
        state = self.store.load_experiment_state(self.experiment_id)

        if state and state.stopped:
            # STRICT CHECK - never resume completed experiments except API failures
            if state.stop_reason and "api_failure" not in state.stop_reason:
                # Completed successfully - HARD STOP
                if self.verbose:
                    print(f"FATAL: Experiment already completed with reason: {state.stop_reason}")
                    print(f"Cannot resume. Delete experiment to start fresh.")
                raise RuntimeError(
                    f"Experiment {self.experiment_id} already completed. "
                    f"Delete the experiment directory to start fresh."
                )

            # Only API failures can be resumed
            if state.stop_reason and "api_failure" in state.stop_reason:
                if self.verbose:
                    print(f"Previous run aborted due to API failures: {state.stop_reason}")
                    print(f"Resuming from {state.n_samples} samples...")
                # Reset stopped flag so we can finalize again
                cursor = self.store.conn.cursor()
                cursor.execute(
                    "UPDATE experiments SET stopped = 0, stop_reason = NULL WHERE experiment_id = ?",
                    (self.experiment_id,),
                )
                self.store.conn.commit()

        # Resume from checkpoint if applicable
        if state and state.n_samples > 0:
            # Only print if we haven't already printed above
            if self.verbose and not (state.stopped and state.stop_reason and "api_failure" in state.stop_reason):
                print(f"Resuming from {state.n_samples} samples...")
            # Restore CS state
            for _ in range(state.n_failures):
                self.cs.update(True)
            for _ in range(state.n_samples - state.n_failures):
                self.cs.update(False)

        # Initialize progress bar
        pbar = tqdm(
            total=self.config.stopping.max_samples,
            initial=self.cs.trials,
            disable=not self.verbose,
            desc="Sampling",
        )

        # Main sampling loop
        while True:
            # Check stopping criteria
            decision = self.stopper.check(self.cs)
            if decision.should_stop:
                if self.verbose:
                    print(f"\nStopping: {decision.reason}")
                break

            # Sample next prompt (stratified or naive)
            if self.prompt_sampler:
                stratum, prompt = self.prompt_sampler.sample_next()
            else:
                prompt = self.prompts.sample_uniform(self.rng)
                stratum = None

            # Save prompt for reference (idempotent)
            self.store.save_prompt(prompt, self.experiment_id)

            # Generate sample
            seed = self._generate_seed()
            generations = self.sampler.generate(
                prompt.text, self.config.decoding, n_samples=1, seed=seed
            )

            # Create sample record (include stratum metadata if stratified)
            sample_metadata = {}
            if stratum:
                sample_metadata["stratum"] = stratum

            sample = Sample(
                id=self._generate_sample_id(),
                prompt_id=prompt.id,
                model_id=self.sampler.model_id,
                decoding_config=self.config.decoding,
                seed=seed,
                generation=generations[0],
                timestamp=datetime.now(),
                metadata=sample_metadata,
            )

            # Check for empty generation (API failure) BEFORE processing
            #
            # ASSUMPTION: Missing data is Missing Completely At Random (MCAR)
            # We assume API failures (empty responses) are independent of prompt difficulty.
            # If this is violated (e.g., harder prompts timeout more often), p̂ is biased downward.
            # MITIGATION: We track API failures with metadata to enable post-hoc validation.
            # TODO: Add stratification or imputation if MCAR is empirically violated.
            if not sample.generation or sample.generation.strip() == "":
                self.consecutive_empty_responses += 1

                # Save to database with special metadata for debugging
                # Track prompt complexity to enable MCAR validation
                prompt_complexity = prompt.metadata.get("complexity", "unknown")
                sample_metadata = {
                    "api_failure": True,
                    "reason": "empty_response",
                    "prompt_complexity": prompt_complexity,
                }
                sample_with_metadata = Sample(
                    id=sample.id,
                    prompt_id=sample.prompt_id,
                    model_id=sample.model_id,
                    decoding_config=sample.decoding_config,
                    seed=sample.seed,
                    generation=sample.generation,
                    timestamp=sample.timestamp,
                    metadata=sample_metadata,
                )
                self.store.save_sample(sample_with_metadata, self.experiment_id)

                if self.consecutive_empty_responses >= self.max_consecutive_empty_responses:
                    pbar.close()
                    error_msg = f"api_failure_abort_after_{self.consecutive_empty_responses}_consecutive_empty_responses"
                    if self.verbose:
                        print(f"\n❌ ABORTING: {self.consecutive_empty_responses} consecutive empty API responses")
                        print("This usually indicates rate limiting or API errors.")
                        print("Check your API key and rate limits.")

                    # Finalize with error
                    lower, upper = self.cs.get_bounds()
                    self.store.finalize_experiment(
                        self.experiment_id,
                        error_msg,
                        lower,
                        upper,
                        self.cs.point_estimate,
                        self.cs.trials,
                        self.cs.failures,
                    )
                    return

                # Skip this sample - don't count it in statistics
                # The progress bar won't increment, user will retry
                continue

            # Reset counter on successful generation
            self.consecutive_empty_responses = 0

            # Validate (extract schema from prompt metadata if using JSON schema prompts)
            schema = None
            if self.config.prompts.type == "json_schema":
                schema = prompt.metadata.get("schema")
            result = self.validator.validate(sample.generation, sample.id, schema=schema)

            # Update statistics (only for non-empty responses)
            lower, upper = self.cs.update(result.failed)

            # Persist
            self.store.save_sample(sample, self.experiment_id)
            self.store.save_validation(result, self.experiment_id)

            # Save statistics snapshot every 10 samples
            if self.cs.trials % 10 == 0:
                self.store.save_statistics_snapshot(
                    self.experiment_id,
                    self.cs.trials,
                    self.cs.failures,
                    lower,
                    upper,
                    self.cs.point_estimate,
                )

            # Update progress bar
            pbar.update(1)
            pbar.set_postfix(
                {
                    "p̂": f"{self.cs.point_estimate:.4f}",
                    "CI": f"[{lower:.4f}, {upper:.4f}]",
                    "width": f"{self.cs.width:.4f}",
                }
            )

        pbar.close()

        # Validate database counts match CS state before finalizing
        self._validate_final_counts()

        # Finalize experiment
        lower, upper = self.cs.get_bounds()
        self.store.finalize_experiment(
            self.experiment_id,
            decision.reason,
            lower,
            upper,
            self.cs.point_estimate,
            self.cs.trials,
            self.cs.failures,
        )

        # Save final statistics snapshot
        self.store.save_statistics_snapshot(
            self.experiment_id,
            self.cs.trials,
            self.cs.failures,
            lower,
            upper,
            self.cs.point_estimate,
        )

        if self.verbose:
            print(f"\nFinal results:")
            print(f"  Samples: {self.cs.trials}")
            print(f"  Failures: {self.cs.failures}")
            print(f"  p̂ = {self.cs.point_estimate:.4f}")
            print(f"  95% CS: [{lower:.4f}, {upper:.4f}]")
            print(f"  Width: {self.cs.width:.4f}")

    def _generate_seed(self) -> int:
        """Generate random seed for sampling."""
        return self.rng.integers(0, 2**31)

    def _generate_sample_id(self) -> str:
        """Generate unique sample ID."""
        return str(uuid.uuid4())

    def _validate_final_counts(self):
        """Validate that database counts match CS state.

        Raises:
            RuntimeError: If counts are inconsistent
        """
        cursor = self.store.conn.cursor()

        # Count samples in DB (excluding API failures with no validation)
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM samples s
            JOIN validation_results vr ON s.sample_id = vr.sample_id
            WHERE s.experiment_id = ?
        """,
            (self.experiment_id,),
        )
        db_samples = cursor.fetchone()[0]

        # Count failures in DB
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM validation_results
            WHERE experiment_id = ? AND passed = 0
        """,
            (self.experiment_id,),
        )
        db_failures = cursor.fetchone()[0]

        # Check consistency
        if db_samples != self.cs.trials:
            raise RuntimeError(
                f"DB count mismatch: {db_samples} samples in DB vs {self.cs.trials} in CS. "
                f"This indicates a critical bug in the harness - database integrity violated."
            )
        if db_failures != self.cs.failures:
            raise RuntimeError(
                f"Failure count mismatch: {db_failures} in DB vs {self.cs.failures} in CS. "
                f"This indicates a critical bug in the harness - database integrity violated."
            )

        if self.verbose:
            print(f"✓ Database validation passed: {db_samples} samples, {db_failures} failures")

    def cleanup(self):
        """Clean up resources."""
        self.store.close()
