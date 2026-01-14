import os
import tempfile

import yaml

from generation import generate_app_caddy_configmap, generate_proxy_caddy_configmap


def test_generate_app_caddy_configmap():
    """Test that app Caddy ConfigMap is generated correctly."""
    test_app_name = "test-app"
    test_configmap_name = "test-app-caddy"
    test_app_urls = ["/settings/test-app", "/apps/test-app", "/test-app"]

    # Generate the ConfigMap
    output_path = generate_app_caddy_configmap(
        configmap_name=test_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
    )

    try:
        # Verify the output file exists
        assert os.path.exists(output_path), f"Output file not created at {output_path}"

        # Read and parse the YAML
        with open(output_path) as f:
            configmap_content = f.read()

        # Parse YAML
        configmap = yaml.safe_load(configmap_content)

        # Verify ConfigMap structure
        assert configmap is not None, "ConfigMap parsed to None"
        assert configmap.get("apiVersion") == "v1", "Invalid apiVersion"
        assert configmap.get("kind") == "ConfigMap", "Invalid kind"

        # Verify metadata
        metadata = configmap.get("metadata", {})
        assert metadata.get("name") == test_configmap_name, "Invalid ConfigMap name"

        # Verify data section
        data = configmap.get("data", {})
        assert "Caddyfile" in data, "Caddyfile key not found in data"

        caddyfile_content = data["Caddyfile"]
        assert "# Caddyfile config for the application" in caddyfile_content
        assert f"/apps/{test_app_name}" in caddyfile_content
        assert "settings" in caddyfile_content  # Route prefix

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


def test_generate_proxy_caddy_configmap():
    """Test that proxy Caddy ConfigMap is generated correctly."""
    test_app_name = "test-app"
    test_configmap_name = "test-proxy-caddy"
    test_app_urls = ["/settings/test-app", "/apps/test-app"]

    # Generate the ConfigMap
    output_path = generate_proxy_caddy_configmap(
        configmap_name=test_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
        app_port="8000",
        chrome_port="9912",
    )

    try:
        # Verify the output file exists
        assert os.path.exists(output_path), f"Output file not created at {output_path}"

        # Read and parse the YAML
        with open(output_path) as f:
            configmap_content = f.read()

        # Parse YAML
        configmap = yaml.safe_load(configmap_content)

        # Verify ConfigMap structure
        assert configmap is not None, "ConfigMap parsed to None"
        assert configmap.get("apiVersion") == "v1", "Invalid apiVersion"
        assert configmap.get("kind") == "ConfigMap", "Invalid kind"

        # Verify metadata
        metadata = configmap.get("metadata", {})
        assert metadata.get("name") == test_configmap_name, "Invalid ConfigMap name"

        # Verify data section - proxy uses "routes" as the key
        data = configmap.get("data", {})
        assert "routes" in data, "routes key not found in data"

        routes_content = data["routes"]
        assert "@root path /" in routes_content
        assert "handle /apps/chrome*" in routes_content
        assert f"handle /apps/{test_app_name}*" in routes_content
        assert "handle /settings/test-app*" in routes_content
        assert "reverse_proxy 127.0.0.1:9912" in routes_content
        assert "reverse_proxy 127.0.0.1:8000" in routes_content

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


def test_configmap_names_are_respected():
    """Test that ConfigMap names are correctly set."""
    test_app_name = "my-app"
    app_configmap_name = "custom-app-config"
    proxy_configmap_name = "custom-proxy-config"
    test_app_urls = ["/my-app"]

    # Generate both ConfigMaps
    app_path = generate_app_caddy_configmap(
        configmap_name=app_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
    )

    proxy_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
    )

    try:
        # Verify file names match
        assert app_path.endswith(f"{app_configmap_name}.yaml")
        assert proxy_path.endswith(f"{proxy_configmap_name}.yaml")

        # Verify ConfigMap metadata names
        with open(app_path) as f:
            app_configmap = yaml.safe_load(f)
        assert app_configmap["metadata"]["name"] == app_configmap_name

        with open(proxy_path) as f:
            proxy_configmap = yaml.safe_load(f)
        assert proxy_configmap["metadata"]["name"] == proxy_configmap_name

    finally:
        # Clean up
        if os.path.exists(app_path):
            os.remove(app_path)
        if os.path.exists(proxy_path):
            os.remove(proxy_path)


def test_configmap_integration_with_fec_config():
    """Integration test that generates ConfigMaps using fec.config.js."""
    test_app_name = "test-app"

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
        app_configmap_name = "integration-app-caddy"
        proxy_configmap_name = "integration-proxy-caddy"

        # Import the function that uses fec config
        from extraction import get_app_url_from_fec_config

        # Get app URLs from fec config
        app_urls = get_app_url_from_fec_config(fec_config_path)
        assert app_urls is not None, "Failed to parse fec.config.js"
        assert len(app_urls) == 3, f"Expected 3 URLs, got {len(app_urls)}"

        # Generate ConfigMaps
        app_path = generate_app_caddy_configmap(
            configmap_name=app_configmap_name,
            app_url_value=app_urls,
            app_name=test_app_name,
        )

        proxy_path = generate_proxy_caddy_configmap(
            configmap_name=proxy_configmap_name,
            app_url_value=app_urls,
            app_name=test_app_name,
        )

        # Verify both ConfigMaps
        with open(app_path) as f:
            app_configmap = yaml.safe_load(f)
        assert app_configmap is not None
        assert app_configmap["kind"] == "ConfigMap"

        with open(proxy_path) as f:
            proxy_configmap = yaml.safe_load(f)
        assert proxy_configmap is not None
        assert proxy_configmap["kind"] == "ConfigMap"

        # Verify fec config URLs made it into the configs
        app_data = app_configmap["data"]["Caddyfile"]
        proxy_data = proxy_configmap["data"]["routes"]  # Proxy uses "routes" key

        assert "settings" in app_data  # Route prefix from /settings/test-app
        assert "handle /settings/test-app*" in proxy_data

        # Clean up
        os.remove(app_path)
        os.remove(proxy_path)

    finally:
        # Clean up temp fec config
        if os.path.exists(fec_config_path):
            os.remove(fec_config_path)


def test_configmap_with_namespace():
    """Test that namespace is correctly added to ConfigMaps."""
    test_app_name = "namespace-test-app"
    app_configmap_name = "namespace-app-caddy"
    proxy_configmap_name = "namespace-proxy-caddy"
    test_namespace = "hcc-platex-services-tenant"
    test_app_urls = ["/namespace-test-app"]

    # Generate both ConfigMaps with namespace
    app_path = generate_app_caddy_configmap(
        configmap_name=app_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
        namespace=test_namespace,
    )

    proxy_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
        namespace=test_namespace,
    )

    try:
        # Verify app ConfigMap has namespace
        with open(app_path) as f:
            app_configmap = yaml.safe_load(f)
        assert app_configmap["metadata"]["name"] == app_configmap_name
        assert app_configmap["metadata"]["namespace"] == test_namespace

        # Verify proxy ConfigMap has namespace
        with open(proxy_path) as f:
            proxy_configmap = yaml.safe_load(f)
        assert proxy_configmap["metadata"]["name"] == proxy_configmap_name
        assert proxy_configmap["metadata"]["namespace"] == test_namespace

        # Verify proxy uses "routes" key
        assert "routes" in proxy_configmap["data"]

    finally:
        # Clean up
        if os.path.exists(app_path):
            os.remove(app_path)
        if os.path.exists(proxy_path):
            os.remove(proxy_path)
