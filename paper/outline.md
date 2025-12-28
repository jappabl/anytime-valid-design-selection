# Sample-Efficient Sequential Evaluation of Stochastic LLM Failure Rates

**Workshop Paper Outline (4 pages)**

---

## Abstract (150 words)

- **Problem**: LLM evaluation typically uses fixed sample sizes, wasting resources when failure rates are clear early or providing insufficient precision when needed.
- **Solution**: Anytime-valid confidence sequences with sequential stopping rules for sample-efficient failure probability estimation.
- **Method**: Betting-based confidence sequences for Bernoulli outcomes; precision and certification stopping criteria.
- **Experiments**: Evaluate on JSON schema generation tasks with objective validators.
- **Results**: Achieve X% cost savings vs fixed-N baselines while maintaining valid statistical guarantees; certify failure rates below thresholds with high confidence.
- **Impact**: Enables more efficient LLM evaluation with rigorous statistical foundations.

---

## 1. Introduction (0.75 pages)

### 1.1 Motivation
- LLMs are inherently stochastic (temperature, sampling)
- Need to estimate **failure probabilities** p_fail for safety-critical tasks
- Traditional approach: fixed N samples → compute empirical rate + CI
- Problems:
  - Wastes samples when p clearly high or low
  - Lacks principled stopping rules
  - Post-hoc peeking invalidates inference

### 1.2 Our Approach
- **Anytime-valid confidence sequences** (CS): valid at all stopping times
- **Sequential stopping rules**:
  - Precision: stop when CI width ≤ ε
  - Certification: stop when upper bound ≤ τ
- No p-hacking, valid under optional stopping

### 1.3 Contributions
1. Evaluation harness with anytime-valid CS for failure rates
2. Sequential stopping with precision/certification criteria
3. Empirical demonstration of X× sample savings on constraint tasks
4. Open-source reproducible framework

---

## 2. Background & Related Work (0.5 pages)

### 2.1 LLM Evaluation
- Standard practice: fixed N samples, Wilson/Clopper-Pearson CI
- Problem: no adaptive stopping, no guarantee under peeking

### 2.2 Sequential Analysis
- Classic: SPRT (Wald 1945), group sequential testing
- Modern: Anytime-valid inference, confidence sequences
- Betting-based CS (Waudby-Smith & Ramdas 2020+)
- Applications: A/B testing, clinical trials

### 2.3 Gap
- No prior work applying anytime-valid CS to LLM failure rate estimation
- Our contribution: principled sequential evaluation for stochastic LLMs

---

## 3. Method (1.5 pages)

### 3.1 Problem Setup
- **Task**: Estimate p_fail for (model, task, decoding config)
- **Outcome**: Binary pass/fail from objective validator
- **Goal**: Minimize sample cost while achieving:
  - Precision: CI width ≤ ε
  - Certification: UCB(p) ≤ τ with confidence 1-α

### 3.2 Anytime-Valid Confidence Sequences
- Definition: CS(t) valid for all t (no multiplicity correction)
- **Betting-based CS for Bernoulli**:
  - Construct via test martingales
  - Bounds: (L_t, U_t) where P(∀t: p ∈ [L_t, U_t]) ≥ 1-α
  - Properties: width decreases as O(1/√n), valid under optional stopping

**Equations**:
```
L_t = p̂_t - sqrt((p̂_t(1-p̂_t)log(2/α))/t) - log(2/α)/(3t)
U_t = p̂_t + sqrt((p̂_t(1-p̂_t)log(2/α))/t) + log(2/α)/(3t)
```

### 3.3 Sequential Stopping Rules
1. **Precision stopping**: Stop when U_t - L_t ≤ ε
2. **Certification stopping**: Stop when U_t ≤ τ
3. **Budget cap**: Stop at t_max
4. **Minimum samples**: Require t ≥ t_min before stopping

### 3.4 Implementation
- Modular architecture: samplers, validators, stats, storage
- Resumable experiments (SQLite)
- Deterministic experiment IDs from config hash

---

## 4. Experiments (1 page)

### 4.1 Evaluation Setting
- **Task**: JSON schema generation
- **Validator**: Parse + jsonschema validation
- **Complexity levels**: simple (flat), medium (nested), complex (constraints)
- **Models**: [TBD - toy models for validation, real models if available]
- **Decoding configs**: temp ∈ {0.0, 0.7, 1.0}

### 4.2 Experimental Design
- **Conditions**: 6 (3 complexity × 2 temps, or multiple models)
- **Baselines**: Fixed-N with N ∈ {100, 500, 1000}
- **Sequential**: ε=0.01, α=0.05, t_min=30, t_max=2000
- **Metrics**:
  - Sample cost to achieve target precision
  - Coverage (CS contains true p)
  - Stopping time distribution

### 4.3 Validation with Toy Model
- Synthetic Bernoulli(p) to verify CS coverage
- Confirm nominal 95% coverage across p ∈ {0.01, 0.05, 0.1, 0.3}

---

## 5. Results (0.75 pages)

### 5.1 Statistical Validity
- Toy model: 95% coverage achieved (Table 1)
- CS width decreases as expected

### 5.2 Sample Efficiency
- **Main result**: Sequential achieves ε=0.01 with median N_seq samples
- Fixed-N requires N=1000 to guarantee ε≤0.01
- **Cost savings**: X× reduction (Table 2, Figure 1)

### 5.3 Certification
- Certify p_fail ≤ 0.01 with N_cert samples (vs N_fixed for fixed approach)

### 5.4 Stopping Time Distributions
- Histogram of stopping times across runs (Figure 2)
- Show variability, early stopping when p clearly high/low

---

## 6. Discussion & Limitations (0.3 pages)

### Limitations
- Binary outcomes only (not rankings or continuous)
- Assumes i.i.d. samples within condition
- No adaptive prompt selection (future work)
- Does not handle multiple testing explicitly (can extend with Bonferroni)

### Future Work
- Extend to pairwise comparisons (CS for difference p_A - p_B)
- Adaptive sampling over prompts (Thompson, UCB)
- Integration with LLM judges (if can treat as noisy validator)

---

## 7. Conclusion (0.2 pages)

- Sequential evaluation with anytime-valid CS enables sample-efficient failure rate estimation
- Demonstrates X× cost savings while maintaining rigorous guarantees
- Open framework supports reproducible research
- Enables more efficient LLM safety evaluation

---

## Figures & Tables

**Figure 1**: Cost curves (CI width vs N) for sequential vs fixed baselines
**Figure 2**: Stopping time histogram
**Table 1**: Coverage validation on toy model
**Table 2**: Sample cost comparison (sequential vs fixed-N)
**Table 3**: Failure rate estimates with CS for real tasks

---

## References (preliminary)

- Waudby-Smith & Ramdas (2020+): Betting-based confidence sequences
- Howard et al. (2021): Time-uniform confidence sequences
- Wald (1945): Sequential analysis
- Wilson (1927): Score confidence intervals
- Relevant LLM evaluation papers (TBD)

---

## Appendix (if space)

- Full experimental configs
- Additional plots (per-task breakdown)
- Implementation details
