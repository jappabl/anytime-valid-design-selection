# The Certification-Overhead Law (conjecture + evidence)

**Status: empirical law with frozen out-of-sample test pending.**
Provisional fits below use only medians already committed in
results\_\*.txt; the rate definitions and predictions were FROZEN
(2026-08-11, in [scripts/fit_overhead_law.py](scripts/fit_overhead_law.py))
before the definitive τ-sweep grid
([scripts/run_overhead_law.py](scripts/run_overhead_law.py)) completed,
making that grid a genuine out-of-sample test.

## The law

For an e-process certification method stopping when its statistic
crosses 1/α, the median sample count n at margin |p\* − τ| satisfies

    n · V  ≈  log(1/α) + (d_eff / 2) · log n + c            (†)

where:

- **V** is the method's *information rate* — the expected log-growth per
  sample of the method's statistic under the true distribution against
  its least-favorable null. Crucially, V is method-specific (frozen
  definitions):
  - single-stream mixture CS: V = KL(p\*, τ) (pooled Bernoulli rate);
  - UI product e-process with round-robin: the
    *allocation-constrained* boundary value
    min over {w·m = τ} of mean_k KL(p_k ‖ m_k) — NOT the max-min game
    value, which presumes optimal allocation;
  - WSR on block means: the exact per-sample optimal Kelly growth
    sup_λ E[log(1 + λ(M − τ))] / K over the (computable, 16-atom) block
    distribution — NOT the Cramér rate, which is a false-alarm exponent,
    not an e-process growth ceiling.
- **d_eff** is the effective number of parameters the statistic must
  learn (each costing ~½·log n of growth — the classical mixture/
  plug-in regret per dimension);
- **c** is a method constant (prior mass, discreteness, overshoot).

## Why (derivation sketch, not a proof)

Wald's identity gives E[τ_stop] ≈ (crossing level)/(growth rate). The
crossing level is log(1/α). A statistic that must learn d free
parameters pays the universal-coding price ~ (d/2)·log n relative to the
oracle that knows them (Krichevsky–Trofimov / mixture regret), raising
the effective crossing level to log(1/α) + (d/2)·log n + c. Dividing by
the per-sample rate V yields (†). The gap between "sketch" and "proof"
is real: overshoot, median-vs-mean, tracking terms, and the exact regret
constant for each statistic are unproven here — this is the open
formalization problem named in FINDINGS.

## Iteration history (full disclosure)

The rate definitions were corrected twice against already-committed
data before freezing — reported because a critic should ask:

1. First pass used the max-min game value for UI+RR: fit failed
   (d = 12, R² = 0.24). Diagnosis: round-robin cannot realize the
   optimal-allocation rate. Fix: allocation-constrained value.
2. First WSR pass used a Gaussian block approximation, second the
   Cramér rate: both failed with *negative* slopes. Diagnosis: an
   e-process's ceiling is its optimal Kelly growth, not a
   large-deviations false-alarm exponent. Fix: exact Kelly-block rate.

Each correction was a principled repair of an identified
mis-specification, not a free parameter — but the only clean answer to
the forking-paths concern is the frozen out-of-sample test now pending.

## Provisional fits (committed points only; ≥90% certification)

| method | d_eff | c | max resid | interpretation |
|---|---|---|---|---|
| single-stream | 0.66 | +0.78 | 0.35 nats | ~1 learned parameter |
| UI+RR | 2.26 | +7.04 | 0.37 nats | ≈ # failure-bearing strata (2) |
| WSR blocks | −0.18 | +2.27 | 0.22 nats | **zero** — constant ~1.7-nat tax |

The invention-round scoreboard follows from these three lines: WSR wins
hard margins because its overhead is flat in n while every alternative
pays d_eff/2 · log n; the sophisticated methods' larger V is consumed by
their larger d_eff until margins are extreme. Equating (†) between two
methods yields the crossover margin in closed form given (V, d, c).

## Frozen predictions and the OUT-OF-SAMPLE VERDICT (2026-08-11)

Scored against 30 fresh grid points
([results_overhead_law.txt](results_overhead_law.txt),
[results_overhead_fit.txt](results_overhead_fit.txt)):

- single-stream: window d ∈ [0.4, 1.6] → measured **0.79 / 1.01**
  (pooled 0.94, R² 0.91, resid ≤ 0.17 nats): **PASS**, centered on the
  theoretical d = 1.
- WSR: window d ∈ [−0.5, 0.5], c ∈ [1.6, 3.0] → measured **0.00 /
  −0.44**, c 2.31 / 2.83 (resid ≤ 0.39): **PASS** per model (pooled
  c = 3.27 marginally outside).
- UI+RR: window d ∈ [1.5, 3.5] → measured **3.37 / 4.04** (pooled
  3.83, R² 0.95): **WINDOW MISSED.** The law's form fits superbly, but
  the pre-registered "≈ #active strata" interpretation was WRONG: the
  dimension is ≈ K = 4, the full parameter count. The provisional
  d = 2.26 was four-point noise; the freeze caught the
  misinterpretation, which is what it was for.
- residual window (≤ 1.5 nats): PASS everywhere (max 0.39).

**Post-verdict statement of the law** (one revision, disclosed): d_eff
equals the number of parameters the statistic learns — 0 for the WSR
block bet (nothing to learn), 1 for the single-stream mixture, K for
the UI product. The sharp discriminating test this creates: on the
code-task pools, strata with zero failures abound (gpt-4.1-mini-code
has one active stratum); if d = K the UI fit stays ≈ 4 there; if the
rejected K_active story were right it would drop toward 1. Prediction
FROZEN before that grid runs: **d_UI ∈ [3, 5] on code pools; d_single ∈
[0.4, 1.6]; d_WSR ∈ [−0.5, 0.5].**

## What this would mean if it holds

A practitioner could choose the certification design *before sampling*
from three computable numbers per candidate method — and the open
theory problem sharpens from "why do simple methods win?" to "prove (†)
with explicit constants for these three statistics," a concrete,
attackable formalization target.
