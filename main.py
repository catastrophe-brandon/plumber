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

    # Read the file
    with open(config_path) as f:
        content = f.read()

    # Find appUrl: [ ... ] pattern
    start_marker = "appUrl:"
    start = content.find(start_marker)
    if start == -1:
        return None

    # Find the opening bracket
    bracket_start = content.find("[", start)
    if bracket_start == -1:
        return None

    # Find the matching closing bracket
    bracket_end = content.find("]", bracket_start)
    if bracket_end == -1:
        return None

    # Extract the array content and convert to valid JSON
    array_content = content[bracket_start : bracket_end + 1]
    # Replace single quotes with double quotes for JSON compatibility
    # This handles JavaScript string literals which can use single quotes
    array_content = array_content.replace("'", '"')
    # Remove trailing commas (JavaScript allows them, JSON doesn't)
    import re
    array_content = re.sub(r',(\s*])', r'\1', array_content)
    return json.loads(array_content)


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


def generate_proxy_routes_json(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    chrome_port: str = "9912",
) -> str:
    """
    Generate JSON configuration for proxy routes (for Tekton pipeline).

    Args:
        app_url_value: List of URL paths from appUrl (e.g., ["/settings/my-app", "/apps/my-app"])
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        chrome_port: Port for Chrome resources (default: "9912")

    Returns:
        JSON string with route configuration
    """
    routes = {}

    # Add standard Chrome routes
    routes["/index.html"] = {
        "url": f"http://localhost:{chrome_port}",
        "is_chrome": True
    }
    routes["/apps/chrome*"] = {
        "url": f"http://localhost:{chrome_port}",
        "is_chrome": True
    }

    # Add app routes
    routes[f"/apps/{app_name}*"] = {
        "url": f"http://localhost:{app_port}",
        "is_chrome": False
    }

    # Add all appUrl routes (pointing to chrome for the shell)
    for route in app_url_value:
        routes[f"{route}*"] = {
            "url": f"http://localhost:{chrome_port}",
            "is_chrome": True
        }

    # Return compact JSON on a single line to avoid YAML parsing issues
    return json.dumps(routes)


def generate_app_caddyfile(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
) -> str:
    """
    Generate a Caddyfile configuration for the application server.

    This creates Caddy route handlers that serve the static application files
    from /srv/dist for each route in appUrl.

    Args:
        app_url_value: List of URL paths from appUrl (e.g., ["/settings/my-app", "/apps/my-app"])
        app_name: Name of the application
        app_port: Port for the application (default: "8000")

    Returns:
        Rendered Caddyfile configuration as a string
    """
    # Start with the server block
    lines = [f":{app_port} {{"]

    # Generate route handlers for each app URL
    for route in app_url_value:
        # Generate matcher name from route (e.g., "/settings/my-app" -> "settings_my_app")
        matcher_name = route.lstrip("/").replace("/", "_").replace("-", "_")

        # Handler for exact route match (/ and /path/)
        lines.append(f"    @{matcher_name}_match {{")
        lines.append(f"        path {route} {route}/")
        lines.append(f"    }}")
        lines.append(f"    handle @{matcher_name}_match {{")
        lines.append(f"        uri strip_prefix {route}")
        lines.append(f"        rewrite / /index.html")
        lines.append(f"        file_server * {{")
        lines.append(f"            root /srv/dist")
        lines.append(f"        }}")
        lines.append(f"    }}")
        lines.append("")

        # Handler for subpaths (e.g., /path/*)
        lines.append(f"    @{matcher_name}_subpath {{")
        lines.append(f"        path {route}/*")
        lines.append(f"    }}")
        lines.append(f"    handle @{matcher_name}_subpath {{")
        lines.append(f"        uri strip_prefix {route}")
        lines.append(f"        file_server * {{")
        lines.append(f"            root /srv/dist")
        lines.append(f"        }}")
        lines.append(f"    }}")
        lines.append("")

    # Fallback handler
    lines.append("    handle / {")
    lines.append("        file_server * {")
    lines.append("            root /srv/dist")
    lines.append("        }")
    lines.append("    }")

    # Close the server block
    lines.append("}")

    return "\n".join(lines)


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

    # Add proper indentation for YAML multiline strings
    # The template uses 6 spaces of indentation for content inside literal blocks
    indent = "      "
    app_caddy_indented = "\n".join(indent + line if line else "" for line in app_caddy_file.split("\n"))
    # Proxy JSON also needs indentation for YAML consistency
    proxy_json_indented = "\n".join(indent + line if line else "" for line in proxy_caddy_file.split("\n"))

    # Perform substitutions
    substituted_content = template_content.replace("{{app_name}}", app_name)
    substituted_content = substituted_content.replace("{{repo_url}}", repo_url)
    substituted_content = substituted_content.replace("{{app_caddy_file}}", app_caddy_indented)
    substituted_content = substituted_content.replace("{{proxy_caddy_file}}", proxy_json_indented)

    # Create output file in /tmp
    output_filename = f"{app_name}-pipeline.yaml"
    output_path = os.path.join("/tmp", output_filename)

    # Write the substituted content
    with open(output_path, "w") as f:
        f.write(substituted_content)

    return output_path


def run_plumber(
    app_name: str, repo_url: str, pipeline_template: str, fec_config_path: str = "fec.config.js"
):
    print("Hello from plumber!")
    print(f"App Name: {app_name}")
    print(f"Repo URL: {repo_url}")
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

    # Generate proxy routes JSON
    proxy_routes_json = generate_proxy_routes_json(
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
        chrome_port=chrome_port,
    )
    print("\nGenerated proxy routes JSON:")
    print(proxy_routes_json)

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
        pipeline_template, app_name, repo_url, app_caddy_file, proxy_routes_json
    )
    print(f"\nGenerated pipeline file: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
    parser.add_argument("app_name", type=str, help="Name of the application")
    parser.add_argument("repo_url", type=str, help="Git URL of the repository")
    parser.add_argument("pipeline_template", type=str, help="Path to the pipeline template file")
    parser.add_argument(
        "--fec-config",
        type=str,
        default="fec.config.js",
        help="Path to fec.config.js file (default: fec.config.js)",
    )

    args = parser.parse_args()
    run_plumber(args.app_name, args.repo_url, args.pipeline_template, args.fec_config)


if __name__ == "__main__":
    main()
