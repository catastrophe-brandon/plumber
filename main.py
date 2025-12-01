import argparse
import json
import os

from jinja2 import Environment, FileSystemLoader


def get_app_url_from_fec_config(config_path: str = "fec.config.js") -> list[str] | None:
    """
    Extract the appUrl from fec.config.js file.

    Args:
        config_path: Path to the fec.config.js file (default: "fec.config.js")

    Returns:
        The appUrl value from fec.config.js, or None if not found

    Raises:
        FileNotFoundError: If fec.config.js is not found
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"fec.config.js not found at: {config_path}")

    # Read and parse the fec.config.js file as JSON
    with open(config_path) as f:
        config = json.load(f)

    # Get appUrl from the config object
    return config.get("appUrl")


def generate_frontend_proxy_caddyfile(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    chrome_port: str = "9912",
    template_path: str = "template/proxy_caddy.template.j2",
) -> str:
    """
    Generate a Caddyfile configuration for the frontend proxy.

    Args:
        app_url_value: List of URL paths from appUrl (e.g., ["/settings/my-app", "/apps/my-app"])
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        chrome_port: Port for chrome resources (default: "9912")
        template_path: Path to the Jinja2 template (default: "template/proxy_caddy.template.j2")

    Returns:
        Rendered Caddyfile configuration as a string
    """
    # Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)

    # Render the template with app_url_value routes
    rendered = template.render(
        app_name=app_name,
        app_port=app_port,
        chrome_port=chrome_port,
        route_prefixes=app_url_value,
    )

    return rendered


def generate_pipeline_from_template(
    pipeline_template_path: str,
    app_name: str,
    repo_url: str,
    app_caddy_file: str,
    proxy_caddy_file: str,
) -> str:
    """
    Read a pipeline template file, substitute app_name, repo_url, and Caddyfile contents,
    and write to a temporary location.

    Args:
        pipeline_template_path: Path to the pipeline template YAML file
        app_name: Name of the application to substitute into the template
        repo_url: Git repository URL to substitute into the template
        app_caddy_file: Contents of the application Caddyfile
        proxy_caddy_file: Contents of the proxy Caddyfile

    Returns:
        Path to the generated pipeline file in /tmp
    """
    # Read the template file
    with open(pipeline_template_path) as f:
        template_content = f.read()

    # Perform substitutions
    substituted_content = template_content.replace("{{app_name}}", app_name)
    substituted_content = substituted_content.replace("{{repo_url}}", repo_url)
    substituted_content = substituted_content.replace("{{app_caddy_file}}", app_caddy_file)
    substituted_content = substituted_content.replace("{{proxy_caddy_file}}", proxy_caddy_file)

    # Create output file in /tmp
    output_filename = f"{app_name}-pipeline.yaml"
    output_path = os.path.join("/tmp", output_filename)

    # Write the substituted content
    with open(output_path, "w") as f:
        f.write(substituted_content)

    return output_path


def main(app_name: str, repo_url: str, pipeline_template: str):
    print("Hello from plumber!")
    print(f"App Name: {app_name}")
    print(f"Repo URL: {repo_url}")
    print(f"Pipeline Template: {pipeline_template}")

    # TODO: Generate these from templates
    app_caddy_file = "# App Caddyfile placeholder"
    proxy_caddy_file = "# Proxy Caddyfile placeholder"

    # Generate pipeline from template
    output_path = generate_pipeline_from_template(
        pipeline_template, app_name, repo_url, app_caddy_file, proxy_caddy_file
    )
    print(f"\nGenerated pipeline file: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
    parser.add_argument("app_name", type=str, help="Name of the application")
    parser.add_argument("repo_url", type=str, help="Git URL of the repository")
    parser.add_argument("pipeline_template", type=str, help="Path to the pipeline template file")

    args = parser.parse_args()
    main(args.app_name, args.repo_url, args.pipeline_template)
