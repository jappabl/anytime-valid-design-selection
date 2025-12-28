"""SQLite-based result storage with resumability.

Stores:
- Experiment metadata
- All samples (prompts + generations)
- Validation results
- Sequential statistics snapshots

Supports:
- Deterministic experiment IDs
- Resuming interrupted experiments
- Querying results for analysis
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from eval_harness.core.types import (
    DecodingConfig,
    ExperimentState,
    Prompt,
    Sample,
    ValidationResult,
)


class ResultStore:
    """SQLite-based storage for experiment results."""

    def __init__(self, db_path: Path):
        """Initialize result store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        """Create database schema."""
        cursor = self.conn.cursor()

        # Experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                stopped BOOLEAN DEFAULT 0,
                stop_reason TEXT,
                final_lower REAL,
                final_upper REAL,
                final_point_estimate REAL,
                final_n_samples INTEGER,
                final_n_failures INTEGER
            )
        """)

        # Samples table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                sample_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                decoding_config_json TEXT NOT NULL,
                seed INTEGER NOT NULL,
                generation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        # Validation results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_results (
                validation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_id TEXT NOT NULL,
                experiment_id TEXT NOT NULL,
                passed BOOLEAN NOT NULL,
                failure_mode TEXT,
                details_json TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        # Statistics snapshots (for tracking CS evolution)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                n_samples INTEGER NOT NULL,
                n_failures INTEGER NOT NULL,
                lower_bound REAL NOT NULL,
                upper_bound REAL NOT NULL,
                point_estimate REAL NOT NULL,
                ci_width REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        # Prompts table (for reference)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                prompt_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        """)

        # Create indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_samples_exp ON samples(experiment_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_validation_exp ON validation_results(experiment_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_validation_sample ON validation_results(sample_id)"
        )

        self.conn.commit()

    def create_experiment(self, experiment_id: str, config_json: str):
        """Create new experiment record.

        Args:
            experiment_id: Unique experiment ID
            config_json: JSON-serialized config
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO experiments (experiment_id, config_json, created_at)
            VALUES (?, ?, ?)
        """,
            (experiment_id, config_json, datetime.now().isoformat()),
        )
        self.conn.commit()

    def save_sample(self, sample: Sample, experiment_id: str):
        """Save a sample.

        Args:
            sample: Sample to save
            experiment_id: Associated experiment ID
        """
        with self.conn:  # Atomic transaction
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO samples
                (sample_id, experiment_id, prompt_id, model_id, decoding_config_json,
                 seed, generation, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    sample.id,
                    experiment_id,
                    sample.prompt_id,
                    sample.model_id,
                    json.dumps(sample.decoding_config.to_dict()),
                    sample.seed,
                    sample.generation,
                    sample.timestamp.isoformat(),
                    json.dumps(sample.metadata),
                ),
            )

    def save_validation(self, result: ValidationResult, experiment_id: str):
        """Save validation result.

        Args:
            result: ValidationResult to save
            experiment_id: Associated experiment ID
        """
        with self.conn:  # Atomic transaction
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO validation_results
                (sample_id, experiment_id, passed, failure_mode, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    result.sample_id,
                    experiment_id,
                    result.passed,
                    result.failure_mode,
                    json.dumps(result.details),
                    result.timestamp.isoformat(),
                ),
            )

    def save_statistics_snapshot(
        self,
        experiment_id: str,
        n_samples: int,
        n_failures: int,
        lower: float,
        upper: float,
        point_estimate: float,
    ):
        """Save a statistics snapshot.

        Args:
            experiment_id: Experiment ID
            n_samples: Total samples so far
            n_failures: Total failures so far
            lower: Lower confidence bound
            upper: Upper confidence bound
            point_estimate: Point estimate of failure rate
        """
        with self.conn:  # Atomic transaction
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO statistics_snapshots
                (experiment_id, n_samples, n_failures, lower_bound, upper_bound,
                 point_estimate, ci_width, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    experiment_id,
                    n_samples,
                    n_failures,
                    lower,
                    upper,
                    point_estimate,
                    upper - lower,
                    datetime.now().isoformat(),
                ),
            )

    def finalize_experiment(
        self,
        experiment_id: str,
        stop_reason: str,
        final_lower: float,
        final_upper: float,
        final_point_estimate: float,
        n_samples: int,
        n_failures: int,
    ):
        """Mark experiment as completed.

        Args:
            experiment_id: Experiment ID
            stop_reason: Why the experiment stopped
            final_lower: Final lower bound
            final_upper: Final upper bound
            final_point_estimate: Final point estimate
            n_samples: Total samples
            n_failures: Total failures

        Raises:
            RuntimeError: If experiment is already finalized
        """
        with self.conn:  # Atomic transaction
            cursor = self.conn.cursor()

            # FIRST: Check if already finalized (prevent double-writes)
            cursor.execute(
                "SELECT stopped, stop_reason FROM experiments WHERE experiment_id = ?",
                (experiment_id,),
            )
            result = cursor.fetchone()
            if result and result[0] == 1:
                # Already finalized - only allow if it was an API failure
                if result[1] and "api_failure" not in result[1]:
                    raise RuntimeError(
                        f"Experiment {experiment_id} already finalized with reason: {result[1]}"
                    )

            # THEN: Finalize atomically
            cursor.execute(
                """
                UPDATE experiments
                SET stopped = 1, stop_reason = ?,
                    final_lower = ?, final_upper = ?, final_point_estimate = ?,
                    final_n_samples = ?, final_n_failures = ?
                WHERE experiment_id = ?
            """,
                (
                    stop_reason,
                    final_lower,
                    final_upper,
                    final_point_estimate,
                    n_samples,
                    n_failures,
                    experiment_id,
                ),
            )

    def load_experiment_state(self, experiment_id: str) -> Optional[ExperimentState]:
        """Load experiment state for resumption.

        Args:
            experiment_id: Experiment ID

        Returns:
            ExperimentState if experiment exists, None otherwise
        """
        cursor = self.conn.cursor()

        # Check if experiment exists
        cursor.execute(
            "SELECT stopped, stop_reason FROM experiments WHERE experiment_id = ?",
            (experiment_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        stopped, stop_reason = row

        # Count samples and failures
        cursor.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN vr.passed = 0 THEN 1 ELSE 0 END)
            FROM samples s
            JOIN validation_results vr ON s.sample_id = vr.sample_id
            WHERE s.experiment_id = ?
        """,
            (experiment_id,),
        )
        n_samples, n_failures = cursor.fetchone()
        n_samples = n_samples or 0
        n_failures = n_failures or 0

        # Get completed prompts
        cursor.execute(
            "SELECT DISTINCT prompt_id FROM samples WHERE experiment_id = ?",
            (experiment_id,),
        )
        completed_prompts = {row[0] for row in cursor.fetchall()}

        # Get latest bounds if available
        cursor.execute(
            """
            SELECT lower_bound, upper_bound
            FROM statistics_snapshots
            WHERE experiment_id = ?
            ORDER BY snapshot_id DESC
            LIMIT 1
        """,
            (experiment_id,),
        )
        bounds_row = cursor.fetchone()
        latest_bounds = tuple(bounds_row) if bounds_row else None

        return ExperimentState(
            experiment_id=experiment_id,
            n_samples=n_samples,
            n_failures=n_failures,
            stopped=bool(stopped),
            stop_reason=stop_reason,
            completed_prompts=completed_prompts,
            latest_bounds=latest_bounds,
        )

    def save_prompt(self, prompt: Prompt, experiment_id: str):
        """Save prompt for reference.

        Args:
            prompt: Prompt to save
            experiment_id: Associated experiment ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO prompts (prompt_id, experiment_id, prompt_text, metadata_json)
            VALUES (?, ?, ?, ?)
        """,
            (prompt.id, experiment_id, prompt.text, json.dumps(prompt.metadata)),
        )
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __del__(self):
        """Ensure connection is closed."""
        if hasattr(self, "conn"):
            self.conn.close()
