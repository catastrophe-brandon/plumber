import json
import os
import tempfile

import pytest

from extraction import get_app_url_from_fec_config


def test_get_app_url_from_fec_config():
    """Test extracting appUrl from a valid fec.config.js file."""
    # Create a temporary fec.config.js file with JavaScript syntax
    fec_config_content = """module.exports = {
  appUrl: ['/learning-resources', '/settings/learning-resources'],
  someOtherKey: 'value'
};
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as temp_file:
        temp_file.write(fec_config_content)
        temp_path = temp_file.name

    try:
        # Test the function
        app_url = get_app_url_from_fec_config(temp_path)

        # Verify the result
        assert app_url is not None, "appUrl should not be None"
        assert isinstance(app_url, list), "appUrl should be a list"
        assert "/learning-resources" in app_url
        assert "/settings/learning-resources" in app_url

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_app_url_missing_key():
    """Test that None is returned when appUrl is not present."""
    # Create a fec.config.js without appUrl
    fec_config_content = """module.exports = {
  someOtherKey: 'value'
};
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as temp_file:
        temp_file.write(fec_config_content)
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
    fec_config_content = """module.exports = {
  appUrl: ['/my-app', '/settings/my-app']
};
"""

    with open("fec.config.js", "w") as f:
        f.write(fec_config_content)

    try:
        app_url = get_app_url_from_fec_config()
        assert app_url is not None, "appUrl should not be None"
        assert isinstance(app_url, list), "appUrl should be a list"
        assert "/my-app" in app_url
        assert "/settings/my-app" in app_url

    finally:
        if os.path.exists("fec.config.js"):
            os.remove("fec.config.js")
