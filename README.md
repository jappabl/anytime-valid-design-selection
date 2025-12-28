# Sequential LLM Evaluation with Stratified Sampling

**Status**: Day 1 complete (2025-12-28) - See [TIMELINE.md](TIMELINE.md)

**Contributions**:
1. Stratified sequential evaluation (prevents early-stopping bias)
2. Intersection bounds with α-splitting (20-60% tighter)

## Quick Start

```bash
# Install
pip install -e .

# Run tests
python3 -m pytest tests/ -v

# Run validation experiments (no API key needed)
python3 scripts/validate_coverage.py
python3 scripts/validate_intersection_tightness.py

# Run full experiments (requires API key in .env)
./scripts/run_all_validations.sh
```

## Implementation Status

**Day 1 Complete**:
- ✅ Intersection bounds (`bernoulli_cs_intersection.py`)
- ✅ Stratified sampling (`stratified_json_prompts.py`)
- ✅ Runner integration
- ✅ Experiment scripts
- ✅ 3 pytest test files (436 lines)
- ✅ Documentation

**Validation Complete**:
- ✅ Coverage validated (100% empirical)
- ✅ Tightness validated (47.9% for p ≤ 0.05)
- ⏳ Stratified experiments ready to run (~10 min)

**Audit Preparation**: See [AUDIT_PREP.md](AUDIT_PREP.md) and [EXPERIMENTS.md](EXPERIMENTS.md)

## Documentation

**Audit Materials**:
- **[AUDIT_PREP.md](AUDIT_PREP.md)** - Claims, rebuttals, audit checklist
- **[EXPERIMENTS.md](EXPERIMENTS.md)** - Validation experiments and evidence

**Implementation**:
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for Claude Code
- **[IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)** - Day 1 status + Day 2 tasks
- **[INTERSECTION_BOUNDS_EXPLAINED.md](INTERSECTION_BOUNDS_EXPLAINED.md)** - Algorithm + theory
- **[STRATIFIED_SAMPLING_GUIDE.md](STRATIFIED_SAMPLING_GUIDE.md)** - Algorithm + usage
- **[TEST_EVALUATION.md](TEST_EVALUATION.md)** - Test effectiveness analysis

## Algorithms

**Intersection Bounds**:
- Combines Hoeffding + Bernstein with α-splitting
- 40-60% tighter for low p (strong models)
- Time-uniform validity maintained

**Stratified Sampling**:
- Round-robin across 4 difficulty strata
- Prevents early-stopping bias
- Guarantees balanced representation

## File Structure

```
research/
├── src/eval_harness/
│   ├── stats/                 # bernoulli_cs.py, bernoulli_cs_intersection.py, stopping.py
│   ├── prompts/               # stratified_json_prompts.py, json_schema_prompts.py
│   ├── core/                  # runner.py, config.py
│   ├── sampling/              # openai_sampler.py, gemini_sampler.py, groq_sampler.py
│   └── validators/            # json_schema.py, sql_validator.py
├── tests/                     # test_stopping.py, test_toy_model.py, test_validators.py
├── configs/                   # stratified_gpt4mini_{naive,stratified}.yaml
├── run_stratified_experiments.py
├── analyze_stratified_results.py
└── docs/                      # CLAUDE.md, IMPLEMENTATION_COMPLETE.md, etc.
```
