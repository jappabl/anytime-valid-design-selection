"""Code execution validator for Python functions."""

import re
import sys
from io import StringIO
from datetime import datetime
from typing import Optional

from eval_harness.core.types import ValidationResult


class CodeValidator:
    """Validates generated Python code by running test cases."""

    def __init__(self, timeout_seconds: int = 5):
        """Initialize code validator.

        Args:
            timeout_seconds: Maximum execution time (not strictly enforced)
        """
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _extract_code(generation: str) -> Optional[str]:
        """Extract Python code from generation (handles markdown fences)."""
        generation = generation.strip()

        # Try to extract from ```python ... ``` blocks
        pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(pattern, generation, re.DOTALL)
        if matches:
            return matches[0].strip()

        # Try to extract from ``` ... ``` blocks
        pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(pattern, generation, re.DOTALL)
        if matches:
            return matches[0].strip()

        # If no fences, try to find function definition
        if 'def ' in generation:
            # Take everything from first def to end, cleaning up explanatory text
            lines = generation.split('\n')
            code_lines = []
            in_function = False
            for line in lines:
                if line.strip().startswith('def '):
                    in_function = True
                if in_function:
                    code_lines.append(line)
            if code_lines:
                return '\n'.join(code_lines).strip()

        # Return as-is if it looks like code
        if 'def ' in generation or 'return' in generation:
            return generation.strip()

        return None

    def validate(
        self,
        generation: str,
        sample_id: str,
        tests: str,
        **kwargs
    ) -> ValidationResult:
        """Validate generated code by running test cases.

        Args:
            generation: Generated code
            sample_id: Sample identifier
            tests: Test code to run (pytest-style assertions)

        Returns:
            ValidationResult with pass/fail
        """
        # Extract code
        code = self._extract_code(generation)
        if code is None:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="no_code_found",
                details={"generation_preview": generation[:200]},
                timestamp=datetime.now(),
            )

        # Try to execute code + tests
        try:
            # Create execution environment
            exec_globals = {}

            # Execute the generated code
            exec(code, exec_globals)

            # Execute the tests in the same environment
            exec(tests, exec_globals)

            # If we get here, all assertions passed
            return ValidationResult(
                sample_id=sample_id,
                passed=True,
                details={"code": code},
                timestamp=datetime.now(),
            )

        except AssertionError as e:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="assertion_failed",
                details={
                    "error": str(e),
                    "code": code,
                },
                timestamp=datetime.now(),
            )

        except SyntaxError as e:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="syntax_error",
                details={
                    "error": str(e),
                    "lineno": e.lineno,
                    "code": code,
                },
                timestamp=datetime.now(),
            )

        except NameError as e:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="name_error",
                details={
                    "error": str(e),
                    "code": code,
                },
                timestamp=datetime.now(),
            )

        except Exception as e:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="runtime_error",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "code": code,
                },
                timestamp=datetime.now(),
            )

    def __repr__(self) -> str:
        return f"CodeValidator(timeout={self.timeout_seconds}s)"
