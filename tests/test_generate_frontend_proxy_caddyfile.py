from generation import generate_frontend_proxy_caddyfile


def test_generate_frontend_proxy_caddyfile():
    """Test generating Caddyfile from app_url_value list."""
    app_url_value = [
        "/settings/learning-resources",
        "/openshift/learning-resources",
        "/ansible/learning-resources",
        "/insights/learning-resources",
        "/edge/learning-resources",
        "/iam/learning-resources",
        "/learning-resources",
    ]

    result = generate_frontend_proxy_caddyfile(
        app_url_value=app_url_value, app_name="learning-resources"
    )

    # Verify the result is a string
    assert isinstance(result, str)

    # Verify basic structure
    assert "@root path /" in result
    assert "handle /index.html" in result
    assert "handle /apps/chrome*" in result

    # Verify app-specific route
    assert "handle /apps/learning-resources*" in result
    assert "reverse_proxy 127.0.0.1:8000" in result

    # Verify all routes from app_url_value are present
    for route in app_url_value:
        assert f"handle {route}*" in result

    # Verify chrome port is used
    assert "reverse_proxy 127.0.0.1:9912" in result

    # Verify catch-all route at the end
    assert "handle /learning-resources*" in result

    print("Generated Caddyfile:")
    print(result)


def test_generate_frontend_proxy_caddyfile_custom_ports():
    """Test with custom ports."""
    app_url_value = ["/my-app"]

    result = generate_frontend_proxy_caddyfile(
        app_url_value=app_url_value,
        app_name="my-app",
        app_port="3000",
        chrome_port="4000",
    )

    # Verify custom ports are used
    assert "reverse_proxy 127.0.0.1:3000" in result
    assert "reverse_proxy 127.0.0.1:4000" in result
    assert "handle /my-app*" in result
