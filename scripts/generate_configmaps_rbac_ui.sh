#!/bin/bash
# Example script for generating Caddy ConfigMaps using Plumber

# Configuration
APP_NAME="insights-rbac-ui"
REPO_URL="https://github.com/RedHatInsights/insights-rbac-ui.git"
FEC_CONFIG="$HOME/repos/js/insights-rbac-ui/fec.config.js"
APP_CONFIGMAP_NAME="${APP_NAME}-test-app-caddyfile"
PROXY_CONFIGMAP_NAME="${APP_NAME}-dev-proxy-caddyfile"
NAMESPACE="rh-platform-experien-tenant"

# Generate ConfigMaps
plumber "${APP_NAME}" "${REPO_URL}" \
  --app-configmap-name "${APP_CONFIGMAP_NAME}" \
  --proxy-configmap-name "${PROXY_CONFIGMAP_NAME}" \
  --fec-config "${FEC_CONFIG}" \
  --namespace "${NAMESPACE}"

echo ""
echo "ConfigMaps generated successfully!"
echo "To apply them to your cluster:"
echo "  kubectl apply -f ${APP_CONFIGMAP_NAME}.yaml"
echo "  kubectl apply -f ${PROXY_CONFIGMAP_NAME}.yaml"
