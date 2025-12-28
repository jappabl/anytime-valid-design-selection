"""Base prompt dataset protocol."""

from typing import Protocol

import numpy as np

from eval_harness.core.types import Prompt


class PromptDataset(Protocol):
    """Protocol for prompt datasets.

    Datasets provide a reproducible set of prompts with metadata.
    """

    def __len__(self) -> int:
        """Return number of prompts in dataset."""
        ...

    def __getitem__(self, idx: int) -> Prompt:
        """Get prompt by index."""
        ...

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        """Sample a random prompt uniformly."""
        ...

    def get_all_prompts(self) -> list[Prompt]:
        """Return all prompts as a list."""
        ...
