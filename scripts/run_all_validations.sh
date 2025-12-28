#!/bin/bash
# Run all objective validation experiments for audit

set -e

echo "========================================="
echo "OBJECTIVE VALIDATION EXPERIMENTS"
echo "Day 2: Empirical Validation"
echo "========================================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# 1. Coverage validation
echo "========================================="
echo "1/3: Coverage Validation"
echo "========================================="
echo ""
python3 scripts/validate_coverage.py
echo ""

# 2. Intersection tightness
echo "========================================="
echo "2/3: Intersection Tightness Validation"
echo "========================================="
echo ""
python3 scripts/validate_intersection_tightness.py
echo ""

# 3. Stratified sampling (requires OpenAI API key)
echo "========================================="
echo "3/3: Stratified Sampling Experiments"
echo "========================================="
echo ""

if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Skipping stratified experiments (require OpenAI API key)"
    echo ""
else
    # Load .env
    export $(grep -v '^#' .env | xargs)

    if [ -z "$OPENAI_API_KEY" ]; then
        echo "Warning: OPENAI_API_KEY not set in .env"
        echo "Skipping stratified experiments"
        echo ""
    else
        echo "Running stratified experiments with OpenAI API..."
        echo "(This will make API calls and may take several minutes)"
        echo ""
        python3 run_stratified_experiments.py
        echo ""

        echo "Analyzing results..."
        python3 analyze_stratified_results.py
        echo ""
    fi
fi

echo "========================================="
echo "VALIDATION COMPLETE"
echo "========================================="
echo ""
echo "Summary:"
echo "  ✓ Coverage validation complete"
echo "  ✓ Intersection tightness validation complete"
if [ -f ".env" ] && [ -n "$OPENAI_API_KEY" ]; then
    echo "  ✓ Stratified experiments complete"
else
    echo "  ⊘ Stratified experiments skipped (no API key)"
fi
echo ""
echo "All validation evidence ready for audit."
echo ""
