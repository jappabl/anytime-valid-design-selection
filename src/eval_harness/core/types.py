"""Core data types for the evaluation harness."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DecodingConfig:
    """Configuration for sampling from LLM."""

    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 512
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    def to_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }


@dataclass(frozen=True)
class Prompt:
    """A single prompt with metadata."""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


@dataclass
class Sample:
    """A single generation from a model."""

    id: str  # Unique sample ID
    prompt_id: str
    model_id: str
    decoding_config: DecodingConfig
    seed: int
    generation: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating a sample."""

    sample_id: str
    passed: bool
    failure_mode: Optional[str] = None
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def failed(self) -> bool:
        """Convenience accessor for failure (inverted pass)."""
        return not self.passed


@dataclass
class ExperimentState:
    """Current state of an experiment (for resumability)."""

    experiment_id: str
    n_samples: int = 0
    n_failures: int = 0
    stopped: bool = False
    stop_reason: Optional[str] = None
    completed_prompts: set[str] = field(default_factory=set)
    latest_bounds: Optional[tuple[float, float]] = None
    timestamp: datetime = field(default_factory=datetime.now)
