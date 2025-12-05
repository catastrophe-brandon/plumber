import os
import tempfile

import yaml

from generation import generate_pipeline_from_template, generate_proxy_routes_caddyfile


def test_generated_pipeline_yaml_is_valid():
    """Test that the generated pipeline produces valid YAML."""
    test_app_name = "test-app"
    test_repo_url = "https://github.com/test/repo.git"
    test_app_caddy = """# Test app Caddyfile
:8000 {
    file_server
}"""
    # Generate proxy routes Caddyfile
    test_proxy_caddyfile = generate_proxy_routes_caddyfile(
        app_url_value=["/settings/test-app", "/test-app"],
        app_name=test_app_name,
        app_port="8000",
        chrome_port="9912",
    )

    # Use the actual template file
    template_path = "template/konflux_pipeline_template.yaml"

    # Generate the pipeline
    output_path = generate_pipeline_from_template(
        template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddyfile
    )

    try:
        # Verify the output file exists
        assert os.path.exists(output_path), f"Output file not created at {output_path}"

        # Read and parse the YAML
        with open(output_path) as f:
            pipeline_content = f.read()

        # This will raise an exception if YAML is invalid
        pipeline = yaml.safe_load(pipeline_content)

        # Verify basic Tekton PipelineRun structure
        assert pipeline is not None, "Pipeline parsed to None"
        assert pipeline.get("apiVersion") == "tekton.dev/v1", "Invalid apiVersion"
        assert pipeline.get("kind") == "PipelineRun", "Invalid kind"

        # Verify metadata
        metadata = pipeline.get("metadata", {})
        assert metadata.get("name") == f"{test_app_name}-on-pull-request", "Invalid pipeline name"

        # Verify spec and params exist
        spec = pipeline.get("spec", {})
        params = spec.get("params", [])
        assert len(params) > 0, "No parameters found in pipeline"

        # Verify app_name substitution in params
        test_app_name_param = next((p for p in params if p["name"] == "test-app-name"), None)
        assert test_app_name_param is not None, "test-app-name param not found"
        assert test_app_name_param["value"] == test_app_name, "test-app-name value incorrect"

        # Verify Caddyfile proxy routes was properly inserted
        proxy_routes = next((p for p in params if p["name"] == "frontend-proxy-routes"), None)
        assert proxy_routes is not None, "frontend-proxy-routes param not found"
        assert "handle /settings/test-app*" in proxy_routes["value"], "Proxy route not found"
        assert "reverse_proxy 127.0.0.1:9912" in proxy_routes["value"], "Chrome proxy not found"

        app_script = next((p for p in params if p["name"] == "run-app-script"), None)
        assert app_script is not None, "run-app-script param not found"
        assert "# Test app Caddyfile" in app_script["value"], "App Caddyfile content not found"

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


def test_pipeline_with_fec_config_integration():
    """Integration test that generates a pipeline using fec.config.js and validates it."""
    # Create a test fec.config.js file
    test_fec_content = """const path = require('path');

module.exports = {
  appUrl: [
    '/settings/test-app',
    '/apps/test-app',
    '/test-app',
  ],
  debug: true,
};
"""

    # Create temporary fec.config.js
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, prefix="fec.config"
    ) as temp_fec:
        temp_fec.write(test_fec_content)
        fec_config_path = temp_fec.name

    try:
        test_app_name = "integration-test-app"
        test_repo_url = "https://github.com/test/integration.git"
        template_path = "template/konflux_pipeline_template.yaml"

        # Import the function that uses fec config
        from extraction import get_app_url_from_fec_config

        # Get app URLs from fec config
        app_urls = get_app_url_from_fec_config(fec_config_path)
        assert app_urls is not None, "Failed to parse fec.config.js"
        assert len(app_urls) == 3, f"Expected 3 URLs, got {len(app_urls)}"
        assert "/settings/test-app" in app_urls, "Expected URL not found"

        # Generate proxy routes Caddyfile
        proxy_caddyfile = generate_proxy_routes_caddyfile(
            app_url_value=app_urls,
            app_name=test_app_name,
            app_port="8000",
            chrome_port="9912",
        )

        # Generate pipeline
        app_caddy = "# Integration test app Caddyfile"
        output_path = generate_pipeline_from_template(
            template_path, test_app_name, test_repo_url, app_caddy, proxy_caddyfile
        )

        # Validate YAML
        with open(output_path) as f:
            pipeline = yaml.safe_load(f)

        assert pipeline is not None, "Failed to parse generated pipeline YAML"
        assert pipeline["kind"] == "PipelineRun", "Invalid pipeline kind"

        # Verify fec config URLs made it into the proxy routes as Caddyfile
        params = pipeline["spec"]["params"]
        proxy_routes = next((p for p in params if p["name"] == "frontend-proxy-routes"), None)
        assert proxy_routes is not None, "frontend-proxy-routes not found"
        assert "handle /settings/test-app*" in proxy_routes["value"], "/settings route not found"
        assert "handle /apps/test-app*" in proxy_routes["value"], "/apps route not found"
        assert "reverse_proxy 127.0.0.1" in proxy_routes["value"], "reverse_proxy not found"

        # Clean up
        os.remove(output_path)

    finally:
        # Clean up temp fec config
        if os.path.exists(fec_config_path):
            os.remove(fec_config_path)


def test_pipeline_yaml_comments_and_special_chars():
    """Test that Caddyfile route data with special chars doesn't break YAML."""
    test_app_name = "special-char-app"
    test_repo_url = "https://github.com/test/special.git"

    # Generate proxy routes Caddyfile with special characters in routes
    test_proxy_caddyfile = generate_proxy_routes_caddyfile(
        app_url_value=["/special-char-app", "/apps/special-char-app", "/settings/special-char-app"],
        app_name=test_app_name,
        app_port="8000",
        chrome_port="9912",
    )

    test_app_caddy = """# App Caddyfile
:8000 {
    # Comment in app config
    file_server
}"""

    template_path = "template/konflux_pipeline_template.yaml"
    output_path = generate_pipeline_from_template(
        template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddyfile
    )

    try:
        # Parse the YAML - this will fail if Caddyfile breaks the YAML structure
        with open(output_path) as f:
            pipeline = yaml.safe_load(f)

        assert pipeline is not None, "Failed to parse YAML with Caddyfile"
        assert pipeline["kind"] == "PipelineRun", "Invalid pipeline structure"

        # Verify Caddyfile is in the parameter
        params = pipeline["spec"]["params"]
        proxy_routes = next((p for p in params if p["name"] == "frontend-proxy-routes"), None)
        assert proxy_routes is not None, "frontend-proxy-routes param not found"
        assert "handle /special-char-app*" in proxy_routes["value"], "Caddyfile routes not found"
        assert "reverse_proxy 127.0.0.1" in proxy_routes["value"], "reverse_proxy not found"

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
