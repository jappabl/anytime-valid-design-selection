# The Beta-mixture certification expansion: what is proved

**Hao Lin — formalization companion to paper/DRAFT.md §5.3 and §4.**

This note states precisely what the project proves versus measures. It
formalizes the one clause that is fully derivable — the fourth term of
the single-stream expansion — and states the phase boundary as a
corollary whose remaining input (WSR's overhead envelope) is empirical,
not proved. Every numerical claim is checked in
[results_overshoot.txt](../results_overshoot.txt) (identity C1, slope
C2, decomposition C4) and [results_phase_test.txt](../results_phase_test.txt)
(the boundary verification). Scope is stated plainly at the end.

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

**Claim.** Let p̂ = f/n with p̂ ∈ (0,1) bounded away from 0 and 1. Then

    log E_n = n · KL(p̂ ‖ τ) − ½ log n + ½ log(2π p̂ (1−p̂)) + r_n,   (2)

with |r_n| ≤ (1/12n)(1/p̂ + 1/(1−p̂) − 1) + O(1/n), where
KL(a‖b) = a log(a/b) + (1−a) log((1−a)/(1−b)).

**Proof.** Write B(1+f, 1+s) = Γ(1+f)Γ(1+s)/Γ(2+n). Apply Stirling in
the form log Γ(1+m) = m log m − m + ½ log(2π m) + 1/(12m) − … to each of
the three Gamma factors (with arguments f, s, n+1, absorbing the +1
shifts into the O(1/n) remainder). The −m and leading m log m terms
regroup: f log f + s log s − (n+1) log(n+1) = −n·H(p̂) + O(log n / n)
after factoring n, where H is binary entropy in nats. Subtracting the
null log-likelihood f log τ + s log(1−τ) converts −n·H(p̂) minus that
term into +n·KL(p̂‖τ) exactly. The three ½ log(2π·) half-terms collect to
½ log(2π f s /(n+1)) = ½ log(2π n p̂(1−p̂)) + O(1/n) = ½ log n +
½ log(2π p̂(1−p̂)) + O(1/n). The 1/(12m) terms give the stated remainder
bound. ∎

**Corollary (crossing residual).** At the stopping time log E_N = log(1/α),
so the median crossing n satisfies

    n · KL(p\*, τ) = log(1/α) + ½ log n − ½ log(2π p\* q\*) + c_ren,   (3)

with q\* = 1−p\*. The p\*-dependent constant is **derived**:
c_Laplace(p\*) = −½ log(2π p\* q\*). The residual carries one further
p\*-independent term c_ren (selection + discrete-check overshoot +
median-vs-mean), stated open in §4.

## 3. What the theorem buys (measured, zero fitted parameters)

Eq. (3) predicts the crossing residual R(p\*) := n·KL − log(1/α) −
½ log n equals −½ log(2π p\* q\*) + c_ren. On the frozen 17-point margin
sweep ([results_margin_sweep.txt](../results_margin_sweep.txt),
committed before this derivation existed):

- **Identity C1.** Eq. (2) matches Eq. (1) to max 0.0037 nats over a
  (p, n) grid, inside the Stirling bound 0.0063 — the theorem is
  numerically exact at the stated order.
- **Slope C2.** Subtracting c_Laplace(p\*) collapses the residual's
  per-point p\*-slope from −1.398 to −0.255 nats and the per-point
  correlation from −0.616 to −0.133, with **nothing fitted** — 82% of
  the measured p\*-structure is the derived term.
- **Decomposition C4.** The residual c_ren ≈ −1.10 nats decomposes
  numerically (within 0.13) into selection −0.68, discrete-check
  overshoot +0.23, median-vs-mean −0.65.

## 4. What is NOT proved (stated open)

1. **c_ren in closed form.** The p\*-independent renewal constant
   (≈ −1.10 nats) is measured and numerically decomposed, not derived.
   Its closed form requires Woodroofe's nonlinear-renewal ladder-height
   distribution for Bernoulli log-likelihood increments — the named
   Month-2+ open clause. C3 (its point-spread ≤ 0.25 nats) marginally
   fails at 0.286, i.e. it is *nearly* but not exactly p\*-independent.
2. **The other statistics.** Eqs. (2)–(3) are the single-stream arm only.
   The UI product e-process has d = K + #boundary empirically (a coarse
   regularity, downgraded to 2-of-3 and shown margin-structure-dependent
   in the lineage test), not a theorem. WSR's overhead is a measured
   two-regime envelope, not derived.
3. **The boundary as a theorem.** §4's phase boundary equates Eq. (3)
   (derived) with WSR's *empirical* envelope; it is therefore a
   verified prediction (v2b: above-band 10/10, below-band 3/3 resolving
   + 7 ties), not a proof. Deriving WSR's own fourth term would close
   this; it is open.

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
