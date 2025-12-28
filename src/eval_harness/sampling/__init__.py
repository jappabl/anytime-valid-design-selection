"""LLM sampling interfaces."""

from eval_harness.sampling.base import Sampler
from eval_harness.sampling.toy_sampler import ToySampler

__all__ = ["Sampler", "ToySampler"]
