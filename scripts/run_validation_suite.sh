#!/bin/bash
# Run a suite of toy model experiments to validate statistical properties

set -e

echo "=== Running Statistical Validation Suite ==="
echo ""

# Create output directory
mkdir -p experiments/results

# Test 1: Coverage validation with p=0.05
echo "Test 1: Coverage validation (p=0.05, precision stopping)"
eval-harness run experiments/configs/toy_model_validation.yaml

# Test 2: Certification with very low p
echo ""
echo "Test 2: Certification (p=0.005, certify p<=0.01)"
eval-harness run experiments/configs/toy_certification.yaml

# Test 3: Multiple runs for coverage check (vary seeds)
echo ""
echo "Test 3: Multiple runs with different seeds (coverage validation)"

for seed in {100..109}; do
    echo "  Running with seed=$seed..."

    # Create temp config with modified seed
    cat > /tmp/config_$seed.yaml <<EOF
name: "toy_coverage_seed_${seed}"

sampler:
  type: "toy"
  model_id: "toy_p0.05_seed${seed}"
  failure_probability: 0.05

validator:
  type: "json_schema"

prompts:
  type: "json_schema"
  n_prompts: 100
  seed: ${seed}
  complexity: "simple"

decoding:
  temperature: 0.7

stopping:
  precision_target: 0.02
  min_samples: 30
  max_samples: 500

statistics:
  alpha: 0.05
  method: "betting"

seed: ${seed}
EOF

    eval-harness run /tmp/config_$seed.yaml --quiet
done

echo ""
echo "=== Validation Suite Complete ==="
echo ""
echo "Analyzing results..."
echo ""

# Find all result directories
RESULT_DIRS=$(find experiments/results -name "results.db" -exec dirname {} \;)

# Summarize results
python experiments/analysis/summarize_results.py $RESULT_DIRS

# Plot stopping times
python experiments/analysis/plot_stopping_times.py $RESULT_DIRS

echo ""
echo "Done! Check experiments/results/ for detailed results."
