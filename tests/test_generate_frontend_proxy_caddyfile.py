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
    test_stage_url = "https://stage.foo.redhat.com"

    result = generate_proxy_routes_caddyfile(
        asset_routes=asset_routes, chrome_routes=chrome_routes, stage_env_url=test_stage_url
    )

    # Verify the result is a string
    assert isinstance(result, str)

    # Verify asset routes go to localhost
    assert "reverse_proxy 127.0.0.1:8000" in result
    for route in asset_routes:
        assert f"handle {route}*" in result

    # Verify Chrome routes go to stage environment (direct URL, not env var)
    assert f"reverse_proxy {test_stage_url}" in result
    for route in chrome_routes:
        assert f"handle {route}*" in result

    # CRITICAL: Verify no environment variable syntax is present (we use direct substitution)
    assert "${HCC_ENV_URL}" not in result, (
        "Generated config should not contain ${HCC_ENV_URL}. "
        "Stage URL should be directly substituted from --stage-env-url argument."
    )
    assert "{env.HCC_ENV_URL}" not in result, (
        "Generated config should not contain {env.HCC_ENV_URL}. "
        "Stage URL should be directly substituted from --stage-env-url argument."
    )

    print("Generated Caddyfile:")
    print(result)


def test_generate_proxy_routes_caddyfile_custom_ports():
    """Test with custom app port."""
    asset_routes = ["/apps/my-app", "/settings/my-app"]
    chrome_routes = ["/iam", "/"]
    test_stage_url = "https://stage.example.com"

    result = generate_proxy_routes_caddyfile(
        asset_routes=asset_routes,
        chrome_routes=chrome_routes,
        app_port="3000",
        stage_env_url=test_stage_url,
    )

    # Verify custom port is used for asset routes
    assert "reverse_proxy 127.0.0.1:3000" in result
    assert "handle /apps/my-app*" in result
    assert "handle /settings/my-app*" in result

    # Verify Chrome routes go to stage environment (direct URL, not env var)
    assert f"reverse_proxy {test_stage_url}" in result
    assert "handle /iam*" in result

    # CRITICAL: Verify no environment variable syntax is present (we use direct substitution)
    assert "${HCC_ENV_URL}" not in result, (
        "Generated config should not contain ${HCC_ENV_URL}. "
        "Stage URL should be directly substituted from --stage-env-url argument."
    )
    assert "{env.HCC_ENV_URL}" not in result, (
        "Generated config should not contain {env.HCC_ENV_URL}. "
        "Stage URL should be directly substituted from --stage-env-url argument."
    )
