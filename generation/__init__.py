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


def generate_proxy_routes_caddyfile(
    asset_routes: list[str],
    app_port: str = "8000",
    template_path: str = "template/proxy_caddy.template.j2",
) -> str:
    """
    Generate Caddyfile configuration snippets for proxy routes using a template.

    Args:
        asset_routes: List of asset paths that route to local app
            (e.g., ["/apps/rbac", "/settings/rbac"])
        app_port: Port for the application (default: "8000")
        template_path: Path to the Jinja2 template (default: "template/proxy_caddy.template.j2")

    Returns:
        Caddyfile configuration snippets as a string
    """
    # Set up Jinja2 environment
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)

    # Render the template with asset routes
    rendered = template.render(
        asset_routes=asset_routes,
        app_port=app_port,
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
    # Strip leading/trailing whitespace from content to avoid extra blank lines
    cleaned_content = caddyfile_content.strip()

    # Indent each line of the Caddyfile content with 4 spaces (for YAML)
    indented_content = "\n".join(
        "    " + line if line else "" for line in cleaned_content.split("\n")
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


def generate_proxy_caddy_configmap(
    configmap_name: str,
    asset_routes: list[str],
    app_port: str = "8000",
    namespace: str | None = None,
) -> str:
    """
    Generate proxy routes Caddyfile and wrap it in a ConfigMap YAML.

    Args:
        configmap_name: Name for the ConfigMap
        asset_routes: List of asset paths that route to local app
        app_port: Port for the application (default: "8000")
        namespace: Optional namespace for the ConfigMap

    Returns:
        Path to the generated ConfigMap YAML file
    """
    # Generate the proxy routes Caddyfile
    proxy_caddyfile = generate_proxy_routes_caddyfile(
        asset_routes=asset_routes,
        app_port=app_port,
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
