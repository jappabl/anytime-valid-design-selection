# Defense Guide: Owning This Project

*For Hao. A judge's job is to find out whether you understand what you
present. This is the material to internalize — twelve questions you WILL
be asked in some form, answer sketches to reconstruct (not memorize),
and exercises to do by hand. FINDINGS.md is the source; every claim
there traces to an artifact you can re-run with `./reproduce.sh`.*

## The twelve questions

**1. Why does "peeking" at results invalidate a normal confidence
interval?**
A 95% CI is calibrated for ONE look at a pre-fixed sample size: the 5%
error budget is spent once. Checking after every sample gives hundreds
of chances to catch the interval in a random excursion — the chance
that it is EVER wrong across n = 1..200 is what matters, and we
measured it at 47.7% for Wilson on real streams. Analogy: a smoke alarm
with a 5% false-alarm rate per test, tested 200 times.

**2. What makes a confidence sequence "anytime-valid"?**
It controls the probability that the true value is EVER outside the
interval, over all sample sizes simultaneously: P(∃n: p ∉ CI_n) ≤ α.
Any stopping rule inherits validity because whenever you stop, you are
inside that "ever" event's complement with probability ≥ 1−α.

**3. What is an e-value/e-process and why does Ville's inequality give
validity?**
An e-process is a running product of fair bets: under the null, its
expected value never exceeds 1. Ville's inequality says a nonnegative
supermartingale exceeds 1/α with probability ≤ α — ever. So "reject
when the bet has multiplied wealth by 20" is a 5%-error test at ANY
time. Our Beta-Bernoulli version: the bet is the Bayes predictive
probability divided by the null probability; the product telescopes to
marginal-likelihood / null-likelihood (be able to show this for n=2).

**4. Why are blocks iid when single stratified draws are not?**
Round-robin draws cycle through strata, so consecutive observations
have different means — not identically distributed. But each complete
block (one draw per stratum) has the same joint distribution as every
other block, independently. The block MEANS are therefore iid bounded
variables with mean exactly p\* — and any CS for iid bounded means
applies with zero caveats. That is the entire stratify→block→bet idea.

**5. Why does mid-block peeking break things?**
Two ways. Bias: stopping mid-block systematically leaves the
last-in-rotation strata undersampled — if the hard stratum is last,
p̂ is systematically low at stopping. Coverage: the per-sample mixture
CS is a bet calibrated against iid Bernoulli(p\*); a stratified stream
is LESS variable, which makes the null LESS plausible than assumed and
inflates the e-value — we exhibited exact-DP configurations with
coverage down to 75%. Both failures vanish if you only evaluate the
stopping rule at complete blocks.

**6. Why did the sophisticated methods (GROW, TaSC) lose?**
GROW: greedy growth-chasing against a least-favorable null that
re-optimizes — the null escapes through whatever stratum you neglect;
plus, without forced exploration, early bad estimates lock in. TaSC
fixed both by solving the max-min game, and it is sound — but learning
K parameters costs ~(K/2)·log n of e-value growth, plus tracking and
exploration overhead, and at every margin testable within n = 4000
that overhead exceeds the game-value advantage. Know the number: TaSC
ran ~6× above its own information bound.

**7. Why does the SPRT — the "optimal" sequential test — fail here?**
Wald's optimality is between two SIMPLE hypotheses p₀ and p₁. A
certification claim is COMPOSITE: "p is below τ," for every p. Between
p₀ and p₁ the SPRT must still pick a side but its error guarantees say
nothing about τ — we measured 16–64% false certification. The CS route
is calibrated against τ itself at every true p.

**8. Isn't p\* just something you chose? (The estimand question.)**
Yes — and say so before the judge does. p\* is the pool mean under a
uniform stratum weighting we chose; reweighting `extreme` to 10% moves
gpt-4o-mini from 0.202 to ≈0.086 and flips the τ=0.15 decision. The
guarantees are about the declared estimand; choosing the estimand is
the evaluator's job, and every certification cost we report states its
margin |p\*−τ| because cost ≈ margin⁻² is the real driver.

**9. How do you know your labels are right?**
We didn't, twice — and found out by adversarial audit: a float
`multipleOf` bug corrupted 59 labels (jsonschema rejects 199.95 as a
multiple of 0.05 in binary floating point), and my first repair
re-queried only failures, which is regression-to-the-mean selection
bias because temperature-0 decoding flips ~1–2% of outcomes on
re-query. The fix was exact decimal arithmetic plus a full symmetric
re-collection, with the flip matrices published. Know both bugs cold —
they are the best evidence the verification process works.

**10. What did the adversarial audits change?**
One withdrawn claim (general validity of the per-sample CS on
stratified streams — my concavity argument was backwards), one retired
absolute ("zero wrong certifications anywhere" — falsified at our own
seed), corrected pre-registration language (the τ=0.10 live arm was
exploratory, not pre-registered, and had a population bug), restored
dropped table rows, and pool-scoped language throughout. Also what
SURVIVED: exact martingale verification, all 320 code reference
solutions, dataset provenance by prompt hashing, seed robustness.

**11. What is actually novel here?**
Not the machinery — betting CSs, stratified anytime-valid inference,
and sequential McNemar are published (know the names: Waudby-Smith &
Ramdas; Spertus, Sridhar & Stark; Turner & Grünwald; Armitage). Ours:
the replay testbed with exact ground truth; the measured
design-selection map with bootstrap-significant winners; the exact-DP
mid-block counterexamples; the invention round's mechanistic negatives.
Positioning: an empirical design-selection study, not a methods paper.

**12. What was the AI's role, and what is yours?**
Answer honestly and specifically per ISEF rules: the direction,
funding, and decisions to pursue/abandon each line were yours; the
implementation and drafting were AI-assisted; the adversarial audits
were AI agents you directed against the AI-produced work, and they
found real bugs. Your preparation for this interview — being able to
re-derive everything in this guide — is the demonstration that the
understanding is yours.

## Three exercises to do by hand (no AI)

1. **Simulate the peeking effect yourself.** In a spreadsheet or 30
   lines of your own Python: flip 200 coins with p = 0.2, compute the
   Wilson interval after every flip, repeat 100 times, count how often
   the interval ever excludes 0.2. You should land near our 47.7%.
2. **Verify the e-value identity for n = 2.** With one failure then one
   success, compute the product of Beta(1,1) predictive ratios by hand
   and check it equals B(2,2)/B(1,1) divided by p₀(1−p₀). This is
   question 3's telescoping, made concrete.
3. **Reproduce one verdict.** Run `./reproduce.sh quick`, pick the SPRT
   artifact, and explain every number in Part 2's table to someone else
   (rubber duck counts). Then change τ in the script, rerun, and
   predict before looking which direction the false-rate moves.

## One-paragraph honest summary (memorize the substance, not the words)

We built a testbed where a real model's failure behavior can be
replayed exactly, used it to measure which anytime-valid sequential
designs win which evaluation decisions, subjected our own work to
adversarial audit (which caught two label-corrupting bugs and one wrong
claim), invented four candidate improvements that all lost to a simple
block reduction under pre-stated predictions, and shipped every claim
with a checksummed, re-runnable artifact — for about two dollars of
API spend.
