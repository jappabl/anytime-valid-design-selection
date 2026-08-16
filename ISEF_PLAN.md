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

## OPEN — theory threshold (the number to hit)

**c_ren = −1.105 nats**, p\*-independent, decomposes numerically
(±0.13) as selection −0.68 + overshoot +0.23 + median-vs-mean −0.65.
- median-vs-mean (−0.65): **CLOSED** — Cornish-Fisher form
  −(γ₁/6)·sd(N)·V, within 0.084 nats zero-fit
  (results_cren.txt, scripts/derive_cren.py).
- selection: EXACT CLOSED FORM E[N·D(p̂‖p\*)] with first-order term
  exactly zero (Wald + Bregman identity, verified 2.7e-12). Corrected
  value 0.639 (repo C4's +0.681 was noise-high, rejected z=−12.6).
  SCHEDULE-DEPENDENT — carries the check period d. results_selection.txt.
- overshoot (+0.23): the hard piece — LITERATURE PASS (lattice/periodic
  boundary overshoot: Lotov, Siegmund lattice renewal; the every-4th
  check makes this a periodic-boundary crossing, not a smooth one).
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

- Design-space PARTITION derived and frozen (results_partition.txt):
  two regions (single | WSR), UI dominated 0/84. Single|WSR verified
  (phase v2b); the UI-dominated claim needs a THREE-ARM harness run
  (extend scripts/run_phase_test.py with a UI arm at partition cells)
  — the frozen-but-unrun verification.

## OPEN — field-opening questions (Hao directive, in sequence)

1. PARTITION (near done): run the three-arm verification; then paper 4
   becomes a derived partition.
2. OPTIMAL STRATIFICATION (bigger): fix the estimand as the POPULATION
   mean (weights prop to stratum sizes) so the target is
   partition-invariant, then minimize the V_rr-driven crossing time
   over partitions -> predicts a FINITE optimal K (learning tax grows,
   rate gain saturates). Unasked in this literature.

## IN FLIGHT

- None. Repo clean at HEAD.

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
