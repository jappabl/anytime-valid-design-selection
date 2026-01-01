"""Easy JSON schema prompts for real-LLM validation.

Tuned to achieve ~12-15% failure rates on GPT-4o-mini.

Difficulty progression (targeting overall p≈0.13):
- Simple: Basic fields with additionalProperties:false → p≈0.05
- Medium: Email + phone patterns → p≈0.10  
- Complex: Nested + stricter patterns → p≈0.18
- Extreme: Deep nesting + multiple patterns → p≈0.25
"""

import json
from typing import Literal

import numpy as np

from eval_harness.core.types import Prompt


class EasyJSONSchemaDataset:
    """Moderate-difficulty JSON schemas."""

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
        if self.complexity == "simple":
            return self._generate_simple_schema(idx, rng)
        elif self.complexity == "medium":
            return self._generate_medium_schema(idx, rng)
        elif self.complexity == "complex":
            return self._generate_complex_schema(idx, rng)
        else:
            return self._generate_extreme_schema(idx, rng)

    def _generate_simple_schema(self, idx: int, rng: np.random.Generator) -> tuple[dict, str]:
        """Simple: 3-4 fields, strict on additionalProperties."""
        
        schemas = [
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "pattern": "^[A-Z]{2}[0-9]{4}$"},
                    "name": {"type": "string", "minLength": 2},
                    "age": {"type": "integer", "minimum": 1, "maximum": 120}
                },
                "required": ["user_id", "name", "age"],
                "additionalProperties": False
            },
            {
                "type": "object",
                "properties": {
                    "product_code": {"type": "string", "pattern": "^P[0-9]{5}$"},
                    "price": {"type": "number", "minimum": 0.01},
                    "available": {"type": "boolean"}
                },
                "required": ["product_code", "price"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a user with user_id (format: AB1234), name (min 2 chars), and age (1-120)",
            "a product with product_code (format: P12345), price (positive), and available flag",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_medium_schema(self, idx: int, rng: np.random.Generator) -> tuple[dict, str]:
        """Medium: 4-5 fields with email/phone patterns."""
        
        schemas = [
            {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string"},
                    "email": {"type": "string", "pattern": "^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"},
                    "phone": {"type": "string", "pattern": "^[0-9]{3}-[0-9]{3}-[0-9]{4}$"},
                    "verified": {"type": "boolean"}
                },
                "required": ["contact_id", "email", "phone"],
                "additionalProperties": False
            },
            {
                "type": "object",
                "properties": {
                    "order_number": {"type": "string", "pattern": "^ORD-[0-9]{6}$"},
                    "date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                    "total": {"type": "number", "minimum": 0},
                    "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]}
                },
                "required": ["order_number", "date", "total", "status"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a contact with contact_id, email (lowercase letters/numbers with @ and .), phone (format: 555-123-4567), and verified status",
            "an order with order_number (format: ORD-123456), date (YYYY-MM-DD), total amount, and status (pending/shipped/delivered)",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_complex_schema(self, idx: int, rng: np.random.Generator) -> tuple[dict, str]:
        """Complex: 6 fields with nested object and patterns."""
        
        schema = {
            "type": "object",
            "properties": {
                "employee_id": {"type": "string", "pattern": "^EMP[0-9]{5}$"},
                "email": {"type": "string", "pattern": "^[a-z.]+@company\\.com$"},
                "department": {"type": "string", "enum": ["eng", "sales", "hr", "ops"]},
                "hire_date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                "address": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "minLength": 2},
                        "state": {"type": "string", "pattern": "^[A-Z]{2}$"},
                        "zip": {"type": "string", "pattern": "^[0-9]{5}$"}
                    },
                    "required": ["city", "state", "zip"],
                    "additionalProperties": False
                }
            },
            "required": ["employee_id", "email", "department", "hire_date", "address"],
            "additionalProperties": False
        }

        description = "an employee with employee_id (EMP12345), email (@company.com domain, lowercase), department (eng/sales/hr/ops), hire_date (YYYY-MM-DD), and nested address with city, state (2 uppercase letters), and 5-digit zip"

        return schema, description

    def _generate_extreme_schema(self, idx: int, rng: np.random.Generator) -> tuple[dict, str]:
        """Extreme: Deep nesting with multiple strict patterns."""
        
        schema = {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "pattern": "^INV-[0-9]{8}-[A-Z]{2}$"},
                "timestamp": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
                "amount": {"type": "number", "minimum": 0.01, "maximum": 999999.99},
                "vendor": {
                    "type": "object",
                    "properties": {
                        "vendor_id": {"type": "string", "pattern": "^VND[0-9]{6}$"},
                        "tax_id": {"type": "string", "pattern": "^[0-9]{2}-[0-9]{7}$"},
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string", "pattern": "^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"},
                                "phone": {"type": "string", "pattern": "^\\+1-[0-9]{3}-[0-9]{3}-[0-9]{4}$"}
                            },
                            "required": ["email", "phone"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["vendor_id", "tax_id", "contact"],
                    "additionalProperties": False
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$"},
                            "quantity": {"type": "integer", "minimum": 1}
                        },
                        "required": ["sku", "quantity"]
                    },
                    "minItems": 1,
                    "maxItems": 10
                }
            },
            "required": ["invoice_id", "timestamp", "amount", "vendor", "line_items"],
            "additionalProperties": False
        }

        description = "an invoice with invoice_id (INV-12345678-US), ISO timestamp, amount, nested vendor object with vendor_id (VND123456), tax_id (12-1234567), and contact info (email and phone +1-555-123-4567), plus array of line_items with sku (ABC-1234) and quantity"

        return schema, description

    def _create_prompt_text(self, schema: dict, description: str) -> str:
        schema_json = json.dumps(schema, indent=2)
        return f"""Generate a valid JSON object representing {description}.

The JSON must conform to this schema:

{schema_json}

Generate only the JSON object, with no additional text or explanation."""

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        idx = rng.integers(0, len(self.prompts))
        return self.prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        return self.prompts.copy()

    def __len__(self) -> int:
        return len(self.prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.prompts[idx]


class StratifiedEasyJSONDataset:
    """Stratified by difficulty."""

    def __init__(
        self,
        prompts_per_stratum: int = 25,
        seed: int = 42,
        strata: list[Literal["simple", "medium", "complex", "extreme"]] = None,
    ):
        self.prompts_per_stratum = prompts_per_stratum
        self.seed = seed
        self.strata = strata or ["simple", "medium", "complex", "extreme"]
        self.stratum_prompts: dict[str, list[Prompt]] = {}
        self._generate_stratified_prompts()
        self.all_prompts = []
        for stratum in self.strata:
            self.all_prompts.extend(self.stratum_prompts[stratum])

    def _generate_stratified_prompts(self):
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
        return self.stratum_prompts[stratum]

    def get_prompt_stratum(self, prompt: Prompt) -> str:
        return prompt.metadata["complexity"]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        idx = rng.integers(0, len(self.all_prompts))
        return self.all_prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        return self.all_prompts.copy()

    def __len__(self) -> int:
        return len(self.all_prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.all_prompts[idx]
