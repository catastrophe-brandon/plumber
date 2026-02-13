import os

from jinja2 import Environment, FileSystemLoader


def test_proxy_caddy_template_rendering():
    """Test that the proxy_caddy.template.j2 renders correctly with substitutions."""
    # Set up Jinja2 environment
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("proxy_caddy.template.j2")

    # Test values - separate asset and Chrome routes
    test_vars = {
        "app_port": "8000",
        "asset_routes": [
            "/apps/test-application",
            "/settings/test-application",
        ],
        "chrome_routes": [
            "/iam/test-application",
            "/openshift/test-application",
            "/ansible/test-application",
            "/insights/test-application",
            "/edge/test-application",
            "/apps/chrome",
            "/",
        ],
    }

    # Render the template
    rendered = template.render(test_vars)

    # Verify no template variables remain
    assert "{{" not in rendered, "Template variables were not fully substituted"
    assert "{%" not in rendered, "Jinja2 control structures remain in output"

    # Verify port was substituted
    assert "8000" in rendered, "app_port not found in rendered output"

    # Verify asset routes proxy to localhost
    assert "reverse_proxy 127.0.0.1:8000" in rendered, "Localhost proxy not found"
    for route_path in test_vars["asset_routes"]:
        expected_route = f"handle {route_path}*"
        assert expected_route in rendered, f"Asset route '{route_path}' not found in output"

    # Verify Chrome routes proxy to stage environment
    assert "reverse_proxy {env.HCC_ENV_URL}" in rendered, "Stage env proxy not found"
    for route_path in test_vars["chrome_routes"]:
        expected_route = f"handle {route_path}*"
        assert expected_route in rendered, f"Chrome route '{route_path}' not found in output"

    print("Rendered Caddyfile:")
    print(rendered)


def test_proxy_caddy_template_with_different_app():
    """Test template with a different application and custom port."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("proxy_caddy.template.j2")

    # Different test values - separate asset and Chrome routes
    test_vars = {
        "app_port": "3000",
        "asset_routes": ["/apps/my-custom-app", "/settings/my-custom-app"],
        "chrome_routes": ["/iam", "/apps/chrome"],
    }

    rendered = template.render(test_vars)

    # Verify the custom port
    assert "3000" in rendered

    # Verify asset routes are present
    assert "handle /apps/my-custom-app*" in rendered
    assert "handle /settings/my-custom-app*" in rendered
    assert "reverse_proxy 127.0.0.1:3000" in rendered

    # Verify Chrome routes are present
    assert "handle /iam*" in rendered
    assert "handle /apps/chrome*" in rendered
    assert "reverse_proxy {env.HCC_ENV_URL}" in rendered

    # Verify routes not in the list are not present
    assert "handle /ansible/my-custom-app*" not in rendered
    assert "handle /edge/my-custom-app*" not in rendered


def test_proxy_caddy_template_route_count():
    """Test that the correct number of routes are generated."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "template")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("proxy_caddy.template.j2")

    test_vars = {
        "app_port": "8000",
        "asset_routes": ["/apps/test-app", "/settings/test-app"],
        "chrome_routes": ["/iam", "/apps/chrome", "/"],
    }

    rendered = template.render(test_vars)

    # Count the handle directives
    handle_count = rendered.count("handle ")

    # Expected handles:
    # Asset routes: 2 (apps, settings)
    # Chrome routes: 3 (iam, chrome, /)
    # Total: 5 handles
    expected_count = 5
    assert handle_count == expected_count, (
        f"Expected {expected_count} handle directives, found {handle_count}"
    )
