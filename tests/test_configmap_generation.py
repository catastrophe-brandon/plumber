import os
import tempfile

import yaml

from generation import generate_proxy_caddy_configmap


def test_generate_proxy_caddy_configmap():
    """Test that proxy Caddy ConfigMap is generated correctly."""
    test_configmap_name = "test-proxy-caddy"
    test_asset_routes = ["/settings/test-app", "/apps/test-app"]

    # Generate the ConfigMap
    output_path = generate_proxy_caddy_configmap(
        configmap_name=test_configmap_name,
        asset_routes=test_asset_routes,
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

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


def test_configmap_names_are_respected():
    """Test that ConfigMap names are correctly set."""
    proxy_configmap_name = "custom-proxy-config"
    test_asset_routes = ["/apps/my-app"]

    # Generate proxy ConfigMap
    proxy_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        asset_routes=test_asset_routes,
    )

    try:
        # Verify file name matches
        assert proxy_path.endswith(f"{proxy_configmap_name}.yaml")

        # Verify ConfigMap metadata name
        with open(proxy_path) as f:
            proxy_configmap = yaml.safe_load(f)
        assert proxy_configmap["metadata"]["name"] == proxy_configmap_name

    finally:
        # Clean up
        if os.path.exists(proxy_path):
            os.remove(proxy_path)


def test_configmap_integration_with_fec_config():
    """Integration test that generates ConfigMap using fec.config.js."""
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
        proxy_configmap_name = "integration-proxy-caddy"

        # Import the function that uses fec config
        from extraction import get_app_url_from_fec_config

        # Get app URLs from fec config
        app_urls = get_app_url_from_fec_config(fec_config_path)
        assert app_urls is not None, "Failed to parse fec.config.js"
        assert len(app_urls) == 3, f"Expected 3 URLs, got {len(app_urls)}"

        # Generate proxy ConfigMap
        proxy_path = generate_proxy_caddy_configmap(
            configmap_name=proxy_configmap_name,
            asset_routes=app_urls,
        )

        # Verify proxy ConfigMap
        with open(proxy_path) as f:
            proxy_configmap = yaml.safe_load(f)
        assert proxy_configmap is not None
        assert proxy_configmap["kind"] == "ConfigMap"

        # Verify fec config URLs made it into the config
        proxy_data = proxy_configmap["data"]["routes"]  # Proxy uses "routes" key
        assert "handle /settings/test-app*" in proxy_data

        # Clean up
        os.remove(proxy_path)

    finally:
        # Clean up temp fec config
        if os.path.exists(fec_config_path):
            os.remove(fec_config_path)


def test_configmap_with_namespace():
    """Test that namespace is correctly added to ConfigMap."""
    proxy_configmap_name = "namespace-proxy-caddy"
    test_namespace = "hcc-platex-services-tenant"
    test_app_urls = ["/namespace-test-app"]

    # Generate proxy ConfigMap with namespace
    proxy_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        asset_routes=test_app_urls,
        namespace=test_namespace,
    )

    try:
        # Verify proxy ConfigMap has namespace
        with open(proxy_path) as f:
            proxy_configmap = yaml.safe_load(f)
        assert proxy_configmap["metadata"]["name"] == proxy_configmap_name
        assert proxy_configmap["metadata"]["namespace"] == test_namespace

        # Verify proxy uses "routes" key
        assert "routes" in proxy_configmap["data"]

    finally:
        # Clean up
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
            proxy_configmap_name="fallback-proxy-caddy",
            fec_config_path=str(fec_config_path),
            frontend_yaml_path=nonexistent_yaml,
        )

        # Verify the generated ConfigMap uses fec.config.js values
        proxy_path = tmp_path / "fallback-proxy-caddy.yaml"
        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

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
            proxy_configmap_name="default-proxy-caddy",
            fec_config_path=nonexistent_fec,
            frontend_yaml_path=nonexistent_yaml,
        )

        # Verify the generated ConfigMap uses default routes
        proxy_path = tmp_path / "default-proxy-caddy.yaml"
        assert proxy_path.exists(), "Proxy ConfigMap should be generated"

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
            proxy_configmap_name="precedence-proxy-caddy",
            fec_config_path=str(fec_path),
            frontend_yaml_path=str(yaml_path),
        )

        # Verify the generated ConfigMap uses frontend.yaml values (not fec.config.js)
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

    # Extract all paths (for reference)
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

    # Now verify the proxy ConfigMap only contains asset paths
    original_dir = os.getcwd()
    try:
        # Copy template directory to tmp_path so templates can be found
        shutil.copytree(os.path.join(original_dir, "template"), tmp_path / "template")

        os.chdir(tmp_path)

        from main import run_plumber

        # Generate ConfigMap
        run_plumber(
            app_name=test_app_name,
            repo_url="https://github.com/test/repo",
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

        # Verify Chrome shell routes are NOT in the proxy config
        assert "handle /iam*" not in proxy_data, "Should NOT include /iam Chrome shell route"
        assert "handle /apps/chrome*" not in proxy_data, "Should NOT include /apps/chrome route"
        assert "handle /*" not in proxy_data and "handle / *" not in proxy_data, (
            "Should NOT include / route"
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
