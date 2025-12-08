#!/bin/bash
set -e

# Run plumber for learning-resources
echo "Generating pipeline for learning-resources..."
uv run plumber learning-resources \
  https://github.com/RedHatInsights/learning-resources.git \
  --pipeline-template template/konflux_pipeline_template.yaml \
  --fec-config fec_configs/fec.config.js

# Copy the generated file to the target location
echo "Copying pipeline file to ~/repos/js/learning-resources/.tekton/..."
cp learning-resources-pull-request.yaml ~/repos/js/learning-resources/.tekton/learning-resources-pull-request.yaml

echo "✓ Pipeline file copied to ~/repos/js/learning-resources/.tekton/learning-resources-pull-request.yaml"
