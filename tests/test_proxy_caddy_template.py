import os

from jinja2 import Environment, FileSystemLoader


def test_proxy_caddy_template_rendering():
    """Test that the proxy_caddy.template.j2 renders correctly with substitutions."""
    # Set up Jinja2 environment
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("proxy_caddy.template.j2")

    # Test values - route_prefixes now contains full paths
    test_vars = {
        "app_name": "test-application",
        "app_port": "8000",
        "route_prefixes": [
            "/settings/test-application",
            "/openshift/test-application",
            "/ansible/test-application",
            "/insights/test-application",
            "/edge/test-application",
            "/iam/test-application",
        ],
    }

    # Render the template
    rendered = template.render(test_vars)

    # Verify no template variables remain
    assert "{{" not in rendered, "Template variables were not fully substituted"
    assert "{%" not in rendered, "Jinja2 control structures remain in output"

    # Verify the app_name was substituted
    assert "test-application" in rendered, "app_name not found in rendered output"

    # Verify port was substituted
    assert "8000" in rendered, "app_port not found in rendered output"

    # Verify specific routes are present
    assert "handle /apps/test-application*" in rendered, "App-specific route not found"
    assert "reverse_proxy 127.0.0.1:8000" in rendered, "App port proxy not found"

    # Verify all routes from route_prefixes were rendered
    for route_path in test_vars["route_prefixes"]:
        expected_route = f"handle {route_path}*"
        assert expected_route in rendered, f"Route path '{route_path}' not found in output"

    print("Rendered Caddyfile:")
    print(rendered)


def test_proxy_caddy_template_with_different_app():
    """Test template with a different application name and ports."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("proxy_caddy.template.j2")

    # Different test values - route_prefixes now contains full paths
    test_vars = {
        "app_name": "my-custom-app",
        "app_port": "3000",
        "route_prefixes": ["/settings/my-custom-app", "/insights/my-custom-app"],
    }

    rendered = template.render(test_vars)

    # Verify the new app_name
    assert "my-custom-app" in rendered
    assert "test-application" not in rendered

    # Verify the new port
    assert "3000" in rendered

    # Verify only the specified route paths are present
    assert "handle /settings/my-custom-app*" in rendered
    assert "handle /insights/my-custom-app*" in rendered

    # Verify route paths not in the list are not present
    assert "handle /ansible/my-custom-app*" not in rendered
    assert "handle /edge/my-custom-app*" not in rendered


def test_proxy_caddy_template_route_count():
    """Test that the correct number of routes are generated."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("proxy_caddy.template.j2")

    test_vars = {
        "app_name": "test-app",
        "app_port": "8000",
        "route_prefixes": ["/settings", "/openshift", "/ansible"],
    }

    rendered = template.render(test_vars)

    # Count the handle directives
    handle_count = rendered.count("handle ")

    # Expected handles:
    # 1. /apps/{app_name}*
    # 2-4. route_paths (3 paths)
    # Total: 4 handles
    expected_count = 4
    assert handle_count == expected_count, (
        f"Expected {expected_count} handle directives, found {handle_count}"
    )
