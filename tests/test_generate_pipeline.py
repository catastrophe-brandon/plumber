import os
import tempfile

from generation import generate_pipeline_from_template


def test_generate_pipeline_from_template():
    """Test that generate_pipeline_from_template correctly substitutes values."""
    # Create a simplified test template
    test_template_content = """apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: {{app_name}}-pipeline
  annotations:
    repo: {{repo_url}}
spec:
  params:
  - name: test-app-name
    value: {{app_name}}
  - name: git-url
    value: {{repo_url}}
  - name: app-caddy
    value: |
      {{app_caddy_file}}
  - name: proxy-caddy
    value: |
      {{proxy_caddy_file}}
"""

    # Create a temporary template file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_template:
        temp_template.write(test_template_content)
        template_path = temp_template.name

    try:
        # Test values
        test_app_name = "test-application"
        test_repo_url = "https://github.com/test/repo.git"
        test_app_caddy = "# App Caddyfile"
        test_proxy_caddy = "# Proxy Caddyfile"

        # Call the function
        output_path = generate_pipeline_from_template(
            template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddy
        )

        # Verify the output file was created
        assert os.path.exists(output_path), f"Output file not created at {output_path}"

        # Read the output file
        with open(output_path) as f:
            output_content = f.read()

        # Verify substitutions were made correctly
        assert "{{app_name}}" not in output_content, "app_name placeholder was not substituted"
        assert "{{repo_url}}" not in output_content, "repo_url placeholder was not substituted"
        assert test_app_name in output_content, f"app_name '{test_app_name}' not found in output"
        assert test_repo_url in output_content, f"repo_url '{test_repo_url}' not found in output"

        # Verify specific expected lines
        assert f"name: {test_app_name}-pipeline" in output_content
        assert f"repo: {test_repo_url}" in output_content
        assert f"value: {test_app_name}" in output_content
        assert f"value: {test_repo_url}" in output_content

        # Verify output path is in /tmp
        assert output_path.startswith("/tmp/"), f"Output path {output_path} is not in /tmp"
        assert output_path.endswith(f"{test_app_name}-pipeline.yaml")

        # Clean up output file
        os.remove(output_path)

    finally:
        # Clean up template file
        if os.path.exists(template_path):
            os.remove(template_path)


def test_generate_pipeline_from_template_with_special_characters():
    """Test that the function handles app names with hyphens and underscores."""
    test_template_content = """name: {{app_name}}
repo: {{repo_url}}
app_caddy: {{app_caddy_file}}
proxy_caddy: {{proxy_caddy_file}}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_template:
        temp_template.write(test_template_content)
        template_path = temp_template.name

    try:
        test_app_name = "my-test_app-123"
        test_repo_url = "https://github.com/org/my-repo_name.git"
        test_app_caddy = "# App config"
        test_proxy_caddy = "# Proxy config"

        output_path = generate_pipeline_from_template(
            template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddy
        )

        with open(output_path) as f:
            output_content = f.read()

        assert test_app_name in output_content
        assert test_repo_url in output_content
        assert test_app_caddy in output_content
        assert test_proxy_caddy in output_content

        # Clean up
        os.remove(output_path)

    finally:
        if os.path.exists(template_path):
            os.remove(template_path)
