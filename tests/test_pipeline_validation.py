import os
import tempfile

import yaml

from main import generate_pipeline_from_template, run_plumber


def test_generated_pipeline_yaml_is_valid():
    """Test that the generated pipeline produces valid YAML."""
    test_app_name = "test-app"
    test_repo_url = "https://github.com/test/repo.git"
    test_app_caddy = """# Test app Caddyfile
:8000 {
    file_server
}"""
    test_proxy_caddy = """# Test proxy Caddyfile
@root path /
handle @root {
    reverse_proxy 127.0.0.1:9912
}

handle /test-app* {
    reverse_proxy 127.0.0.1:8000
}"""

    # Use the actual template file
    template_path = "template/pipeline_template.yaml"

    # Generate the pipeline
    output_path = generate_pipeline_from_template(
        template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddy
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

        # Verify Caddyfile content was properly inserted
        proxy_script = next((p for p in params if p["name"] == "proxy-routes-script"), None)
        assert proxy_script is not None, "proxy-routes-script param not found"
        assert "# Test proxy Caddyfile" in proxy_script["value"], "Proxy Caddyfile content not found"
        assert "handle /test-app*" in proxy_script["value"], "Test app routes not found in proxy script"

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
        template_path = "template/pipeline_template.yaml"

        # Import the function that uses fec config
        from main import get_app_url_from_fec_config, generate_frontend_proxy_caddyfile

        # Get app URLs from fec config
        app_urls = get_app_url_from_fec_config(fec_config_path)
        assert app_urls is not None, "Failed to parse fec.config.js"
        assert len(app_urls) == 3, f"Expected 3 URLs, got {len(app_urls)}"
        assert "/settings/test-app" in app_urls, "Expected URL not found"

        # Generate proxy Caddyfile
        proxy_caddy = generate_frontend_proxy_caddyfile(
            app_url_value=app_urls,
            app_name=test_app_name,
            app_port="8000",
            chrome_port="9912",
        )

        # Generate pipeline
        app_caddy = "# Integration test app Caddyfile"
        output_path = generate_pipeline_from_template(
            template_path, test_app_name, test_repo_url, app_caddy, proxy_caddy
        )

        # Validate YAML
        with open(output_path) as f:
            pipeline = yaml.safe_load(f)

        assert pipeline is not None, "Failed to parse generated pipeline YAML"
        assert pipeline["kind"] == "PipelineRun", "Invalid pipeline kind"

        # Verify fec config URLs made it into the proxy script
        params = pipeline["spec"]["params"]
        proxy_script = next((p for p in params if p["name"] == "proxy-routes-script"), None)
        assert proxy_script is not None, "proxy-routes-script not found"
        assert "handle /settings/test-app*" in proxy_script["value"], "/settings route not found"
        assert "handle /apps/test-app*" in proxy_script["value"], "/apps route not found"

        # Clean up
        os.remove(output_path)

    finally:
        # Clean up temp fec config
        if os.path.exists(fec_config_path):
            os.remove(fec_config_path)


def test_pipeline_yaml_comments_and_special_chars():
    """Test that Caddyfile content with comments and special chars doesn't break YAML."""
    test_app_name = "special-char-app"
    test_repo_url = "https://github.com/test/special.git"

    # Caddyfile with various special characters and comments
    test_proxy_caddy = """# Caddyfile with special characters
# Port 9912 - Chrome
# Port 8000 - App

@root path /
handle @root {
    reverse_proxy 127.0.0.1:9912
}

# Handle app routes
handle /special-char-app* {
    reverse_proxy 127.0.0.1:8000
}

# Wildcard matching
handle /apps/chrome* {
    reverse_proxy 127.0.0.1:9912
}"""

    test_app_caddy = """# App Caddyfile
:8000 {
    # Comment in app config
    file_server
}"""

    template_path = "template/pipeline_template.yaml"
    output_path = generate_pipeline_from_template(
        template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddy
    )

    try:
        # Parse the YAML - this will fail if comments break the YAML structure
        with open(output_path) as f:
            pipeline = yaml.safe_load(f)

        assert pipeline is not None, "Failed to parse YAML with comments"
        assert pipeline["kind"] == "PipelineRun", "Invalid pipeline structure"

        # Verify comments are preserved in the script
        params = pipeline["spec"]["params"]
        proxy_script = next((p for p in params if p["name"] == "proxy-routes-script"), None)
        assert "# Caddyfile with special characters" in proxy_script["value"]
        assert "# Port 9912 - Chrome" in proxy_script["value"]

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
