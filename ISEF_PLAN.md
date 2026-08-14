# Three-Month Plan: 2026-08-14 → 2026-11-14

Target category: **Systems Software (SOFT)**.
Reach item: **formalize the boundary-stratum result**.

Governing principle: **the project does not need more results.** It needs
one theoretical claim severely tested, one clause proved, and the design
map compiled into working software. Every item below either closes a
stated limitation or converts an existing finding into something a
non-specialist can use. Nothing below adds a new regime.

Each completed item updates `AUDIT_PREP.md` per the documentation-sync
rule.

---

## Month 1 (Aug 14 → Sep 15): the designed experiment + real trajectories

### 1.1 Designed rate-variation test of the expansion — THE centerpiece

The severe live test (027e72c) failed with no information: bootstrapping
its C3 ratio statistic gives P(landing inside the pre-registered window)
= 0.56 at 20 reps/arm. The window was narrower than the sampling noise.
Replace the ratio-of-two-medians design with a direct test.

**Design.**
- Sweep the induced margin |p* − τ| across a grid, varying p* by stratum
  reweighting of existing pools and τ by choice. Many points, not two.
- For each grid point, replay to the stopping time, many reps.
- Test `n·V = log(1/α) + (d/2)·log n + c` directly against a
  pre-registered residual band, d = 1 and c in closed form for the
  single-stream arm (zero fitted parameters, as §5.2).
- **Power the test before freezing it.** Compute reps so the acceptance
  window is narrower than the statistic's sampling noise. This is what
  `severity_sim.py` failed to do and is the whole reason the last test
  was uninformative.

**Blocking prerequisite — fix `scripts/severity_sim.py`.** It can
currently pre-register criteria that are *jointly unsatisfiable* and
disclose a severity computed as though they were not. In the severe test,
once the τ1 arm closed at median 982, C2 required median(τ2) ≤ 240 while
C3 required ≥ 253.4; the observed 252 fell in the dead zone and failed
both. Add a compatibility check across criteria conditional on a realized
first arm, and a power calculation per criterion. This fix is itself a
methodology contribution and belongs in §6.

**Also resolves:** Limitation 7 (d = 0 vs d = 1 not identifiable at
200 reps × 6 points) if the grid is swept wide enough.

Cost: zero. Local inference only.

### 1.2 Real release trajectories

Limitation 10 says the chain and router trajectories are synthetic,
anchored to real epoch-2 rates. Replace them with actual model version
history, same prompts, same validator, same protocol:

- Meta lineage: llama3.2-3b, llama3.1-8b, llama3-8b
- Alibaba lineage: qwen2.5-7b, qwen2-7b

This makes the entire warm-start arc (§4.4) real rather than simulated —
the transfer prior now comes from a genuinely prior model version, which
is the deployment claim the section actually wants to make. Re-run the
chaining and staleness results against it.

**Also resolves:** Limitation 8 (no cross-vendor live runs) — live arms
on the local lineages cost nothing.

Cost: zero. Runs unattended overnight.

---

## Month 2 (Sep 15 → Oct 15): formalization, auto-selection, consolidation

### 2.1 Prove the boundary-stratum contribution

§5.3 already contains the proof sketch: the Beta(1,1) marginal of an
all-success stratum is 1/(n+1), so such a stratum contributes ~log n
rather than ½·log n to the mixture regret — which is exactly the
`d = K + #boundary-strata` rule.

Formalize it:
- State the theorem and its regularity conditions precisely.
- Prove the marginal identity and the resulting regret contribution.
- Connect to Xie & Barron (1997) and Watanabe's RLCT as the classical
  boundary/singular coefficient.
- State explicitly what is **not** proved: the full expansion, overshoot,
  median-versus-mean, tracking terms (Limitation 12 stands, narrowed).

This upgrades §5.3 from "a coarse regularity that survives where it is
testable, not a law" to "one clause proved, the remainder empirical."
That is a real contribution and the single largest available Creativity
gain.

### 2.2 Compile the design map into the API

`certify()` already exists as a practitioner API (f623f51). Extend it to
**select the design automatically** from a measured stratum ratio:
measure pool heterogeneity from a pilot, then dispatch to WSR blocks,
directed allocation, single stream, or warm-start UI per the §4 map.

Then **test the auto-selection**: across all eight pools and both
decision directions, how often does the automatic choice match the oracle
best design, and what does it cost when it misses? That is a new, cheap,
legitimate experiment that directly validates the map's practical claim —
and it is the strongest possible SOFT-category framing, because it turns
the paper's central finding into software that does the thing.

### 2.3 Consolidate — cut, do not add

- Rewrite the abstract and §1.1 to lead with findings. Keep every
  disclaimer; move them out of first position. The heterogeneity axis,
  the drift-asymmetry reversal with its diagnosed mechanism, and the
  information-bound guard are original and currently buried.
- Move the router arc (§4.4 tail) and the TaSC/invention round (§4.5) to
  an appendix. Excellent science; a judge has no time for it in the main
  line.
- Doc-sync fixes: the draft says "76 passing tests" (actual: **106**) and
  lists Figures 7–9 as "in preparation" when `fig7_drift_budget.png`,
  `fig8_frontier.png`, `fig9_design_map.png` have existed since
  2026-08-12.
- Position the severe-test failure deliberately, before a judge frames it
  for you: hypothesis → severe test → failure → diagnosis of why the test
  was underpowered → redesigned experiment → verdict.

---

## Month 3 (Oct 15 → Nov 14): presentation

Presentation is 35 of 100 rubric points — more than methodology and
execution combined. This is not the leftover month.

### 3.1 Ship the library

Pip-installable, documented, `reproduce.sh` as a live one-command
demonstration of byte-identical reproduction. For SOFT judges, a working
installable tool with an honest test suite is the strongest possible
artifact.

### 3.2 Upgrade the demo

`demo/index.html` ("Watch an evaluation stream with continuous peeking")
is the one asset a non-specialist understands in ten seconds — the
fixed-n interval misses 47.7% under peeking, the betting CS holds at
3.6%. Run it live at the board.

Add a second view: an **interactive design-map selector** — enter your
pool heterogeneity and decision direction, get the recommended design and
its expected sample count. It makes the contribution usable in front of
the judge.

### 3.3 Board

Built around three things only: the live demo, the zero-fit table
(§5.2, −2.6%…+6.8% with nothing fitted), and the design map figure.
Everything else is backup.

### 3.4 Interview drills

Adversarial, cold, at a whiteboard, until fluent. The four places a sharp
judge will push hardest:

1. The C3 resolution deficit — why the failed test carried little
   information, and how the redesign fixes it.
2. d = 0 vs d = 1 identifiability (Limitation 7; corr(d̂, ĉ) = −0.994).
3. The per-sample mixture CS having empirical validity only on non-iid
   stratified streams (Limitation 9).
4. Why α-splitting is not data-dependent switching.

Plus: derive the (d/2)·log n term, explain what an e-process is, and
explain why the conservation hypothesis was falsified.

---

## Explicitly not doing

- A fifth regime, or more models beyond the trajectories.
- Router v3. Stopping at v2 was correct; restarting undoes the best
  epistemics in the project.
- A fifth invention round. Four lost, and that is a finding.

## Open item

The assistance-disclosure question should be settled well before the
Month 3 work, not after.
