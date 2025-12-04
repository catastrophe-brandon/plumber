import argparse
import json

from extraction import get_app_url_from_fec_config
from generation import generate_app_caddyfile, generate_pipeline_from_template, generate_proxy_routes_caddyfile


def run_plumber(
    app_name: str,
    repo_url: str,
    pipeline_template: str,
    fec_config_path: str = "fec.config.js",
    pipeline_type: str = "konflux"
):
    print("Hello from plumber!")
    print(f"App Name: {app_name}")
    print(f"Repo URL: {repo_url}")
    print(f"Pipeline Type: {pipeline_type}")
    print(f"Pipeline Template: {pipeline_template}")

    # Default ports
    app_port = "8000"
    chrome_port = "9912"

    # Try to get appUrl from fec.config.js
    try:
        app_url_value = get_app_url_from_fec_config(fec_config_path)
        print(f"Found appUrl in {fec_config_path}: {app_url_value}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not read {fec_config_path} ({e}), using default routes")
        app_url_value = [f"/{app_name}"]

    # Generate proxy routes Caddyfile
    proxy_routes_caddyfile = generate_proxy_routes_caddyfile(
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
        chrome_port=chrome_port,
    )
    print("\nGenerated proxy routes Caddyfile:")
    print(proxy_routes_caddyfile)

    # Generate app Caddyfile
    app_caddy_file = generate_app_caddyfile(
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
    )
    print("\nGenerated app Caddyfile:")
    print(app_caddy_file)

    # Generate pipeline from template
    output_path = generate_pipeline_from_template(
        pipeline_template, app_name, repo_url, app_caddy_file, proxy_routes_caddyfile
    )
    print(f"\nGenerated pipeline file: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
    parser.add_argument("app_name", type=str, help="Name of the application")
    parser.add_argument("repo_url", type=str, help="Git URL of the repository")

    # Mutually exclusive group for pipeline type
    pipeline_group = parser.add_mutually_exclusive_group(required=True)
    pipeline_group.add_argument(
        "--pipeline-template",
        type=str,
        help="Path to the Konflux pipeline template file"
    )
    pipeline_group.add_argument(
        "--minikube-template",
        type=str,
        help="Path to the Minikube pipeline template file"
    )

    parser.add_argument(
        "--fec-config",
        type=str,
        default="fec.config.js",
        help="Path to fec.config.js file (default: fec.config.js)",
    )

    args = parser.parse_args()

    # Determine which template was provided
    pipeline_template = args.pipeline_template or args.minikube_template
    pipeline_type = "konflux" if args.pipeline_template else "minikube"

    run_plumber(args.app_name, args.repo_url, pipeline_template, args.fec_config, pipeline_type)


if __name__ == "__main__":
    main()
