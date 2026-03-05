#!/bin/bash
# Example script for generating Caddy ConfigMap using Plumber

# Configuration
APP_NAME="learning-resources"
REPO_URL="https://github.com/RedHatInsights/learning-resources.git"
FEC_CONFIG="fec_configs/fec.config.js"
PROXY_CONFIGMAP_NAME="${APP_NAME}-dev-proxy-caddyfile"
NAMESPACE="hcc-platex-services-tenant"

# Generate ConfigMap
plumber "${APP_NAME}" "${REPO_URL}" \
  --proxy-configmap-name "${PROXY_CONFIGMAP_NAME}" \
  --fec-config "${FEC_CONFIG}" \
  --namespace "${NAMESPACE}"

echo ""
echo "ConfigMap generated successfully!"
echo "To apply it to your cluster:"
echo "  kubectl apply -f ${PROXY_CONFIGMAP_NAME}.yaml"
