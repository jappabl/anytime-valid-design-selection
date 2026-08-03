"""Regression tests for decimal-aware multipleOf validation.

jsonschema's stock multipleOf check uses binary floating point and wrongly
rejects decimal multiples such as 199.95 for multipleOf 0.05. The
validator overrides it with exact decimal arithmetic; a regression to the
stock behavior corrupted 59 outcome labels in the 2026-08-02 pools.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.validators.json_schema import JSONSchemaValidator

SCHEMA = {
    "type": "object",
    "properties": {"amount": {"type": "number", "multipleOf": 0.05}},
    "required": ["amount"],
    "additionalProperties": False,
}


@pytest.fixture
def validator():
    return JSONSchemaValidator()


class TestDecimalMultipleOf:
    @pytest.mark.parametrize("value", [199.95, 299.95, 12.35, 1500.05,
                                       12345.55, 0.15, 100.1, 0.05])
    def test_decimal_multiples_pass(self, validator, value):
        # All are exact decimal multiples of 0.05; the stock float check
        # rejects several of them.
        result = validator.validate(
            f'{{"amount": {value}}}', "t", schema=SCHEMA)
        assert result.passed, f"{value} wrongly rejected"

    @pytest.mark.parametrize("value", [199.951, 0.017, 12.34999])
    def test_genuine_violations_fail(self, validator, value):
        result = validator.validate(
            f'{{"amount": {value}}}', "t", schema=SCHEMA)
        assert not result.passed
        assert "multiple of" in (result.details or {}).get("error", "")

    def test_integers_and_integer_multiple_of(self, validator):
        schema = {
            "type": "object",
            "properties": {"n": {"type": "integer", "multipleOf": 3}},
            "required": ["n"],
        }
        assert validator.validate('{"n": 9}', "t", schema=schema).passed
        assert not validator.validate('{"n": 10}', "t", schema=schema).passed

    def test_boolean_not_treated_as_number(self, validator):
        schema = {
            "type": "object",
            "properties": {"flag": {"type": "boolean"}},
            "required": ["flag"],
        }
        assert validator.validate('{"flag": true}', "t", schema=schema).passed
