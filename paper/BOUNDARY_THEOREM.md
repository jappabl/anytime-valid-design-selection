# The Beta-mixture certification expansion: what is proved

**Hao Lin — formalization companion to paper/DRAFT.md §5.3 and §4.**

This note states precisely what the project proves versus measures. It
formalizes the one clause that is fully derivable — the fourth term of
the single-stream expansion — and states the phase boundary as a
corollary whose remaining input (WSR's overhead envelope) is empirical,
not proved. Every numerical claim is checked in
[results_overshoot.txt](../results_overshoot.txt) (identity C1, slope
C2), [results_cren_exact.txt](../results_cren_exact.txt) (the exact
c_ren value, superseding the old C4 decomposition), and
[results_phase_test.txt](../results_phase_test.txt) (the boundary
verification). Scope is stated plainly at the end.

## 1. Setup

A single-stream certifier draws iid Bernoulli(p\*) outcomes X_1, X_2, …
(failure = 1) and tests H_0: p ≤ τ against p\* > τ using the
Beta-(1,1)-mixture e-value. With f failures and s = n − f successes after
n draws, the log e-value against the boundary null p = τ is

    log E_n = log B(1+f, 1+s) − [ f log τ + s log(1−τ) ],          (1)

where B is the Beta function. The stopping time is
N = inf{ n : log E_n ≥ log(1/α) }. This is the exact statistic the code
computes (`StratifiedUICS(k=1)`), verified against Eq. (1) to 7×10⁻¹⁴ in
the test suite.

## 2. Theorem (fourth-order expansion of the crossing level)

**Claim.** Let p̂ = f/n with f ≥ 1 and s = n − f ≥ 1. Then

    log E_n = n · KL(p̂ ‖ τ) − ½ log n + ½ log(2π p̂ (1−p̂)) + r_n,   (2)

with the EXPLICIT remainder interval (rigorous, no unspecified tails)

    C_n − 1/(360 f³) − 1/(360 s³)  ≤  r_n  ≤  C_n + 1/(360 (n+1)³),
    C_n = A_n + 1/(12f) + 1/(12s) − 1/(12(n+1)),
    A_n = 1 − (n + 3/2) log(1 + 1/n)  = −1/n + 5/(12 n²) + O(n⁻³),

and, uniformly for p̂ bounded away from {0, 1},

    r_n = [1/p̂ + 1/(1−p̂) − 13] / (12 n) + 1/(2 n²) + O(n⁻³).

(The coefficient is −13, not −1: the (n+1) shift in Γ(2+n) contributes
−12/(12n) through A_n. An earlier version of this document displayed
−1 and appended an untestable O(1/n) tail; both were corrected under
adversarial audit — see §3 and AUDIT_PREP.)

**Proof.** Write B(1+f, 1+s) = Γ(1+f)Γ(1+s)/Γ(2+n) and apply the
explicit Stirling form log(m!) = (m+½)log m − m + ½ log 2π + 1/(12m) +
ε_m with −1/(360 m³) < ε_m < 0 to each factor (arguments f, s, n+1).
Since f + s = n, the leading terms give EXACTLY

    f log f + s log s − n log n = −n·H(p̂),

with H binary entropy in nats. The Gamma denominator carries n+1, not
n; the shift is the exact deterministic quantity

    (n+1) log(n+1) − n log n = log n + (n+1) log(1 + 1/n),

whose −log n cancels against the +½ log(f s/(n+1)) half-log terms'
excess and whose remainder, combined with the linear −m terms' +1,
collects into A_n = 1 − (n + 3/2) log(1 + 1/n) exactly. Subtracting
the null log-likelihood f log τ + s log(1−τ) converts −n·H(p̂) into
+n·KL(p̂‖τ) exactly; the half-log terms collect to ½ log(2π f s/(n+1))
= ½ log(2π n p̂(1−p̂)) − ½ log(1 + 1/n) (the last piece absorbed into
A_n's display above). The 1/(12m) terms and ε bounds give the stated
interval, with nothing unspecified. ∎

(An earlier draft asserted f log f + s log s − (n+1) log(n+1) =
−n·H(p̂) + O(log n / n); the true residual of that line is O(log n)
and Eq. (2) survived only because the −log n − 1 cancels downstream.
The audit lineage (gpt-5.6-sol) found this; the repaired proof above
displays the cancellation explicitly rather than hiding it in a wrong
order estimate.)

**Definition (crossing residual).** Substituting p̂_N → p\* in Eq. (2)
at the stopping time is NOT an identity: the pathwise gap is
θ·M_N + N·D(p̂_N‖p\*) with θ = log[p\*(1−τ)/(τ(1−p\*))] and
M_N = F_N − p\* N (the Bregman decomposition). Wald's identity kills
the first term in expectation (E[M_N] = 0, verified −0.01 ± 0.05);
the second is strictly nonnegative — it is the SELECTION term, exact
value 0.6404 at (d, n0) = (4, 20) (results_selection.txt). Eq. (3) is
therefore a DEFINITION of c_ren (absorbing selection, overshoot, and
the median convention), not a corollary of Eq. (2): the median
crossing n satisfies

    n · KL(p\*, τ) = log(1/α) + ½ log n − ½ log(2π p\* q\*) + c_ren,   (3)

with q\* = 1−p\*. The p\*-dependent constant is **derived**:
c_Laplace(p\*) = −½ log(2π p\* q\*). The residual carries one further
term c_ren = c_ren(p\*, tau, alpha, d, n0) — NOT p\*-independent and
NOT a universal scalar; it is a full function, EXACTLY COMPUTABLE by a
finite absorption recursion (§4, results_cren_exact.txt).

## 3. What the theorem buys (measured, zero fitted parameters)

Eq. (3) predicts the crossing residual R(p\*) := n·KL − log(1/α) −
½ log n equals −½ log(2π p\* q\*) + c_ren. On the frozen 17-point margin
sweep ([results_margin_sweep.txt](../results_margin_sweep.txt),
committed before this derivation existed):

- **Identity C1 (rev 2).** The original C1 check compared the max grid
  error (0.0037, at n = 200, p̂ = 0.5) against an ad hoc threshold
  (the displayed −1 bound × an unexplained 1.5, evaluated at a
  different grid point) — the error EXCEEDED the displayed bound and
  the check passed anyway. Audit finding; now gate rule R4b. C1 rev 2
  tests the rigorous interval of §2 pointwise: every grid point's r_n
  lies inside [C_n − 1/(360f³) − 1/(360s³), C_n + 1/(360(n+1)³)] up to
  float64 accumulation (≤ 3×10⁻¹¹ observed; the peer's high-precision
  13,579-point grid has zero failures). The expansion was always
  right; the old check was not testing it.
- **Slope C2.** Subtracting c_Laplace(p\*) collapses the residual's
  per-point p\*-slope from −1.398 to −0.255 nats and the per-point
  correlation from −0.616 to −0.133, with **nothing fitted** — 82% of
  the measured p\*-structure is the derived term.
- **Exact value.** c_ren = −1.1700824 at
  (p\*, τ, α, d, n0) = (0.202, 0.157, 0.05, 4, 20), discrete-median
  convention, computed exactly by the absorption recursion (verified to
  7 decimals against an independent transfer-operator; the earlier
  8000-rep Monte-Carlo −1.105 was noise-high by 0.065). The
  three-piece selection/overshoot/median decomposition was an
  approximate diagnostic and is SUPERSEDED by the exact recursion — it
  does not sum exactly.

## 4. What is NOT proved (stated open)

1. **c_ren scalar closed form.** c_ren is EXACTLY COMPUTABLE for any
   (p\*, τ, α, d, n0) by the finite absorption recursion (zero fit) —
   so the four-term expansion is fully predictive in practice. What is
   OPEN is a scalar elementary/special-function reduction: the
   obstruction is a time-inhomogeneous, NONCOMMUTING killed kernel
   (continuation-then-draw operators do not commute across check
   times), a genuine mathematical obstruction, not an unfitted
   constant. The overshoot piece has an asymptotic closed form
   (ρ_d = E[H_d²]/(2E[H_d]), Spitzer) but a finite-L gap (0.170 vs
   0.228 at α = 0.05); selection has an exact closed form
   E[N·D(p̂‖p\*)] with first-order term exactly zero (Wald).
2. **The other statistics.** Eqs. (2)–(3) are the single-stream arm only.
   The UI product e-process has d = K + #boundary empirically (a coarse
   regularity, downgraded to 2-of-3 and shown margin-structure-dependent
   in the lineage test), not a theorem. WSR's overhead is a measured
   two-regime envelope, not derived.
3. **The boundary as a theorem.** §4's phase boundary equates Eq. (3)
   (derived) with WSR's *empirical* envelope; it is a verified
   prediction (v2c, results_phase_test.txt: below-band 4/4 resolving
   + 6 ties, above-band 3/3 — 10/10 counting v1's seven — and a
   wrong-certification rate of 0/6000), not a proof. The v2b counts
   displayed here earlier (below-band 3/3 resolving + 7 ties) were
   scored by a paired bootstrap of the PLAIN median of a tied lattice,
   whose actual size was 1.8–2.6% against a nominal 5%: a
   conservative interval inflates ties and states a resolution it
   does not have. That is a SCORED defect (the R1b class, one level
   down), not a re-scoring for a pass — v2c holds the estimand, arms,
   seeds, pools, and frozen predictions fixed and replaces only the
   estimator with a calibrated Harrell-Davis quantile (measured size
   4.4–5.2%); the pre-stated consequence, exactly one below-band
   point moving from tie to resolving, is what occurred. The
   stock-WSR side's status
   (results_wsr_expansion.txt, frozen test on the SHIPPED classes):
   the externally-derived "no expansion — nV ~ A log n (loglog n)²"
   claim is a HYPOTHESIS, not established. The form is consistent
   (P2: max deviation from mean 6.1%, within the ±10% criterion) but
   the pre-registered divergence criterion FAILED (P1: nV/log n grew
   1.23× vs the 1.5× threshold, non-monotone at the deep end); the
   external lineage's 1.80× came from a REIMPLEMENTATION of the
   schedule, 43% off the shipped code at matched settings, and is
   withdrawn. The derive-WSR's-fourth-term route is therefore OPEN
   AND UNRESOLVED — neither derived nor proven impossible. (An earlier
   revision of this paragraph asserted the no-expansion claim as
   settled while the frozen test of it was still running; the test
   then failed P1. Recorded in the miss ledger; now gate rule R9.)
   What the same frozen test DID establish, within-implementation
   (identical code, ladder, and seeds, so absolute-level bias cancels
   in the contrast): the Kelly-FLOORED variant restores the
   regularity the stock schedule lacks — nV/log n drift 1.2% vs stock
   22.9% across the ladder — so an expansion EXISTS on the floored
   arm. Chasing it (results_floor_d.txt) settled the regular half and
   restructured the rest. **d = 1 is DERIVED** and verified on the
   post-warmup idealization: once the Kelly floor binds the plug-in
   bet is first-order efficient (c_reg = |V''(λ\*)|·AVar → 1, spread
   0.9619…0.9971 across the ladder), so the regular arm costs exactly
   (1/2) log T — the same as the single stream. The SHIPPED floored
   class is that idealization plus a warmup over-bet, charged +0.5071
   in d by the slope attribution (predicting +1.5301; attribution sum
   and direct regression agree to four decimals). That contribution
   decays as 1/log t_c, so the literal shipped class has NO fixed d
   either — only a slowly drifting effective d, milder than stock's.
   The earlier measured (d, c) = (+1.27, −3.35) is SUPERSEDED: the
   externally reported τ-grid defect (every rung mid-cell at a fixed
   +0.0005 offset, biasing V by 2.8% → 10.2% down the ladder) is
   CONFIRMED, but its claimed DIRECTION is REFUTED — correcting it
   moves d AWAY from 1, to +1.3614 ± 0.2006 (intercept −3.6011) at 3×
   reps, with the stock arm at +4.4969 under the same correction; the
   only arithmetic yielding a sub-1.27 figure scores at a grid point
   ABOVE τ, which cannot hold n fixed and is invalid. Both
   pre-registered windows (P-A, the idealization d = 1; P-B, the
   warmup-corrected +1.5301) contain the measurement, so the frozen
   adjudication is UNRESOLVED, and {1, 1.12, 1.27, 1.53} are mutually
   indistinguishable at any feasible rep budget on this ladder. The
   floored arm remains the live route to a full boundary theorem, now
   with its regular half derived rather than fitted.

## 5. Relation to classical results

Eq. (3) is the finite-sample form of the Pollak–Siegmund (1975) /
Woodroofe (1982) sequential expansion; the ½ log n term is the
Krichevsky–Trofimov / Clarke–Barron (1990) mixture regret for one
parameter; c_Laplace is the Laplace-approximation constant of the
Beta(1,1) mixture, i.e. the d=1 case of the Xie–Barron (1997) /
Watanabe RLCT boundary coefficient. **The contribution is not the
expansion** — it is the calibration on real LLM-evaluation data with
the fourth term made explicit and verified zero-fit, plus the boundary
corollary. Priority for the underlying machinery is classical and is
credited as such throughout the paper.
