"""Base sampler protocol."""

from typing import Protocol

from eval_harness.core.types import DecodingConfig


class Sampler(Protocol):
    """Protocol for LLM samplers.

    All samplers must implement this interface to be used in the evaluation harness.
    """

    model_id: str

    def generate(
        self, prompt: str, config: DecodingConfig, n_samples: int = 1, seed: int = 0
    ) -> list[str]:
        """Generate n independent samples from the model.

        Args:
            prompt: Input prompt text
            config: Decoding configuration (temperature, top_p, etc.)
            n_samples: Number of independent samples to generate
            seed: Random seed for reproducibility

        Returns:
            List of n generated strings
        """
        ...
