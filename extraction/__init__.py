import json
import os


def get_app_url_from_fec_config(config_path: str = "fec.config.js") -> list[str] | None:
    """
    Extract the appUrl from fec.config.js file.

    Args:
        config_path: Path to the fec.config.js file (default: "fec.config.js")

    Returns:
        The appUrl value from fec.config.js, or None if not found

    Raises:
        FileNotFoundError: If fec.config.js is not found
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"fec.config.js not found at: {config_path}")

    # Read the file
    with open(config_path) as f:
        content = f.read()

    # Find appUrl: [ ... ] pattern
    start_marker = "appUrl:"
    start = content.find(start_marker)
    if start == -1:
        return None

    # Find the opening bracket
    bracket_start = content.find("[", start)
    if bracket_start == -1:
        return None

    # Find the matching closing bracket
    bracket_end = content.find("]", bracket_start)
    if bracket_end == -1:
        return None

    # Extract the array content and convert to valid JSON
    array_content = content[bracket_start : bracket_end + 1]
    # Replace single quotes with double quotes for JSON compatibility
    # This handles JavaScript string literals which can use single quotes
    array_content = array_content.replace("'", '"')
    # Remove trailing commas (JavaScript allows them, JSON doesn't)
    import re

    array_content = re.sub(r",(\s*])", r"\1", array_content)
    return json.loads(array_content)
