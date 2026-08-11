# The Certification-Overhead Expansion (calibration of a classical result)

**STATUS AFTER ADVERSARIAL REFEREE (2026-08-11): what this document
initially called a conjectured "law" is, for the d = 1 case, a
fifty-year-old theorem — Pollak & Siegmund (1975), Woodroofe (1982,
Nonlinear Renewal Theory), with boundary shape from Schwarz (1962) and
Lai (1988), matching lower bound Pollak (1978), and the (d/2)·log n
term from Krichevsky–Trofimov / Rissanen / Clarke–Barron mixture
regret. Our contribution is repositioned honestly as: (i) a
CALIBRATION of the classical expansion on real LLM evaluation data,
with zero-free-parameter closed-form predictions matching measured
medians within ±5%; (ii) the boundary-stratum dimension rule
d = K + #boundary-strata for the UI statistic (classically related to
Xie–Barron 1997 / Watanabe's RLCT; apparently unstated in the modern
e-value literature); (iii) an ANTI-RESULT for the WSR schedule — its
predictable λ ∝ 1/√(t log t) forfeits the Kelly growth rate entirely
(achieved/optimal → 0), so its practical advantage is "a bounded rate
sacrifice beats a (K/2)·log n additive penalty when log n ≈ 6–8," and
our earlier "flat overhead" reading was a finite-window artifact; and
(iv) the observation that the modern e-value literature under-cites
this classical expansion (Agrawal–Ramdas stop at first order). The
referee's full report is summarized at the bottom; everything above the
verdict sections is preserved as honest history.**

**Original status line (superseded):** empirical law with frozen
out-of-sample test pending.
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

**Post-verdict statement, superseded within hours — see the referee
report below.** An earlier revision here claimed d = K. The adversarial
referee (2026-08-11) corrected it: **d = K + #boundary-strata** (strata
with rate exactly 0 or 1 cost a FULL log n each — the Beta(1,1)
marginal of an all-success stratum is 1/(n+1); classically this is the
boundary/singular coefficient of Xie–Barron 1997 and Watanabe's RLCT),
verified on eight controlled synthetic configurations to ±0.21.

**LIVE ADJUDICATION (frozen while the code-pool grid was still
computing):** my earlier window predicted d_UI ∈ [3, 5] on the code
pools. The referee's rule predicts d_UI ≈ K + #boundary = **6**
(gpt-4o-mini code: rates 0/0/.063/.138), **6** (nano code:
0/.013/0/.05), **7** (mini code: 0/0/.037/0 — wait, .037 stratum and
three zero strata: 4 + 3 = 7). If the code grid fits d_UI in [5, 8],
the referee's rule wins and my window loses again; if [3, 5], the
reverse. Both predictions frozen before
results_overhead_law_code.txt existed.

## What this would mean if it holds

A practitioner could choose the certification design *before sampling*
from three computable numbers per candidate method — and the open
theory problem sharpens from "why do simple methods win?" to "prove (†)
with explicit constants for these three statistics," a concrete,
attackable formalization target.


## Referee verdicts (adversarial audit, 2026-08-11; independent
## replication of our grid at 10,000 reps agreed cell-by-cell)

- UI rate V_rr (allocation-constrained boundary value): **SOUND**
  (envelope argument; measured E[LLR]/(nV) → 1.002).
- WSR rate V_kelly: **REFUTED as a rate** — it is a ceiling the WSR
  schedule never approaches (achieved/Kelly = 0.73 → 0.29 and falling;
  overhead grows ~linearly; the wide-sweep data is U-shaped with max
  residual 2.37 nats, violating our own frozen criterion; the grid
  "pass" had R² = 0.000 — a flat scatter passing a window is not
  evidence).
- Single-stream: **SOUND at first order**; d = 1 EXACTLY (derivation via
  Laplace + Wald); our fitted 0.66–0.94 were stopping-time artifacts
  (overshoot, median-vs-mean, check-grid rounding — all quantified).
  Even c is derivable in closed form: ½log n − ½log(2π p*q*) − ρ/2 with
  ρ the stratification variance ratio.
- d_eff interpretation: **CORRECTED** to d = K + #boundary-strata
  (eight synthetic configs, measured within ±0.21 of prediction;
  4o-mini JSON pools predict 5, path-measured 4.99).
- Fit methodology: **d = 0 vs d = 1 not identifiable** at 200 reps × 6
  points (bootstrap CIs span both; corr(d̂, ĉ) = −0.994); the residual
  criterion was vacuous (P(pass) = 1.00); functional form untested
  (√log n and log log n fit equally over our windows).
- Prior art: see status header. The positioning opportunity is
  citation, not discovery.

## What survives, verified constructively by the referee

Zero-free-parameter predictions (d and c from theory/sample paths only,
never fitted to crossing times) reproduce the definitive grid medians:
single-stream within −3%…+7%, UI within −5%…+4%, across both models
and all margins with ≥90% certification. The invention-round headline
stands with a corrected mechanism: **the simple block reduction wins at
practical sample sizes because it sacrifices a bounded factor of rate
while every mixture-based alternative pays an additive
(K + #boundary)/2 · log n that dominates when log n ≈ 6–8.**
