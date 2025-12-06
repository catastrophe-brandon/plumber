#!/bin/bash
set -e

# Run plumber for learning-resources with minikube template
echo "Generating minikube pipeline for learning-resources..."
uv run plumber learning-resources \
  https://github.com/RedHatInsights/learning-resources.git \
  --minikube-template template/minikube_pipeline_template.yaml \
  --fec-config fec_configs/fec.config.js

echo ""
echo "✓ Minikube pipeline generated: learning-resources-pull-request.yaml"
