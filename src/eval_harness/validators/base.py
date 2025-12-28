"""Base validator protocol."""

from typing import Any, Protocol

from eval_harness.core.types import ValidationResult


class Validator(Protocol):
    """Protocol for output validators.

    Validators check if a generation passes or fails according to objective criteria.
    """

    def validate(self, generation: str, sample_id: str, **kwargs: Any) -> ValidationResult:
        """Validate a generation.

        Args:
            generation: The generated text to validate
            sample_id: Unique identifier for this sample
            **kwargs: Additional validator-specific parameters

        Returns:
            ValidationResult with pass/fail and failure mode
        """
        ...
