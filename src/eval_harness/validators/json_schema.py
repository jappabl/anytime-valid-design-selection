"""JSON schema validator."""

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import jsonschema

from eval_harness.core.types import ValidationResult


def _decimal_multiple_of(validator, db, instance, schema):
    """Decimal-aware multipleOf check.

    jsonschema's default check uses binary floating point, which wrongly
    rejects values like 199.95 for multipleOf 0.05 (a decimal multiple
    that is not a binary one). Exact decimal arithmetic on the JSON
    literals avoids the artifact.
    """
    if not isinstance(instance, (int, float)) or isinstance(instance, bool):
        return
    try:
        remainder = Decimal(str(instance)) % Decimal(str(db))
    except InvalidOperation:
        remainder = None
    if remainder is None or remainder != 0:
        yield jsonschema.ValidationError(
            f"{instance} is not a multiple of {db}"
        )


_Draft7Decimal = jsonschema.validators.extend(
    jsonschema.Draft7Validator, {"multipleOf": _decimal_multiple_of}
)


class JSONSchemaValidator:
    """Validates JSON outputs against a schema.

    Checks:
    1. Valid JSON parse
    2. Schema conformance (if schema provided)
    3. No extra keys (if require_exact_keys=True)
    """

    def __init__(
        self, schema: Optional[dict] = None, require_exact_keys: bool = False
    ):
        """Initialize JSON validator.

        Args:
            schema: JSON schema dict (if None, only checks valid JSON)
            require_exact_keys: If True, fail on extra keys not in schema
        """
        self.schema = schema
        self.require_exact_keys = require_exact_keys

        # Validate schema itself if provided
        if schema is not None:
            try:
                jsonschema.Draft7Validator.check_schema(schema)
            except jsonschema.SchemaError as e:
                raise ValueError(f"Invalid JSON schema: {e}")

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Strip markdown code fences from text.

        Many LLMs wrap JSON in ```json ... ``` fences. This strips them.

        Args:
            text: Text that may contain markdown fences

        Returns:
            Text with fences removed
        """
        text = text.strip()

        # Check if text starts with ``` (code fence)
        if text.startswith('```'):
            # Remove opening fence (```json or ```) and everything up to first newline
            lines = text.split('\n', 1)
            if len(lines) > 1:
                text = lines[1]  # Skip first line with ```
            else:
                text = ''  # Only had the opening fence

        # Check if text ends with ```
        if text.rstrip().endswith('```'):
            # Remove closing fence
            text = text.rstrip()[:-3].rstrip()

        return text.strip()

    def validate(self, generation: str, sample_id: str, schema: Optional[dict] = None) -> ValidationResult:
        """Validate JSON generation.

        Args:
            generation: Generated text (should be JSON)
            sample_id: Sample identifier
            schema: Optional schema to validate against (overrides self.schema if provided)

        Returns:
            ValidationResult with pass/fail and detailed failure mode
        """
        # Use provided schema or fall back to instance schema
        active_schema = schema if schema is not None else self.schema

        # Strip markdown code fences if present (many LLMs wrap JSON in ```json ... ```)
        cleaned_generation = self._strip_markdown_fences(generation)

        # Step 1: Try to parse as JSON
        try:
            parsed = json.loads(cleaned_generation)
        except json.JSONDecodeError as e:
            return ValidationResult(
                sample_id=sample_id,
                passed=False,
                failure_mode="json_parse_error",
                details={
                    "error": str(e),
                    "error_position": e.pos,
                    "generation_preview": generation[:200],
                },
                timestamp=datetime.now(),
            )

        # Step 2: Validate against schema if provided
        if active_schema is not None:
            try:
                _Draft7Decimal(active_schema).validate(parsed)
            except jsonschema.ValidationError as e:
                return ValidationResult(
                    sample_id=sample_id,
                    passed=False,
                    failure_mode="schema_validation_error",
                    details={
                        "error": e.message,
                        "path": list(e.path),
                        "validator": e.validator,
                        "schema_path": list(e.schema_path),
                    },
                    timestamp=datetime.now(),
                )

        # Step 3: Check for extra keys if required
        if self.require_exact_keys and active_schema is not None:
            extra_keys = self._find_extra_keys(parsed, active_schema)
            if extra_keys:
                return ValidationResult(
                    sample_id=sample_id,
                    passed=False,
                    failure_mode="extra_keys",
                    details={"extra_keys": extra_keys},
                    timestamp=datetime.now(),
                )

        # All checks passed
        return ValidationResult(
            sample_id=sample_id,
            passed=True,
            details={"parsed_object": parsed},
            timestamp=datetime.now(),
        )

    def _find_extra_keys(self, obj: dict, schema: dict) -> list[str]:
        """Find keys in obj that are not in schema properties.

        Args:
            obj: Parsed JSON object
            schema: JSON schema

        Returns:
            List of extra key paths (e.g., ["root.field.extra"])
        """
        if not isinstance(obj, dict) or "properties" not in schema:
            return []

        allowed_keys = set(schema.get("properties", {}).keys())
        actual_keys = set(obj.keys())
        extra = actual_keys - allowed_keys

        return sorted(extra)

    def __repr__(self) -> str:
        has_schema = self.schema is not None
        return (
            f"JSONSchemaValidator(has_schema={has_schema}, "
            f"require_exact_keys={self.require_exact_keys})"
        )
