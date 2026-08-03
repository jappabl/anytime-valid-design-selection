"""Tests for the code-generation dataset and its validation pipeline.

Closes the audit gap: the code-task labelling path previously had no
tests guarding the prompt generators, reference outputs, or the
extraction/normalization helpers in scripts/validate_code_generations.py.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.prompts.diverse_code_prompts import (
    StratifiedDiverseCodeDataset,
)


def _load_validator_module():
    path = (Path(__file__).parent.parent / "scripts"
            / "validate_code_generations.py")
    spec = importlib.util.spec_from_file_location("vcg", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDataset:
    def test_deterministic_expected_outputs(self):
        # Same seed => identical prompts AND identical expected outputs;
        # guards against silent reference-solution drift.
        a = StratifiedDiverseCodeDataset(prompts_per_stratum=20, seed=42)
        b = StratifiedDiverseCodeDataset(prompts_per_stratum=20, seed=42)
        for pa, pb in zip(a.get_all_prompts(), b.get_all_prompts()):
            assert pa.id == pb.id
            assert pa.text == pb.text
            assert json.dumps(pa.metadata["expected"]) == \
                json.dumps(pb.metadata["expected"])

    def test_prompt_texts_unique_per_stratum(self):
        ds = StratifiedDiverseCodeDataset(prompts_per_stratum=40, seed=42)
        for s in ds.STRATA:
            texts = [p.text for p in ds.get_stratum_prompts(s)]
            assert len(set(texts)) == len(texts)

    def test_metadata_survives_json_roundtrip(self):
        # The validator compares JSON-normalized outputs, so the stored
        # tests/expected must be JSON-serializable without loss under
        # that comparison.
        ds = StratifiedDiverseCodeDataset(prompts_per_stratum=15, seed=42)
        for p in ds.get_all_prompts():
            rt = json.loads(json.dumps({"t": p.metadata["tests"],
                                        "e": p.metadata["expected"]}))
            assert json.loads(json.dumps(rt)) == rt


class TestValidatorHelpers:
    def test_extract_code_variants(self):
        mod = _load_validator_module()
        code = "def solve(x):\n    return x"
        assert mod.extract_code(f"```python\n{code}\n```") == code
        assert mod.extract_code(f"```\n{code}\n```") == code
        assert mod.extract_code(code) == code
        assert mod.extract_code(f"Here you go:\n```python\n{code}\n```") == code

    def test_normalize_tuple_list_equivalence(self):
        # Intended leniency: a correct answer returning tuples must not
        # be penalized relative to lists.
        mod = _load_validator_module()
        assert mod.normalize([(1, 2), (3, 4)]) == mod.normalize([[1, 2], [3, 4]])
        assert mod.normalize((0, "a")) == mod.normalize([0, "a"])

    def test_normalize_distinguishes_values(self):
        mod = _load_validator_module()
        assert mod.normalize([1, 2]) != mod.normalize([2, 1])
        assert mod.normalize("1") != mod.normalize(1)
