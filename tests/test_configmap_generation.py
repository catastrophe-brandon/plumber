import os
import tempfile

import pytest
import yaml

from generation import (
    generate_app_caddy_configmap,
    generate_app_caddyfile,
    generate_proxy_caddy_configmap,
    validate_federated_module_config,
)


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
    test_configmap_name = "test-proxy-caddy"
    test_asset_routes = ["/settings/test-app", "/apps/test-app"]
    test_chrome_routes = ["/iam", "/apps/chrome", "/", "/index.html"]

    # Generate the ConfigMap
    output_path = generate_proxy_caddy_configmap(
        configmap_name=test_configmap_name,
        asset_routes=test_asset_routes,
        chrome_routes=test_chrome_routes,
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

        # Verify asset routes go to localhost
        assert "handle /apps/test-app*" in routes_content
        assert "handle /settings/test-app*" in routes_content
        assert "reverse_proxy 127.0.0.1:8000" in routes_content

        # Verify Chrome routes go to stage environment
        assert "handle /iam*" in routes_content
        assert "handle /apps/chrome*" in routes_content
        assert "reverse_proxy ${HCC_ENV_URL}" in routes_content

        # CRITICAL: Verify incorrect Caddy syntax is NOT present
        assert "{env.HCC_ENV_URL}" not in routes_content, (
            "Generated config contains incorrect Caddy syntax {env.HCC_ENV_URL}. "
            "Must use ${HCC_ENV_URL} for environment variable substitution."
        )

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
    test_asset_routes = ["/apps/my-app"]

    # Generate both ConfigMaps
    app_path = generate_app_caddy_configmap(
        configmap_name=app_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
    )

    proxy_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        asset_routes=test_asset_routes,
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
            asset_routes=app_urls,
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
        asset_routes=test_app_urls,
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
    """Test that navigation routes are extracted but NOT included in proxy ConfigMap."""
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

    # Import the extraction functions
    from extraction import get_app_url_from_frontend_yaml, get_proxy_routes_from_frontend_yaml

    # Extract all paths (for app ConfigMap)
    all_paths = get_app_url_from_frontend_yaml(str(yaml_path))

    # Verify all expected paths are extracted
    assert all_paths is not None, "Should extract paths from frontend.yaml"
    assert "/apps/rbac" in all_paths, "Should extract from spec.frontend.paths"
    assert "/settings/rbac" in all_paths, (
        "Should extract from spec.module.modules[].routes[].pathname"
    )
    assert "/iam" in all_paths, "Should extract from spec.module.modules[].routes[].pathname"
    assert "/iam/user-access/users" in all_paths, "Should extract from searchEntries[].href"
    assert "/iam/user-access/groups" in all_paths, "Should extract from serviceTiles[].href"
    assert "/iam/user-access/overview" in all_paths, (
        "Should extract from bundleSegments[].navItems[].href"
    )
    assert "/iam/my-user-access" in all_paths, (
        "Should extract from bundleSegments[].navItems[].href"
    )
    assert "/iam/access-management/users-and-user-groups" in all_paths, (
        "Should extract from bundleSegments[].navItems[].routes[].href"
    )
    assert "/iam/access-management/roles" in all_paths, (
        "Should extract from bundleSegments[].navItems[].routes[].href"
    )

    # Verify the paths are unique
    assert len(all_paths) == len(set(all_paths)), "Paths should be unique"

    # Extract proxy routes (asset paths only, not navigation routes)
    proxy_routes = get_proxy_routes_from_frontend_yaml(str(yaml_path))

    # Verify proxy routes (asset routes) contain ONLY /apps/* and /settings/* paths
    assert proxy_routes is not None, "Should extract proxy routes"
    assert "/apps/rbac" in proxy_routes, "Should include spec.frontend.paths"
    assert "/settings/rbac" in proxy_routes, (
        "Should include spec.module.modules[].routes (asset paths)"
    )

    # Verify /iam is NOT in asset routes (it's a Chrome shell bundle mount)
    assert "/iam" not in proxy_routes, "Should exclude Chrome shell bundle mounts from asset routes"

    # Verify navigation routes are NOT in proxy routes
    assert "/iam/user-access/users" not in proxy_routes, "Should exclude searchEntries"
    assert "/iam/user-access/groups" not in proxy_routes, "Should exclude serviceTiles"
    assert "/iam/user-access/overview" not in proxy_routes, "Should exclude bundleSegments navItems"
    assert "/iam/my-user-access" not in proxy_routes, "Should exclude bundleSegments navItems"
    assert "/iam/access-management/users-and-user-groups" not in proxy_routes, (
        "Should exclude bundleSegments navItems routes"
    )
    assert "/iam/access-management/roles" not in proxy_routes, (
        "Should exclude bundleSegments navItems routes"
    )

    # Verify proxy routes are fewer than all paths
    assert len(proxy_routes) < len(all_paths), "Proxy routes should be a subset of all paths"

    # Extract Chrome shell routes
    from extraction import get_chrome_routes_from_frontend_yaml

    chrome_routes = get_chrome_routes_from_frontend_yaml(str(yaml_path))
    assert chrome_routes is not None, "Should extract Chrome shell routes"
    assert "/iam" in chrome_routes, "Should include Chrome shell bundle mounts"
    assert "/apps/chrome" in chrome_routes, "Should include standard Chrome route"
    assert "/" in chrome_routes, "Should include root route"
    assert "/index.html" in chrome_routes, "Should include index.html route"

    # Now verify the proxy ConfigMap only contains asset paths
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

        # Verify proxy ConfigMap only contains asset paths
        proxy_path = tmp_path / "rbac-proxy-caddy.yaml"
        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

        proxy_configmap = yaml.safe_load(proxy_path.read_text())
        proxy_data = proxy_configmap["data"]["routes"]

        # Verify asset paths ARE in the proxy config and route to localhost
        assert "handle /apps/rbac*" in proxy_data, "Should include /apps/rbac asset path"
        assert "handle /settings/rbac*" in proxy_data, "Should include /settings/rbac asset path"
        assert "reverse_proxy 127.0.0.1:8000" in proxy_data, (
            "Asset routes should proxy to localhost"
        )

        # Verify Chrome shell routes ARE in the proxy config and route to stage environment
        assert "handle /iam*" in proxy_data, "Should include /iam Chrome shell route"
        assert "handle /apps/chrome*" in proxy_data, "Should include /apps/chrome route"
        assert "handle /*" in proxy_data or "handle / " in proxy_data, "Should include / route"
        assert "reverse_proxy ${HCC_ENV_URL}" in proxy_data, (
            "Chrome routes should proxy to stage env"
        )

        # CRITICAL: Verify incorrect Caddy syntax is NOT present
        assert "{env.HCC_ENV_URL}" not in proxy_data, (
            "Generated config contains incorrect Caddy syntax {env.HCC_ENV_URL}. "
            "Must use ${HCC_ENV_URL} for environment variable substitution."
        )

        # Verify navigation routes are NOT in the proxy config
        assert "handle /iam/user-access/users*" not in proxy_data, (
            "Should NOT include navigation route"
        )
        assert "handle /iam/user-access/groups*" not in proxy_data, (
            "Should NOT include navigation route"
        )
        assert "handle /iam/user-access/overview*" not in proxy_data, (
            "Should NOT include navigation route"
        )
        assert "handle /iam/my-user-access*" not in proxy_data, (
            "Should NOT include navigation route"
        )
        assert "handle /iam/access-management/users-and-user-groups*" not in proxy_data, (
            "Should NOT include navigation route"
        )
        assert "handle /iam/access-management/roles*" not in proxy_data, (
            "Should NOT include navigation route"
        )

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_validate_federated_module_config_rejects_try_files():
    """Test that validation raises an error if a federated module config contains try_files."""
    caddyfile_with_try_files = """
    :8000 {
        handle /apps/my-app* {
            try_files {path} /index.html
            file_server * {
                root /srv/dist
            }
        }
    }
    """

    # Should raise ValueError for federated module with try_files
    with pytest.raises(ValueError, match="Federated module configuration contains 'try_files'"):
        validate_federated_module_config(caddyfile_with_try_files, is_federated=True)


def test_validate_federated_module_config_allows_no_try_files():
    """Test that validation passes if a federated module config has no try_files."""
    caddyfile_without_try_files = """
    :8000 {
        handle /apps/my-app* {
            file_server * {
                root /srv/dist
            }
        }
    }
    """

    # Should not raise any error
    validate_federated_module_config(caddyfile_without_try_files, is_federated=True)


def test_validate_standalone_app_allows_try_files():
    """Test that validation passes for standalone apps with try_files."""
    caddyfile_with_try_files = """
    :8000 {
        handle /apps/my-app* {
            try_files {path} /index.html
            file_server * {
                root /srv/dist
            }
        }
    }
    """

    # Should not raise any error for standalone apps
    validate_federated_module_config(caddyfile_with_try_files, is_federated=False)


def test_federated_module_generates_config_without_try_files():
    """Test that federated modules generate Caddy config without try_files directives."""
    test_app_name = "rbac"
    test_app_urls = ["/apps/rbac", "/settings/rbac"]

    # Generate Caddyfile for federated module
    caddyfile = generate_app_caddyfile(
        app_url_value=test_app_urls,
        app_name=test_app_name,
        is_federated=True,
    )

    # Verify no try_files directives in the output
    assert "try_files" not in caddyfile, (
        "Federated module config should not contain 'try_files' directives"
    )

    # Verify file_server is still present (we still serve static files)
    assert "file_server" in caddyfile


def test_standalone_app_generates_config_with_try_files():
    """Test that standalone apps generate Caddy config with try_files directives."""
    test_app_name = "my-standalone-app"
    test_app_urls = ["/apps/my-standalone-app"]

    # Generate Caddyfile for standalone app
    caddyfile = generate_app_caddyfile(
        app_url_value=test_app_urls,
        app_name=test_app_name,
        is_federated=False,
    )

    # Verify try_files directives ARE present for standalone apps
    assert "try_files" in caddyfile, "Standalone app config should contain 'try_files' directives"

    # Verify file_server is present
    assert "file_server" in caddyfile


def test_federated_module_configmap_has_no_try_files():
    """Integration test: Verify federated module ConfigMap has no try_files."""
    test_app_name = "rbac"
    test_configmap_name = "rbac-federated-caddy"
    test_app_urls = ["/apps/rbac", "/settings/rbac"]

    # Generate the ConfigMap for a federated module
    output_path = generate_app_caddy_configmap(
        configmap_name=test_configmap_name,
        app_url_value=test_app_urls,
        app_name=test_app_name,
        is_federated=True,
    )

    try:
        # Verify the output file exists
        assert os.path.exists(output_path), f"Output file not created at {output_path}"

        # Read and parse the YAML
        with open(output_path) as f:
            configmap_content = f.read()

        # Parse YAML
        configmap = yaml.safe_load(configmap_content)
        caddyfile_content = configmap["data"]["Caddyfile"]

        # Verify no try_files in the generated config
        assert "try_files" not in caddyfile_content, (
            "Federated module ConfigMap should not contain 'try_files' directives"
        )

        # Verify routes are still present
        assert "/apps/rbac" in caddyfile_content
        assert "/settings/rbac" in caddyfile_content

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)
