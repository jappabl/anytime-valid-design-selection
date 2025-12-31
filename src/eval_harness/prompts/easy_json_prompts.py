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
        """Simple: 3-4 fields with basic regex patterns."""

        schemas = [
            # User profile with email
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 2, "maxLength": 50},
                    "email": {"type": "string", "pattern": "^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"},
                    "age": {"type": "integer", "minimum": 1, "maximum": 120},
                    "verified": {"type": "boolean"}
                },
                "required": ["name", "email", "age"],
                "additionalProperties": False
            },
            # Product with SKU
            {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{5}$"},
                    "title": {"type": "string", "minLength": 3, "maxLength": 100},
                    "price": {"type": "number", "minimum": 0.01, "maximum": 10000},
                    "quantity": {"type": "integer", "minimum": 0}
                },
                "required": ["sku", "title", "price"],
                "additionalProperties": False
            },
            # Event with date format
            {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "pattern": "^EVT[0-9]{6}$"},
                    "name": {"type": "string", "minLength": 3},
                    "date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                    "capacity": {"type": "integer", "minimum": 10, "maximum": 10000}
                },
                "required": ["event_id", "name", "date"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a user profile with name, valid email address, age, and verified status",
            "a product with SKU code (format: ABC-12345), title, price, and quantity",
            "an event with ID (format: EVT123456), name, date (YYYY-MM-DD), and capacity",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_medium_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Medium: 5-6 fields with phone numbers, tighter regex."""

        schemas = [
            # Product with UPC
            {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "pattern": "^PROD-[0-9]{8}$"},
                    "upc": {"type": "string", "pattern": "^[0-9]{12}$"},
                    "name": {"type": "string", "minLength": 3, "maxLength": 100},
                    "price": {"type": "number", "minimum": 0.01, "multipleOf": 0.01},
                    "category": {"type": "string", "enum": ["electronics", "clothing", "food", "books", "home"]},
                    "in_stock": {"type": "boolean"}
                },
                "required": ["product_id", "upc", "name", "price", "category"],
                "additionalProperties": False
            },
            # User with phone
            {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "pattern": "^USR[0-9]{7}$"},
                    "username": {"type": "string", "pattern": "^[a-z][a-z0-9_]{2,19}$"},
                    "email": {"type": "string", "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
                    "phone": {"type": "string", "pattern": "^\\+1-[0-9]{3}-[0-9]{3}-[0-9]{4}$"},
                    "age": {"type": "integer", "minimum": 18, "maximum": 100},
                    "verified": {"type": "boolean"}
                },
                "required": ["user_id", "username", "email", "phone"],
                "additionalProperties": False
            },
            # Order with timestamp
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "pattern": "^ORD-[0-9]{10}$"},
                    "created_at": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
                    "total": {"type": "number", "minimum": 1.00, "multipleOf": 0.01},
                    "status": {"type": "string", "enum": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                    "item_count": {"type": "integer", "minimum": 1, "maximum": 100},
                    "priority": {"type": "boolean"}
                },
                "required": ["order_id", "created_at", "total", "status", "item_count"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a product with ID (PROD-12345678), 12-digit UPC, name, price, category, and stock status",
            "a user with ID (USR1234567), username (lowercase starting with letter), email, US phone (+1-555-123-4567), age, and verified status",
            "an order with ID (ORD-1234567890), ISO timestamp, total, status, item count, and priority",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_complex_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Complex: 7-8 fields, nested objects with strict patterns."""

        schemas = [
            # Customer order with strict address
            {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "pattern": "^ORD-[0-9]{8}-[A-Z]{2}$"},
                    "customer_email": {"type": "string", "pattern": "^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$"},
                    "total_amount": {"type": "number", "minimum": 5.00, "maximum": 50000, "multipleOf": 0.01},
                    "tax_amount": {"type": "number", "minimum": 0, "multipleOf": 0.01},
                    "status": {"type": "string", "enum": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                    "shipping_address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string", "minLength": 5, "maxLength": 100},
                            "city": {"type": "string", "minLength": 2, "maxLength": 50},
                            "state": {"type": "string", "pattern": "^[A-Z]{2}$"},
                            "zip": {"type": "string", "pattern": "^[0-9]{5}(-[0-9]{4})?$"}
                        },
                        "required": ["street", "city", "state", "zip"],
                        "additionalProperties": False
                    },
                    "created_at": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"},
                },
                "required": ["order_id", "customer_email", "total_amount", "tax_amount", "status", "shipping_address", "created_at"],
                "additionalProperties": False
            },
            # Employee with nested contact
            {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string", "pattern": "^EMP-[0-9]{6}$"},
                    "ssn_last_four": {"type": "string", "pattern": "^[0-9]{4}$"},
                    "first_name": {"type": "string", "minLength": 2, "maxLength": 50},
                    "last_name": {"type": "string", "minLength": 2, "maxLength": 50},
                    "department": {"type": "string", "enum": ["engineering", "sales", "hr", "marketing", "finance", "operations"]},
                    "annual_salary": {"type": "number", "minimum": 30000, "maximum": 500000, "multipleOf": 1000},
                    "contact_info": {
                        "type": "object",
                        "properties": {
                            "work_email": {"type": "string", "pattern": "^[a-z.]+@company\\.com$"},
                            "work_phone": {"type": "string", "pattern": "^\\+1-[0-9]{3}-[0-9]{3}-[0-9]{4}$"},
                            "extension": {"type": "string", "pattern": "^x[0-9]{4}$"}
                        },
                        "required": ["work_email", "work_phone"],
                        "additionalProperties": False
                    },
                    "hire_date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}
                },
                "required": ["employee_id", "ssn_last_four", "first_name", "last_name", "department", "annual_salary", "contact_info", "hire_date"],
                "additionalProperties": False
            },
        ]

        descriptions = [
            "a customer order with ID (ORD-12345678-US), email, total amount, tax amount, status, shipping address (with 5 or 9-digit ZIP), and ISO timestamp",
            "an employee record with ID (EMP-123456), last 4 of SSN, name, department, salary (multiple of 1000), contact info (work email @company.com, phone, extension like x1234), and hire date",
        ]

        choice = rng.integers(0, len(schemas))
        return schemas[choice], descriptions[choice]

    def _generate_extreme_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Extreme: 12+ fields, deep nesting, very strict patterns."""

        schema = {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "pattern": "^TXN-[0-9]{10}-[A-Z]{3}$"},
                "batch_id": {"type": "string", "pattern": "^BATCH[0-9]{8}$"},
                "timestamp": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"},
                "amount": {"type": "number", "minimum": 0.01, "maximum": 100000, "multipleOf": 0.01},
                "currency": {"type": "string", "enum": ["USD", "EUR", "GBP", "JPY", "CNY", "AUD", "CAD"]},
                "exchange_rate": {"type": "number", "minimum": 0.0001, "exclusiveMaximum": 1000},
                "status": {"type": "string", "enum": ["pending", "approved", "declined", "refunded", "chargeback"]},
                "merchant": {
                    "type": "object",
                    "properties": {
                        "merchant_id": {"type": "string", "pattern": "^MER-[0-9]{8}$"},
                        "tax_id": {"type": "string", "pattern": "^[0-9]{2}-[0-9]{7}$"},
                        "name": {"type": "string", "minLength": 3, "maxLength": 100},
                        "category": {"type": "string", "enum": ["retail", "restaurant", "online", "service", "healthcare"]},
                        "mcc_code": {"type": "string", "pattern": "^[0-9]{4}$"}
                    },
                    "required": ["merchant_id", "tax_id", "name", "category", "mcc_code"],
                    "additionalProperties": False
                },
                "customer": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string", "pattern": "^CUST-[0-9]{10}$"},
                        "email": {"type": "string", "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
                        "phone": {"type": "string", "pattern": "^\\+1-[0-9]{3}-[0-9]{3}-[0-9]{4}$"},
                        "loyalty_number": {"type": "string", "pattern": "^LOY[0-9]{12}$"},
                        "billing_address": {
                            "type": "object",
                            "properties": {
                                "street_number": {"type": "string", "pattern": "^[0-9]+[A-Za-z]?$"},
                                "street_name": {"type": "string", "minLength": 3, "maxLength": 100},
                                "unit": {"type": "string", "pattern": "^(Apt|Suite|Unit|#)\\s*[A-Za-z0-9]+$"},
                                "city": {"type": "string", "minLength": 2, "maxLength": 50},
                                "state": {"type": "string", "pattern": "^[A-Z]{2}$"},
                                "zip": {"type": "string", "pattern": "^[0-9]{5}-[0-9]{4}$"},
                                "country": {"type": "string", "enum": ["USA"]}
                            },
                            "required": ["street_number", "street_name", "city", "state", "zip", "country"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["customer_id", "email", "phone", "loyalty_number", "billing_address"],
                    "additionalProperties": False
                },
                "payment_method": {"type": "string", "enum": ["credit_card", "debit_card", "bank_transfer", "digital_wallet", "cryptocurrency"]},
                "card_last_four": {"type": "string", "pattern": "^[0-9]{4}$"},
                "authorization_code": {"type": "string", "pattern": "^AUTH[0-9]{10}$"},
                "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "fraud_flags": {"type": "array", "items": {"type": "string", "enum": ["high_value", "foreign_ip", "new_device", "velocity_check", "none"]}, "minItems": 1, "maxItems": 5}
            },
            "required": ["transaction_id", "batch_id", "timestamp", "amount", "currency", "exchange_rate", "status", "merchant", "customer", "payment_method", "card_last_four", "authorization_code", "risk_score", "fraud_flags"],
            "additionalProperties": False
        }

        description = "a payment transaction with ID (TXN-1234567890-USD), batch ID, ISO timestamp with milliseconds, amount, currency, exchange rate, status, merchant (with tax ID, MCC code), customer (with loyalty number and detailed billing address including unit, 9-digit ZIP), payment method, last 4 digits of card, authorization code, integer risk score, and array of fraud flags"

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
