import argparse
import os


def generate_pipeline_from_template(
    pipeline_template_path: str, app_name: str, repo_url: str
) -> str:
    """
    Read a pipeline template file, substitute app_name and repo_url,
    and write to a temporary location.

    Args:
        pipeline_template_path: Path to the pipeline template YAML file
        app_name: Name of the application to substitute into the template
        repo_url: Git repository URL to substitute into the template

    Returns:
        Path to the generated pipeline file in /tmp
    """
    # Read the template file
    with open(pipeline_template_path) as f:
        template_content = f.read()

    # Perform substitutions
    substituted_content = template_content.replace("{{app_name}}", app_name)
    substituted_content = substituted_content.replace("{{repo_url}}", repo_url)

    # Create output file in /tmp
    output_filename = f"{app_name}-pipeline.yaml"
    output_path = os.path.join("/tmp", output_filename)

    # Write the substituted content
    with open(output_path, "w") as f:
        f.write(substituted_content)

    return output_path


def main(app_name: str, repo_url: str, pipeline_template: str):
    print("Hello from plumber!")
    print(f"App Name: {app_name}")
    print(f"Repo URL: {repo_url}")
    print(f"Pipeline Template: {pipeline_template}")

    # Generate pipeline from template
    output_path = generate_pipeline_from_template(pipeline_template, app_name, repo_url)
    print(f"\nGenerated pipeline file: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
    parser.add_argument("app_name", type=str, help="Name of the application")
    parser.add_argument("repo_url", type=str, help="Git URL of the repository")
    parser.add_argument("pipeline_template", type=str, help="Path to the pipeline template file")

    args = parser.parse_args()
    main(args.app_name, args.repo_url, args.pipeline_template)
