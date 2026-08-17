# Resumable state — anytime-valid design selection

**Handoff document. Any agent picks this up cold. State lives in the
repo, not in context.** Last synced 2026-08-16 at commit HEAD. To
orient: read this, then FINDINGS.md (results), THEORY.md (the method +
theory thread), AUDIT_PREP.md (audit trail). Verify any claim with
`./reproduce.sh <script>` — 26/26 offline artifacts are byte-identical.

## The thesis (paper/DRAFT.md v4)

Sequential design selection is derivable in advance from three
pre-observable quantities — stratum heterogeneity ratio, decision
direction, margin. The underlying CS machinery (WSR, UI, Beta mixture)
is classical/prior work and credited as such; original here are the
boundary derivation+verification, the fourth expansion term, and the
relation gate.

## DONE and verified (artifact — checksum)

- Fourth expansion term derived: crossing residual = −½log(2π p\* q\*),
  zero fitted; per-point slope −1.398→−0.255 collapse. Proof in
  paper/BOUNDARY_THEOREM.md. (results_overshoot.txt — 0b7fa43558e3530f)
- Phase boundary derived (4 passes, anchors A1/A3 discriminating).
  (results_phase_curve.txt — c4a4720dbba3ccb8)
- Boundary VERIFIED, three-region form: above-band WSR 10/10; below-band
  3/3 resolving + 7 ties (ties are the finding: choice unmeasurable
  below the boundary). (results_phase_test.txt — 33adc872c71e5193)
- Margin-sweep test of the expansion: FAILED-as-frozen by 0.008 nats,
  d=0/d=2 excluded — the failure localized the o(1) term.
  (results_margin_sweep.txt — 73a11a759f542c5a)
- Two designed-method WINS: asymmetric shade prior halves worst-case
  staleness (results_asym_prior.txt — 0d923b6853d420cc); Kelly-floored
  WSR fixes the long-horizon pathology (results_kelly_floor.txt —
  2bc2c94a2101cde1). Both opt-in in src/.
- Relation gate (rules R1/R1b/R4/R5/R6/R7/R8) from a 16-defect census;
  artifact retrofit R4-clean. scripts/relation_gate.py.
- 110 tests green. Certifier is O(1)/block (21 µs/sample).

## OPEN — theory threshold (RESOLVED to an exact algorithm + named obstruction)

c_ren is EXACTLY COMPUTABLE for any (p*, tau, alpha, d, n0) by a finite
absorption recursion, zero fit (results_cren_exact.txt): the exact
value is -1.1700824 at (0.202,0.157,0.05,4,20), NOT the old -1.105
(MC noise). c_ren is a full function, not a scalar/universal constant.
The four-term expansion is now fully predictive in practice. OPEN: a
SCALAR closed form — obstruction NAMED (time-inhomogeneous noncommuting
killed kernel; C_j P_d do not commute across check times). Overshoot
has an asymptotic closed form (rho_d, Spitzer) with a finite-L gap;
selection an exact form with first-order zero. Peer attacking the
scalar reduction.

## OPEN — c_ren piece detail

**c_ren = −1.105 nats**, p\*-independent, decomposes numerically
(±0.13) as selection −0.68 + overshoot +0.23 + median-vs-mean −0.65.
- median-vs-mean (−0.65): **CLOSED** — Cornish-Fisher form
  −(γ₁/6)·sd(N)·V, within 0.084 nats zero-fit
  (results_cren.txt, scripts/derive_cren.py).
- selection: EXACT CLOSED FORM E[N·D(p̂‖p\*)] with first-order term
  exactly zero (Wald + Bregman identity, verified 2.7e-12). Corrected
  value 0.639 (repo C4's +0.681 was noise-high, rejected z=−12.6).
  SCHEDULE-DEPENDENT — carries the check period d. results_selection.txt.
- overshoot: ASYMPTOTIC constant CLOSED — rho_d = E[H_d^2]/(2E[H_d]),
  block-skeleton ladder height via Spitzer (rho_4=0.1703), verified two
  ways (results_overshoot_closed.txt). The measured 0.228 at L=3 is
  finite-L; the 0.170->0.228 gap is OPEN. Ladder height, NOT a lattice
  span (my earlier guess was wrong).
Test data frozen (results_margin_sweep.txt); any closed form is checked
against it with nothing fitted. NOTE: c_ren is schedule-dependent (a
finding); results_overshoot.txt C4 is STALE (regenerate with the
corrected selection + higher reps); the three-piece decomposition does
NOT close exactly once the inflated selection is fixed.

## OPEN — measurement threshold

Below-band region unresolvable at 200 reps/arm (7/13 ties). Per the
fork: this is a NOISE-limited threshold — the correct response is a
better instrument, not more reps. First ask whether comparing MEDIANS
is right; try full-distribution (stochastic dominance / paired quantile
band), which may resolve at the same rep count. scripts/run_phase_test.py
is the harness; streams are CRN-seeded.

## FROZEN and executable by anyone

- Design-space PARTITION derived AND VERIFIED: two regions
  (single | WSR), UI dominated. Single|WSR by phase v2b; UI-dominated
  by results_partition_test.txt (0/10 UI outright wins, 0/3000 wrong).
  Both claims now empirical.

## OPEN — field-opening questions (Hao directive, in sequence)

1. PARTITION (near done): run the three-arm verification; then paper 4
   becomes a derived partition.
2. OPTIMAL STRATIFICATION: DONE, rev 2 (results_gain.txt supersedes
   the universal claim in results_optimal_k.txt). K* is POPULATION-
   dependent: census on the ten real pools is K*=1 on 4, K*=2 on 4
   (llama3.2 2.8x faster stratified), K*=4 on 2; gains 1.06-4.31x.
   Finite-interior-K* prediction CONFIRMED on 4 pools. "K*=1 explains
   UI-domination" RETRACTED (WSR beats UI, single does not, on 6/10).
   Follow-ups: WSR block-granularity K*; temp>0 per-prompt pools for
   finer K.

## IN FLIGHT — HIGHEST-VALUE TARGET (Hao directive): derive floored-arm d

Derive the Kelly-floored WSR expansion dimension d with zero fit; the
measured target-not-tuning value is d = +1.27 (results_wsr_expansion.txt
P3; within-implementation, survives the simulator discrepancy). If it
closes, both sides of the phase boundary are derived on the floored arm
and the design map becomes PROVABLE (BOUNDARY_THEOREM 4.3). Method:
(1) exact floored schedule from src/eval_harness/stats/wsr_kelly_floor.py
— where the floor binds; (2) log wealth = S_T + xi_T (positive-drift
walk + perturbation, mirroring the Beta-mixture decomposition);
(3) d from xi_T's log n coefficient — candidate mechanism: one-parameter
adaptive-Kelly regret, Sum_j (V(lam*)-V(lam_j)) ~ (c/2) log n with
c = |V''(lam*)| x AVar(plug-in lam) computed exactly from the 16-atom
block distribution; (4) PREDICT BEFORE COMPARING to 1.27; severity_sim
the window; state (d_check, n0); R9 applies. If it does not close, name
the obstruction precisely (that settles 4.3 permanently as a scoped
limitation — a publishable negative). A first derivation agent died on
a model usage limit mid-prototype (no files written); relaunched.
Everything else (safety domain, new arms) HELD until this resolves.

## HELD for Hao's explicit go (do NOT start autonomously)

- Task #50 LLM-safety domain test: selecting/running a jailbreak or
  harmful-compliance corpus is a sensitive scope decision — held.
- After it, the RLA bridge (Spertus construction already implemented/
  validated → risk-limiting-audit framing; lower risk, writeup-shaped).
- Sequence is safety → RLA per the scope decision.

## Month 3 — HUMAN-BOUND, untouched

Library packaging, interactive design-map demo selector, physical
board, interview drills. These are Hao's, not agent work. Do not start.

## Deprioritized (open but low value)

- #34 McNemar release-pair comparison; #36 HumanEval third benchmark.
  Both optional; neither on the critical path.
