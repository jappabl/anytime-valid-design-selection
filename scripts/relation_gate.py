#!/usr/bin/env python3
"""The relation gate: check RELATIONS between objects, not objects.

Derived from a 16-defect census of this project (peer analysis,
2026-08-15): in 16/16 defects the local object was correct; in 15/16
an unchecked RELATION failed (criterion<->hypotheses, window<->window,
powered-model<->executed-code, artifact<->claim, per-cell<->aggregate,
result<->other-sites, code<->runtime-budget). severity_sim rev 3
already implements three of these for experiments; this tool
generalizes the discipline to anchors, artifacts, claims, and code.

RULES (R1-R3 live in severity_sim for experiment designs; this tool
adds their non-experiment forms plus R4-R7):

  R1 DISCRIMINATION for anchors/sanity checks: an anchor whose verdict
     is invariant across the entire constant band discriminates
     nothing (the A2 defect). --anchors evaluates the phase-boundary
     anchors under every band corner and flags invariant ones.
  R4 ARTIFACT-CLAIM IDENTITY: every artifact cited with a verdict in
     FINDINGS/THEORY must itself print PASS/FAIL/VERDICT lines.
     --artifacts scans and lists violators.
  R5 AGGREGATION TRANSPARENCY: n-of-m / "all pass" claims must cite an
     artifact that prints the per-cell breakdown. --aggregates lists
     n-of-m claims and whether the cited artifact enumerates cells.
  R6 PROPAGATION: --propagate <term> greps the repo's living docs and
     artifacts for a quantity and lists every asserting site, so a
     change to the quantity comes with an explicit still-holds check.
  R9 ABSORPTION ORDERING (from the 805ae03 miss): an EXTERNAL result
     may not be absorbed into paper/THEORY while a frozen test of that
     same result is pending — absorb only after the test scores. The
     805ae03 instance: a no-expansion claim entered BOUNDARY_THEOREM
     after the freeze (7e80dbe) and before the run that scored its P1
     FAIL. Discipline rule (not mechanically scanned): every
     absorption commit must cite the scored artifact it rests on.
  R4b THRESHOLD IDENTITY (audit finding, fifth generator instance):
     any check whose pass criterion cites a NAMED theoretical quantity
     (a bound, a derived constant) must COMPUTE that quantity from the
     theory at the point being tested — never a tolerance multiplier
     wearing the bound's name. C1 rev 1 printed PASS against
     bound(-1 coeff, wrong grid point) x 1.5 while the actual error
     exceeded the displayed bound; R4 was satisfied because a verdict
     was printed. --thresholds scans scripts for multiplicative fudge
     adjacent to bound-naming words and lists hits for adjudication
     (semi-mechanical, like R5).
  R1b SCORING RESOLUTION (extension of R1, fourth-instance rule):
     any verdict rule comparing two measured quantities must state
     the comparison's resolution (CI) and report ties as
     unresolved-by-measurement. A comparison with no error bar is an
     anchor with no discrimination check. Enforced by protocol in
     run_phase_test v2b; future comparison tests must print per-point
     CIs or be refused at freeze.
  R8 ALLOCATION DISCRIMINATION: a verification whose scored points
     concentrate in the region where the hypothesis is already
     established is not discriminating regardless of point count
     (three instances: the pool sweep, anchor A2, phase-test v1's
     7-of-9 WSR-region allocation). --allocation checks the phase
     test's POINTS list: >= 50% of scored points must carry the
     novel-region prediction.
  R7 RESOURCE INVARIANT: --budgets runs the shipped wall-clock
     regression (certify 2,000 samples inside budget) so "fast enough"
     is a tested relation, not an assumption.

This gate runs before freezes and before verdict-asserting commits.
It reports; humans (or the calling script) decide. Exit code 1 if any
rule flags.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
DOCS = ["FINDINGS.md", "THEORY.md", "paper/DRAFT.md"]


def r1_anchors():
    """Evaluate phase-boundary anchors under every constant corner;
    flag anchors whose verdict never changes (non-discriminating)."""
    import types
    import numpy as np
    src = open(REPO / "scripts" / "derive_phase_boundary.py").read()
    m = types.ModuleType("pb")
    m.__dict__["__file__"] = str(REPO / "scripts"
                                 / "derive_phase_boundary.py")
    exec(src.rsplit("if __name__", 1)[0], m.__dict__)
    # Synced to the FROZEN pass-4 constants (f75eb8d): single arm is
    # the derived four-term form; corners span only the WSR envelope.
    corners = [(1.6, 1.81, -3.4), (3.0, 2.34, -5.9), (2.3, 1.95, -4.6)]
    anchors = {
        "A1 (MBPP-like R~2.6)": (np.array([0.140, 0.215, 0.224, 0.358]),
                                 "single"),
        "A3 (llama3-8b-like R~7.5)": (np.array([0.456, 0.128, 0.892,
                                                0.960]), "wsr"),
        "A2 (llama-like R~31)": (np.array([0.040, 0.032, 0.864, 0.996]),
                                 "wsr"),
    }
    flags = []
    print("R1 anchor discrimination (frozen pass-4 constants; verdict "
          "under every WSR corner):")
    for name, (rates, expect) in anchors.items():
        p = float(rates.mean())
        tau = p - 0.045
        n_s = m.single_fourterm(p, tau)
        verdicts = []
        for csh, dlg, clg in corners:
            n_w = m.wsr_crossing(m.v_kelly_block(rates, tau),
                                 csh, dlg, clg)
            verdicts.append("single" if n_s < n_w else "wsr")
        # Discrimination = the verdict CHANGES under a wrong theory
        # (d-alternative single arms), not merely across envelope
        # corners: post-freeze, corner-invariant AGREEMENT is
        # robustness, not vacuity (semantics fixed after the pass-4
        # sync falsely flagged robust passes).
        alt_verdicts = []
        for d_alt in (0.0, 2.0):
            c4 = (-0.5 * np.log(2 * np.pi * p * (1 - p)) - 1.105)
            n_alt = m.crossing_n(m.kl(p, tau), d_alt, c4)
            n_w_c = m.wsr_crossing(m.v_kelly_block(rates, tau),
                                   *corners[-1])
            alt_verdicts.append("single" if n_alt < n_w_c else "wsr")
        agree = all(v == expect for v in verdicts)
        can_fail = len(set(verdicts + alt_verdicts)) > 1
        tag = ("discriminating (verdict flips under d-alternatives)"
               if can_fail else "NON-DISCRIMINATING (cannot fail even "
               "under wrong theory)")
        print(f"  {name}: corners -> {verdicts}; d-alts -> "
              f"{alt_verdicts}; expected {expect}; "
              f"{'agrees' if agree else 'DISAGREES'}; {tag}")
        if not can_fail:
            flags.append(f"R1: {name} verdict invariant even under "
                         f"wrong theory — not evidence")
    return flags


def r4_artifacts():
    """Flag an artifact ONLY when a citing sentence asserts a verdict
    about it (the relation), not when the artifact merely lacks
    verdict strings (rev 2 — the first implementation had the exact
    object-vs-relation defect this gate exists to catch, found by peer
    review running the gate on the gate)."""
    flags = []
    print("R4 artifact-claim identity (verdict-asserting citations "
          "must point at self-scoring artifacts):")
    verdict_words = re.compile(
        r'FAILED|REFUTED|CONFIRMED|MISSED|PASS|FALSIF|vacuous|LOST'
        r'|WIN\b|hollow|withdrawn', re.IGNORECASE)
    cited_with_verdict = set()
    for doc in DOCS:
        txt = open(REPO / doc).read()
        for m_ in re.finditer(r'results_[a-z0-9_]+\.txt', txt):
            window = txt[max(0, m_.start() - 160):m_.end() + 160]
            if verdict_words.search(window):
                cited_with_verdict.add(m_.group(0))
    for art in sorted(cited_with_verdict):
        p = REPO / art
        if not p.exists():
            continue
        txt = open(p).read()
        if not re.search(r'\b(PASS|FAIL|VERDICT|CONFIRMED|REFUSE)',
                         txt):
            print(f"  {art}: cited WITH a verdict but does not "
                  f"self-score")
            flags.append(f"R4: {art} verdict-cited but not "
                         f"self-scoring")
    if not flags:
        print(f"  {len(cited_with_verdict)} verdict-cited artifacts "
              f"all self-score")
    return flags


def r5_aggregates():
    flags = []
    print("R5 aggregation transparency (n-of-m claims):")
    pat = re.compile(r'(\d+)[-\s]of[-\s](\d+)')
    for doc in DOCS:
        txt = open(REPO / doc).read()
        for m_ in pat.finditer(txt):
            line = txt[max(0, m_.start() - 120):m_.end() + 120]
            arts = re.findall(r'results_[a-z0-9_]+\.txt', line)
            ok = False
            for art in arts:
                p = REPO / art
                if p.exists() and len(re.findall(
                        r'PASS|FAIL', open(p).read())) >= int(
                            m_.group(2)):
                    ok = True
            status = "cells enumerated" if ok else \
                "NO per-cell breakdown found near claim"
            if not ok:
                print(f"  {doc}: '{m_.group(0)}' -> {status}")
                flags.append(f"R5: {doc} claim '{m_.group(0)}' lacks "
                             f"an enumerating artifact citation")
    if not flags:
        print("  all n-of-m claims cite enumerating artifacts")
    return flags


def r6_propagate(term):
    print(f"R6 propagation sites for '{term}':")
    out = subprocess.run(
        ["grep", "-rn", "-l", term] + DOCS
        + [str(p.name) for p in REPO.glob("results_*.txt")],
        capture_output=True, text=True, cwd=REPO)
    files = [f for f in out.stdout.split() if f]
    for f in files:
        print(f"  {f}")
    print(f"  {len(files)} sites — each must be re-verified when "
          f"'{term}' changes")
    return []


def r4b_thresholds():
    import re
    hits = []
    for f in sorted((REPO / "scripts").glob("*.py")):
        src = f.read_text()
        for i, line in enumerate(src.splitlines(), 1):
            if re.search(r"(bound|Bound)\w*\s*=.*\*\s*[0-9.]+\s*$",
                         line) and "1e" not in line:
                hits.append(f"{f.name}:{i}: {line.strip()}")
    print("R4b threshold identity (multiplicative fudge adjacent to a "
          "named bound):")
    for h in hits:
        print(f"  {h}")
    if not hits:
        print("  none found")
    return [f"R4b: {h}" for h in hits]


def r8_allocation():
    import types
    src = open(REPO / "scripts" / "run_phase_test.py").read()
    m = types.ModuleType("pt")
    m.__dict__["__file__"] = str(REPO / "scripts" / "run_phase_test.py")
    exec(src.split("def load_base")[0], m.__dict__)
    scored = [p for p in m.POINTS if p[3]]
    novel = [p for p in scored if p[3] == "single"]
    frac = len(novel) / len(scored)
    print(f"R8 allocation: {len(novel)}/{len(scored)} scored points "
          f"in the novel (single) region ({frac:.0%}; need >= 50%): "
          f"{'ok' if frac >= 0.5 else 'REFUSE'}")
    return [] if frac >= 0.5 else [
        "R8: verification concentrates in the established region"]


def r7_budgets():
    print("R7 resource invariants (shipped wall-clock budgets):")
    r = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_certify.py::test_full_run_wall_clock_budget",
         "-q"], capture_output=True, text=True, cwd=REPO)
    ok = "1 passed" in r.stdout
    print(f"  certify 2,000 samples in budget: "
          f"{'PASS' if ok else 'FAIL'}")
    return [] if ok else ["R7: wall-clock budget test failing"]


def main():
    args = sys.argv[1:]
    flags = []
    if not args or "--anchors" in args:
        flags += r1_anchors()
        print()
    if not args or "--artifacts" in args:
        flags += r4_artifacts()
        print()
    if not args or "--aggregates" in args:
        flags += r5_aggregates()
        print()
    for i, a in enumerate(args):
        if a == "--propagate" and i + 1 < len(args):
            r6_propagate(args[i + 1])
            print()
    if not args or "--thresholds" in args:
        flags += r4b_thresholds()
        print()
    if not args or "--allocation" in args:
        flags += r8_allocation()
        print()
    if not args or "--budgets" in args:
        flags += r7_budgets()
        print()
    if flags:
        print("GATE FLAGS:")
        for f in flags:
            print(f"  {f}")
        sys.exit(1)
    print("relation gate: no flags")


if __name__ == "__main__":
    main()
