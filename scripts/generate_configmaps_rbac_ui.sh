#!/bin/bash
# Example script for generating Caddy ConfigMap using Plumber

# Configuration
APP_NAME="insights-rbac-ui"
REPO_URL="https://github.com/RedHatInsights/insights-rbac-ui.git"
FEC_CONFIG="$HOME/repos/js/insights-rbac-ui/fec.config.js"
PROXY_CONFIGMAP_NAME="${APP_NAME}-dev-proxy-caddyfile"
NAMESPACE="rh-platform-experien-tenant"

# Generate ConfigMap
plumber "${APP_NAME}" "${REPO_URL}" \
  --proxy-configmap-name "${PROXY_CONFIGMAP_NAME}" \
  --fec-config "${FEC_CONFIG}" \
  --namespace "${NAMESPACE}"

echo ""
echo "ConfigMap generated successfully!"
echo "To apply it to your cluster:"
echo "  kubectl apply -f ${PROXY_CONFIGMAP_NAME}.yaml"
