"""Easy JSON schema prompts for real-LLM validation.

Designed to achieve ~10-20% failure rates on GPT-4o-mini, enabling early stopping
for Experiment A replication.

Difficulty progression:
- Simple: 2-3 fields, primitive types, no constraints
- Medium: 4-5 fields, simple constraints (min/max, enum)
- Complex: 6-8 fields, basic nesting, simple patterns
- Extreme: 10+ fields, moderate nesting, some regex
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
        """Simple: 2-3 fields, primitive types, no constraints."""

        schemas = [
            # User profile
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number"},
                    "active": {"type": "boolean"}
                },
                "required": ["name", "age"],
                "additionalProperties": False
            },
            # Product
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "price": {"type": "number"},
                },
                "required": ["title", "price"],
                "additionalProperties": False
            },
            # Event
            {
                "type": "object",
                "properties": {
                    "event_name": {"type": "string"},
                    "date": {"type": "string"},
                    "attendees": {"type": "number"}
                },
                "required": ["event_name", "date"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a user profile with name, age, and active status",
            "a product with title and price",
            "an event with name, date, and attendee count",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_medium_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Medium: 4-5 fields, simple constraints (min/max, enum)."""

        schemas = [
            # Product with constraints
            {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "name": {"type": "string", "minLength": 1, "maxLength": 100},
                    "price": {"type": "number", "minimum": 0},
                    "category": {"type": "string", "enum": ["electronics", "clothing", "food", "books"]},
                    "in_stock": {"type": "boolean"}
                },
                "required": ["product_id", "name", "price", "category"],
                "additionalProperties": False
            },
            # User registration
            {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "minLength": 3, "maxLength": 20},
                    "email": {"type": "string"},
                    "age": {"type": "number", "minimum": 13, "maximum": 120},
                    "country": {"type": "string", "enum": ["US", "UK", "CA", "AU"]},
                },
                "required": ["username", "email", "age"],
                "additionalProperties": False
            },
            # Order
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "total": {"type": "number", "minimum": 0},
                    "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]},
                    "item_count": {"type": "number", "minimum": 1},
                    "priority": {"type": "boolean"}
                },
                "required": ["order_id", "total", "status"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a product with ID, name, price, category, and stock status",
            "a user registration with username, email, age, and country",
            "an order with ID, total, status, item count, and priority flag",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_complex_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Complex: 6-8 fields, basic nesting, simple patterns."""

        schemas = [
            # Customer order with address
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "pattern": "^ORD-[0-9]{6}$"},
                    "customer_name": {"type": "string", "minLength": 2},
                    "total_amount": {"type": "number", "minimum": 0.01},
                    "status": {"type": "string", "enum": ["pending", "processing", "shipped", "delivered"]},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "zip": {"type": "string"}
                        },
                        "required": ["street", "city", "zip"]
                    },
                    "created_date": {"type": "string"},
                },
                "required": ["order_id", "customer_name", "total_amount", "status", "address"],
                "additionalProperties": False
            },
            # Employee record
            {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "pattern": "^EMP[0-9]{4}$"},
                    "first_name": {"type": "string", "minLength": 1},
                    "last_name": {"type": "string", "minLength": 1},
                    "department": {"type": "string", "enum": ["engineering", "sales", "hr", "marketing"]},
                    "salary": {"type": "number", "minimum": 30000, "maximum": 500000},
                    "contact": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "phone": {"type": "string"}
                        },
                        "required": ["email"]
                    },
                    "hire_date": {"type": "string"}
                },
                "required": ["employee_id", "first_name", "last_name", "department", "contact"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a customer order with ID, name, amount, status, and shipping address",
            "an employee record with ID, name, department, salary, and contact info",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_extreme_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Extreme: 10+ fields, moderate nesting, regex patterns."""

        schema = {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "pattern": "^TXN-[0-9]{10}-[A-Z]{3}$"},
                "timestamp": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
                "amount": {"type": "number", "minimum": 0.01, "maximum": 100000},
                "currency": {"type": "string", "enum": ["USD", "EUR", "GBP", "JPY", "CNY"]},
                "status": {"type": "string", "enum": ["pending", "approved", "declined", "refunded"]},
                "merchant": {
                    "type": "object",
                    "properties": {
                        "merchant_id": {"type": "string", "pattern": "^MER[0-9]{6}$"},
                        "name": {"type": "string", "minLength": 2, "maxLength": 100},
                        "category": {"type": "string", "enum": ["retail", "restaurant", "online", "service"]}
                    },
                    "required": ["merchant_id", "name", "category"]
                },
                "customer": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string", "pattern": "^CUST[0-9]{8}$"},
                        "email": {"type": "string"},
                        "phone": {"type": "string", "pattern": "^\\+1[0-9]{10}$"},
                        "billing_address": {
                            "type": "object",
                            "properties": {
                                "street": {"type": "string", "minLength": 5},
                                "city": {"type": "string", "minLength": 2},
                                "state": {"type": "string", "pattern": "^[A-Z]{2}$"},
                                "zip": {"type": "string", "pattern": "^[0-9]{5}$"}
                            },
                            "required": ["street", "city", "state", "zip"]
                        }
                    },
                    "required": ["customer_id", "email", "billing_address"]
                },
                "payment_method": {"type": "string", "enum": ["credit_card", "debit_card", "bank_transfer", "digital_wallet"]},
                "risk_score": {"type": "number", "minimum": 0, "maximum": 100}
            },
            "required": ["transaction_id", "timestamp", "amount", "currency", "status", "merchant", "customer", "payment_method"],
            "additionalProperties": False
        }

        description = "a payment transaction with ID, timestamp, amount, merchant details, customer info with billing address, payment method, and risk score"

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
