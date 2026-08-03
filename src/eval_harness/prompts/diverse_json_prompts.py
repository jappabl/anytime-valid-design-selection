"""Diverse stratified JSON schema prompts for real-LLM evaluation.

Unlike easy_json_prompts.py (which has only 6 fixed templates), every prompt
here is a distinct randomly-composed schema. Difficulty is controlled
STRUCTURALLY per stratum, not by hand-tuning individual templates:

- simple:  3-4 flat fields, 1 easy pattern, additionalProperties: false
- medium:  4-6 flat fields, 2 patterns + enum, integer bounds
- complex: 5-6 fields incl. 1 nested object, 3 patterns, strict nesting
- extreme: 2-level nesting + array of objects, 4+ patterns incl. exact-length
           strings and multipleOf constraints

All generation is seeded and deterministic. Prompts within a dataset are
deduplicated by text, so at temperature=0 each prompt is a distinct
(deterministic) trial from the model.
"""

import json
from typing import Literal

import numpy as np

from eval_harness.core.types import Prompt

Complexity = Literal["simple", "medium", "complex", "extreme"]

# Word pools for field/entity names (combined multiplicatively for diversity)
_ENTITIES = [
    "user", "order", "device", "shipment", "ticket", "account", "sensor",
    "booking", "invoice", "product", "employee", "vehicle", "package",
    "session", "payment", "warehouse", "customer", "contract", "license",
    "reservation",
]

_ID_FIELDS = ["id", "code", "ref", "key", "number", "tag"]

_ENUM_POOLS = [
    ["pending", "active", "closed", "archived"],
    ["low", "medium", "high", "critical"],
    ["draft", "submitted", "approved", "rejected"],
    ["bronze", "silver", "gold", "platinum"],
    ["north", "south", "east", "west"],
    ["daily", "weekly", "monthly", "yearly"],
]

_STR_FIELDS = ["name", "label", "title", "owner", "region", "category"]
_INT_FIELDS = ["count", "quantity", "priority", "capacity", "level", "score"]
_NUM_FIELDS = ["price", "weight", "amount", "rate", "balance", "total"]
_BOOL_FIELDS = ["active", "verified", "enabled", "archived", "flagged"]


def _letters(rng: np.random.Generator, k: int) -> str:
    return "".join(chr(ord("A") + int(c)) for c in rng.integers(0, 26, k))


class DiverseJSONSchemaDataset:
    """Randomly-composed JSON schemas at a fixed difficulty level."""

    def __init__(
        self,
        n_prompts: int = 250,
        complexity: Complexity = "medium",
        seed: int = 42,
    ):
        self.n_prompts = n_prompts
        self.complexity = complexity
        self.seed = seed
        self.prompts = self._generate_prompts()

    # ------------------------------------------------------------------
    # Field factories (each returns (name, subschema))
    # ------------------------------------------------------------------

    def _pattern_field(self, rng: np.random.Generator, hard: bool) -> tuple:
        """ID-like string field with an anchored regex pattern."""
        name = f"{rng.choice(_ENTITIES)}_{rng.choice(_ID_FIELDS)}"
        prefix = _letters(rng, int(rng.integers(2, 5)))
        n_digits = int(rng.integers(3, 7)) if not hard else int(rng.integers(7, 12))
        sep = str(rng.choice(["-", "_", ""]))
        if hard and rng.random() < 0.5:
            # multi-group pattern: PREFIX-1234-xy style
            n_lower = int(rng.integers(2, 4))
            pattern = f"^{prefix}{sep}[0-9]{{{n_digits}}}{sep}[a-z]{{{n_lower}}}$"
        else:
            pattern = f"^{prefix}{sep}[0-9]{{{n_digits}}}$"
        return name, {"type": "string", "pattern": pattern}

    def _date_field(self, rng: np.random.Generator, timestamp: bool) -> tuple:
        if timestamp:
            return "timestamp", {
                "type": "string",
                "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$",
            }
        name = str(rng.choice(["created_date", "due_date", "start_date", "end_date"]))
        return name, {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}

    def _enum_field(self, rng: np.random.Generator) -> tuple:
        name = str(rng.choice(["status", "tier", "zone", "cadence", "stage"]))
        pool = _ENUM_POOLS[int(rng.integers(0, len(_ENUM_POOLS)))]
        k = int(rng.integers(3, len(pool) + 1))
        values = list(rng.choice(pool, size=k, replace=False))
        return name, {"type": "string", "enum": sorted(values)}

    def _string_field(self, rng: np.random.Generator, exact_length: bool) -> tuple:
        name = str(rng.choice(_STR_FIELDS))
        if exact_length:
            n = int(rng.integers(8, 15))
            return name, {"type": "string", "minLength": n, "maxLength": n}
        return name, {"type": "string", "minLength": int(rng.integers(2, 5))}

    def _int_field(self, rng: np.random.Generator) -> tuple:
        name = str(rng.choice(_INT_FIELDS))
        lo = int(rng.integers(0, 10))
        hi = lo + int(rng.integers(5, 500))
        return name, {"type": "integer", "minimum": lo, "maximum": hi}

    def _number_field(self, rng: np.random.Generator, multiple_of: bool) -> tuple:
        name = str(rng.choice(_NUM_FIELDS))
        schema = {"type": "number", "minimum": 0.01, "maximum": float(rng.integers(100, 100000))}
        if multiple_of:
            schema["multipleOf"] = float(rng.choice([0.25, 0.05, 0.5]))
        return name, schema

    def _bool_field(self, rng: np.random.Generator) -> tuple:
        return str(rng.choice(_BOOL_FIELDS)), {"type": "boolean"}

    # ------------------------------------------------------------------
    # Object composers
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble(fields: list, required_all: bool, rng: np.random.Generator) -> dict:
        props = {}
        for name, sub in fields:
            # Dedupe field names within one object
            base, i = name, 2
            while name in props:
                name = f"{base}_{i}"
                i += 1
            props[name] = sub
        names = list(props.keys())
        if required_all:
            required = names
        else:
            n_req = max(2, len(names) - int(rng.integers(0, 2)))
            required = sorted(rng.choice(names, size=n_req, replace=False))
        return {
            "type": "object",
            "properties": props,
            "required": list(required),
            "additionalProperties": False,
        }

    def _nested_object(self, rng: np.random.Generator, hard: bool) -> tuple:
        name = str(rng.choice(["address", "contact", "vendor", "location", "meta"]))
        fields = [
            self._pattern_field(rng, hard=hard),
            self._string_field(rng, exact_length=False),
        ]
        if hard:
            fields.append(self._date_field(rng, timestamp=bool(rng.random() < 0.5)))
        else:
            fields.append(self._bool_field(rng))
        return name, self._assemble(fields, required_all=True, rng=rng)

    def _array_field(self, rng: np.random.Generator) -> tuple:
        name = str(rng.choice(["items", "entries", "line_items", "events"]))
        item_fields = [
            self._pattern_field(rng, hard=False),
            self._int_field(rng),
        ]
        return name, {
            "type": "array",
            "items": self._assemble(item_fields, required_all=True, rng=rng),
            "minItems": int(rng.integers(1, 3)),
            "maxItems": int(rng.integers(3, 8)),
        }

    # ------------------------------------------------------------------
    # Stratum-level schema composition
    # ------------------------------------------------------------------

    def _generate_schema(self, rng: np.random.Generator) -> dict:
        c = self.complexity
        if c == "simple":
            fields = [
                self._pattern_field(rng, hard=False),
                self._string_field(rng, exact_length=False),
                self._int_field(rng),
            ]
            if rng.random() < 0.5:
                fields.append(self._bool_field(rng))
            return self._assemble(fields, required_all=True, rng=rng)

        if c == "medium":
            fields = [
                self._pattern_field(rng, hard=False),
                self._date_field(rng, timestamp=False),
                self._enum_field(rng),
                self._number_field(rng, multiple_of=False),
            ]
            if rng.random() < 0.5:
                fields.append(self._int_field(rng))
            if rng.random() < 0.5:
                fields.append(self._bool_field(rng))
            return self._assemble(fields, required_all=True, rng=rng)

        if c == "complex":
            fields = [
                self._pattern_field(rng, hard=True),
                self._date_field(rng, timestamp=False),
                self._enum_field(rng),
                self._nested_object(rng, hard=False),
                self._int_field(rng),
            ]
            if rng.random() < 0.5:
                fields.append(self._number_field(rng, multiple_of=False))
            return self._assemble(fields, required_all=True, rng=rng)

        # extreme
        fields = [
            self._pattern_field(rng, hard=True),
            self._date_field(rng, timestamp=True),
            self._string_field(rng, exact_length=True),
            self._number_field(rng, multiple_of=True),
            self._nested_object(rng, hard=True),
            self._array_field(rng),
        ]
        return self._assemble(fields, required_all=True, rng=rng)

    def _create_prompt_text(self, schema: dict) -> str:
        schema_json = json.dumps(schema, indent=2)
        field_list = ", ".join(schema["properties"].keys())
        return f"""Generate a valid JSON object with fields: {field_list}.

The JSON must conform to this schema:

{schema_json}

Generate only the JSON object, with no additional text or explanation."""

    def _generate_prompts(self) -> list:
        rng = np.random.default_rng(self.seed)
        prompts = []
        seen = set()
        attempts = 0
        max_attempts = self.n_prompts * 50

        while len(prompts) < self.n_prompts and attempts < max_attempts:
            attempts += 1
            schema = self._generate_schema(rng)
            text = self._create_prompt_text(schema)
            if text in seen:
                continue
            seen.add(text)
            prompts.append(
                Prompt(
                    id=f"diverse_json_{self.complexity}_{len(prompts):04d}",
                    text=text,
                    metadata={"schema": schema, "complexity": self.complexity},
                )
            )

        if len(prompts) < self.n_prompts:
            raise ValueError(
                f"Could only generate {len(prompts)} unique prompts "
                f"for stratum '{self.complexity}' (requested {self.n_prompts})"
            )
        return prompts

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        return self.prompts[int(rng.integers(0, len(self.prompts)))]

    def get_all_prompts(self) -> list:
        return self.prompts.copy()

    def __len__(self) -> int:
        return len(self.prompts)

    def __getitem__(self, idx: int) -> Prompt:
        return self.prompts[idx]


class StratifiedDiverseJSONDataset:
    """Four difficulty strata of diverse schemas (simple/medium/complex/extreme)."""

    STRATA = ["simple", "medium", "complex", "extreme"]
    STRATUM_SEED_OFFSETS = {"simple": 0, "medium": 1000, "complex": 2000, "extreme": 3000}

    def __init__(self, prompts_per_stratum: int = 250, seed: int = 42):
        self.prompts_per_stratum = prompts_per_stratum
        self.seed = seed
        self.datasets = {
            stratum: DiverseJSONSchemaDataset(
                n_prompts=prompts_per_stratum,
                complexity=stratum,
                seed=seed + self.STRATUM_SEED_OFFSETS[stratum],
            )
            for stratum in self.STRATA
        }

    def get_stratum_prompts(self, stratum: str) -> list:
        return self.datasets[stratum].get_all_prompts()

    def get_prompt_stratum(self, prompt: Prompt) -> str:
        return prompt.metadata["complexity"]

    def sample_uniform(self, rng: np.random.Generator) -> Prompt:
        stratum = self.STRATA[int(rng.integers(0, len(self.STRATA)))]
        return self.datasets[stratum].sample_uniform(rng)

    def get_all_prompts(self) -> list:
        return [p for s in self.STRATA for p in self.datasets[s].get_all_prompts()]

    def __len__(self) -> int:
        return sum(len(d) for d in self.datasets.values())
