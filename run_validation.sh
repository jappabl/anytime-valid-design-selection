#!/bin/bash
# Objective statistical validation - NO SUGARCOATING

set -e

echo "========================================================================"
echo "OBJECTIVE STATISTICAL VALIDATION SUITE"
echo "========================================================================"
echo ""
echo "This test suite validates the statistical framework with HARD criteria:"
echo "  ✓ Coverage: CS must contain true p in ≥90% of runs"
echo "  ✓ Convergence: Point estimates within 2 SE in ≥90% of runs"
echo "  ✓ Monotonicity: CI width never increases"
echo "  ✓ Stopping: Rules trigger when and only when criteria met"
echo ""
echo "If ANY test fails, the framework is BROKEN."
echo ""
echo "========================================================================"
echo ""

# Run the validation tests
poetry run pytest tests/test_statistical_validation.py -v --tb=short

EXIT_CODE=$?

echo ""
echo "========================================================================"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓✓✓ VALIDATION PASSED ✓✓✓"
    echo ""
    echo "The statistical framework works correctly:"
    echo "  • Confidence sequences achieve nominal coverage"
    echo "  • Point estimates converge to truth"
    echo "  • CI widths decrease monotonically"
    echo "  • Stopping rules are correct"
    echo ""
    echo "STATUS: READY FOR REAL LLM EXPERIMENTS"
else
    echo "✗✗✗ VALIDATION FAILED ✗✗✗"
    echo ""
    echo "The statistical framework has issues that MUST be fixed before"
    echo "proceeding to real LLM experiments."
    echo ""
    echo "STATUS: NOT READY - FIX BUGS FIRST"
fi

echo "========================================================================"

exit $EXIT_CODE
