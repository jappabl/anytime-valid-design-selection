# Supplementary pre-registration S1 (real-chain asymmetry magnitudes)

Timing disclosure: added while scripts/run_real_chain.py is MID-RUN
(deterministic offline replay; results_real_chain.txt does not exist
and no partial results have been read — verified in the transcript at
commit time). These sharpen the frozen P2 window directionally, per
the drift-asymmetry mechanism, at magnitudes the drift grid never
reached:

S1a Meta epoch 2 (real downward jump, delta = -0.342): chain-warm /
    cold <= 1.15 (downward staleness stays cheap even at 3.4x the
    grid's largest tested drift).
S1b Meta epoch 3 (real upward jump, delta = +0.216, and a wrong-model
    3B-from-8B prior): chain-warm / cold in [1.10, 1.40] (saturates at
    the contamination floor; never catastrophic).

Scored when results_real_chain.txt lands; misses logged as misses.
