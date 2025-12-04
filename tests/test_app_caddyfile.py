from generation import generate_app_caddyfile


def test_generate_app_caddyfile_basic():
    """Test basic app Caddyfile generation."""
    app_urls = ["/my-app", "/settings/my-app"]
    app_name = "my-app"
    app_port = "8000"

    result = generate_app_caddyfile(app_urls, app_name, app_port)

    # Verify server block
    assert ":8000 {" in result
    assert result.endswith("}")

    # Verify route handlers are present
    assert "@my_app_match" in result
    assert "@my_app_subpath" in result
    assert "@settings_my_app_match" in result
    assert "@settings_my_app_subpath" in result

    # Verify path matchers
    assert "path /my-app /my-app/" in result
    assert "path /my-app/*" in result
    assert "path /settings/my-app /settings/my-app/" in result
    assert "path /settings/my-app/*" in result

    # Verify URI stripping
    assert "uri strip_prefix /my-app" in result
    assert "uri strip_prefix /settings/my-app" in result

    # Verify rewrite for exact matches
    assert "rewrite / /index.html" in result

    # Verify file server configuration
    assert "file_server *" in result
    assert "root /srv/dist" in result


def test_generate_app_caddyfile_single_route():
    """Test app Caddyfile generation with a single route."""
    app_urls = ["/single-app"]
    app_name = "single-app"

    result = generate_app_caddyfile(app_urls, app_name)

    assert ":8000 {" in result
    assert "@single_app_match" in result
    assert "@single_app_subpath" in result
    assert "path /single-app /single-app/" in result
    assert "path /single-app/*" in result


def test_generate_app_caddyfile_multiple_routes():
    """Test app Caddyfile generation with many routes."""
    app_urls = [
        "/settings/learning-resources",
        "/openshift/learning-resources",
        "/ansible/learning-resources",
        "/insights/learning-resources",
        "/edge/learning-resources",
        "/iam/learning-resources",
        "/learning-resources",
        "/learning-resources/creator",
    ]
    app_name = "learning-resources"

    result = generate_app_caddyfile(app_urls, app_name)

    # Verify all routes have handlers
    for url in app_urls:
        matcher_name = url.lstrip("/").replace("/", "_").replace("-", "_")
        assert f"@{matcher_name}_match" in result
        assert f"@{matcher_name}_subpath" in result
        assert f"path {url} {url}/" in result
        assert f"path {url}/*" in result
        assert f"uri strip_prefix {url}" in result

    # Verify fallback handler
    assert "handle / {" in result


def test_generate_app_caddyfile_custom_port():
    """Test app Caddyfile generation with custom port."""
    app_urls = ["/test-app"]
    app_name = "test-app"
    app_port = "9000"

    result = generate_app_caddyfile(app_urls, app_name, app_port)

    assert ":9000 {" in result
    assert ":8000" not in result


def test_generate_app_caddyfile_special_characters():
    """Test app Caddyfile handles routes with hyphens and slashes."""
    app_urls = ["/my-special-app", "/settings/my-special-app/section"]
    app_name = "my-special-app"

    result = generate_app_caddyfile(app_urls, app_name)

    # Matcher names should have underscores instead of hyphens
    assert "@my_special_app_match" in result
    assert "@settings_my_special_app_section_match" in result

    # Original paths should be preserved
    assert "path /my-special-app /my-special-app/" in result
    assert "path /settings/my-special-app/section /settings/my-special-app/section/" in result


def test_generate_app_caddyfile_structure():
    """Test the structure of the generated Caddyfile."""
    app_urls = ["/app"]
    app_name = "app"

    result = generate_app_caddyfile(app_urls, app_name)

    lines = result.split("\n")

    # Should start with server block
    assert lines[0] == ":8000 {"

    # Should end with closing brace
    assert lines[-1] == "}"

    # Should have proper indentation (4 spaces for top-level handlers)
    handler_lines = [l for l in lines if l.strip().startswith("@")]
    for line in handler_lines:
        assert line.startswith("    ")  # 4 spaces
