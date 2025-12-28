"""Toy sampler for statistical validation.

Generates synthetic pass/fail outcomes from a known Bernoulli distribution.
This is critical for validating that our confidence sequences achieve nominal coverage.
"""

import numpy as np

from eval_harness.core.types import DecodingConfig


class ToySampler:
    """Synthetic sampler that returns fail/pass with known probability.

    Useful for:
    - Testing statistical properties of confidence sequences
    - Validating stopping rule behavior
    - Benchmarking sample efficiency

    The sampler returns "FAIL" with probability p_fail and "PASS" otherwise.
    """

    def __init__(self, model_id: str, failure_probability: float):
        """Initialize toy sampler.

        Args:
            model_id: Identifier for this toy model (e.g., "toy_p0.05")
            failure_probability: True failure probability (ground truth)
        """
        if not 0 <= failure_probability <= 1:
            raise ValueError(
                f"failure_probability must be in [0, 1], got {failure_probability}"
            )

        self.model_id = model_id
        self.failure_probability = failure_probability

    def generate(
        self, prompt: str, config: DecodingConfig, n_samples: int = 1, seed: int = 0
    ) -> list[str]:
        """Generate n synthetic outcomes.

        Args:
            prompt: Ignored (toy model doesn't use prompts)
            config: Ignored (toy model doesn't use decoding config)
            n_samples: Number of samples to generate
            seed: Random seed for reproducibility

        Returns:
            List of "FAIL" or "PASS" strings
        """
        rng = np.random.default_rng(seed)
        outcomes = rng.random(n_samples) < self.failure_probability
        return ["FAIL" if outcome else "PASS" for outcome in outcomes]

    def __repr__(self) -> str:
        return f"ToySampler(id={self.model_id}, p_fail={self.failure_probability})"
