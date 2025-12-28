"""Toy validator for testing with ToySampler."""

from datetime import datetime
from typing import Any

from eval_harness.core.types import ValidationResult


class ToyValidator:
    """Validator for toy sampler outputs.

    Simply checks if output is "FAIL" or "PASS".
    """

    def validate(self, generation: str, sample_id: str, **kwargs: Any) -> ValidationResult:
        """Validate toy model output.

        Args:
            generation: Should be "FAIL" or "PASS"
            sample_id: Sample identifier

        Returns:
            ValidationResult (passed=True if "PASS", False if "FAIL")
        """
        generation_clean = generation.strip().upper()

        if generation_clean == "FAIL":
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="synthetic_fail",
                details={"generation": generation},
                timestamp=datetime.now(),
            )
        elif generation_clean == "PASS":
            return ValidationResult(
                sample_id=sample_id,
                passed=True,
                details={"generation": generation},
                timestamp=datetime.now(),
            )
        else:
            # Unexpected output from toy model
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="invalid_toy_output",
                details={"generation": generation, "expected": "FAIL or PASS"},
                timestamp=datetime.now(),
            )
