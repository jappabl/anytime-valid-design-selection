"""Tests for the diverse stratified JSON schema dataset."""

import sys
from pathlib import Path

import jsonschema
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eval_harness.prompts.diverse_json_prompts import (
    DiverseJSONSchemaDataset,
    StratifiedDiverseJSONDataset,
)


class TestDiverseJSONSchemaDataset:
    def test_generates_requested_count(self):
        ds = DiverseJSONSchemaDataset(n_prompts=50, complexity="medium", seed=7)
        assert len(ds) == 50

    def test_prompts_are_unique(self):
        for complexity in ["simple", "medium", "complex", "extreme"]:
            ds = DiverseJSONSchemaDataset(n_prompts=100, complexity=complexity, seed=7)
            texts = [p.text for p in ds.get_all_prompts()]
            assert len(set(texts)) == len(texts)

    def test_schemas_are_valid_draft7(self):
        for complexity in ["simple", "medium", "complex", "extreme"]:
            ds = DiverseJSONSchemaDataset(n_prompts=30, complexity=complexity, seed=7)
            for p in ds.get_all_prompts():
                jsonschema.Draft7Validator.check_schema(p.metadata["schema"])

    def test_deterministic_across_instances(self):
        a = DiverseJSONSchemaDataset(n_prompts=30, complexity="extreme", seed=7)
        b = DiverseJSONSchemaDataset(n_prompts=30, complexity="extreme", seed=7)
        assert [p.text for p in a.get_all_prompts()] == [p.text for p in b.get_all_prompts()]

    def test_different_seeds_differ(self):
        a = DiverseJSONSchemaDataset(n_prompts=30, complexity="simple", seed=7)
        b = DiverseJSONSchemaDataset(n_prompts=30, complexity="simple", seed=8)
        assert [p.text for p in a.get_all_prompts()] != [p.text for p in b.get_all_prompts()]


class TestStratifiedDiverseJSONDataset:
    def test_strata_and_counts(self):
        ds = StratifiedDiverseJSONDataset(prompts_per_stratum=25, seed=7)
        assert len(ds) == 100
        for stratum in ds.STRATA:
            prompts = ds.get_stratum_prompts(stratum)
            assert len(prompts) == 25
            assert all(ds.get_prompt_stratum(p) == stratum for p in prompts)

    def test_unique_across_strata(self):
        ds = StratifiedDiverseJSONDataset(prompts_per_stratum=25, seed=7)
        texts = [p.text for p in ds.get_all_prompts()]
        assert len(set(texts)) == len(texts)

    def test_sample_uniform_returns_valid_prompt(self):
        ds = StratifiedDiverseJSONDataset(prompts_per_stratum=10, seed=7)
        rng = np.random.default_rng(0)
        all_ids = {p.id for p in ds.get_all_prompts()}
        for _ in range(20):
            assert ds.sample_uniform(rng).id in all_ids
