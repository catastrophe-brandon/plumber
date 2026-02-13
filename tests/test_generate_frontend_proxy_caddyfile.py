from generation import generate_proxy_routes_caddyfile


def test_generate_proxy_routes_caddyfile():
    """Test generating proxy routes Caddyfile from asset and Chrome routes."""
    asset_routes = [
        "/apps/learning-resources",
        "/settings/learning-resources",
    ]
    chrome_routes = [
        "/openshift/learning-resources",
        "/ansible/learning-resources",
        "/insights/learning-resources",
        "/edge/learning-resources",
        "/iam/learning-resources",
        "/",
    ]

    result = generate_proxy_routes_caddyfile(
        asset_routes=asset_routes, chrome_routes=chrome_routes
    )

    # Verify the result is a string
    assert isinstance(result, str)

    # Verify asset routes go to localhost
    assert "reverse_proxy 127.0.0.1:8000" in result
    for route in asset_routes:
        assert f"handle {route}*" in result

    # Verify Chrome routes go to stage environment
    assert "reverse_proxy {env.HCC_ENV_URL}" in result
    for route in chrome_routes:
        assert f"handle {route}*" in result

    print("Generated Caddyfile:")
    print(result)


def test_generate_proxy_routes_caddyfile_custom_ports():
    """Test with custom app port."""
    asset_routes = ["/apps/my-app", "/settings/my-app"]
    chrome_routes = ["/iam", "/"]

    result = generate_proxy_routes_caddyfile(
        asset_routes=asset_routes,
        chrome_routes=chrome_routes,
        app_port="3000",
    )

    # Verify custom port is used for asset routes
    assert "reverse_proxy 127.0.0.1:3000" in result
    assert "handle /apps/my-app*" in result
    assert "handle /settings/my-app*" in result

    # Verify Chrome routes go to stage environment
    assert "reverse_proxy {env.HCC_ENV_URL}" in result
    assert "handle /iam*" in result
