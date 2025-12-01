import json
import os
import tempfile

import pytest

from main import get_app_url_from_fec_config


def test_get_app_url_from_fec_config():
    """Test extracting appUrl from a valid fec.config.js file."""
    # Create a temporary fec.config.js file
    fec_config_data = {"appUrl": "/learning-resources", "someOtherKey": "value"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as temp_file:
        json.dump(fec_config_data, temp_file)
        temp_path = temp_file.name

    try:
        # Test the function
        app_url = get_app_url_from_fec_config(temp_path)

        # Verify the result
        assert app_url == "/learning-resources"

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_app_url_missing_key():
    """Test that None is returned when appUrl is not present."""
    # Create a fec.config.js without appUrl
    fec_config_data = {"someOtherKey": "value"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as temp_file:
        json.dump(fec_config_data, temp_file)
        temp_path = temp_file.name

    try:
        app_url = get_app_url_from_fec_config(temp_path)
        assert app_url is None

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_app_url_file_not_found():
    """Test that FileNotFoundError is raised when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        get_app_url_from_fec_config("nonexistent_file.js")


def test_get_app_url_default_path():
    """Test using the default path (current directory)."""
    # Create fec.config.js in current directory
    fec_config_data = {"appUrl": "/my-app"}

    with open("fec.config.js", "w") as f:
        json.dump(fec_config_data, f)

    try:
        app_url = get_app_url_from_fec_config()
        assert app_url == "/my-app"

    finally:
        if os.path.exists("fec.config.js"):
            os.remove("fec.config.js")
