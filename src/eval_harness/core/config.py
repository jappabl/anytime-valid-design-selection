"""Experiment configuration using Pydantic."""

import hashlib
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field

from eval_harness.core.types import DecodingConfig


class SamplerConfig(BaseModel):
    """Configuration for LLM sampler."""

    type: Literal["openai", "vllm", "toy", "gemini", "groq"] = "toy"
    model_id: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    # Toy model specific
    failure_probability: Optional[float] = None


class ValidatorConfig(BaseModel):
    """Configuration for validator."""

    type: Literal["json_schema", "regex", "sql"] = "json_schema"
    # JSON schema specific
    json_schema: Optional[dict] = Field(None, alias="schema")
    require_exact_keys: bool = False
    # Regex specific
    pattern: Optional[str] = None

    class Config:
        populate_by_name = True  # Allow both 'schema' and 'json_schema'


class PromptConfig(BaseModel):
    """Configuration for prompt dataset."""

    type: Literal["json_schema", "static", "sql", "stratified_json"] = "json_schema"
    n_prompts: int = 100
    seed: int = 42
    # JSON schema prompt specific
    complexity: Literal["simple", "medium", "complex", "extreme"] = "medium"
    # Stratified JSON schema specific
    prompts_per_stratum: Optional[int] = Field(None, description="Prompts per difficulty level")
    sampling_mode: Literal["naive", "stratified"] = Field("naive", description="Naive or stratified sampling")
    # Static prompt specific
    prompts_file: Optional[str] = None


class StoppingConfig(BaseModel):
    """Configuration for sequential stopping rules."""

    precision_target: Optional[float] = Field(0.01, description="Stop when CI width <= this")
    certification_threshold: Optional[float] = Field(
        None, description="Stop when upper bound <= this"
    )
    min_samples: int = Field(30, description="Minimum samples before allowing stop")
    max_samples: int = Field(2000, description="Maximum samples (budget cap)")
    max_consecutive_api_failures: int = Field(
        5, description="Abort experiment after this many consecutive empty API responses"
    )


class StatisticsConfig(BaseModel):
    """Configuration for statistical inference."""

    alpha: float = Field(0.05, description="Significance level (1 - confidence)")
    method: Literal["betting", "mixture"] = Field(
        "betting", description="CS construction method"
    )


class ExperimentConfig(BaseModel):
    """Complete experiment configuration."""

    name: str = Field(..., description="Human-readable experiment name")
    sampler: SamplerConfig
    validator: ValidatorConfig
    prompts: PromptConfig
    decoding: DecodingConfig = Field(default_factory=DecodingConfig)
    stopping: StoppingConfig = Field(default_factory=StoppingConfig)
    statistics: StatisticsConfig = Field(default_factory=StatisticsConfig)
    seed: int = Field(42, description="Master random seed")

    def get_experiment_id(self) -> str:
        """Generate deterministic experiment ID from config hash."""
        # Use model_dump with sort to get deterministic dict, then json.dumps with sort_keys
        config_dict = self.model_dump(mode='json')
        config_json = json.dumps(config_dict, sort_keys=True)
        hash_digest = hashlib.sha256(config_json.encode()).hexdigest()
        return hash_digest[:12]

    class Config:
        frozen = True
