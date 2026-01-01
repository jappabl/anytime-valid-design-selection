"""Easy JSON schema prompts for real-LLM validation.

Designed to achieve ~5-10% failure rates on GPT-4o-mini, enabling early stopping
for Experiment A replication.

Difficulty progression (targeting overall p≈0.08):
- Simple: 3 fields, basic types → p≈0.02
- Medium: 4-5 fields, simple email, enums → p≈0.05  
- Complex: 5-6 fields, nested object → p≈0.10
- Extreme: 7-8 fields, deeper nesting, simple regex → p≈0.15
"""

import json
from typing import Literal

import numpy as np

from eval_harness.core.types import Prompt


class EasyJSONSchemaDataset:
    """Easy JSON schema prompts with realistic difficulty heterogeneity."""

    def __init__(
        self,
        n_prompts: int = 100,
        complexity: Literal["simple", "medium", "complex", "extreme"] = "medium",
        seed: int = 42,
    ):
        self.n_prompts = n_prompts
        self.complexity = complexity
        self.seed = seed
        self.prompts = self._generate_prompts()

    def _generate_prompts(self) -> list[Prompt]:
        """Generate all prompts deterministically."""
        rng = np.random.default_rng(self.seed)
        prompts = []

        for i in range(self.n_prompts):
            schema, description = self._generate_schema(i, rng)
            prompt_text = self._create_prompt_text(schema, description)

            prompts.append(
                Prompt(
                    id=f"easy_json_{self.complexity}_{i:04d}",
                    text=prompt_text,
                    metadata={
                        "schema": schema,
                        "complexity": self.complexity,
                        "description": description,
                    },
                )
            )

        return prompts

    def _generate_schema(self, idx: int, rng: np.random.Generator) -> tuple[dict, str]:
        """Generate schema based on complexity."""
        if self.complexity == "simple":
            return self._generate_simple_schema(idx, rng)
        elif self.complexity == "medium":
            return self._generate_medium_schema(idx, rng)
        elif self.complexity == "complex":
            return self._generate_complex_schema(idx, rng)
        else:  # extreme
            return self._generate_extreme_schema(idx, rng)

    def _generate_simple_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Simple: 3 fields, basic types only."""

        schemas = [
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0, "maximum": 150},
                    "active": {"type": "boolean"}
                },
                "required": ["name", "age"],
                "additionalProperties": False
            },
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "price": {"type": "number", "minimum": 0},
                    "in_stock": {"type": "boolean"}
                },
                "required": ["title", "price"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a user profile with name (string), age (integer 0-150), and active status (boolean)",
            "a product with title (string), price (positive number), and in_stock status (boolean)",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_medium_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Medium: 4-5 fields with simple email pattern and enums."""

        schemas = [
            {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "name": {"type": "string", "minLength": 1},
                    "price": {"type": "number", "minimum": 0},
                    "category": {"type": "string", "enum": ["electronics", "clothing", "food", "books"]},
                    "in_stock": {"type": "boolean"}
                },
                "required": ["product_id", "name", "price", "category"],
                "additionalProperties": False
            },
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "username": {"type": "string", "minLength": 3},
                    "email": {"type": "string", "pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                    "age": {"type": "integer", "minimum": 13},
                },
                "required": ["user_id", "username", "email"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a product with product_id (string), name (non-empty), price (non-negative), category (one of: electronics, clothing, food, books), and in_stock (boolean)",
            "a user with user_id (string), username (min 3 chars), email (simple format: text@text.text), and age (13+)",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_complex_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Complex: 5-6 fields with one nested object."""

        schemas = [
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "customer_email": {"type": "string", "pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                    "total": {"type": "number", "minimum": 0},
                    "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "zip": {"type": "string"}
                        },
                        "required": ["street", "city", "zip"],
                        "additionalProperties": False
                    },
                },
                "required": ["order_id", "customer_email", "total", "status", "address"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a customer order with order_id (string), customer_email (email format), total (non-negative), status (pending/shipped/delivered), and nested address object with street, city, zip",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_extreme_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Extreme: 7-8 fields with deeper nesting and simple patterns."""

        schema = {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "pattern": "^TXN-[0-9]{6}$"},
                "amount": {"type": "number", "minimum": 0.01},
                "currency": {"type": "string", "enum": ["USD", "EUR", "GBP"]},
                "status": {"type": "string", "enum": ["pending", "approved", "declined"]},
                "merchant": {
                    "type": "object",
                    "properties": {
                        "merchant_id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                    "required": ["merchant_id", "name"],
                    "additionalProperties": False
                },
                "customer": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "email": {"type": "string", "pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                        "address": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "zip": {"type": "string"}
                            },
                            "required": ["city", "zip"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["customer_id", "email", "address"],
                    "additionalProperties": False
                },
            },
            "required": ["transaction_id", "amount", "currency", "status", "merchant", "customer"],
            "additionalProperties": False
        }

        description = "a payment transaction with transaction_id (format: TXN-123456), amount, currency (USD/EUR/GBP), status, nested merchant object, and nested customer object with email and address"

        return schema, description

    def _create_prompt_text(self, schema: dict, description: str) -> str:
        """Create prompt text from schema."""
        schema_json = json.dumps(schema, indent=2)

        prompt = f"""Generate a valid JSON object representing {description}.

The JSON must conform to this schema:

{schema_json}

Generate only the JSON object, with no additional text or explanation."""

        return prompt

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        """Sample uniformly from all prompts."""
        idx = rng.integers(0, len(self.prompts))
        return self.prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        """Return all prompts."""
        return self.prompts.copy()

    def __len__(self) -> int:
        return len(self.prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.prompts[idx]


class StratifiedEasyJSONDataset:
    """Easy JSON prompts stratified by difficulty."""

    def __init__(
        self,
        prompts_per_stratum: int = 25,
        seed: int = 42,
        strata: list[Literal["simple", "medium", "complex", "extreme"]] = None,
    ):
        self.prompts_per_stratum = prompts_per_stratum
        self.seed = seed
        self.strata = strata or ["simple", "medium", "complex", "extreme"]

        # Generate prompts for each stratum
        self.stratum_prompts: dict[str, list[Prompt]] = {}
        self._generate_stratified_prompts()

        # Flatten for compatibility
        self.all_prompts = []
        for stratum in self.strata:
            self.all_prompts.extend(self.stratum_prompts[stratum])

    def _generate_stratified_prompts(self):
        """Generate prompts for each difficulty stratum."""
        # Use deterministic seed offsets
        SEED_OFFSETS = {"simple": 0, "medium": 1000, "complex": 2000, "extreme": 3000}

        for stratum in self.strata:
            stratum_seed = self.seed + SEED_OFFSETS[stratum]
            dataset = EasyJSONSchemaDataset(
                n_prompts=self.prompts_per_stratum,
                complexity=stratum,
                seed=stratum_seed,
            )
            self.stratum_prompts[stratum] = dataset.prompts

    def get_stratum_prompts(self, stratum: str) -> list[Prompt]:
        """Get all prompts for a specific stratum."""
        return self.stratum_prompts[stratum]

    def get_prompt_stratum(self, prompt: Prompt) -> str:
        """Determine which stratum a prompt belongs to."""
        return prompt.metadata["complexity"]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        """Sample uniformly from all prompts."""
        idx = rng.integers(0, len(self.all_prompts))
        return self.all_prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        """Return all prompts."""
        return self.all_prompts.copy()

    def __len__(self) -> int:
        return len(self.all_prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.all_prompts[idx]
