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
        assert f"handle /apps/{test_app_name}*" in routes_content
        assert "handle /settings/test-app*" in routes_content
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


def test_fallback_from_frontend_yaml_to_fec_config(tmp_path):
    """Test that when frontend.yaml is missing, it falls back to fec.config.js."""
    import shutil

    test_app_name = "fallback-app"

    # Create a test fec.config.js file
    test_fec_content = """module.exports = {
  appUrl: ['/fallback-app', '/settings/fallback-app'],
  debug: true,
};
"""

    # Create temporary fec.config.js
    fec_config_path = tmp_path / "fec.config.js"
    fec_config_path.write_text(test_fec_content)

    # Import the main function
    from main import run_plumber

    # Use a non-existent frontend.yaml path to trigger fallback
    nonexistent_yaml = str(tmp_path / "nonexistent_frontend.yaml")

    # Save current directory and change to tmp_path
    original_dir = os.getcwd()
    try:
        # Copy template directory to tmp_path so templates can be found
        shutil.copytree(os.path.join(original_dir, "template"), tmp_path / "template")

        os.chdir(tmp_path)

        # Run plumber with missing frontend.yaml but valid fec.config.js
        run_plumber(
            app_name=test_app_name,
            repo_url="https://github.com/test/repo",
            app_configmap_name="fallback-app-caddy",
            proxy_configmap_name="fallback-proxy-caddy",
            fec_config_path=str(fec_config_path),
            frontend_yaml_path=nonexistent_yaml,
        )

        # Verify the generated ConfigMaps use fec.config.js values
        app_path = tmp_path / "fallback-app-caddy.yaml"
        proxy_path = tmp_path / "fallback-proxy-caddy.yaml"

        assert app_path.exists(), "App ConfigMap should be generated"
        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

        # Parse and verify app ConfigMap contains routes from fec.config.js
        app_configmap = yaml.safe_load(app_path.read_text())
        app_data = app_configmap["data"]["Caddyfile"]
        assert "fallback-app" in app_data

        # Parse and verify proxy ConfigMap contains routes from fec.config.js
        proxy_configmap = yaml.safe_load(proxy_path.read_text())
        proxy_data = proxy_configmap["data"]["routes"]
        assert "handle /fallback-app*" in proxy_data
        assert "handle /settings/fallback-app*" in proxy_data

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_fallback_to_default_when_both_missing(tmp_path):
    """Test that when both frontend.yaml and fec.config.js are missing, default routes are used."""
    import shutil

    test_app_name = "default-routes-app"

    # Import the main function
    from main import run_plumber

    # Use non-existent paths for both files
    nonexistent_yaml = str(tmp_path / "nonexistent_frontend.yaml")
    nonexistent_fec = str(tmp_path / "nonexistent_fec.config.js")

    # Save current directory and change to tmp_path
    original_dir = os.getcwd()
    try:
        # Copy template directory to tmp_path so templates can be found
        shutil.copytree(os.path.join(original_dir, "template"), tmp_path / "template")

        os.chdir(tmp_path)

        # Run plumber with both files missing
        run_plumber(
            app_name=test_app_name,
            repo_url="https://github.com/test/repo",
            app_configmap_name="default-app-caddy",
            proxy_configmap_name="default-proxy-caddy",
            fec_config_path=nonexistent_fec,
            frontend_yaml_path=nonexistent_yaml,
        )

        # Verify the generated ConfigMaps use default routes
        app_path = tmp_path / "default-app-caddy.yaml"
        proxy_path = tmp_path / "default-proxy-caddy.yaml"

        assert app_path.exists(), "App ConfigMap should be generated"
        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

        # Parse and verify app ConfigMap contains default route
        app_configmap = yaml.safe_load(app_path.read_text())
        app_data = app_configmap["data"]["Caddyfile"]
        assert test_app_name in app_data

        # Parse and verify proxy ConfigMap contains default route
        proxy_configmap = yaml.safe_load(proxy_path.read_text())
        proxy_data = proxy_configmap["data"]["routes"]
        # Default route should be /{app_name}
        assert f"handle /{test_app_name}*" in proxy_data

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_frontend_yaml_takes_precedence_over_fec_config(tmp_path):
    """Test that when both frontend.yaml and fec.config.js exist, frontend.yaml takes precedence."""
    import shutil

    test_app_name = "precedence-app"

    # Create a test frontend.yaml with specific paths
    frontend_yaml_content = """apiVersion: template.openshift.io/v1
kind: Template
metadata:
  name: test-template
objects:
  - apiVersion: cloud.redhat.com/v1alpha1
    kind: Frontend
    metadata:
      name: precedence-app
    spec:
      frontend:
        paths:
          - /yaml-path-1
          - /yaml-path-2
"""

    # Create a test fec.config.js with different paths
    fec_config_content = """module.exports = {
  appUrl: ['/fec-path-1', '/fec-path-2'],
};
"""

    # Create temporary files
    yaml_path = tmp_path / "frontend.yaml"
    yaml_path.write_text(frontend_yaml_content)

    fec_path = tmp_path / "fec.config.js"
    fec_path.write_text(fec_config_content)

    # Import the main function
    from main import run_plumber

    # Save current directory and change to tmp_path
    original_dir = os.getcwd()
    try:
        # Copy template directory to tmp_path so templates can be found
        shutil.copytree(os.path.join(original_dir, "template"), tmp_path / "template")

        os.chdir(tmp_path)

        # Run plumber with both files present
        run_plumber(
            app_name=test_app_name,
            repo_url="https://github.com/test/repo",
            app_configmap_name="precedence-app-caddy",
            proxy_configmap_name="precedence-proxy-caddy",
            fec_config_path=str(fec_path),
            frontend_yaml_path=str(yaml_path),
        )

        # Verify the generated ConfigMaps use frontend.yaml values (not fec.config.js)
        proxy_path = tmp_path / "precedence-proxy-caddy.yaml"

        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

        # Parse and verify proxy ConfigMap contains routes from frontend.yaml
        proxy_configmap = yaml.safe_load(proxy_path.read_text())
        proxy_data = proxy_configmap["data"]["routes"]

        # Should contain yaml paths
        assert "handle /yaml-path-1*" in proxy_data
        assert "handle /yaml-path-2*" in proxy_data

        # Should NOT contain fec.config.js paths
        assert "/fec-path-1" not in proxy_data
        assert "/fec-path-2" not in proxy_data

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_frontend_yaml_extracts_navigation_routes(tmp_path):
    """Test navigation routes from frontend.yaml are extracted and included in Caddy configs."""
    import shutil

    test_app_name = "rbac"

    # Create a frontend.yaml with navigation routes similar to insights-rbac-ui
    frontend_yaml_content = """apiVersion: v1
kind: Template
metadata:
  name: rbac-frontend
objects:
  - apiVersion: cloud.redhat.com/v1alpha1
    kind: Frontend
    metadata:
      name: rbac
    spec:
      frontend:
        paths:
          - /apps/rbac
      searchEntries:
        - id: rbac-org-admin
          title: Org Admins
          href: /iam/user-access/users
          description: Test search entry
      serviceTiles:
        - id: users
          href: /iam/user-access/users
          title: Users
        - id: groups
          href: /iam/user-access/groups
          title: Groups
      bundleSegments:
        - segmentId: module-rbac-ui
          bundleId: iam
          navItems:
            - id: overview
              title: Overview
              href: /iam/user-access/overview
            - id: my-access
              title: My Access
              href: /iam/my-user-access
            - id: access-management
              title: Access Management
              expandable: true
              routes:
                - id: users-and-groups
                  title: Users and Groups
                  href: /iam/access-management/users-and-user-groups
                - id: roles
                  title: Roles
                  href: /iam/access-management/roles
      module:
        modules:
          - id: settings-user-access
            module: ./SettingsUserAccess
            routes:
              - pathname: /settings/rbac
          - id: iam-user-access
            module: ./Iam
            routes:
              - pathname: /iam
"""

    # Create temporary frontend.yaml
    yaml_path = tmp_path / "frontend.yaml"
    yaml_path.write_text(frontend_yaml_content)

    # Import the extraction function
    from extraction import get_app_url_from_frontend_yaml

    # Extract paths
    paths = get_app_url_from_frontend_yaml(str(yaml_path))

    # Verify all expected paths are extracted
    assert paths is not None, "Should extract paths from frontend.yaml"
    assert "/apps/rbac" in paths, "Should extract from spec.frontend.paths"
    assert "/settings/rbac" in paths, "Should extract from spec.module.modules[].routes[].pathname"
    assert "/iam" in paths, "Should extract from spec.module.modules[].routes[].pathname"
    assert "/iam/user-access/users" in paths, "Should extract from searchEntries[].href"
    assert "/iam/user-access/groups" in paths, "Should extract from serviceTiles[].href"
    assert "/iam/user-access/overview" in paths, (
        "Should extract from bundleSegments[].navItems[].href"
    )
    assert "/iam/my-user-access" in paths, "Should extract from bundleSegments[].navItems[].href"
    assert "/iam/access-management/users-and-user-groups" in paths, (
        "Should extract from bundleSegments[].navItems[].routes[].href"
    )
    assert "/iam/access-management/roles" in paths, (
        "Should extract from bundleSegments[].navItems[].routes[].href"
    )

    # Verify the paths are unique
    assert len(paths) == len(set(paths)), "Paths should be unique"

    # Now verify these paths make it into the generated ConfigMaps
    original_dir = os.getcwd()
    try:
        # Copy template directory to tmp_path so templates can be found
        shutil.copytree(os.path.join(original_dir, "template"), tmp_path / "template")

        os.chdir(tmp_path)

        from main import run_plumber

        # Generate ConfigMaps
        run_plumber(
            app_name=test_app_name,
            repo_url="https://github.com/test/repo",
            app_configmap_name="rbac-app-caddy",
            proxy_configmap_name="rbac-proxy-caddy",
            fec_config_path="nonexistent.js",
            frontend_yaml_path=str(yaml_path),
        )

        # Verify proxy ConfigMap includes navigation routes
        proxy_path = tmp_path / "rbac-proxy-caddy.yaml"
        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

        proxy_configmap = yaml.safe_load(proxy_path.read_text())
        proxy_data = proxy_configmap["data"]["routes"]

        # Verify navigation routes are in the proxy config
        assert "handle /iam/user-access/users*" in proxy_data
        assert "handle /iam/user-access/groups*" in proxy_data
        assert "handle /iam/user-access/overview*" in proxy_data
        assert "handle /iam/my-user-access*" in proxy_data
        assert "handle /iam/access-management/users-and-user-groups*" in proxy_data
        assert "handle /iam/access-management/roles*" in proxy_data

    finally:
        # Restore original directory
        os.chdir(original_dir)
