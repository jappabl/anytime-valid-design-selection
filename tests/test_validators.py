"""Tests for validators."""

import json

import pytest

from eval_harness.validators.json_schema import JSONSchemaValidator
from eval_harness.validators.toy_validator import ToyValidator


class TestToyValidator:
    """Tests for ToyValidator."""

    def test_pass_validation(self):
        """Test that 'PASS' is validated correctly."""
        validator = ToyValidator()
        result = validator.validate("PASS", "sample_1")

        assert result.passed
        assert not result.failed
        assert result.failure_mode is None

    def test_fail_validation(self):
        """Test that 'FAIL' is validated correctly."""
        validator = ToyValidator()
        result = validator.validate("FAIL", "sample_2")

        assert not result.passed
        assert result.failed
        assert result.failure_mode == "synthetic_fail"

    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        validator = ToyValidator()

        assert validator.validate("pass", "s1").passed
        assert validator.validate("  PASS  ", "s2").passed
        assert not validator.validate("fail", "s3").passed
        assert not validator.validate("  FAIL  ", "s4").passed

    def test_invalid_output(self):
        """Test handling of invalid toy outputs."""
        validator = ToyValidator()
        result = validator.validate("INVALID", "sample_5")

        assert not result.passed
        assert result.failure_mode == "invalid_toy_output"


class TestJSONSchemaValidator:
    """Tests for JSONSchemaValidator."""

    def test_valid_json_no_schema(self):
        """Test that valid JSON passes when no schema is provided."""
        validator = JSONSchemaValidator()
        result = validator.validate('{"key": "value"}', "sample_1")

        assert result.passed

    def test_invalid_json(self):
        """Test that invalid JSON fails."""
        validator = JSONSchemaValidator()
        result = validator.validate('{"key": invalid}', "sample_2")

        assert not result.passed
        assert result.failure_mode == "json_parse_error"

    def test_valid_json_with_schema(self):
        """Test validation against a schema."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }

        validator = JSONSchemaValidator(schema=schema)

        valid_json = '{"name": "Alice", "age": 30}'
        result = validator.validate(valid_json, "sample_3")

        assert result.passed

    def test_schema_validation_missing_required(self):
        """Test that missing required fields fail."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }

        validator = JSONSchemaValidator(schema=schema)

        invalid_json = '{"name": "Alice"}'
        result = validator.validate(invalid_json, "sample_4")

        assert not result.passed
        assert result.failure_mode == "schema_validation_error"

    def test_schema_validation_wrong_type(self):
        """Test that wrong types fail."""
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
            "required": ["age"],
        }

        validator = JSONSchemaValidator(schema=schema)

        invalid_json = '{"age": "thirty"}'
        result = validator.validate(invalid_json, "sample_5")

        assert not result.passed
        assert result.failure_mode == "schema_validation_error"

    def test_extra_keys_allowed(self):
        """Test that extra keys pass when require_exact_keys=False."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        validator = JSONSchemaValidator(schema=schema, require_exact_keys=False)

        json_with_extra = '{"name": "Alice", "extra_field": "value"}'
        result = validator.validate(json_with_extra, "sample_6")

        assert result.passed

    def test_extra_keys_rejected(self):
        """Test that extra keys fail when require_exact_keys=True."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        validator = JSONSchemaValidator(schema=schema, require_exact_keys=True)

        json_with_extra = '{"name": "Alice", "extra_field": "value"}'
        result = validator.validate(json_with_extra, "sample_7")

        assert not result.passed
        assert result.failure_mode == "extra_keys"
        assert "extra_field" in result.details["extra_keys"]

    def test_invalid_schema_initialization(self):
        """Test that invalid schemas raise errors on initialization."""
        invalid_schema = {"type": "not_a_valid_type"}

        with pytest.raises(ValueError, match="Invalid JSON schema"):
            JSONSchemaValidator(schema=invalid_schema)
