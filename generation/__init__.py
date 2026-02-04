import os
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader


def validate_yaml_file(file_path: str) -> None:
    """
    Validate a YAML file using yamllint.

    Args:
        file_path: Path to the YAML file to validate

    Raises:
        SystemExit: If yamllint validation fails
    """
    try:
        result = subprocess.run(
            ["yamllint", "-d", "relaxed", file_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"❌ YAML validation failed for {file_path}:", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)

        print(f"✅ YAML validation passed: {file_path}")

    except FileNotFoundError:
        print("⚠️  Warning: yamllint not found. Skipping YAML validation.", file=sys.stderr)
        print("   Install with: pip install yamllint", file=sys.stderr)


def generate_app_caddyfile(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    is_federated_module: bool = False,
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
        is_federated_module: Whether this is a federated module (default: False)
        template_path: Path to the Jinja2 template (default: "template/app_caddy.template.j2")

    Returns:
        Rendered Caddyfile configuration as a string
    """
    # Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)

    # Render the template with the exact app URLs from fec.config.js
    rendered = template.render(
        app_name=app_name,
        app_urls=app_url_value,
        is_federated_module=is_federated_module,
    )

    return rendered


def generate_proxy_routes_caddyfile(
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    chrome_port: str = "9912",
    template_path: str = "template/proxy_caddy.template.j2",
) -> str:
    """
    Generate Caddyfile configuration snippets for proxy routes using a template.

    Args:
        app_url_value: List of URL paths from appUrl (e.g., ["/settings/my-app", "/apps/my-app"])
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        chrome_port: Port for Chrome resources (default: "9912")
        template_path: Path to the Jinja2 template (default: "template/proxy_caddy.template.j2")

    Returns:
        Caddyfile configuration snippets as a string
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


def generate_configmap(
    name: str, caddyfile_content: str, namespace: str | None = None, data_key: str = "Caddyfile"
) -> str:
    """
    Create a Kubernetes ConfigMap YAML with the given name and Caddyfile content.

    Args:
        name: Name of the ConfigMap
        caddyfile_content: Caddyfile configuration content
        namespace: Optional namespace for the ConfigMap
        data_key: Key name for the data section (default: "Caddyfile")

    Returns:
        ConfigMap YAML as a string
    """
    # Indent each line of the Caddyfile content with 4 spaces (for YAML)
    indented_content = "\n".join(
        "    " + line if line else "" for line in caddyfile_content.split("\n")
    )

    # Build namespace line if provided
    namespace_line = f"\n  namespace: {namespace}" if namespace else ""

    configmap = f"""---
apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}{namespace_line}
data:
  {data_key}: |
{indented_content}
"""
    return configmap


def generate_app_caddy_configmap(
    configmap_name: str,
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    namespace: str | None = None,
    is_federated_module: bool = False,
) -> str:
    """
    Generate app Caddyfile and wrap it in a ConfigMap YAML.

    Args:
        configmap_name: Name for the ConfigMap
        app_url_value: List of URL paths from appUrl
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        namespace: Optional namespace for the ConfigMap
        is_federated_module: Whether this is a federated module (default: False)

    Returns:
        Path to the generated ConfigMap YAML file
    """
    # Generate the app Caddyfile
    app_caddyfile = generate_app_caddyfile(
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
        is_federated_module=is_federated_module,
    )

    # Wrap in ConfigMap
    configmap_yaml = generate_configmap(configmap_name, app_caddyfile, namespace=namespace)

    # Write to file
    output_filename = f"{configmap_name}.yaml"
    output_path = os.path.join(os.getcwd(), output_filename)

    with open(output_path, "w") as f:
        f.write(configmap_yaml)

    # Validate the generated YAML
    validate_yaml_file(output_path)

    return output_path


def generate_proxy_caddy_configmap(
    configmap_name: str,
    app_url_value: list[str],
    app_name: str,
    app_port: str = "8000",
    chrome_port: str = "9912",
    namespace: str | None = None,
) -> str:
    """
    Generate proxy routes Caddyfile and wrap it in a ConfigMap YAML.

    Args:
        configmap_name: Name for the ConfigMap
        app_url_value: List of URL paths from appUrl
        app_name: Name of the application
        app_port: Port for the application (default: "8000")
        chrome_port: Port for Chrome resources (default: "9912")
        namespace: Optional namespace for the ConfigMap

    Returns:
        Path to the generated ConfigMap YAML file
    """
    # Generate the proxy routes Caddyfile
    proxy_caddyfile = generate_proxy_routes_caddyfile(
        app_url_value=app_url_value,
        app_name=app_name,
        app_port=app_port,
        chrome_port=chrome_port,
    )

    # Wrap in ConfigMap with "routes" as the data key
    configmap_yaml = generate_configmap(
        configmap_name, proxy_caddyfile, namespace=namespace, data_key="routes"
    )

    # Write to file
    output_filename = f"{configmap_name}.yaml"
    output_path = os.path.join(os.getcwd(), output_filename)

    with open(output_path, "w") as f:
        f.write(configmap_yaml)

    # Validate the generated YAML
    validate_yaml_file(output_path)

    return output_path
