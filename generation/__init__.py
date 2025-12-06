import json
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


def generate_app_caddyfile(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    template_path: str = "template/app_caddy.template.j2",
) -> str:
    """
    Generate a Caddyfile configuration for the application server using a Jinja2 template.

    This creates Caddy route handlers that serve the static application files
    from /srv/dist for each route in appUrl.

    Args:
        app_url_value: List of URL paths from appUrl (e.g., ["/settings/my-app", "/apps/my-app"])
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        template_path: Path to the Jinja2 template (default: "template/app_caddy.template.j2")

    Returns:
        Rendered Caddyfile configuration as a string
    """
    # Extract route path prefixes from app URLs
    # E.g., "/settings/learning-resources" -> "settings"
    # E.g., "/openshift/learning-resources" -> "openshift"
    # Skip routes that are just "/{app_name}" or "/{app_name}/..." (no prefix)
    route_path_prefixes = []
    for route in app_url_value:
        parts = route.strip("/").split("/")
        # Only process routes that end with the app_name
        # E.g., "/settings/learning-resources" -> ["settings", "learning-resources"]
        # E.g., "/learning-resources" -> ["learning-resources"]
        # E.g., "/learning-resources/creator" -> skip (doesn't end with app_name)
        if len(parts) >= 1 and parts[-1] == app_name:
            if len(parts) == 2:
                # Route like "/settings/learning-resources" -> prefix is "settings"
                prefix = parts[0]
                if prefix not in route_path_prefixes:
                    route_path_prefixes.append(prefix)
            # If len(parts) == 1, it's just "/{app_name}", no prefix to add

    # Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)

    # Render the template
    rendered = template.render(
        app_name=app_name,
        route_path_prefixes=route_path_prefixes,
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
    and write to the current directory.

    Args:
        pipeline_template_path: Path to the pipeline template YAML file
        app_name: Name of the application to substitute into the template
        repo_url: Git repository URL to substitute into the template
        app_caddy_file: Contents of the application Caddyfile
        proxy_caddy_file: Contents of the proxy Caddyfile

    Returns:
        Path to the generated pipeline file in the current directory
    """
    # Read the template file
    with open(pipeline_template_path) as f:
        template_content = f.read()

    # Perform substitutions with proper indentation
    # The placeholders in the template are already indented, so we need to:
    # 1. Keep the first line at the placeholder's indentation level
    # 2. Indent subsequent lines to match

    def indent_multiline_replacement(content: str, placeholder: str, template: str) -> str:
        """Indent a multiline string to match the placeholder's indentation in the template."""
        # Find the indentation of the placeholder
        for line in template.split('\n'):
            if placeholder in line:
                # Get the whitespace before the placeholder
                indent = line[:line.index(placeholder)]
                break
        else:
            indent = ""

        lines = content.split("\n")
        # First line stays at placeholder level, rest get the same indentation
        return lines[0] + ("\n" + "\n".join(indent + line if line else "" for line in lines[1:]) if len(lines) > 1 else "")

    # Generate current date in user-readable format
    generation_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    substituted_content = template_content.replace("{{app_name}}", app_name)
    substituted_content = substituted_content.replace("{{repo_url}}", repo_url)
    substituted_content = substituted_content.replace("{{generation_date}}", generation_date)
    substituted_content = substituted_content.replace("{{app_caddy_file}}",
        indent_multiline_replacement(app_caddy_file, "{{app_caddy_file}}", template_content))
    substituted_content = substituted_content.replace("{{proxy_caddy_file}}",
        indent_multiline_replacement(proxy_caddy_file, "{{proxy_caddy_file}}", template_content))

    # Create output file in current directory
    output_filename = f"{app_name}-pull-request.yaml"
    output_path = os.path.join(os.getcwd(), output_filename)

    # Write the substituted content
    with open(output_path, "w") as f:
        f.write(substituted_content)

    return output_path


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
    routes["/index.html"] = {"url": f"http://localhost:{chrome_port}", "is_chrome": True}
    routes["/apps/chrome*"] = {"url": f"http://localhost:{chrome_port}", "is_chrome": True}

    # Add app routes
    routes[f"/apps/{app_name}*"] = {"url": f"http://localhost:{app_port}", "is_chrome": False}

    # Add all appUrl routes (pointing to chrome for the shell)
    for route in app_url_value:
        routes[f"{route}*"] = {"url": f"http://localhost:{chrome_port}", "is_chrome": True}

    # Return compact JSON on a single line to avoid YAML parsing issues
    return json.dumps(routes)


def generate_proxy_routes_caddyfile(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    chrome_port: str = "9912",
) -> str:
    """
    Generate Caddyfile configuration snippets for proxy routes.

    Args:
        app_url_value: List of URL paths from appUrl (e.g., ["/settings/my-app", "/apps/my-app"])
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        chrome_port: Port for Chrome resources (default: "9912")

    Returns:
        Caddyfile configuration snippets as a string
    """
    lines = []

    # Add root route handler
    lines.append("@root path /")
    lines.append("handle @root {")
    lines.append(f"    reverse_proxy 127.0.0.1:{chrome_port}")
    lines.append("}")
    lines.append("")

    # Add /index.html handler
    lines.append("handle /index.html {")
    lines.append(f"    reverse_proxy 127.0.0.1:{chrome_port}")
    lines.append("}")
    lines.append("")

    # Add /apps/chrome* handler
    lines.append("handle /apps/chrome* {")
    lines.append(f"    reverse_proxy 127.0.0.1:{chrome_port}")
    lines.append("}")
    lines.append("")

    # Add /apps/{app_name}* handler (points to app port)
    lines.append(f"handle /apps/{app_name}* {{")
    lines.append(f"    reverse_proxy 127.0.0.1:{app_port}")
    lines.append("}")
    lines.append("")

    # Add all appUrl routes (pointing to chrome for the shell)
    for route in app_url_value:
        lines.append(f"handle {route}* {{")
        lines.append(f"    reverse_proxy 127.0.0.1:{chrome_port}")
        lines.append("}")
        lines.append("")

    # Remove trailing empty line
    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


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
