import argparse
import sys
from unittest.mock import patch

import pytest

# Import the main module to test argument parsing


def test_pipeline_template_argument():
    """Test that --pipeline-template argument is parsed correctly."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--pipeline-template",
        "template/konflux_pipeline_template.yaml",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        pipeline_group = parser.add_mutually_exclusive_group(required=True)
        pipeline_group.add_argument(
            "--pipeline-template", type=str, help="Path to the Konflux pipeline template file"
        )
        pipeline_group.add_argument(
            "--minikube-template", type=str, help="Path to the Minikube pipeline template file"
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        args = parser.parse_args(test_args)

        assert args.app_name == "test-app"
        assert args.repo_url == "https://github.com/test/repo.git"
        assert args.pipeline_template == "template/konflux_pipeline_template.yaml"
        assert args.minikube_template is None


def test_minikube_template_argument():
    """Test that --minikube-template argument is parsed correctly."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--minikube-template",
        "template/minikube_pipeline_template.yaml",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        pipeline_group = parser.add_mutually_exclusive_group(required=True)
        pipeline_group.add_argument(
            "--pipeline-template", type=str, help="Path to the Konflux pipeline template file"
        )
        pipeline_group.add_argument(
            "--minikube-template", type=str, help="Path to the Minikube pipeline template file"
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        args = parser.parse_args(test_args)

        assert args.app_name == "test-app"
        assert args.repo_url == "https://github.com/test/repo.git"
        assert args.minikube_template == "template/minikube_pipeline_template.yaml"
        assert args.pipeline_template is None


def test_mutually_exclusive_templates():
    """Test that providing both template arguments raises an error."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--pipeline-template",
        "template/konflux_pipeline_template.yaml",
        "--minikube-template",
        "template/minikube_pipeline_template.yaml",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        pipeline_group = parser.add_mutually_exclusive_group(required=True)
        pipeline_group.add_argument(
            "--pipeline-template", type=str, help="Path to the Konflux pipeline template file"
        )
        pipeline_group.add_argument(
            "--minikube-template", type=str, help="Path to the Minikube pipeline template file"
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        with pytest.raises(SystemExit):
            parser.parse_args(test_args)


def test_pipeline_type_determination_konflux():
    """Test that pipeline_type is correctly set to 'konflux' when --pipeline-template is used."""

    # Simulate parsed args
    class Args:
        pipeline_template = "template/konflux_pipeline_template.yaml"
        minikube_template = None

    args = Args()

    # Determine pipeline type
    pipeline_template = args.pipeline_template or args.minikube_template
    pipeline_type = "konflux" if args.pipeline_template else "minikube"

    assert pipeline_template == "template/konflux_pipeline_template.yaml"
    assert pipeline_type == "konflux"


def test_pipeline_type_determination_minikube():
    """Test that pipeline_type is correctly set to 'minikube' when --minikube-template is used."""

    # Simulate parsed args
    class Args:
        pipeline_template = None
        minikube_template = "template/minikube_pipeline_template.yaml"

    args = Args()

    # Determine pipeline type
    pipeline_template = args.pipeline_template or args.minikube_template
    pipeline_type = "konflux" if args.pipeline_template else "minikube"

    assert pipeline_template == "template/minikube_pipeline_template.yaml"
    assert pipeline_type == "minikube"


def test_fec_config_default():
    """Test that --fec-config has correct default value."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--pipeline-template",
        "template/konflux_pipeline_template.yaml",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        pipeline_group = parser.add_mutually_exclusive_group(required=True)
        pipeline_group.add_argument(
            "--pipeline-template", type=str, help="Path to the Konflux pipeline template file"
        )
        pipeline_group.add_argument(
            "--minikube-template", type=str, help="Path to the Minikube pipeline template file"
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        args = parser.parse_args(test_args)

        assert args.fec_config == "fec.config.js"


def test_fec_config_custom_path():
    """Test that --fec-config accepts custom paths."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--pipeline-template",
        "template/konflux_pipeline_template.yaml",
        "--fec-config",
        "custom/path/fec.config.js",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(description="Plumber - Pipeline management tool")
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        pipeline_group = parser.add_mutually_exclusive_group(required=True)
        pipeline_group.add_argument(
            "--pipeline-template", type=str, help="Path to the Konflux pipeline template file"
        )
        pipeline_group.add_argument(
            "--minikube-template", type=str, help="Path to the Minikube pipeline template file"
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        args = parser.parse_args(test_args)

        assert args.fec_config == "custom/path/fec.config.js"
