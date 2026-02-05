import argparse
import json

from extraction import (
    get_app_url_from_fec_config,
    get_app_url_from_frontend_yaml,
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
):
    print("Hello from plumber!")
    print(f"App Name: {app_name}")
    print(f"Repo URL: {repo_url}")
    print(f"App ConfigMap Name: {app_configmap_name}")
    print(f"Proxy ConfigMap Name: {proxy_configmap_name}")
    if namespace:
        print(f"Namespace: {namespace}")

    # Default ports
    app_port = "8000"
    chrome_port = "9912"

    # Try to get appUrl from frontend.yaml first (for older repos)
    app_url_value = None
    try:
        app_url_value = get_app_url_from_frontend_yaml(frontend_yaml_path)
        if app_url_value:
            print(f"Found paths in {frontend_yaml_path}: {app_url_value}")
    except (FileNotFoundError, ValueError):
        print(f"Note: Could not read {frontend_yaml_path}, trying fec.config.js")

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

    # Detect if this is a federated module
    is_fed_module = False
    try:
        is_fed_module = is_federated_module(frontend_yaml_path)
        if is_fed_module:
            print("Detected federated module (has manifestLocation in frontend.yaml)")
            print("  → Will skip index.html fallback in Caddyfile")
    except (FileNotFoundError, ValueError):
        print("Note: Could not detect federated module status, assuming standalone app")

    # Generate app Caddy ConfigMap
    app_configmap_path = generate_app_caddy_configmap(
        configmap_name=app_configmap_name,
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
        namespace=namespace,
        is_federated_module=is_fed_module,
    )
    print(f"\nGenerated app Caddy ConfigMap: {app_configmap_path}")

    # Generate proxy Caddy ConfigMap
    proxy_configmap_path = generate_proxy_caddy_configmap(
        configmap_name=proxy_configmap_name,
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
        chrome_port=chrome_port,
        namespace=namespace,
        is_federated_module=is_fed_module,
    )
    print(f"Generated proxy Caddy ConfigMap: {proxy_configmap_path}")


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

    args = parser.parse_args()

    run_plumber(
        args.app_name,
        args.repo_url,
        args.app_configmap_name,
        args.proxy_configmap_name,
        args.fec_config,
        args.frontend_yaml,
        args.namespace,
    )


if __name__ == "__main__":
    main()
