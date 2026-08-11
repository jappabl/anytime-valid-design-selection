# Draft note to Spertus, Sridhar & Stark (NOT SENT — draft for Hao's review)

*Purpose: a short, honest technical note to the authors of
"Sequential stratified inference for the mean" (arXiv:2409.06680),
summarizing our independent implementation and evaluation of their
UI-TS construction on LLM-evaluation data, and the open question our
measurements raise. Sending is Hao's decision; nothing here has been
transmitted anywhere.*

---

Subject: Independent evaluation of your UI-TS on LLM failure-rate
certification — results and an open question

Dear Dr. Spertus, Mayuri Sridhar, and Prof. Stark,

I am a high-school researcher who has been building an empirical
testbed for anytime-valid sequential evaluation of language-model
failure rates, and your union-of-intersections construction became the
central baseline in it. I'm writing to share results you may find
useful, and one measured phenomenon we cannot fully explain.

**What we built.** A replay testbed: three OpenAI models evaluated once
per prompt at temperature 0 on 1,320 structurally-graded prompts
(4 difficulty strata), giving outcome pools whose stratified mixture
mean is exactly known. Sequential procedures replay against the pools,
so competing designs can be compared with exact ground truth,
common random numbers, and bootstrap error bars, at zero marginal cost.
Everything (code, data, per-call raw generations, results with
checksums, a one-command reproduction script) is in a public-ready
repository.

**What we ran.** An adaptation of your UI-TS to K = 4 Bernoulli strata
with-replacement: inverse bets with predictable frozen coefficients
(your Sec. 4.2.2 defaults), exact boundary minimization over
C = {w·η = τ} via the per-stratum KKT quadratic, running-max statistic,
and your Section-6 greedy selection. Validity was verified empirically
in both certification directions (false-certification 0.007–0.030 at
α = 0.05). Two earlier drafts of our implementation were invalid —
caught by an information-bound check (medians below log(1/α)/game-value
are impossible) that we now run automatically; we mention this because
the failure modes (vertex minimization with η-aware bets; flat strata
pinned to the top of the null boundary) may be traps worth flagging for
other implementers.

**Results in brief** (τ = 0.15 threshold unless noted; full tables and
artifacts available):

- Your UI-TS with greedy selection is the fastest method we tested when
  it certifies: e.g. median 156 samples vs 178 for a per-stratum
  Bonferroni method and 244 for a betting CS on block means (WSR-type)
  at an easy UNSAFE instance; it takes the easy SAFE instance outright
  (184 vs 240, bootstrap CI [+40, +80]).
- Its abstention rate within fixed budgets grows quickly with problem
  hardness (3% → 63% across our margin sweep) where the block-mean
  betting CS abstains 0–10%; at our hardest margin the block method
  certifies 90% vs 37%. We suspect our frozen-coefficient variant
  understates your banded AGRAPA version here, and would welcome
  correction.
- A Track-and-Stop-style allocation we built (Frank–Wolfe on the
  max-min KL game, D-tracking, forced exploration) is sound but runs
  ~6× above its own game-value bound at every margin we can test —
  the overhead of learning K parameters plus tracking slack appears to
  consume the stratified rate advantage at practical sample sizes.

**The open question.** Across methods and margins our stopping times
are well described by n·V ≈ log(1/α) + (d_eff/2)·log n + c with method-
dependent effective dimension d_eff [fit results to be inserted from
results_overhead_fit.txt when final]. Equating laws yields a predicted
crossover margin below which simpler low-dimension statistics beat
rate-optimal stratified ones. Is a finite-sample version of this
tradeoff — rate optimality vs parametric overhead for UI-TSs — known or
derivable within your framework? Your paper's Section 4.2 constructs
the STO test for known alternatives; our data suggest the unknown-
alternative price is the dominant practical term precisely in the
regimes where stratification's rate advantage is largest.

If any of this is useful — the testbed, the LLM-domain benchmark of
your method, or the anomaly — I would be glad to share everything, and
would welcome any pointers on the crossover question.

Respectfully,
Hao Lin

---

*Draft notes for Hao: (1) verify the fitted-law sentence against
results_overhead_fit.txt before sending; (2) attach or link the repo
once you decide where to host it; (3) the claims above deliberately
credit their method's wins and flag our variant's fidelity limits —
keep that framing; (4) expect that they may know the answer to the
open question — that outcome is also a win.*
