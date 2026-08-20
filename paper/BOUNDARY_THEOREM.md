# The Beta-mixture certification expansion: what is proved

**Hao Lin — formalization companion to paper/DRAFT.md §5.3 and §4.**

This note states precisely what the project proves versus measures. It
formalizes the one clause that is fully derivable — the fourth term of
the single-stream expansion — and states the phase boundary as a
corollary whose remaining input (WSR's overhead envelope) is empirical,
not proved. Every numerical claim is checked in
[results_overshoot.txt](../results_overshoot.txt) (identity C1, slope
C2), [results_cren_exact.txt](../results_cren_exact.txt) (the exact
c_ren value, superseding the old C4 decomposition),
[results_phase_test.txt](../results_phase_test.txt) (the boundary
verification), and — for the WSR side of §4 —
[results_wsr_envelope.txt](../results_wsr_envelope.txt) (the derived
envelope law, checksum `c052f57840f4f670`) together with
[results_floor_d.txt](../results_floor_d.txt) and the 10,000-rep
journal `data/floor_ladder_long.jsonl`. Scope is stated plainly at the
end, and §4 states one impossibility whose scope is a named function
class rather than "all closed forms".

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
finite absorption recursion (§4, results_cren_exact.txt), and PROVED
in §4 to admit no scalar closed form within the class stated there.

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

1. **c_ren scalar closed form: PROVED IMPOSSIBLE in the stated class;
   the exact algorithm is retained and is the answer.** c_ren is
   EXACTLY COMPUTABLE for any (p\*, τ, α, d, n0) by the finite
   absorption recursion (zero fit), so the four-term expansion is fully
   predictive in practice. What was listed here as OPEN — a scalar
   elementary/special-function reduction — is now CLOSED NEGATIVELY.
   The argument does not use the kernel obstruction previously named
   (a time-inhomogeneous, NONCOMMUTING killed kernel, continuation-
   then-draw operators failing to commute across check times); that
   obstruction stands but is no longer what carries the result.

   THE MEDIAN-JUMP ARGUMENT. Crossings occur only on multiples of the
   check period d, so the discrete-median crossing n_med is a STEP
   function of the barrier L = log(1/α): between steps n is constant
   and c_ren falls at unit rate in L; at a step n rises by d and c_ren
   jumps by ≈ d·V. The steps do not thin out. c_ren(L) therefore has
   INFINITELY MANY JUMPS of size ≥ d·V/2 > 0 for EVERY (τ, p\*), so no
   limit constant C₀ exists and no smooth scalar expansion can
   represent the function. Verified at the reference point
   (p\* = 0.202, τ = 0.157, d = 4): bound d·V/2 = 0.014263, reproduced
   jump 0.025740 (above the bound, as required). The proof is
   RESONANCE-FREE; the quasi-lattice resonance of the increment law
   only reinforces it (O(1) periodic phase at rational resonance,
   arbitrarily slow convergence nearby). Non-resonant cells admit
   pointwise leading asymptotics and nothing stronger. Reproduction
   trap, documented: differencing c_ren across a grid of L returns
   (jump − ΔL), not the jump — read the jump AT a step.

   SCOPE LIMIT, stated rather than elided. An absolute proof excluding
   every imaginable closed form would first have to fix the function
   class; no such theorem is claimed. What IS excluded is the class the
   question meant: SMOOTH FINITE-DIMENSIONAL RENEWAL REDUCTIONS, POWER
   SERIES in the natural parameters, UNIVERSAL THRESHOLDS, and
   SINGLE-EIGENVALUE FORMULAS. Inside that class the answer is *no*,
   not *unknown*. Note that the bound carries d EXPLICITLY: the check
   period sits inside the obstruction, which derives from first
   principles the schedule-dependence of c_ren that this project had
   previously only measured.

   THE TWO FINITE-L PIECES, split verdict. SELECTION is CLOSED: on top
   of the exact form E[N·D(p̂‖p\*)] with first-order term exactly zero
   (Wald), an exact likelihood-differentiation identity gives the
   leading finite-L behaviour Δ_sel = (1 + (1 − 2p\*)·θ)/(2L) + o(1/L)
   with θ as in §2 — INDEPENDENT of the check period d — overpredicting
   the exact value by 8.9% at L = 3 and ~5% by L = 20 (0.19743 vs an
   exact 0.181355 at the reference point). OVERSHOOT is REFUTED as any
   smooth finite-L correction: its asymptotic constant
   ρ_d = E[H_d²]/(2E[H_d]) (Spitzer) is an L → ∞ LIMIT, and the
   approach is controlled by a quasi-lattice near-resonance of the
   d-block increment law — at (p, τ, d) = (0.3, 0.2, 4) the k = 1 atom
   is 0.004871 against a lattice spacing 0.538997, 111× smaller, so the
   renewal phase never mixes, the error is visible past L = 200 and
   changes sign there. The finite-L gap (exact 0.228658 vs ρ_4 = 0.1703
   at α = 0.05) is exactly computable by the absorption recursion, is
   NOT closed in smooth form, and admits NO UNIVERSAL L THRESHOLD,
   since the resonance is (p, τ, d)-dependent. The absorption recursion
   is the operational answer.
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
   WHAT IS NOW DERIVED, and what it does not settle: the WSR overhead
   envelope's K-LINEAR LAW (d_K = 4.1407 − 0.4267·K,
   c_K = 0.9638·K − 8.9801, measured in results_wsr_k.txt) is derived
   ZERO-FIT by TWO INDEPENDENT ROUTES, mutually blind until frozen and
   each verified in-repo against the committed grids — a finite-window
   projection of the stock schedule's cumulative drift, and a loglog
   Kelly-deficit integral with warm-up t0 = K/(4p(1−p)) fixed by the
   SHIPPED prior sq0 = 1/4 (results_wsr_envelope.txt, checksum
   c052f57840f4f670: 4 of 4 frozen constants HIT). Two structural
   results come with it, both exact: WSRBlockCS is x → 1 − x
   EQUIVARIANT (lo(x) = 1 − hi(1−x) to 1.1e−16, crossing times
   bit-identical), so decision DIRECTION is not an independent axis but
   a reflection of the p\* axis; and the p\* carrier is the block
   skewness μ₃/μ₂² = (1 − 2p)/(p(1−p)), exact, K-free, odd under
   precisely that reflection. The measured K-linearity is a CHORD of a
   convex d(K), the convexity confirmed by the sign pattern (+,−,−,+)
   of the measured grid's own linear-fit residuals. THIS DOES NOT MAKE
   THE WSR SIDE DERIVED. Both routes overshoot the measured SLOPES by
   +4.4% / +9.6% in the same direction (intercepts agree to 1.4–1.6%),
   an unexplained K-dependent slope-damping term omitted by both; three
   candidates were scored against a criterion frozen in advance
   ((a) K-dependent, (b) damps both slopes, (c) leaves intercepts
   untouched) and ALL THREE were REFUTED — chord geometry (on a
   symmetric grid the OLS slope IS the midpoint tangent exactly, so the
   convexity cancels), median-versus-mean (hard-fails (c); also already
   inside route 2's first-passage operator; its 0.10-nat accuracy does
   not transfer, 0.170 avg / 0.481 max here), and finite-boundary
   overshoot (wrong sign, fails (b)). §4's bands therefore still use
   the MEASURED envelope, and the law is derived as a finite-window
   projection rather than as an asymptotic — consistent with, not a
   refutation of, the no-fixed-(d, c) hypothesis above.
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
   ABOVE τ, which cannot hold n fixed and is invalid. At that
   artifact's precision both pre-registered windows (P-A, the
   idealization d = 1; P-B, the warmup-corrected +1.5301) contained the
   measurement, so the frozen adjudication was UNRESOLVED.
   THE ADJUDICATION IS NOW RESOLVED, at 10,000 journaled reps on the
   same ladder and class (data/floor_ladder_long.jsonl, zero censored
   rungs). Scored in the DERIVATION'S OWN convention — at the binding
   grid point m = τ − 0.0005, which is the rate derive_floor_d.py
   itself uses (vstar_m, "grid-aligned scoring: rho = 1") — the ladder
   gives d = +1.5824 with bootstrap SE 0.1016 (4,000 within-rung
   resamples). That REJECTS the post-warmup idealization d = 1 at
   z = +5.73 and is CONSISTENT with the warmup-corrected +1.5301 at
   z = +0.51: P-A MISSES, P-B HITS. The earlier claim that
   {1, 1.12, 1.27, 1.53} are mutually indistinguishable at any feasible
   rep budget is WITHDRAWN.
   THE CONVENTION TRAP, recorded because it briefly inverted this
   verdict. The first analysis of the same 10,000 crossings scored at
   the NOMINAL mid-cell τ and returned d = +1.2071 ± 0.11, from which
   "d = 1.53 rejected, d = 1 not rejected" was recorded in the audit
   trail. That is the grid bias this very artifact had already
   identified and corrected: ρ = V\*(τ)/V\*(m) < 1 and FALLS down the
   ladder, so scoring at τ_nom depresses the deep rungs more and biases
   d DOWNWARD. One dataset, two conventions, opposite verdicts; the
   corrected reading is the one above. Scoped honestly: the shipped
   class's warmup term decays as 1/log t_c, so it has no fixed d, and
   what is measured here is an EFFECTIVE d over this ladder's horizon
   window (n ≈ 1.8k–38k). The floored arm remains the live route to a
   full boundary theorem, now with its regular half derived rather than
   fitted and its shipped half measured in agreement with the
   warmup-corrected derivation over the reachable window.

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
