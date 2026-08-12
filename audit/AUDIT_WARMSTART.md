# Adversarial audit — warm-start certification

**Scope**: `scripts/run_warmstart.py`, `scripts/run_warmstart_joint.py`,
`scripts/run_warmstart_stress.py`, `src/eval_harness/stats/stratified_ui_cs.py`,
`results_warmstart.txt`, `results_warmstart_stress.txt`,
`results_warmstart_joint.txt`, THEORY.md warm-start section.
`scripts/run_warmstart_drift.py`, `scripts/run_warmstart_chain.py` and their
results files appeared mid-audit; they are not in the brief but are covered
where they bear on the same claims (§5a), because they materially change the
verdict on one of them.

**Posture**: hostile. The brief was to break the claims. Where an attack
failed, that is stated as a survival, not a compliment.

**Reproducible artifacts added by this audit** (nothing outside `audit/` was
modified):

| file | what it does |
| --- | --- |
| `audit/sim_warmstart_null.py` | the missing type-I-error experiment: adversarial priors, `p* == tau`, 2000 reps × 8 configs × 3 arms |
| `audit/check_mixture_recursion.py` | brute-force proof of the mixture bookkeeping, the numerator's normalisation, the ε-premium, and that `min_log_e` is not anti-conservative |
| `audit/check_warmstart_claims.py` | prior forensics, CRN demonstration, bootstrap error bars, nats-vs-samples audit, genuine-prior-epoch comparison |
| `audit/repro_warmstart_artifacts.py` | re-runs each experiment `main()` in memory and diffs the published checksum |
| `audit/out_sim_warmstart_null.txt` | raw output of the 48 000-replication null-coverage run quoted below |
| `audit/out_check_warmstart_claims.txt` | raw output of the forensics / CRN / bootstrap / epoch run quoted below |
| `audit/out_repro_warmstart_artifacts.txt` | raw checksum-reproduction log |

---

## Verdict table

| # | Claim | Verdict | Severity |
| --- | --- | --- | --- |
| V1 | "the prior epoch predates and is independent of the current pools' sampling stream, so anytime validity is exact" | **OVERCLAIMED** (premise false and irrelevant; conclusion nevertheless holds) | Medium |
| V2 | "58/3000 labels differ from current truth" | **BUG** (wrong number; the pool used differs in 16/1000) | Medium |
| V3 | "a genuinely stale, slightly mislabeled epoch … a realistic warm start, not an oracle" | **OVERCLAIMED** (indistinguishable from a literal oracle) | High |
| V4 | "zero wrong certifications" as evidence of validity | **OVERCLAIMED** (vacuous: no replication is under the null) | High |
| V5 | Anytime validity of `TransferPriorUICS` / `TransferPriorJointUICS` under an adversarial prior | **CONFIRMED** — survived 2000-rep boundary MC | — |
| M1 | ε-contamination premium: `K·log(1/ε)` per-stratum, `log(1/ε)` joint | **CONFIRMED** exactly, pathwise | — |
| M2 | `update()` implements the mixture it claims | **CONFIRMED** to 1e-9 against closed form | — |
| M3 | `min_log_e` boundary minimisation is sound | **CONFIRMED** — not anti-conservative vs independent SLSQP | — |
| M4 | The nats cap is reported as a *sample-count* cap | **OVERCLAIMED** (the cap does not bound a median crossing time; the artifacts' own numbers exceed it in 5 of 6 places) | Medium |
| M5 | THEORY.md "measured **+2.3/+2.8** … on the bound to the decimal" | **OVERCLAIMED** (selective reporting: the third value, +3.17, is omitted and breaches the cap) | Medium-High |
| P1 | `results_warmstart.txt`'s own pre-registered overhead window `[1.5, 6]` | **failed at all three margins**; artifact prints the scoring rule with no verdict | Medium |
| P2 | Pre-registration blocks in the stress/joint scripts | **BUG** (verbatim copy-paste from the benign experiment; scored against the wrong criteria) | Medium |
| P3 | Stress test's own prediction "(b) inverted within 3–4 nats of cold" | **falsified** (measured ~+10); artifact does not say so | Medium |
| P4 | "predictions pre-registered" | **unverifiable** — all six files land in one commit | Low-Medium |
| D1 | Common random numbers across arms | **BUG** — streams desynchronise after replication 1 | Low (design), Medium (consequence) |
| D2 | The WSR win *within* `results_warmstart.txt`'s three margins | **OVERCLAIMED as published** (4 of 6 bootstrap CIs straddle 0); becomes **true** under a correctly paired re-run | Medium |
| D3 | That win reported for one archive prior, with no prior-epoch spread | **OVERCLAIMED** — over 40 genuine prior epochs the median ranges to 502, which loses to WSR's 374 | Medium |
| D4 | "faster than every incumbent including WSR at all margins tested" as a *general* statement (THEORY.md:228, FINDINGS.md) | **CONTRADICTED** by the repo's own newer `results_warmstart_chain.txt` (WSR wins 4 of 6 epochs) and `results_warmstart_drift.txt` | High |
| O1 | `cs.update(k if cs.k == 4 else 0, …)` | latent invalidity in a **dead branch** | Low |
| O2 | `WSRBlockCS.get_bounds` grid granularity | minor anti-conservatism, **favours the baseline** | Low |
| O3 | Checkpoint gating `n >= 20 and n % 4 == 0` | **CONFIRMED correct** (no off-by-one) | — |
| O4 | Level-fairness of UI arms (2α?) vs WSR (α) | **CONFIRMED fair** — attacked and survived | — |
| O5 | Artifact reproducibility | **CONFIRMED** bit-for-bit for `warmstart`, `stress`, `drift` (`joint` still re-running) | — |

---

## 1. Validity

### V1 — the independence argument is the wrong argument (and its premise is false)

`run_warmstart.py:192-196` (and the identical footer in the other two scripts —
`run_warmstart_stress.py:205-209`, `run_warmstart_joint.py:248-252` — and in all
three results files):

> Validity note: the prior epoch predates and is independent of the current
> pools' sampling stream, so anytime validity is exact

Two separate problems.

**(a) The premise is factually false.** The "prior epoch"
(`data/archive_pre_multipleof_fix/llm_outcomes_diverse_json.jsonl`) is not a
prior epoch. Measured (`audit/check_warmstart_claims.py` §1):

```
records: current 1000, archive 1000, ids present in both 1000, ids unique to one 0
label flips between the two files: 16/1000 = 1.600%
   per stratum {'simple': 0, 'medium': 0, 'complex': 3, 'extreme': 13}
```

Identical id sets, identical generations (the archive even carries a
`text_sha` field), file mtimes eight minutes apart (Aug 2 19:17 vs 19:25).
It is the *same* 1000 generations re-scored after a validator bug fix. It does
not "predate" anything in the sense the sentence implies, and it is emphatically
not independent of the current pool — it *is* the current pool with 1.6 % of
labels flipped.

**(b) Independence is not what validity needs, so the sentence proves the
right thing for the wrong reason.** The correct statement:

> For any prior π that is **fixed** (measurable at time 0, i.e. not a function
> of the realised stream), `M_π(x_{1:n}) / L(x_{1:n}; m)` is a nonnegative
> martingale under `x_i ~ iid Bern(m)`. Conditional on the pools, the transfer
> prior is a deterministic constant, so the e-process is exactly valid and
> `P(sup_n E(p*) ≥ 1/α) ≤ α`. Because this holds for every pool realisation, it
> also holds unconditionally for the estimand `p* = Σ_k w_k p_k` (the pool
> rate). The prior's *accuracy* affects power only, never validity.

Independence from the stream is irrelevant; **non-randomness with respect to
the stream** is what is required, and it holds trivially. The distinction
matters because the artifacts' framing would license a genuinely invalid
construction — fitting the prior on a prefix of the *same* stream would also be
"independent of the pool" in the loose sense used here, and would break the
martingale.

Where the framing *would* bite: if the estimand were a population rate of which
the pools are themselves a sample, a pool-derived prior is data-dependent for
that estimand. The artifacts never make that claim, so validity stands.

**Honest replacement**, suggested verbatim:

> Validity note: the transfer prior is a fixed function of an archived label
> set and does not depend on the realised sampling stream, so the e-process is
> an exact nonnegative martingale and anytime validity holds conditional on the
> pools. The prior's accuracy affects power only. NOTE: the archive is the same
> 1000 generations re-scored after a validator fix (16/1000 labels differ), not
> an independent evaluation epoch; the transfer-quality claim below should be
> read accordingly.

### V2 — "58/3000" does not match the data

The docstring shared by all three scripts asserts "58/3000 labels differ from
current truth". Measured across the three JSON outcome files:

| file | label flips |
| --- | --- |
| `llm_outcomes_diverse_json.jsonl` (**the pool actually used**) | **16 / 1000** |
| `llm_outcomes_diverse_json_gpt-4.1-mini.jsonl` | 59 / 1000 |
| `llm_outcomes_diverse_json_gpt-4.1-nano.jsonl` | 13 / 1000 |
| total | **88 / 3000** |

"58/3000" reproduces nothing: the aggregate is 88, not 58. It appears to be a
garbled reference to the gpt-4.1-mini file's 59 flips (cf. FINDINGS.md "59
labels corrupted"), a file this experiment never touches. The number that
matters — the staleness of the prior actually used — is **16/1000 = 1.6 %**,
which "58/3000" overstates by 3.6×. The error runs in the direction that makes
the prior sound staler than it is.

### V3 — the prior is an oracle in everything but name

`audit/check_warmstart_claims.py` §1:

```
stratum       n  p_current   p_prior   |gap|  gap/prior_sd  KL(cur||prior)
simple      250     0.0040    0.0040  0.0000         -0.74        0.000000
medium      250     0.0000    0.0000  0.0000         -1.00        0.000000
complex     250     0.0680    0.0800  0.0120         -0.83        0.001027
extreme     250     0.7360    0.7480  0.0120         -0.31        0.000378

p*_current = 0.2020   p*_prior = 0.2080   gap = 0.0060
total residual KL the prior pays = 0.001405 nats
```

Max per-stratum gap **0.012**; two strata match the truth *exactly*; the total
residual KL the prior pays is **0.0014 nats** — 1600× below the 2.303-nat
contamination budget the artifacts advertise as the insurance premium, and ~700×
below the ~1 nat of measured overhead. Under κ = 200 the truth sits 0.31–1.00
prior standard deviations from the prior mean.

The decisive number comes from the repo's own later experiment. In
`results_warmstart_drift.txt`, δ = 0 sets `p_prior = p_current` — a **literal
oracle** — and yields median **306** at τ = 0.16. The "genuinely stale" archive
prior yields **302** (`results_warmstart_joint.txt`). The stale prior is
*marginally faster than the oracle*. There is no measurable staleness cost, so
"not an oracle" is not a defensible description of the number being reported.

`scripts/run_warmstart_drift.py`'s own docstring already concedes the point —
"used a benign prior (near-copy of the truth)" — which directly contradicts
`run_warmstart.py`'s "a realistic warm start, not an oracle". The two files
should not disagree.

**In fairness** (this is the counterweight, and it is real): the 0.012 gap is
*within* the sampling noise a genuine 250-draw epoch would carry
(sd ≈ 0.028 on the extreme stratum), so the *magnitude* of the accuracy is not
absurd for a real prior epoch — only the *provenance* language is false. See
§5 for the measured performance distribution over genuine epochs.

### V4 — "zero wrong certifications" is vacuous, and the missing experiment

Every warm-start artifact reports `wrong 0` and THEORY.md/FINDINGS.md elevate
it to "Zero wrong certifications anywhere". In `run_warmstart.py:176`:

```python
wrong = sum(1 for d, _ in outs if d == "SAFE")
```

with `p* = 0.2020` and `tau ∈ {0.15, 0.16, 0.17}`. **Every replication is drawn
from the alternative for the UNSAFE direction.** `wrong` counts only SAFE
decisions, which require the confidence sequence to be wrong by ≥ 0.032. The
type-I error the certification claim actually rests on — `P(rejects_le fires |
p* ≤ τ)` — is **never exercised at any margin, in any of the three artifacts**.
As evidence of validity, `wrong 0` is worth nothing.

That experiment is supplied here as `audit/sim_warmstart_null.py`. Design: pools
constructed so `p*` sits **exactly at τ** (the least-favourable null point,
where both one-sided nulls are true), an **adversarially wrong** prior in the
direction that inflates the numerator toward the forbidden rejection, the
certification loop taken verbatim from `run_warmstart.py`, and the estimator
classes *imported from the scripts under audit* rather than reimplemented.
Two nested statistics so a failure would localise:

* **T1** = `P(sup_n E(p_true) ≥ 1/α)` — numerator/bookkeeping only.
* **T2** = `P(the shipped rejects_le / rejects_ge fires)` — T1 plus the
  Lagrange-bisection minimisation over the null boundary.

8 configurations × 3 arms × **2000 replications**, `n_max = 4000`, α = 0.05:

```
WORST over all configs/arms:  T1 = 0.0470,  T2 false-UNSAFE = 0.0145,
                              T2 false-SAFE = 0.0365      (alpha = 0.05)
```

Worst individual cells: `B/joint warm` false-UNSAFE 29/2000 = 0.0145;
`G/joint warm` false-SAFE 73/2000 = 0.0365 and T1 94/2000 = 0.0470. **No cell
exceeds α, and none is significantly above α by a one-sided exact binomial
test.** T1 reaching 0.047 against a nominal 0.05 confirms the configurations
genuinely stressed the bound rather than testing a vacuously conservative
regime.

### V5 — VALIDITY SURVIVED

The headline attack failed. An adversarial prior costs power, not coverage,
exactly as the theory says. The e-process is exactly valid; what is
overclaimed is the *evidence the artifacts offer for it*, not the property.

---

## 2. The mathematics

All checks in `audit/check_mixture_recursion.py`; the whole file prints a
single PASS line and currently passes.

### M1/M2 — the contamination premium and the mixture bookkeeping: CONFIRMED

Re-derivation. Per-stratum, the numerator is a product of independent
two-component mixtures, so

```
M_perstrat = Π_k [(1-ε)·M_conc,k + ε·M_unif,k]  ≥  ε^K · Π_k M_unif,k
           = ε^K · M_cold        →   premium K·log(1/ε) = 9.21 nats
```

and yes, the premium genuinely **multiplies across strata in the product
e-process** — that is the whole reason the joint variant exists. Jointly,

```
M_joint = (1-ε)·Π_k M_conc,k + ε·Π_k M_unif,k  ≥  ε · M_cold
                              →   premium log(1/ε) = 2.30 nats
```

Because the denominator `L(·; m)` is shared, the inequality survives the
`min` over the null set: `min_m [log M_joint − ℓ(m)] ≥ log ε + min_m [log M_cold
− ℓ(m)]`. Verified numerically at every prefix of 200 random 20-observation
sequences, for τ ∈ {0.15, 0.25, 0.5} and both sides.

Brute-force checks that passed:

1. **Closed form.** The incremental posterior-weighted predictive recursion in
   `update()` telescopes to `Σ_k log[(1-ε)B(a_k,b_k;f_k,s_k) + εB(1,1;f_k,s_k)]`
   (per-stratum) and `log[(1-ε)Π_k B(a_k,b_k) + εΠ_k B(1,1)]` (joint) to
   **< 1e-9**, at every one of 20 steps, over 200 random prior vectors. The
   posterior-weight update `lw = self._logw + self._logm[:, i]` is the correct
   two-component marginal recursion; the joint variant's global
   `_logm_total` is the correct product-measure analogue.
2. **Normalisation.** At every step, `mix_pred(failure) + mix_pred(success) = 1`
   to **< 1e-12**. This is the sharp form of the martingale property: it makes
   `M` a probability mass function over sequences, hence `E[M/L(·;p)] = 1`
   *exactly* — a far stronger statement than any Monte-Carlo mean of a
   heavy-tailed martingale could give.
3. **Exchangeability.** `log_pred` is invariant to the order of observations
   within a stratum, as it must be for a Beta mixture.

### M3 — the boundary minimisation is not anti-conservative: CONFIRMED

An inf that comes out **too high** is the dangerous direction — it rejects when
the true inf would not. `StratifiedUICS.min_log_e` was compared against
independent SLSQP constrained minimisation from 26 starts (the code's own answer
never used as a start), over 12 accumulated states × 4 thresholds × 2 sides:
never above the brute-force infimum by more than 1e-6.

The KKT quadratic in `_m_of_lambda` is also correct at the degenerate points I
hand-checked: `f=0`, `s=0`, `n=0`, and `a≈0` (which falls through to the MLE
branch). Strict convexity of `-f log m - s log(1-m) + a·m` guarantees at most
one interior stationary point, so the `in1 ? r1 : r2` root selection is
unambiguous; in the degenerate `f=s=0` case both roots are `{0,1}` and the
selection still picks the correct endpoint for either sign of `a`.

### M4 — nats are reported as samples

The ε-cap bounds `log E`. The artifacts convert it into stopping-time and
median-sample statements it does not imply, and then score against those.
Every number below is computed from the artifacts' **own published tables**:

| assertion | source | measured | cap | verdict |
| --- | --- | --- | --- | --- |
| joint-inverted "≤ ~150 samples slower" than cold | `run_warmstart_joint.py:8` | +118 / **+250** / **+372** samples (τ=.15/.16/.17) | 150 | fails 2 of 3 |
| joint-inverted overhead gap vs cold | `results_warmstart_joint.txt` | +2.27 / **+3.17** / +2.77 nats | 2.303 | exceeds 1 of 3 |
| per-stratum inverted overhead gap vs cold, "measured +9.9 vs bound +9.2 — consistent" | `run_warmstart_joint.py:5-6` | **+9.93 / +10.95 / +9.60** nats | 9.21 | exceeds 3 of 3 |
| "worst median ≤ cold + log(1/ε)/V_rr ~ 1700" | `run_warmstart_drift.py` prediction 2 | 1770 | ~1700 | exceeds; printed without a fail verdict |

An independent 200-replication re-run with correct per-replication seeding
(`audit/check_warmstart_claims.py` §4) reproduces the pattern rather than the
published sampling luck — **5 of 6 median-sample gaps exceed the nats cap**:

```
tau=0.15  joint-inv    +128 samples =  +2.46 nats   cap 2.30   EXCEEDS
tau=0.15  perstrat-inv +570 samples = +10.97 nats   cap 9.21   EXCEEDS
tau=0.16  joint-inv    +256 samples =  +3.25 nats   cap 2.30   EXCEEDS
tau=0.16  perstrat-inv +880 samples = +11.16 nats   cap 9.21   EXCEEDS
tau=0.17  joint-inv    +288 samples =  +2.15 nats   cap 2.30   WITHIN
tau=0.17  perstrat-inv+1282 samples =  +9.56 nats   cap 9.21   EXCEEDS
```

**None of this is a validity failure** — the pathwise nats bound holds exactly
(M1). The defect is presentational and it is systematic: `overhead = median·V_rr
− log(1/α)` is a *derived diagnostic about a first-crossing time*, not the
bounded quantity, and calling a measurement that exceeds an upper bound
"consistent" or "on the bound to the decimal" is not defensible. A nats cap on
`log E` implies `T_warm ≤ T_cold(L + c)` pathwise, which does **not** imply
`median(T_warm) ≤ median(T_cold) + c/V_rr` — the first-crossing time overshoots
the boundary, and a wrong prior slows the *rate* of growth early on, so the
median gap systematically exceeds `c/V_rr`.

### M5 — THEORY.md selectively reports the joint result

THEORY.md:236-237:

> **Joint contamination** … caps the premium at log(1/ε) ≈ 2.3 nats total —
> measured **+2.3/+2.8** vs cold, on the bound to the decimal.

The three measured values are **+2.27, +3.17, +2.77**. The middle margin
(τ = 0.16) — the only one that *breaches* the 2.303 cap, by 38 % — is silently
dropped, and the surviving two are described as "on the bound to the decimal".
The commit message for `06ea04a` repeats the same two-of-three ("measured
+2.3/+2.8, exact"). Given that this repo's stated norm is to log misses
honestly, and that it does so elsewhere in the same paragraph, this omission is
the single most damaging integrity finding in the audit.

---

## 3. Pre-registration integrity

### P1 — the headline experiment's own pre-registration failed, silently

`run_warmstart.py:22-23` predicts "warm-start UI overhead in **[1.5, 6] nats**
at all three margins". Measured: **+0.93, +1.01, +1.37** — outside the window at
all three. `results_warmstart.txt` nonetheless closes with

```
Scoring: warm-start overhead in [1.5, 6] nats and >= 2.5x faster than
the cold mixture everywhere; within +-30% of WSR at tau=0.17.
```

— the criterion restated as if satisfied, with no verdict line. THEORY.md
*does* log it ("Pre-registered overhead window [1.5, 6] missed LOW — favorably
wrong is still logged as wrong"), which is to the project's credit; the
**artifact** does not, and the artifact is what a reader checksums.

### P2 — copy-pasted pre-registration blocks

`run_warmstart_stress.py:30-38` and `run_warmstart_joint.py:37-45` each carry a
verbatim copy of `run_warmstart.py`'s "PRE-REGISTERED PREDICTIONS" — overhead
[1.5, 6], medians 310/470/800, "beats the cold mixture ≥ 2.5×", "within ±30 % of
WSR at τ=0.17". Those describe the **benign** experiment and are meaningless for
arms driven by inverted and drifted priors, yet both results files print that
block as their scoring footer. `run_warmstart_joint.py`'s docstring stacks three
mutually inconsistent prediction blocks (joint's own, the stress test's, and the
benign one). A reader cannot tell which criteria the artifact was scored
against.

Minor, same family: `run_warmstart_joint.py:7` contains `within 15%% of` — a
stray `%%` in a plain (non-format) docstring.

### P3 — the stress test's own prediction was falsified without comment

`run_warmstart_stress.py:7-11` predicts the inverted prior lands "within
~log(1/ε)+O(1) ~ **3–4 nats** of the COLD mixture … graceful, never
catastrophic". Measured: **+9.93 / +10.95 / +9.60** — a ~3× miss, caused by a
real math error (the per-stratum product pays `K·log(1/ε)`, not `log(1/ε)`).
`results_warmstart_stress.txt` reports the copy-pasted benign footer instead of
scoring its own prediction. The recited footer's "abstention ≤ 5 %" is also
breached in that file: per-stratum inverted at τ=0.17 abstains 12/200 = **6 %**.

THEORY.md again logs this honestly ("my '3–4 nats' pre-statement forgot the K
factor"). The pattern is consistent: **THEORY.md is honest; the results
artifacts are stale and self-congratulatory.** Fixing the artifacts' footers is
the cheapest high-value change available.

### P4 — no timestamped pre-registration

`git log` shows all six warm-start files — three scripts *and* three results —
added in a single commit (`06ea04a`). There is no version-control evidence that
any prediction preceded any run. For a project whose credibility rests on
pre-registration, predictions should be committed before the results file
exists.

---

## 4. Design, seeds, error bars

### D1 — common random numbers are broken after replication 1

`run_warmstart.py:173-174`:

```python
rng = np.random.default_rng(BASE_SEED + 7919)
outs = [run_arm(pools, tau, rng, mk) for _ in range(N_REPS)]
```

The Generator is reset per **arm**, then shared across all 200 replications.
Arms stop at different `n`, so they consume different numbers of draws.
Demonstrated (`audit/check_warmstart_claims.py` §2, τ=0.16):

```
cold  first 5 stopping times [1228, 1732, 2320, 896, 1024]  -> cumulative draws [1228, 2960, 5280, 6176, 7200]
warm  first 5 stopping times [664, 160, 244, 84, 396]       -> cumulative draws [664, 824, 1068, 1152, 1548]
PRNG state identical at the START of reps 1..5? [True, False, False, False, False]
```

Only replication 1 is a common-random-number pair. The design is *one line* from
working: within a replication the coupling is exact — `run_arm` and `run_wsr`
both draw one index per stratum per block of four, in `STRATA` order, from pools
of identical length 250, so block *b* sees the same four pool indices in both.
Giving each replication its own seed
(`np.random.SeedSequence(seed).spawn(N_REPS)`) restores pairing across arms at
zero cost.

Nothing published *depends* on pairing (only medians and counts are reported),
so this is not a correctness bug — but it is what prevents the "beats WSR" claim
from being defensible, below.

### D2 — "faster than every incumbent including WSR at all margins tested" is not established by the published experiment

Bootstrap of `median(WSR) − median(arm)`, 20 000 resamples, 200 replications,
95 % CI (`audit/check_warmstart_claims.py` §3). The as-published design permits
only the **unpaired** column:

| τ | arm | as-published (unpaired) | correctly paired |
| --- | --- | --- | --- |
| 0.15 | warm | +36 **[−22, +94]** | +46 [+14, +66] |
| 0.15 | joint | +52 **[−4, +112]** | +60 [+30, +88] |
| 0.16 | warm | +60 [+4, +116] | +60 [+16, +108] |
| 0.16 | joint | +72 [+18, +124] | +84 [+36, +132] |
| 0.17 | warm | +40 **[−108, +154]** | +98 [+28, +172] |
| 0.17 | joint | +78 **[−64, +192]** | +140 [+72, +208] |

**Four of six as-published comparisons have CIs that straddle zero.** The
τ = 0.16 pair is significant only barely. Even restricted to this three-margin
slice, THEORY.md's bolded "**faster than every incumbent including WSR at all
margins tested**" and FINDINGS.md's "medians beat every incumbent including WSR
at all tested margins" are, on the published evidence, unsupported at two of
three margins.

**However** — and this is the honest counterweight — with per-replication common
seeds (the correct design) **all six become significant**, with comfortable
margins. So *within this slice* the claim is true; the *experiment as run cannot
show it*. The fix is a one-line seeding change plus reporting CIs, and it
strengthens rather than weakens the result. (The broader claim is a separate
matter — see §5a.)

My re-run reproduces the published medians exactly (as-published column: warm
204/316/586, joint 186/302/548, WSR 248/374/640), confirming the harness is
faithful.

---

## 5. Is the archive prior a realistic prior epoch?

The scripts justify κ = 200 as "prior epoch had 250 samples/stratum". If that
were the provenance, the prior rates would carry the sampling noise of 250 draws
per stratum. `audit/check_warmstart_claims.py` §5 draws genuine 250-per-stratum
epochs from the same pools and measures the resulting warm-start medians against
the archive prior and against an exact-truth oracle.

40 genuine epochs × 60 replications, joint contamination, τ = 0.16 (all three
rows computed identically, so they are directly comparable):

```
truth p_k          = [0.004, 0.0, 0.068, 0.736]
archive prior p_k  = [0.004, 0.0, 0.080, 0.748]   max|gap| = 0.0120
40 genuine 250/stratum epochs: max|gap| median 0.0260, p10 0.0080, p90 0.0640
  -> the archive prior is at percentile 22 of epoch ACCURACY
     (more accurate than 78% of genuine epochs)

median samples, exact-truth ORACLE prior : 310
median samples, ARCHIVE prior            : 316   (+1.9% vs oracle)
median samples, genuine epochs           : median 332, p10 302, p90 368, max 502
  -> the archive prior is at percentile 78 of epoch PERFORMANCE
```

Three readings, all worth stating:

* The **provenance** claim is false (V1, V3): the archive is the same data
  re-scored, it is more accurate than 78 % of genuine epochs, and its
  performance is within 1.9 % of a literal oracle.
* The **central performance** consequence is nonetheless **small**: a genuinely
  independent 250-sample epoch gives a median of 332 against the archive's 316
  — the reported speedup is optimistic by ~5 %, not by a factor. The warm-start
  result is *robust* to honest prior-epoch noise at κ = 200. This exonerates the
  substance while leaving the language indefensible.
* The **tail** is the part the artifacts hide. Across genuine epochs the median
  ranges to p90 = 368 and max = **502** — and 502 **loses to WSR's 374**. The
  claim "faster than every incumbent including WSR" is a property of the single
  archive realisation, not of the warm-start method under realistic prior-epoch
  variation. Reporting one draw with no spread conceals exactly the deployment
  risk a practitioner needs.

The right presentation is the warm-start median **averaged over genuine prior
epochs, with the spread and the loss probability against WSR**, rather than a
single archive realisation described as "stale".

### 5a. The repo's own newer experiments contradict the WSR claim

Two warm-start artifacts appeared while this audit was running
(`results_warmstart_drift.txt`, `results_warmstart_chain.txt`). Both are better
designed than the originals — the chain experiment in particular uses a
genuinely sequential prior (the previous epoch's Jeffreys estimates at its own
stopping time, with κ set from that epoch's actual sample counts), adds an
oracle-prior reference arm, and covers SAFE as well as UNSAFE truths. It is the
experiment §5 asks for.

It also **contradicts the headline claim**. In `results_warmstart_chain.txt`,
WSR beats chain-warm at four of six epochs, three of them decisively:

| epoch | chain-warm | WSR | |
| --- | --- | --- | --- |
| 1 | 428 | **114** | WSR 3.8× faster |
| 2 | **322** | 348 | |
| 3 | 3620 (57/200 decided) | **2052** (165/200) | WSR far better |
| 4 | 5164 (24/200) | **2344** (173/200) | WSR far better |
| 5 | 512 | **414** | |
| 6 | **136** | 260 | |

`results_warmstart_drift.txt` says the same thing along a different axis: warm
start loses to WSR at every drift `|δ| ≥ 0.015` except δ ∈ {−0.03, −0.015, 0}.

The chain commit message concedes the point in as many words — "**WSR owns the
boundary**" (`dbc0a98`) — so the project has already reached this conclusion.
What has not happened is propagating it back: THEORY.md:228's "**faster than
every incumbent including WSR at all margins tested**" and FINDINGS.md's
"medians beat every incumbent including WSR at all tested margins" are still
stated unqualified. They are true only of the three-margin,
single-archive-prior slice in `results_warmstart.txt`, and are contradicted by
the repo's own later, broader evidence. Those two sentences need scoping to
that slice, or retiring. Per CLAUDE.md's documentation-synchronisation rule,
AUDIT_PREP.md needs the same correction.

---

## 6. Other findings

**O1 — latent invalidity in a dead branch.** `run_arm` (all three scripts):

```python
cs.update(k if cs.k == 4 else 0, bool(pool[int(rng.integers(0, len(pool)))]))
```

Both warm-start arms use `k=4`, so the `else 0` path never fires here. If a
`k=1` CS were ever passed, the deterministic round-robin stream folded into one
stratum is independent but **not identically distributed** (it cycles
`p_1 … p_4`), and a Beta(1,1) mixture e-process is not a martingale at the
pooled mean. Replace with `assert cs.k == 4` or handle the pooled case
explicitly.

**O2 — `WSRBlockCS.get_bounds` grid granularity.** The CS is evaluated only at
1000 grid points on `[0.0005, 0.9995]`; means strictly between grid points are
never tested, so `lo`/`hi` can be anti-conservative by up to ~0.001. This makes
the **incumbent** marginally faster, so it works against the warm-start claim
and does not inflate anything here. Worth a footnote, not a fix.

**O3 — checkpoint gating is correct.** With `k = (n-1) % 4`, the condition
`n % 4 == 0` fires exactly at the end of a complete round-robin cycle, so the CS
is only evaluated at balanced allocations; `run_wsr`'s `4*b >= 20` matches
`run_arm`'s `n >= 20`. Evaluating on a subsequence of times is conservative under
anytime validity. No off-by-one.

**O4 — level-fairness: attacked, survived.** I expected the UI arms to spend 2α
(`rejects_le` at α **plus** `rejects_ge` at α) against WSR's single α-level
hedged CS, which would have made the head-to-head unfair by ~log 2 = 0.69 nats
(≈ 55 samples at τ=0.16 — enough to erase the WSR margin). It does not: at any
`p*`, *both* directional rejections require `sup_n E(p*) ≥ 1/α`, the same event,
so the UI arms' total error is also ≤ α. The comparison is level-fair.

**O5 — reproducibility CONFIRMED.** `audit/repro_warmstart_artifacts.py` re-runs
each `main()` in memory (writing nothing) and compares checksums.

```
warmstart  recomputed c6684a068de30647  published c6684a068de30647  MATCH
drift      recomputed 1e5e5d85a8cad4fc  published 1e5e5d85a8cad4fc  MATCH
stress     recomputed 8139a36f5ce34fb4  published 8139a36f5ce34fb4  MATCH
```

All three re-run bit-for-bit. `joint` was still re-running when this report was
finalised (it is the expensive one — five arms including two inverted priors
with medians past 4000); the command is
`python3 audit/repro_warmstart_artifacts.py joint`.
Separately, the medians my own independent harness produces under the
as-published seeding match the published tables exactly at all three margins
(warm 204/316/586, joint 186/302/548, WSR 248/374/640), which is strong
corroboration that the two remaining artifacts will also reproduce.

---

## 7. Ranked fix list

**Tier 1 — integrity (do these first; all are edits to prose, not code)**

1. **Restore the omitted +3.17.** THEORY.md:236 and the `06ea04a` commit
   narrative must report **+2.27 / +3.17 / +2.77** and state plainly that the
   median-sample gap at τ=0.16 exceeds the 2.303-nat cap *because the cap bounds
   `log E`, not a median crossing time*. Delete "on the bound to the decimal".
2. **Rewrite the validity note** in all three scripts and all three results
   files. Use the fixed-prior/conditional-on-pools statement (§V1); drop
   "predates", drop "independent".
3. **Fix "58/3000" → "16/1000"** and describe the archive accurately: the same
   1000 generations re-scored after a validator fix, not a prior epoch.
4. **Retire "a realistic warm start, not an oracle."** The repo's own δ=0 drift
   arm (306) versus the archive prior (302) makes it untenable. Replace with the
   §5 framing: an oracle-equivalent prior, whose performance a genuine 250-sample
   epoch nearly matches.
5. **Score each artifact against its own predictions.** Add a verdict line to
   `results_warmstart.txt` (overhead window [1.5, 6] **MISSED LOW** at all three
   margins), `results_warmstart_stress.txt` (the 3–4 nat prediction **MISSED**,
   ~+10 measured; abstention 6 % > 5 %), and
   `results_warmstart_drift.txt` (saturation ceiling 1770 > ~1700 **MISSED**).
6. **Delete the copy-pasted pre-registration blocks** from
   `run_warmstart_stress.py` and `run_warmstart_joint.py`; each script should
   state only its own predictions.
7. **Scope or retire "faster than every incumbent including WSR at all margins
   tested."** The repo's own `results_warmstart_chain.txt` (WSR wins 4 of 6
   epochs) and `results_warmstart_drift.txt` (warm loses at every
   `|δ| ≥ 0.015` bar one) contradict it. The defensible version is: *at the
   three margins of `results_warmstart.txt`, with a prior drawn from the same
   labels, warm start beats WSR by 15–25 %.*

**Tier 2 — evidence that is missing**

8. **Ship a null-coverage experiment.** `audit/sim_warmstart_null.py` is the
   template; promote it (or an equivalent) into `scripts/` and cite it wherever
   "zero wrong certifications" currently appears. Replace that phrase with the
   measured type-I rates. Without it, the certification claim has no type-I
   evidence at all. (Note the chain experiment's SAFE epochs get closer but
   still never place the truth *at* τ, the least-favourable point.)
9. **Fix the seeding and publish error bars.** One line:
   `seeds = np.random.SeedSequence(BASE_SEED + 7919).spawn(N_REPS)`, one
   Generator per replication, shared across arms. Then report paired bootstrap
   CIs for every "beats X" claim.
10. **Report warm-start performance averaged over genuine prior epochs**, with
    spread and the probability of losing to WSR, instead of the single archive
    realisation (§5). The centre barely moves (316 → 332) but the p90 (368) and
    max (502) change the deployment story: WSR's 374 is not beaten in the tail.

**Tier 3 — code hygiene**

11. `assert cs.k == 4` (or handle `k=1` properly) in the three `run_arm`
    functions — closes a latent invalidity in a currently-dead branch.
12. Commit predictions before results, in a separate commit, so
    "pre-registered" is verifiable.
13. Footnote `WSRBlockCS.get_bounds`'s 1000-point grid as a ~0.001
    anti-conservatism in the baseline's favour.
14. Fix the stray `%%` in `run_warmstart_joint.py:7`.

---

## 8. What survived

Stated plainly, because most of it did:

* **Anytime validity holds**, including under an adversarially inverted prior,
  measured at the least-favourable null point over 48 000 replications. Worst
  observed rate 0.047 against α = 0.05, with no significant excess anywhere.
* **The mixture bookkeeping is exact** — the recursion equals the closed-form
  two-component marginal to 1e-9, the numerator is a probability measure to
  1e-12, and the accumulator is order-invariant.
* **Both ε-contamination bounds are exactly right**, including the claim that
  the per-stratum premium multiplies to `K·log(1/ε)` in the product e-process,
  and they survive the min over the null boundary.
* **The boundary minimisation is sound** and not anti-conservative against an
  independent optimiser.
* **The checkpoint schedule, the level-matching against WSR, and the artifact's
  reproducibility** all survived direct attack.
* **The substantive result is real**: warm-starting does convert the learning
  tax into ~1 nat, and at the centre of the prior-epoch distribution it does
  beat WSR — the correctly-paired re-run makes that claim *stronger*, not
  weaker, and a genuine independent prior epoch costs only ~5 % against the
  archive.

The failures are concentrated in how the work is described, not in what it does:
a false provenance story, a mis-cited label count, a nats/samples conflation, one
selectively-reported number, stale scoring footers, a single-realisation
performance claim with no spread, and a type-I-error claim with no type-I-error
experiment behind it.

---

## Appendix — how to re-run this audit

```bash
python3 audit/check_mixture_recursion.py            # ~2 min, prints one PASS line
python3 audit/sim_warmstart_null.py --reps 2000 --procs 9    # ~25 min
python3 audit/sim_warmstart_null.py --reps 200 --verify-screen   # screen equivalence
python3 audit/check_warmstart_claims.py --reps 200 --epochs 40 --epoch-reps 60
python3 audit/repro_warmstart_artifacts.py          # checksum diff, writes nothing
```

Environment used: python 3, numpy 2.3.5, scipy 1.16.3, macOS (darwin 25.2.0),
10 cores. All scripts are offline and deterministic given their `--seed`
defaults (`sim_warmstart_null.py` spawns a seed per replication, so results do
not depend on `--procs`).
