import argparse
import sys
from unittest.mock import patch

import pytest


def test_configmap_name_arguments():
    """Test that ConfigMap name arguments are parsed correctly."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--app-configmap-name",
        "test-app-caddy",
        "--proxy-configmap-name",
        "test-proxy-caddy",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(
            description="Plumber - Generate Caddy ConfigMaps for application testing"
        )
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        parser.add_argument(
            "--app-configmap-name",
            type=str,
            required=True,
            help="Name for the app Caddy ConfigMap",
        )
        parser.add_argument(
            "--proxy-configmap-name",
            type=str,
            required=True,
            help="Name for the proxy routes Caddy ConfigMap",
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
        assert args.app_configmap_name == "test-app-caddy"
        assert args.proxy_configmap_name == "test-proxy-caddy"


def test_missing_app_configmap_name():
    """Test that missing --app-configmap-name raises an error."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--proxy-configmap-name",
        "test-proxy-caddy",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(
            description="Plumber - Generate Caddy ConfigMaps for application testing"
        )
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        parser.add_argument(
            "--app-configmap-name",
            type=str,
            required=True,
            help="Name for the app Caddy ConfigMap",
        )
        parser.add_argument(
            "--proxy-configmap-name",
            type=str,
            required=True,
            help="Name for the proxy routes Caddy ConfigMap",
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        with pytest.raises(SystemExit):
            parser.parse_args(test_args)


def test_missing_proxy_configmap_name():
    """Test that missing --proxy-configmap-name raises an error."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--app-configmap-name",
        "test-app-caddy",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(
            description="Plumber - Generate Caddy ConfigMaps for application testing"
        )
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        parser.add_argument(
            "--app-configmap-name",
            type=str,
            required=True,
            help="Name for the app Caddy ConfigMap",
        )
        parser.add_argument(
            "--proxy-configmap-name",
            type=str,
            required=True,
            help="Name for the proxy routes Caddy ConfigMap",
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        with pytest.raises(SystemExit):
            parser.parse_args(test_args)


def test_fec_config_default():
    """Test that --fec-config has correct default value."""
    test_args = [
        "test-app",
        "https://github.com/test/repo.git",
        "--app-configmap-name",
        "test-app-caddy",
        "--proxy-configmap-name",
        "test-proxy-caddy",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(
            description="Plumber - Generate Caddy ConfigMaps for application testing"
        )
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        parser.add_argument(
            "--app-configmap-name",
            type=str,
            required=True,
            help="Name for the app Caddy ConfigMap",
        )
        parser.add_argument(
            "--proxy-configmap-name",
            type=str,
            required=True,
            help="Name for the proxy routes Caddy ConfigMap",
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
        "--app-configmap-name",
        "test-app-caddy",
        "--proxy-configmap-name",
        "test-proxy-caddy",
        "--fec-config",
        "custom/path/fec.config.js",
    ]

    with patch.object(sys, "argv", ["plumber"] + test_args):
        parser = argparse.ArgumentParser(
            description="Plumber - Generate Caddy ConfigMaps for application testing"
        )
        parser.add_argument("app_name", type=str, help="Name of the application")
        parser.add_argument("repo_url", type=str, help="Git URL of the repository")

        parser.add_argument(
            "--app-configmap-name",
            type=str,
            required=True,
            help="Name for the app Caddy ConfigMap",
        )
        parser.add_argument(
            "--proxy-configmap-name",
            type=str,
            required=True,
            help="Name for the proxy routes Caddy ConfigMap",
        )

        parser.add_argument(
            "--fec-config",
            type=str,
            default="fec.config.js",
            help="Path to fec.config.js file (default: fec.config.js)",
        )

        args = parser.parse_args(test_args)

        assert args.fec_config == "custom/path/fec.config.js"
