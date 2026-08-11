#!/bin/bash
# Push-button reproduction: re-runs every offline experiment from the
# committed outcome pools and diffs the resulting checksums against the
# committed results artifacts.
#
#   ./reproduce.sh            # run everything (several hours)
#   ./reproduce.sh quick      # the fast subset (~15 minutes)
#   ./reproduce.sh <script>   # one experiment, e.g. ./reproduce.sh run_sprt_comparison
#
# Live experiments (results_live_*.txt) are excluded: they consumed
# fresh API calls and are not offline-reproducible by construction.
# Checksums on results files are tamper-evidence; THIS script is the
# actual reproducibility demonstration.

set -u
cd "$(dirname "$0")"

QUICK="run_sprt_comparison run_model_comparison run_codetask_experiments run_graded_scores run_wsr_hard run_ppc"
FULL="$QUICK run_realllm_offline run_advanced_experiments run_crossmodel_experiments run_block_reduction run_uncertainty run_spertus_baseline run_ui_grow run_sharp run_tasc_hard"

artifact_for() {
  case "$1" in
    run_sprt_comparison)      echo results_sprt_comparison.txt ;;
    run_model_comparison)     echo results_model_comparison.txt ;;
    run_codetask_experiments) echo results_codetask.txt ;;
    run_graded_scores)        echo results_graded_scores.txt ;;
    run_wsr_hard)             echo results_wsr_hard.txt ;;
    run_ppc)                  echo results_ppc.txt ;;
    run_realllm_offline)      echo results_realllm_betting.txt ;;
    run_advanced_experiments) echo results_advanced.txt ;;
    run_crossmodel_experiments) echo results_crossmodel.txt ;;
    run_block_reduction)      echo results_block_reduction.txt ;;
    run_uncertainty)          echo results_uncertainty.txt ;;
    run_spertus_baseline)     echo results_spertus_baseline.txt ;;
    run_ui_grow)              echo results_ui_grow.txt ;;
    run_sharp)                echo results_sharp.txt ;;
    run_tasc_hard)            echo results_tasc_hard.txt ;;
    *) echo "" ;;
  esac
}

case "${1:-all}" in
  quick) TARGETS=$QUICK ;;
  all)   TARGETS=$FULL ;;
  *)     TARGETS="$1" ;;
esac

pass=0; fail=0; missing=0
for t in $TARGETS; do
  art=$(artifact_for "$t")
  if [ -z "$art" ] || [ ! -f "$art" ]; then
    echo "SKIP  $t (no committed artifact)"; missing=$((missing+1)); continue
  fi
  before=$(shasum -a 256 "$art" | cut -d' ' -f1)
  echo "RUN   scripts/$t.py ..."
  if ! python3 "scripts/$t.py" > /dev/null 2>&1; then
    echo "ERROR $t exited nonzero"; fail=$((fail+1)); continue
  fi
  after=$(shasum -a 256 "$art" | cut -d' ' -f1)
  if [ "$before" = "$after" ]; then
    echo "PASS  $art reproduced byte-identically"
    pass=$((pass+1))
  else
    echo "FAIL  $art CHANGED (was ${before:0:12}..., now ${after:0:12}...)"
    fail=$((fail+1))
  fi
done

echo
echo "Reproduction summary: $pass PASS, $fail FAIL, $missing skipped"
python3 -m pytest tests/ -q | tail -1
[ "$fail" -eq 0 ]
