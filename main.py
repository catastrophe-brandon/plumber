import argparse
import json

from extraction import (
    get_app_url_from_fec_config,
    get_app_url_from_frontend_yaml,
    get_chrome_routes_from_frontend_yaml,
    get_module_name_from_frontend_yaml,
    get_proxy_routes_from_frontend_yaml,
    is_federated_module,
)
from generation import generate_app_caddy_configmap, generate_proxy_caddy_configmap


def run_plumber(
    app_name: str,
    repo_url: str,
    app_configmap_name: str,
    proxy_configmap_name: str,
    fec_config_path: str = "fec.config.js",
    frontend_yaml_path: str = "deploy/frontend.yaml",
    namespace: str | None = None,
    stage_env_url: str | None = None,
):
    print("Hello from plumber!")
    print(f"App Name (from CLI): {app_name}")
    print(f"Repo URL: {repo_url}")
    print(f"App ConfigMap Name: {app_configmap_name}")
    print(f"Proxy ConfigMap Name: {proxy_configmap_name}")
    if namespace:
        print(f"Namespace: {namespace}")

    # Default port
    app_port = "8000"

    # Detect if this is a federated module
    is_federated = False
    try:
        is_federated = is_federated_module(frontend_yaml_path)
        if is_federated:
            print("✓ Detected federated module (has spec.module.manifestLocation)")
        else:
            print("✓ Detected standalone app (no spec.module.manifestLocation)")
    except (FileNotFoundError, ValueError) as e:
        print(f"Note: Could not detect module type from {frontend_yaml_path}: {e}")

    # Try to extract module name from frontend.yaml (overrides CLI app_name)
    module_name = None
    try:
        module_name = get_module_name_from_frontend_yaml(frontend_yaml_path)
        if module_name:
            print(f"✓ Extracted module name from frontend.yaml: {module_name}")
            if module_name != app_name:
                print(f"  Note: Using '{module_name}' instead of CLI app_name '{app_name}'")
            app_name = module_name  # Override CLI app_name with extracted module name
        else:
            print(
                f"Note: No module name found in {frontend_yaml_path}, "
                f"using CLI app_name: {app_name}"
            )
    except (FileNotFoundError, ValueError) as e:
        print(f"Note: Could not extract module name from {frontend_yaml_path}: {e}")
        print(f"      Using CLI app_name: {app_name}")

    # Try to get appUrl from frontend.yaml first (for older repos)
    app_url_value = None
    try:
        app_url_value = get_app_url_from_frontend_yaml(frontend_yaml_path)
        if app_url_value:
            print(f"✓ Found paths in {frontend_yaml_path}: {app_url_value}")
    except (FileNotFoundError, ValueError):
        print(f"Note: Could not read paths from {frontend_yaml_path}, trying fec.config.js")

    # Fall back to fec.config.js if frontend.yaml didn't provide paths
    if not app_url_value:
        try:
            app_url_value = get_app_url_from_fec_config(fec_config_path)
            if app_url_value:
                print(f"Found appUrl in {fec_config_path}: {app_url_value}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not read {fec_config_path} ({e}), using default routes")

    # Use default if neither file provided paths
    if not app_url_value:
        app_url_value = [f"/{app_name}"]
        print(f"Using default routes: {app_url_value}")

    # Extract proxy routes (asset paths only, not navigation routes)
    # For federated modules, proxy should only route /apps/* and /settings/* paths,
    # NOT navigation routes like /iam/* which should be routed to Chrome shell
    asset_routes = None
    try:
        asset_routes = get_proxy_routes_from_frontend_yaml(frontend_yaml_path)
        if asset_routes:
            print(f"✓ Extracted asset routes (for local app): {asset_routes}")
    except (FileNotFoundError, ValueError):
        print(
            f"Note: Could not extract asset routes from {frontend_yaml_path}, using all app routes"
        )

    # Fall back to app_url_value if asset routes couldn't be extracted
    if not asset_routes:
        asset_routes = app_url_value
        print(f"Using all app routes as asset routes: {asset_routes}")

    # Extract Chrome shell routes (bundle mounts and standard Chrome paths)
    chrome_routes = None
    try:
        chrome_routes = get_chrome_routes_from_frontend_yaml(frontend_yaml_path)
        if chrome_routes:
            print(f"✓ Extracted Chrome shell routes (for stage env): {chrome_routes}")
    except (FileNotFoundError, ValueError):
        print(
            f"Note: Could not extract Chrome routes from {frontend_yaml_path}, "
            f"using default Chrome routes"
        )

    # Use default Chrome routes if extraction failed
    # Note: Only /apps/chrome is included as an explicit route.
    # Root path (/) and /index.html are handled by the main Caddyfile's final catch-all.
    if not chrome_routes:
        chrome_routes = ["/apps/chrome"]
        print(f"Using default Chrome shell routes: {chrome_routes}")

    # Generate app Caddy ConfigMap (using asset_routes, not all routes)
    app_configmap_path = generate_app_caddy_configmap(
        configmap_name=app_configmap_name,
        app_url_value=asset_routes,  # Use asset routes, not all routes
        app_name=app_name,
        app_port=app_port,
        namespace=namespace,
        is_federated=is_federated,
    )
    print(f"\n✓ Generated app Caddy ConfigMap: {app_configmap_path}")

    # Generate proxy Caddy ConfigMap (using asset_routes and chrome_routes)
    proxy_configmap_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        asset_routes=asset_routes,
        chrome_routes=chrome_routes,
        app_port=app_port,
        namespace=namespace,
        stage_env_url=stage_env_url,
    )
    print(f"✓ Generated proxy Caddy ConfigMap: {proxy_configmap_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Plumber - Generate Caddy ConfigMaps for application testing"
    )
    parser.add_argument("app_name", type=str, help="Name of the application")
    parser.add_argument("repo_url", type=str, help="Git URL of the repository")

    parser.add_argument(
        "--app-configmap-name",
        type=str,
        required=True,
        help="Name for the app Caddy ConfigMap",
    )
    parser.add_argument(
        "--proxy-configmap-name",
        type=str,
        required=True,
        help="Name for the proxy routes Caddy ConfigMap",
    )

    parser.add_argument(
        "--fec-config",
        type=str,
        default="fec.config.js",
        help="Path to fec.config.js file (default: fec.config.js)",
    )

    parser.add_argument(
        "--frontend-yaml",
        type=str,
        default="deploy/frontend.yaml",
        help="Path to frontend.yaml file (default: deploy/frontend.yaml)",
    )

    parser.add_argument(
        "--namespace",
        type=str,
        default=None,
        help="Optional Kubernetes namespace for the ConfigMaps",
    )

    parser.add_argument(
        "--stage-env-url",
        type=str,
        default=None,
        help="Stage environment URL for Chrome shell routes (e.g., https://stage.foo.redhat.com)",
    )

    args = parser.parse_args()

    run_plumber(
        args.app_name,
        args.repo_url,
        args.app_configmap_name,
        args.proxy_configmap_name,
        args.fec_config,
        args.frontend_yaml,
        args.namespace,
        args.stage_env_url,
    )


if __name__ == "__main__":
    main()
