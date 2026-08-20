# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
You are a senior software engineer writing production-quality code and tests.

GLOBAL RULES (HARD CONSTRAINTS)
- Do exactly what is requested. Do not add demonstrations, explanations, banners, or commentary unless explicitly asked.
- Never write scripts disguised as tests.
- Never include print statements, logging for demonstration, or manual execution blocks.
- Never modify import paths, environment variables, or runtime state to "make things work".
- Never assume properties that are not guaranteed by a formal specification or by explicit instructions.
- If a property is uncertain, test only invariants that must hold.
- All outputs must be deterministic and reproducible.
- **NEVER add Claude/Anthropic attribution to git commits** - All work should be attributed to the user only. Do not include "Generated with Claude Code", "Co-Authored-By: Claude", or similar attributions in commit messages.

TEST-SPECIFIC RULES
- Use the project’s standard test framework only (e.g., pytest).
- Tests must be silent: no console output under normal execution.
- Tests must fail only for real regressions, not for stylistic or heuristic reasons.
- Do not assert “improvements”, “tightness”, “better performance”, or probabilistic dominance unless mathematically guaranteed.
- Prefer invariant-based tests (bounds, monotonicity, determinism, idempotence) over numeric snapshots.
- Avoid hard-coding numeric values unless they are part of the public API contract.

CODE QUALITY RULES
- Keep each unit of code single-purpose.
- Do not introduce unused abstractions or speculative features.
- Avoid cleverness; prefer clarity and explicitness.
- Do not infer undocumented behavior. If behavior is unclear, choose the most conservative interpretation.

OUTPUT RULES
- Output only what was requested (e.g., code only).
- Do not include explanations, summaries, or justifications unless explicitly asked.
- Do not restate the prompt or describe your reasoning.

FAIL-SAFE BEHAVIOR
- If the request would require guessing unstated assumptions, stop and ask for clarification.
- If a claim cannot be proven from the specification, do not encode it as a test.

COLLABORATION RULES
- Don't be afraid to make rebuttals or disagree with the user if you genuinely believe they are wrong.
- Only disagree based on logical reasoning, evidence, or technical correctness—not subjective preferences.
- When you disagree, explain your reasoning clearly and propose alternatives.
- Respectfully point out logical inconsistencies, technical errors, or claims unsupported by evidence.
- If uncertain, express your concerns and ask clarifying questions rather than silently implementing something questionable.

README SYNCHRONIZATION
- README.md is the public face of the repo. Whenever research progress lands
  (a new result, a corrected claim, a new artifact, a status change), update
  README.md in the same commit or the immediately following one — headline
  table, status section, and layout notes must never lag the audit trail.
- README numbers defer to AUDIT_PREP.md; on any conflict, fix README.
- PUBLIC REPO: github.com/jappabl/anytime-valid-design-selection carries the
  FULL commit history, published via scripts/publish_sync.sh which filters on
  the way out: .env dropped from all commits, the old key string scrubbed,
  and author identity rewritten hlincontacts@gmail.com -> haogotmilk@gmail.com
  (hlincontacts is linked to the wrong GitHub account — never let it appear
  in public commits; repo-local git config already sets haogotmilk). NEVER
  push the local repo directly; always go through publish_sync.sh (it has
  hard key/identity guards). After milestone commits + README update, run it.

DOCUMENTATION SYNCHRONIZATION
- Whenever research claims, contributions, or experimental results are changed, AUDIT_PREP.md MUST be updated to reflect those changes.
- AUDIT_PREP.md is the single source of truth for the audit trail and must remain consistent with all other documentation.
- If you modify claims in code, tests, or other docs (EXPERIMENTS.md, TECHNICAL_SPEC.md, etc.), immediately check if AUDIT_PREP.md needs updating.
- Document withdrawn claims explicitly with ❌ status and explain what invalidated them.
- Document validated claims with ✅ status and link to supporting evidence.

## Project Overview

**Anytime-Valid Sequential Evaluation for LLM Failure Rates** - A rigorous evaluation harness for estimating LLM failure probabilities with sample-efficient sequential testing and time-uniform confidence sequences.

**Key innovations**:
1. **Stratified Sequential Evaluation**: Prevents composition drift under early stopping with heterogeneous prompts (MAIN CONTRIBUTION)
2. ~~**Intersection Bounds**~~: WITHDRAWN after bug fix—provides no benefit in our experimental regime (n ≤ 200)

**Status**: Implementation complete, all critical bugs fixed, ready for audit review.

---

## Common Commands

### Installation
```bash
# With Poetry (recommended)
poetry install

# Or with pip
pip install -e .
```

### Running Tests
```bash
# All tests
python3 -m pytest tests/ -v

# Specific test file
python3 test_intersection_coverage.py
python3 test_stratified_sampling.py

# With coverage
poetry run pytest tests/ --cov=eval_harness --cov-report=html
```

### Running Experiments

**Stratified experiments (for paper)**:
```bash
# Set API key
export OPENAI_API_KEY="your-key"

# Run both naive and stratified experiments
python3 run_stratified_experiments.py

# Analyze results
python3 analyze_stratified_results.py
```

**Single experiment**:
```bash
# Via CLI (if installed with poetry)
eval-harness run configs/stratified_gpt4mini_stratified.yaml

# Or directly
python3 -c "from eval_harness.core.runner import ExperimentRunner; ..."
```

### Code Quality
```bash
# Format
poetry run black src/ tests/

# Lint
poetry run ruff src/ tests/

# Type check
poetry run mypy src/
```

---

## Architecture Overview

### Core Design Pattern

The harness follows a **plugin architecture** with four main components:

```
Runner orchestrates:
  ├─ Sampler (LLM API) → generates completions
  ├─ Validator (pass/fail checker) → binary outcomes
  ├─ Confidence Sequence (stats) → time-uniform bounds
  └─ Storage (SQLite) → resumable state
```

**Key invariant**: The runner never "sees" the model—it only sees binary outcomes (pass/fail). This ensures statistical rigor (no data-dependent decisions based on model internals).

### Module Structure

```
src/eval_harness/
├── core/
│   ├── runner.py          # Orchestration + resumability
│   ├── config.py          # Pydantic schemas for YAML configs
│   └── types.py           # Shared types (Sample, Prompt, etc.)
├── stats/
│   ├── bernoulli_cs.py                # Hoeffding time-uniform CS (baseline)
│   ├── bernoulli_cs_intersection.py   # Hoeffding ∩ Bernstein with α-splitting
│   └── stopping.py                    # Sequential stopping criteria
├── sampling/
│   ├── base.py            # Sampler interface
│   ├── toy_sampler.py     # Synthetic Bernoulli (for validation)
│   ├── openai_sampler.py  # OpenAI API
│   ├── gemini_sampler.py  # Google Gemini API
│   └── groq_sampler.py    # Groq API
├── validators/
│   ├── base.py            # Validator interface
│   ├── json_schema.py     # JSON parsing + schema validation
│   └── sql_validator.py   # SQL syntax validation
├── prompts/
│   ├── base.py                      # PromptDataset interface
│   ├── json_schema_prompts.py       # Random JSON schema generation
│   ├── stratified_json_prompts.py   # Stratified by complexity (4 strata)
│   └── sql_prompts.py               # SQL query templates
└── storage/
    └── store.py           # SQLite with resumability
```

---

## Critical Concepts

### 1. Time-Uniform Confidence Sequences

**Problem**: Traditional confidence intervals break under "peeking" (checking results before N is fixed).

**Solution**: Confidence sequences remain valid at ALL stopping times n ∈ {1, ..., n_max}.

**Implementation**: We use **finite-horizon stitching**:
```python
δ_n = α / (n * (n + 1))  # Stitching for time-uniform validity
```

This is implemented in both:
- `bernoulli_cs.py` (Hoeffding-only baseline)
- `bernoulli_cs_intersection.py` (optimized intersection bounds)

**Why it matters**: Allows optional stopping without p-hacking. The CI coverage guarantee holds no matter when you stop.

### 2. Intersection Bounds with α-Splitting

**Key insight**: Don't choose between Hoeffding and Bernstein—run BOTH in parallel with α/2 each, then take the intersection.

```python
# WRONG (data-dependent switching - breaks coverage!)
epsilon = min(eps_hoeffding, eps_bernstein)

# CORRECT (α-splitting + intersection)
ci_h = hoeffding_bounds(α/2)
ci_b = bernstein_bounds(α/2)
ci_final = [max(ci_h[0], ci_b[0]), min(ci_h[1], ci_b[1])]
```

**File**: `src/eval_harness/stats/bernoulli_cs_intersection.py`

**Why it works**: Bonferroni union bound ensures P(p ∈ CI_h ∩ CI_b) ≥ 1 - α

**Performance**: 40-60% tighter bounds for low p (strong models), ~3% worse for p ≈ 0.5 (rare).

**Documentation**: See `INTERSECTION_BOUNDS_EXPLAINED.md` for full derivation.

### 3. Stratified Sequential Evaluation

**Problem**: Naive uniform sampling + sequential stopping can exhibit **early-stopping bias** when prompts have heterogeneous difficulty.

**Example**:
- 25% simple prompts (p=0.01), 25% medium (p=0.05), 25% complex (p=0.10), 25% extreme (p=0.20)
- Naive sampling might oversample easy prompts early → underestimate overall p → stop too early with biased estimate

**Solution**: **Stratified sampling** with round-robin allocation ensures perfect balance across strata.

**Files**:
- `src/eval_harness/prompts/stratified_json_prompts.py`:
  - `StratifiedJSONSchemaDataset`: Defines 4 difficulty strata
  - `StratifiedSampler`: Round-robin balanced sampling
  - `NaiveSampler`: Baseline uniform random sampling

**Key property**: E[p̂_stratified | stop at n] = p (unbiased), whereas E[p̂_naive | stop at n] can be biased.

**Documentation**: See `STRATIFIED_SAMPLING_GUIDE.md` for algorithm details.

### 4. Stopping Criteria

The harness supports THREE stopping criteria (configured via `StoppingConfig`):

1. **Precision stopping**: Stop when CI width ≤ target (e.g., 0.20)
2. **Certification stopping**: Stop when upper bound ≤ threshold (e.g., 0.15)
3. **Budget cap**: Hard limit on max_samples

**Important**: Always enforce `min_samples` to prevent premature stopping.

**Realistic targets for time-uniform bounds**:
- Precision: width ≤ 0.20 (NOT 0.05—that requires >500 samples!)
- Certification: p ≤ 0.15 (depends on use case)
- Min samples: 50-100

**File**: `src/eval_harness/stats/stopping.py`

### 5. Resumability

**Key design**: Experiments can be interrupted and resumed from checkpoint.

**How it works**:
1. All samples stored in SQLite (`storage/store.py`)
2. On restart, runner replays all outcomes to restore CS state:
   ```python
   for _ in range(n_failures):
       cs.update(True)
   for _ in range(n_samples - n_failures):
       cs.update(False)
   ```
3. Continues from where it left off

**Important**: The confidence sequence state is ONLY the count (n_samples, n_failures). No complex state to serialize.

---

## Adding New Components

### Adding a New Sampler

1. Subclass `Sampler` from `sampling/base.py`
2. Implement `sample(prompt: Prompt, decoding: DecodingConfig) -> str`
3. Register in `runner.py`'s `_create_sampler()` method
4. Add to `SamplerConfig.type` literal in `config.py`

**Example**: See `openai_sampler.py`, `gemini_sampler.py`, `groq_sampler.py`

### Adding a New Validator

1. Subclass `Validator` from `validators/base.py`
2. Implement `validate(generation: str, sample_id: str, **kwargs) -> ValidationResult`
3. Register in `runner.py`'s `_create_validator()` method
4. Add to `ValidatorConfig.type` literal in `config.py`

**Example**: See `json_schema.py`, `sql_validator.py`

### Adding a New Prompt Dataset

1. Subclass `PromptDataset` from `prompts/base.py`
2. Implement:
   - `sample_uniform(rng) -> Prompt`
   - `get_all_prompts() -> List[Prompt]`
3. Register in `runner.py`'s `_create_prompts()` method
4. Add to `PromptConfig.type` literal in `config.py`

**Example**: See `stratified_json_prompts.py`, `sql_prompts.py`

---

## Statistical Validity Checklist

When modifying stats code, ensure these properties hold:

### Time-Uniform Validity
- [ ] CI coverage ≥ 1-α for ALL n ∈ {1, ..., n_max} (not just n_max)
- [ ] Test via Monte Carlo: Run 500+ replications, check coverage at multiple n

### No Data-Dependent Switching
- [ ] Any "choice" between methods must use α-splitting
- [ ] Never select bound based on observed p̂ without splitting α

### Stopping Rules
- [ ] Stopping decision only depends on CS bounds (not raw data)
- [ ] Min samples enforced before allowing stop
- [ ] Max samples enforced (budget cap)

### Resumability
- [ ] CS state can be reconstructed via replay of outcomes
- [ ] No hidden state besides (n, failures)

**Validation tests**: See `test_intersection_coverage.py`, `test_statistical_validation.py`

---

## Configuration Files

### Experiment Config Structure (YAML)

```yaml
name: "experiment_name"

sampler:
  type: "openai"  # or "gemini", "groq", "toy"
  model_id: "gpt-4o-mini"
  api_key: null  # or set OPENAI_API_KEY env var

validator:
  type: "json_schema"  # or "sql"

prompts:
  type: "stratified_json"  # or "json_schema", "sql"
  prompts_per_stratum: 25  # For stratified: 25 × 4 strata = 100 total
  sampling_mode: "stratified"  # or "naive"
  seed: 42

decoding:
  temperature: 0.0
  max_tokens: 500
  top_p: 1.0

stopping:
  precision_target: 0.20  # Realistic for time-uniform bounds
  certification_threshold: 0.15  # One-sided upper bound
  min_samples: 50
  max_samples: 100

statistics:
  alpha: 0.05  # 95% confidence

seed: 42
```

### Key Config Files

- **Stratified experiments**: `configs/stratified_gpt4mini_{naive,stratified}.yaml`
- Both use SAME prompts, model, stopping criteria
- Only difference: `sampling_mode: "naive"` vs `"stratified"`

---

## Testing Strategy

### Unit Tests
- `tests/test_validators.py`: Validator logic
- `tests/test_stopping.py`: Stopping criteria

### Statistical Validation
- `tests/test_toy_model.py`: Coverage validation on synthetic data
- `tests/test_statistical_validation.py`: CS properties

### Integration Tests
- `test_intersection_coverage.py`: 500 MC replications, validates coverage ≥ 95%
- `test_intersection_integration.py`: Interface compatibility
- `test_stratified_sampling.py`: Balance validation (variance = 0 for stratified)

### Running Tests Without Poetry

Many test files are standalone scripts that can be run directly:
```bash
python3 test_intersection_coverage.py
python3 test_stratified_sampling.py
python3 analyze_stratified_results.py
```

This is intentional—makes validation easy without needing the full package installed.

---

## Common Pitfalls

### 1. Don't Use Fixed-n Confidence Intervals

**WRONG**:
```python
# This breaks under sequential stopping!
from scipy.stats import beta
ci = beta.interval(0.95, failures+1, successes+1)
```

**RIGHT**:
```python
# Time-uniform confidence sequence
from eval_harness.stats.bernoulli_cs_intersection import BernoulliCSIntersection
cs = BernoulliCSIntersection(alpha=0.05, n_max=100)
```

### 2. Don't Modify CS State Directly

**WRONG**:
```python
cs.failures = 5
cs.trials = 10
```

**RIGHT**:
```python
# Always update via replay
for _ in range(5):
    cs.update(True)  # failure
for _ in range(5):
    cs.update(False)  # success
```

### 3. Realistic Stopping Targets

Time-uniform bounds are 3-10× wider than fixed-n intervals. Use realistic targets:

- ✅ `precision_target: 0.20` (achievable with ~100 samples)
- ❌ `precision_target: 0.05` (requires >500 samples)

### 4. Stratum Metadata Tracking

When using stratified sampling, the runner tracks stratum in sample metadata:
```python
# In runner.py
if self.prompt_sampler:
    stratum, prompt = self.prompt_sampler.sample_next()
    # Store stratum in sample metadata for analysis
```

Don't break this tracking—it's needed for `analyze_stratified_results.py`.

---

## Key Documentation Files

**Must read for understanding the system**:
- `INTERSECTION_BOUNDS_EXPLAINED.md`: Full derivation of α-splitting approach
- `STRATIFIED_SAMPLING_GUIDE.md`: Algorithm, motivation, expected results
- `IMPLEMENTATION_COMPLETE.md`: Deliverables checklist for workshop paper

**Quick reference**:
- `README.md`: High-level overview
- `QUICKSTART.md`: Installation and first experiments

**Historical context** (can skip):
- Various `*_FIX.md`, `*_ISSUE.md` files document the evolution of the implementation

---

## For Workshop Paper

**Main contribution**: Stratified sequential evaluation prevents early-stopping bias

**Secondary contribution**: Intersection bounds save 20-40% samples for strong models

**Experiments to run**:
1. Both naive and stratified on GPT-4o-mini with JSON schema task
2. Show heterogeneity exists (per-stratum failure rates differ)
3. Show naive exhibits imbalance, stratified maintains perfect balance
4. Show both maintain time-uniform validity

**Scripts**:
- `run_stratified_experiments.py`: Runs both experiments
- `analyze_stratified_results.py`: Compares results and computes metrics

**Expected result**: |p̂_naive - p̂_stratified| > 0.01 in some runs (demonstrates bias), variance = 0 for stratified vs >0 for naive.

---

## Notes on Current State

**What's complete**:
- ✅ All core statistics (Hoeffding, Bernstein, intersection with α-splitting)
- ✅ Stratified sampling (4 difficulty strata)
- ✅ OpenAI, Gemini, Groq samplers
- ✅ JSON schema and SQL validators
- ✅ Full resumability via SQLite
- ✅ All validation tests passing
- ✅ Comprehensive documentation

**What's ready to run**:
- Experiments just need API keys
- All configs use realistic stopping targets
- Analysis scripts are ready

**What's NOT implemented**:
- vLLM sampler (mentioned in docs but not implemented)
- CLI is minimal (most usage is via direct script execution)
