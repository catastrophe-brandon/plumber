import os

import yaml

from generation import (
    generate_app_caddyfile,
    generate_frontend_proxy_caddyfile,
    generate_pipeline_from_template,
)


def test_minikube_pipeline_generation_and_validation():
    """Test that pipeline generation with minikube_pipeline_template.yaml produces valid YAML."""
    test_app_name = "learning-resources"
    test_repo_url = "https://github.com/RedHatInsights/learning-resources.git"
    test_app_urls = ["/settings/learning-resources", "/apps/learning-resources"]

    # Generate app Caddyfile
    test_app_caddy = generate_app_caddyfile(
        app_url_value=test_app_urls,
        app_name=test_app_name,
        app_port="8000",
    )

    # Generate proxy Caddyfile
    test_proxy_caddyfile = generate_frontend_proxy_caddyfile(
        app_url_value=test_app_urls,
        app_name=test_app_name,
        app_port="8000",
        chrome_port="9912",
    )

    # Use the minikube template
    template_path = "template/minikube_pipeline_template.yaml"

    # Generate the pipeline
    output_path = generate_pipeline_from_template(
        template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddyfile
    )

    try:
        # Verify the output file exists
        assert os.path.exists(output_path), f"Output file not created at {output_path}"

        # Read and parse the YAML
        with open(output_path) as f:
            pipeline_content = f.read()

        # This will raise an exception if YAML is invalid
        pipeline = yaml.safe_load(pipeline_content)

        # Verify basic Tekton PipelineRun structure
        assert pipeline is not None, "Pipeline parsed to None"
        assert pipeline.get("apiVersion") == "tekton.dev/v1", "Invalid apiVersion"
        assert pipeline.get("kind") == "PipelineRun", "Invalid kind"

        # Verify metadata
        metadata = pipeline.get("metadata", {})
        assert metadata.get("name") == "e2e-pipeline-run", "Invalid pipeline name"

        # Verify spec and params exist
        spec = pipeline.get("spec", {})
        params = spec.get("params", [])
        assert len(params) > 0, "No parameters found in pipeline"

        # Verify repo-url parameter substitution
        repo_url_param = next((p for p in params if p["name"] == "repo-url"), None)
        assert repo_url_param is not None, "repo-url param not found"
        assert repo_url_param["value"] == test_repo_url, "repo-url value incorrect"

        # Verify proxy routes Caddyfile was properly inserted
        proxy_routes = next((p for p in params if p["name"] == "proxy-routes"), None)
        assert proxy_routes is not None, "proxy-routes param not found"
        assert "handle /settings/learning-resources*" in proxy_routes["value"], (
            "Proxy route not found"
        )
        assert "reverse_proxy 127.0.0.1:9912" in proxy_routes["value"], "Chrome proxy not found"

        # Verify app Caddyfile was properly inserted
        app_caddy_param = next((p for p in params if p["name"] == "app-caddy-config"), None)
        assert app_caddy_param is not None, "app-caddy-config param not found"
        assert "handle @settings_learning-resources_match" in app_caddy_param["value"], (
            "App Caddyfile content not found"
        )

        # Verify workspaces configuration
        workspaces = spec.get("workspaces", [])
        assert len(workspaces) > 0, "No workspaces found"
        shared_workspace = next(
            (w for w in workspaces if w["name"] == "shared-code-workspace"), None
        )
        assert shared_workspace is not None, "shared-code-workspace not found"

        # Verify pipelineRef
        pipeline_ref = spec.get("pipelineRef", {})
        assert pipeline_ref.get("name") == "e2e-pipeline", "Invalid pipelineRef name"

        # Verify taskRunSpecs for host aliases
        task_run_specs = spec.get("taskRunSpecs", [])
        assert len(task_run_specs) > 0, "No taskRunSpecs found"
        e2e_task = next(
            (t for t in task_run_specs if t["pipelineTaskName"] == "e2e-test-run"), None
        )
        assert e2e_task is not None, "e2e-test-run taskRunSpec not found"

        # Verify host aliases for stage.foo.redhat.com
        host_aliases = e2e_task.get("podTemplate", {}).get("hostAliases", [])
        assert len(host_aliases) > 0, "No hostAliases found"
        localhost_alias = next((ha for ha in host_aliases if "127.0.0.1" in ha.get("ip", "")), None)
        assert localhost_alias is not None, "localhost hostAlias not found"
        assert "stage.foo.redhat.com" in localhost_alias.get("hostnames", []), (
            "stage.foo.redhat.com not in hostnames"
        )

    finally:
        # Clean up
        if os.path.exists(output_path):
            os.remove(output_path)


def test_minikube_pipeline_with_different_app():
    """Test minikube pipeline generation with a different app configuration."""
    test_app_name = "test-app"
    test_repo_url = "https://github.com/test/test-app.git"
    test_app_urls = ["/apps/test-app"]

    # Generate app Caddyfile
    test_app_caddy = generate_app_caddyfile(
        app_url_value=test_app_urls,
        app_name=test_app_name,
        app_port="3000",
    )

    # Generate proxy Caddyfile
    test_proxy_caddyfile = generate_frontend_proxy_caddyfile(
        app_url_value=test_app_urls,
        app_name=test_app_name,
        app_port="3000",
        chrome_port="9912",
    )

    template_path = "template/minikube_pipeline_template.yaml"
    output_path = generate_pipeline_from_template(
        template_path, test_app_name, test_repo_url, test_app_caddy, test_proxy_caddyfile
    )

    try:
        # Parse the YAML - this will fail if generation breaks the YAML structure
        with open(output_path) as f:
            pipeline = yaml.safe_load(f)

        assert pipeline is not None, "Failed to parse generated pipeline YAML"
        assert pipeline["kind"] == "PipelineRun", "Invalid pipeline kind"

        # Verify repo URL was substituted
        params = pipeline["spec"]["params"]
        repo_url_param = next((p for p in params if p["name"] == "repo-url"), None)
        assert repo_url_param["value"] == test_repo_url, "repo-url not substituted correctly"

        # Verify Caddyfiles are present
        proxy_routes = next((p for p in params if p["name"] == "proxy-routes"), None)
        assert proxy_routes is not None, "proxy-routes param not found"

        app_caddy = next((p for p in params if p["name"] == "app-caddy-config"), None)
        assert app_caddy is not None, "app-caddy-config param not found"

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
