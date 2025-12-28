"""JSON schema prompt generation with difficulty knobs.

Generates prompts asking the model to produce JSON conforming to various schemas.
Difficulty can be controlled via:
- Schema complexity (nested depth, number of fields)
- Required vs optional fields
- Type constraints (enums, ranges, patterns)
"""

import json
from typing import Literal

import numpy as np

from eval_harness.core.types import Prompt


class JSONSchemaPromptDataset:
    """Dataset of JSON schema generation prompts.

    Generates diverse prompts with controllable complexity.
    """

    def __init__(
        self,
        n_prompts: int = 100,
        complexity: Literal["simple", "medium", "complex", "extreme"] = "medium",
        seed: int = 42,
    ):
        """Initialize JSON schema prompt dataset.

        Args:
            n_prompts: Number of prompts to generate
            complexity: Difficulty level
            seed: Random seed for reproducibility
        """
        self.n_prompts = n_prompts
        self.complexity = complexity
        self.seed = seed

        # Generate prompts
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
                    id=f"json_schema_{self.complexity}_{i:04d}",
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
        """Generate a JSON schema with controlled complexity.

        Returns:
            Tuple of (schema_dict, human_description)
        """
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
        """Generate 'simple' schema - now much harder with strict validation.

        New floor: 6-8 fields, regex patterns, enums, constraints, 1-2 level nesting.
        """
        properties = {
            "user_id": {"type": "integer", "minimum": 100000, "maximum": 999999},
            "email": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            },
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 20,
                "pattern": "^[a-zA-Z0-9_]+$"
            },
            "age": {"type": "integer", "minimum": 13, "maximum": 120},
            "country": {
                "type": "string",
                "enum": ["US", "UK", "CA", "AU", "DE", "FR", "JP", "CN"]
            },
            "is_active": {"type": "boolean"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 5
            },
            "settings": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "enum": ["light", "dark", "auto"]},
                    "language": {"type": "string", "pattern": "^[a-z]{2}$"}
                },
                "required": ["theme"],
                "additionalProperties": False
            }
        }

        schema = {
            "type": "object",
            "properties": properties,
            "required": ["user_id", "email", "username", "age", "country", "is_active", "tags", "settings"],
            "additionalProperties": False,
        }

        description = (
            "user profile with validated email/username, age range 13-120, country enum, "
            "tags array (1-5 items), nested settings with theme and 2-letter language code"
        )
        return schema, description

    def _generate_medium_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Generate medium schema - significantly harder, 10-15 fields, 2-3 levels deep."""
        properties = {
            "order_id": {
                "type": "string",
                "pattern": "^ORD-[0-9]{8}-[A-Z]{4}$"
            },
            "created_at": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$"
            },
            "status": {
                "type": "string",
                "enum": ["pending", "processing", "shipped", "delivered", "cancelled", "refunded"]
            },
            "total_amount": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 50000.00,
                "multipleOf": 0.01
            },
            "customer": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "pattern": "^CUST-[0-9]{10}$"},
                    "name": {"type": "string", "minLength": 2, "maxLength": 100},
                    "phone": {"type": "string", "pattern": "^\\+1-\\d{3}-\\d{3}-\\d{4}$"},
                    "shipping_address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string", "minLength": 5},
                            "city": {"type": "string", "minLength": 2},
                            "state": {"type": "string", "pattern": "^[A-Z]{2}$"},
                            "zip": {"type": "string", "pattern": "^\\d{5}$"}
                        },
                        "required": ["street", "city", "state", "zip"],
                        "additionalProperties": False
                    }
                },
                "required": ["customer_id", "name", "phone", "shipping_address"],
                "additionalProperties": False
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "pattern": "^PROD-[A-Z0-9]{8}$"},
                        "quantity": {"type": "integer", "minimum": 1, "maximum": 100},
                        "price": {"type": "number", "minimum": 0.01, "multipleOf": 0.01}
                    },
                    "required": ["product_id", "quantity", "price"],
                    "additionalProperties": False
                }
            },
            "payment": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["credit_card", "paypal", "apple_pay", "google_pay"]},
                    "confirmed": {"type": "boolean"},
                    "transaction_id": {"type": "string", "minLength": 16, "maxLength": 32}
                },
                "required": ["method", "confirmed"],
                "additionalProperties": False
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 10
            }
        }

        schema = {
            "type": "object",
            "properties": properties,
            "required": ["order_id", "created_at", "status", "total_amount", "customer", "items", "payment"],
            "additionalProperties": False,
        }

        description = (
            "e-commerce order with pattern-validated order_id, ISO timestamp, status enum, "
            "precise amount, nested customer with phone/address (3 levels), items array "
            "with product_id/quantity/price, payment object, optional notes"
        )
        return schema, description

    def _generate_complex_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Generate complex schema - 15-20 fields, 3-4 levels, oneOf conditionals."""
        properties = {
            "api_key": {
                "type": "string",
                "pattern": "^[a-f0-9]{64}$"
            },
            "request_id": {
                "type": "string",
                "pattern": "^req_[0-9a-zA-Z]{24}$"
            },
            "timestamp": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z$"
            },
            "endpoint": {
                "type": "string",
                "pattern": "^/api/v[1-9]/[a-z_/]+$"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
            },
            "user": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "pattern": "^usr_[0-9a-f]{32}$"},
                    "email": {
                        "type": "string",
                        "pattern": "^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\\.[a-zA-Z0-9-]+)*$"
                    },
                    "roles": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["admin", "developer", "analyst", "viewer", "auditor"]
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "uniqueItems": True
                    },
                    "permissions": {
                        "type": "object",
                        "properties": {
                            "read": {"type": "boolean"},
                            "write": {"type": "boolean"},
                            "delete": {"type": "boolean"},
                            "admin": {"type": "boolean"}
                        },
                        "required": ["read", "write", "delete", "admin"],
                        "additionalProperties": False
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "last_login": {
                                "type": "string",
                                "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$"
                            },
                            "ip_address": {
                                "type": "string",
                                "pattern": "^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$"
                            },
                            "session_id": {"type": "string", "minLength": 32, "maxLength": 128}
                        },
                        "required": ["last_login", "ip_address"],
                        "additionalProperties": False
                    }
                },
                "required": ["user_id", "email", "roles", "permissions", "metadata"],
                "additionalProperties": False
            },
            "request_data": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "query"},
                            "query_string": {"type": "string", "minLength": 1},
                            "filters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {"type": "string"},
                                        "operator": {
                                            "type": "string",
                                            "enum": ["eq", "ne", "gt", "lt", "gte", "lte", "in"]
                                        },
                                        "value": {}
                                    },
                                    "required": ["field", "operator", "value"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["type", "query_string"],
                        "additionalProperties": False
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "const": "mutation"},
                            "action": {
                                "type": "string",
                                "enum": ["create", "update", "delete"]
                            },
                            "entity": {"type": "string", "pattern": "^[A-Z][a-zA-Z0-9]*$"},
                            "data": {"type": "object"}
                        },
                        "required": ["type", "action", "entity", "data"],
                        "additionalProperties": False
                    }
                ]
            },
            "response_metadata": {
                "type": "object",
                "properties": {
                    "status_code": {
                        "type": "integer",
                        "minimum": 100,
                        "maximum": 599
                    },
                    "duration_ms": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 300000
                    },
                    "cache_hit": {"type": "boolean"}
                },
                "required": ["status_code", "duration_ms", "cache_hit"],
                "additionalProperties": False
            },
            "billing": {
                "type": "object",
                "properties": {
                    "cost_usd": {
                        "type": "number",
                        "minimum": 0,
                        "multipleOf": 0.0001
                    },
                    "tokens_used": {"type": "integer", "minimum": 0},
                    "tier": {
                        "type": "string",
                        "enum": ["free", "basic", "pro", "enterprise"]
                    }
                },
                "required": ["cost_usd", "tokens_used", "tier"],
                "additionalProperties": False
            }
        }

        schema = {
            "type": "object",
            "properties": properties,
            "required": [
                "api_key", "request_id", "timestamp", "endpoint", "method",
                "user", "request_data", "response_metadata", "billing"
            ],
            "additionalProperties": False,
        }

        description = (
            "COMPLEX: API request log with 64-char hex api_key, validated request_id/timestamp/endpoint, "
            "nested user (4 levels deep) with roles array/permissions/metadata/IP, "
            "oneOf request_data (query OR mutation with different schemas), "
            "response metadata with status/duration, billing with precise cost"
        )
        return schema, description

    def _generate_extreme_schema(
        self, idx: int, rng: np.random.Generator
    ) -> tuple[dict, str]:
        """Generate extremely difficult schema to stress-test LLMs.

        Features:
        - 5-level deep nesting
        - Strict regex patterns (phone, URL, ISO date, UUID)
        - Multiple enums with specific values
        - Array length constraints
        - Numeric precision (multipleOf)
        - Many required fields at each level
        """
        properties = {
            "transaction_id": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            },
            "timestamp": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$",
            },
            "amount": {
                "type": "number",
                "minimum": 0.01,
                "maximum": 999999.99,
                "multipleOf": 0.01,
            },
            "currency": {
                "type": "string",
                "enum": ["USD", "EUR", "GBP", "JPY", "CNY"],
            },
            "customer": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer", "minimum": 1000000, "maximum": 9999999},
                    "phone": {
                        "type": "string",
                        "pattern": "^\\+1-\\d{3}-\\d{3}-\\d{4}$",
                    },
                    "email": {
                        "type": "string",
                        "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                    },
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string", "minLength": 5, "maxLength": 100},
                            "city": {"type": "string", "minLength": 2, "maxLength": 50},
                            "state": {
                                "type": "string",
                                "enum": ["CA", "NY", "TX", "FL", "IL", "WA", "MA"],
                            },
                            "zip": {"type": "string", "pattern": "^\\d{5}(-\\d{4})?$"},
                            "coordinates": {
                                "type": "object",
                                "properties": {
                                    "latitude": {
                                        "type": "number",
                                        "minimum": -90,
                                        "maximum": 90,
                                    },
                                    "longitude": {
                                        "type": "number",
                                        "minimum": -180,
                                        "maximum": 180,
                                    },
                                },
                                "required": ["latitude", "longitude"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["street", "city", "state", "zip", "coordinates"],
                        "additionalProperties": False,
                    },
                    "verification": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["pending", "verified", "failed", "expired"],
                            },
                            "verified_at": {
                                "type": "string",
                                "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$",
                            },
                            "method": {
                                "type": "string",
                                "enum": ["email", "sms", "phone_call", "document"],
                            },
                        },
                        "required": ["status", "method"],
                        "additionalProperties": False,
                    },
                },
                "required": ["customer_id", "phone", "email", "address", "verification"],
                "additionalProperties": False,
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string", "pattern": "^[A-Z]{3}-\\d{6}$"},
                        "quantity": {"type": "integer", "minimum": 1, "maximum": 100},
                        "unit_price": {
                            "type": "number",
                            "minimum": 0.01,
                            "multipleOf": 0.01,
                        },
                        "category": {
                            "type": "string",
                            "enum": ["electronics", "clothing", "food", "books", "other"],
                        },
                    },
                    "required": ["sku", "quantity", "unit_price", "category"],
                    "additionalProperties": False,
                },
            },
            "payment_method": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["credit_card", "debit_card", "paypal", "bank_transfer"],
                    },
                    "last_four": {"type": "string", "pattern": "^\\d{4}$"},
                    "expiry": {"type": "string", "pattern": "^(0[1-9]|1[0-2])/\\d{2}$"},
                },
                "required": ["type", "last_four"],
                "additionalProperties": False,
            },
        }

        schema = {
            "type": "object",
            "properties": properties,
            "required": [
                "transaction_id",
                "timestamp",
                "amount",
                "currency",
                "customer",
                "items",
                "payment_method",
            ],
            "additionalProperties": False,
        }

        description = (
            "EXTREME: e-commerce transaction with UUID, ISO timestamp, precise amount, "
            "nested customer with phone/email/address/coordinates/verification (5 levels deep), "
            "array of items with SKU pattern, payment method with card details - "
            "multiple strict regex patterns, enums, and numeric constraints throughout"
        )
        return schema, description

    def _create_prompt_text(self, schema: dict, description: str) -> str:
        """Create prompt text from schema.

        Args:
            schema: JSON schema dict
            description: Human-readable description

        Returns:
            Prompt text
        """
        schema_json = json.dumps(schema, indent=2)

        prompt = f"""Generate a valid JSON object that conforms to the following schema.

Description: {description}

Schema:
```json
{schema_json}
```

Output only the JSON object, with no additional text or explanation.
"""
        return prompt

    def __len__(self) -> int:
        return len(self.prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.prompts[idx]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        """Sample a random prompt uniformly."""
        idx = rng.integers(0, len(self.prompts))
        return self.prompts[idx]

    def get_all_prompts(self) -> list[Prompt]:
        """Return all prompts."""
        return self.prompts.copy()

    def __repr__(self) -> str:
        return (
            f"JSONSchemaPromptDataset(n={len(self.prompts)}, "
            f"complexity={self.complexity}, seed={self.seed})"
        )
