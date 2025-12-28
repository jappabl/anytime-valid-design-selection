"""Stratified JSON schema prompt dataset for heterogeneity-aware evaluation.

Generates prompts across 4 difficulty strata:
- Simple: 2-4 fields, flat structure, primitive types
- Medium: 4-6 fields, shallow nesting, arrays
- Complex: 7-10 fields, deep nesting, constraints
- Extreme: >10 fields, multiple nesting levels, oneOf/anyOf

Key contribution: Allows balanced sampling across difficulty levels to avoid
early-stopping bias from "easy streaks."
"""

from collections import defaultdict
from typing import Dict, List, Literal, Tuple
import numpy as np

from eval_harness.core.types import Prompt
from eval_harness.prompts.json_schema_prompts import JSONSchemaPromptDataset


class StratifiedJSONSchemaDataset:
    """JSON schema prompts stratified by difficulty.

    Maintains separate pools for each difficulty level, enabling:
    1. Balanced sampling across strata
    2. Per-stratum failure rate analysis
    3. Detection of difficulty-dependent early stopping bias
    """

    def __init__(
        self,
        prompts_per_stratum: int = 25,
        seed: int = 42,
        strata: List[Literal["simple", "medium", "complex", "extreme"]] = None,
    ):
        """Initialize stratified dataset.

        Args:
            prompts_per_stratum: Number of prompts per difficulty level
            seed: Random seed for reproducibility
            strata: Difficulty levels to include (default: all 4)
        """
        self.prompts_per_stratum = prompts_per_stratum
        self.seed = seed
        self.strata = strata or ["simple", "medium", "complex", "extreme"]

        # Generate prompts for each stratum
        self.stratum_prompts: Dict[str, List[Prompt]] = {}
        self._generate_stratified_prompts()

        # Flatten for compatibility with uniform sampling
        self.all_prompts = []
        for stratum in self.strata:
            self.all_prompts.extend(self.stratum_prompts[stratum])

    def _generate_stratified_prompts(self):
        """Generate prompts for each difficulty stratum."""
        for stratum in self.strata:
            # Generate prompts for this stratum
            dataset = JSONSchemaPromptDataset(
                n_prompts=self.prompts_per_stratum,
                complexity=stratum,
                seed=self.seed + hash(stratum) % 1000,  # Unique seed per stratum
            )
            self.stratum_prompts[stratum] = dataset.prompts

    def get_stratum_prompts(self, stratum: str) -> List[Prompt]:
        """Get all prompts for a specific stratum."""
        return self.stratum_prompts[stratum]

    def get_prompt_stratum(self, prompt: Prompt) -> str:
        """Determine which stratum a prompt belongs to."""
        return prompt.metadata["complexity"]

    def __len__(self) -> int:
        """Total number of prompts across all strata."""
        return len(self.all_prompts)

    def __getitem__(self, idx: int) -> Prompt:
        """Get prompt by flat index."""
        return self.all_prompts[idx]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        """Sample uniformly from all prompts (naive, ignores strata)."""
        idx = rng.integers(0, len(self.all_prompts))
        return self.all_prompts[idx]

    def get_all_prompts(self) -> List[Prompt]:
        """Return all prompts."""
        return self.all_prompts.copy()


class StratifiedSampler:
    """Samples prompts with balanced representation across difficulty strata.

    Key idea: Prevent early stopping during "easy streaks" by ensuring
    each stratum is sampled proportionally throughout the evaluation.
    """

    def __init__(
        self,
        stratified_dataset: StratifiedJSONSchemaDataset,
        rng: np.random.Generator,
        balance_mode: Literal["strict", "proportional"] = "strict",
    ):
        """Initialize stratified sampler.

        Args:
            stratified_dataset: Dataset with stratified prompts
            rng: Random number generator
            balance_mode:
                - "strict": Sample round-robin from each stratum
                - "proportional": Sample with equal probability from each stratum
        """
        self.dataset = stratified_dataset
        self.rng = rng
        self.balance_mode = balance_mode

        # Track samples per stratum
        self.samples_per_stratum = defaultdict(int)

        # Remaining prompts per stratum (for sampling without replacement)
        self.remaining_prompts: Dict[str, List[Prompt]] = {
            stratum: prompts.copy()
            for stratum, prompts in self.dataset.stratum_prompts.items()
        }

    def sample_next(self) -> Tuple[str, Prompt]:
        """Sample next prompt using stratified strategy.

        Returns:
            Tuple of (stratum_name, prompt)
        """
        if self.balance_mode == "strict":
            # Round-robin: sample from least-sampled stratum
            min_count = min(self.samples_per_stratum.values(),
                          default=0)
            candidate_strata = [
                s for s in self.dataset.strata
                if self.samples_per_stratum[s] == min_count
                   and len(self.remaining_prompts[s]) > 0
            ]

            if not candidate_strata:
                raise ValueError("No prompts remaining in any stratum")

            # Random tie-break among equally-sampled strata
            stratum = self.rng.choice(candidate_strata)

        else:  # proportional
            # Sample stratum with equal probability
            available_strata = [
                s for s in self.dataset.strata
                if len(self.remaining_prompts[s]) > 0
            ]

            if not available_strata:
                raise ValueError("No prompts remaining in any stratum")

            stratum = self.rng.choice(available_strata)

        # Sample prompt from chosen stratum (without replacement)
        prompt_idx = self.rng.integers(0, len(self.remaining_prompts[stratum]))
        prompt = self.remaining_prompts[stratum].pop(prompt_idx)

        # Update counts
        self.samples_per_stratum[stratum] += 1

        return stratum, prompt

    def get_stratum_counts(self) -> Dict[str, int]:
        """Get number of samples drawn from each stratum."""
        return dict(self.samples_per_stratum)

    def has_remaining(self) -> bool:
        """Check if any prompts remain."""
        return any(len(prompts) > 0
                  for prompts in self.remaining_prompts.values())


class NaiveSampler:
    """Samples uniformly from all prompts (baseline comparison).

    This is the naive approach that can exhibit early-stopping bias
    by over-sampling easy prompts before stopping.
    """

    def __init__(
        self,
        stratified_dataset: StratifiedJSONSchemaDataset,
        rng: np.random.Generator,
    ):
        """Initialize naive uniform sampler.

        Args:
            stratified_dataset: Dataset (used for compatibility)
            rng: Random number generator
        """
        self.dataset = stratified_dataset
        self.rng = rng

        # Track for analysis
        self.samples_per_stratum = defaultdict(int)

        # All prompts, sampling with replacement
        self.all_prompts = self.dataset.all_prompts

    def sample_next(self) -> Tuple[str, Prompt]:
        """Sample next prompt uniformly (ignoring strata).

        Returns:
            Tuple of (stratum_name, prompt)
        """
        prompt = self.dataset.sample_uniform(self.rng)
        stratum = self.dataset.get_prompt_stratum(prompt)

        self.samples_per_stratum[stratum] += 1

        return stratum, prompt

    def get_stratum_counts(self) -> Dict[str, int]:
        """Get number of samples drawn from each stratum."""
        return dict(self.samples_per_stratum)

    def has_remaining(self) -> bool:
        """Always has remaining (samples with replacement)."""
        return True
