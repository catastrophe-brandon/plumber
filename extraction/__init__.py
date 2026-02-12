import json
import os

import yaml


def get_app_url_from_fec_config(config_path: str = "fec.config.js") -> list[str] | None:
    """
    Extract the appUrl from fec.config.js file.

    Args:
        config_path: Path to the fec.config.js file (default: "fec.config.js")

    Returns:
        The appUrl value from fec.config.js as a list, or None if not found.
        If appUrl is a string, it will be wrapped in a list.

    Raises:
        FileNotFoundError: If fec.config.js is not found
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"fec.config.js not found at: {config_path}")

    # Read the file
    with open(config_path) as f:
        content = f.read()

    # Find appUrl: pattern
    start_marker = "appUrl:"
    start = content.find(start_marker)
    if start == -1:
        return None

    # Skip past "appUrl:" and any whitespace
    value_start = start + len(start_marker)
    value_start_content = content[value_start:].lstrip()

    # Check if it's an array or a string
    if value_start_content.startswith("["):
        # Handle array case: appUrl: [ ... ]
        bracket_start = content.find("[", start)
        bracket_end = content.find("]", bracket_start)
        if bracket_end == -1:
            return None

        # Extract the array content and convert to valid JSON
        array_content = content[bracket_start : bracket_end + 1]
        # Replace single quotes with double quotes for JSON compatibility
        array_content = array_content.replace("'", '"')
        # Remove trailing commas (JavaScript allows them, JSON doesn't)
        import re

        array_content = re.sub(r",(\s*])", r"\1", array_content)
        return json.loads(array_content)

    elif value_start_content.startswith("'") or value_start_content.startswith('"'):
        # Handle string case: appUrl: '/some/path' or appUrl: "/some/path"
        quote_char = value_start_content[0]
        string_start = content.find(quote_char, value_start)
        string_end = content.find(quote_char, string_start + 1)
        if string_end == -1:
            return None

        # Extract the string value
        url_value = content[string_start + 1 : string_end]
        # Return as a single-element list
        return [url_value]

    else:
        # Unknown format
        return None


def get_proxy_routes_from_frontend_yaml(
    yaml_path: str = "deploy/frontend.yaml",
) -> list[str] | None:
    """
    Extract proxy routes (asset paths only) from frontend.yaml file.

    This extracts ONLY the paths that should be proxied to the local app container:
    - spec.frontend.paths[] (e.g., /apps/rbac)
    - spec.module.modules[].routes[].pathname (e.g., /settings/rbac)

    This does NOT include navigation routes (searchEntries, serviceTiles, bundleSegments)
    because those should fall through to the Chrome shell in the stage environment.

    Args:
        yaml_path: Path to the frontend.yaml file (default: "deploy/frontend.yaml")

    Returns:
        List of unique proxy routes, or None if not found

    Raises:
        FileNotFoundError: If frontend.yaml is not found
    """
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"frontend.yaml not found at: {yaml_path}")

    # Read and parse the YAML file
    with open(yaml_path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file: {e}")

    paths = []

    # Navigate to the Frontend spec
    # The file is a Template with objects array
    if "objects" in data and isinstance(data["objects"], list):
        for obj in data["objects"]:
            if obj.get("kind") == "Frontend":
                spec = obj.get("spec", {})

                # Extract from spec.frontend.paths[]
                frontend_paths = spec.get("frontend", {}).get("paths", [])
                if isinstance(frontend_paths, list):
                    paths.extend(frontend_paths)

                # Extract from spec.module.modules[].routes[].pathname
                modules = spec.get("module", {}).get("modules", [])
                if isinstance(modules, list):
                    for module in modules:
                        routes = module.get("routes", [])
                        if isinstance(routes, list):
                            for route in routes:
                                pathname = route.get("pathname")
                                if pathname:
                                    paths.append(pathname)

    # Return unique paths, preserving order
    seen = set()
    unique_paths = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths if unique_paths else None


def get_app_url_from_frontend_yaml(yaml_path: str = "deploy/frontend.yaml") -> list[str] | None:
    """
    Extract application paths from frontend.yaml file.

    This extracts paths from:
    - spec.frontend.paths[]
    - spec.module.modules[].routes[].pathname
    - spec.searchEntries[].href
    - spec.serviceTiles[].href
    - spec.bundleSegments[].navItems[].href
    - spec.bundleSegments[].navItems[].routes[].href

    Args:
        yaml_path: Path to the frontend.yaml file (default: "deploy/frontend.yaml")

    Returns:
        List of unique application paths, or None if not found

    Raises:
        FileNotFoundError: If frontend.yaml is not found
    """
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"frontend.yaml not found at: {yaml_path}")

    # Read and parse the YAML file
    with open(yaml_path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file: {e}")

    paths = []

    # Navigate to the Frontend spec
    # The file is a Template with objects array
    if "objects" in data and isinstance(data["objects"], list):
        for obj in data["objects"]:
            if obj.get("kind") == "Frontend":
                spec = obj.get("spec", {})

                # Extract from spec.frontend.paths[]
                frontend_paths = spec.get("frontend", {}).get("paths", [])
                if isinstance(frontend_paths, list):
                    paths.extend(frontend_paths)

                # Extract from spec.module.modules[].routes[].pathname
                modules = spec.get("module", {}).get("modules", [])
                if isinstance(modules, list):
                    for module in modules:
                        routes = module.get("routes", [])
                        if isinstance(routes, list):
                            for route in routes:
                                pathname = route.get("pathname")
                                if pathname:
                                    paths.append(pathname)

                # Extract from spec.searchEntries[].href
                search_entries = spec.get("searchEntries", [])
                if isinstance(search_entries, list):
                    for entry in search_entries:
                        href = entry.get("href")
                        if href:
                            paths.append(href)

                # Extract from spec.serviceTiles[].href
                service_tiles = spec.get("serviceTiles", [])
                if isinstance(service_tiles, list):
                    for tile in service_tiles:
                        href = tile.get("href")
                        if href:
                            paths.append(href)

                # Extract from spec.bundleSegments[].navItems[]
                bundle_segments = spec.get("bundleSegments", [])
                if isinstance(bundle_segments, list):
                    for segment in bundle_segments:
                        nav_items = segment.get("navItems", [])
                        if isinstance(nav_items, list):
                            paths.extend(_extract_nav_item_hrefs(nav_items))

    # Return unique paths, preserving order
    seen = set()
    unique_paths = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths if unique_paths else None


def _extract_nav_item_hrefs(nav_items: list) -> list[str]:
    """
    Recursively extract href values from navigation items.

    Extracts from:
    - navItems[].href (direct href on nav item)
    - navItems[].routes[].href (nested routes within nav items)

    Args:
        nav_items: List of navigation items to process

    Returns:
        List of href values found
    """
    hrefs = []

    for item in nav_items:
        if not isinstance(item, dict):
            continue

        # Extract direct href from nav item
        if "href" in item:
            hrefs.append(item["href"])

        # Extract hrefs from nested routes
        routes = item.get("routes", [])
        if isinstance(routes, list):
            for route in routes:
                if isinstance(route, dict) and "href" in route:
                    hrefs.append(route["href"])

    return hrefs


def is_federated_module(yaml_path: str = "deploy/frontend.yaml") -> bool:
    """
    Detect if the application is a federated module.

    A federated module is identified by the presence of spec.module.manifestLocation
    in the frontend.yaml file. Federated modules are loaded dynamically by Chrome
    and don't have their own index.html file.

    Args:
        yaml_path: Path to the frontend.yaml file (default: "deploy/frontend.yaml")

    Returns:
        True if the app is a federated module, False otherwise

    Raises:
        FileNotFoundError: If frontend.yaml is not found
    """
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"frontend.yaml not found at: {yaml_path}")

    # Read and parse the YAML file
    with open(yaml_path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file: {e}")

    # Navigate to the Frontend spec
    if "objects" in data and isinstance(data["objects"], list):
        for obj in data["objects"]:
            if obj.get("kind") == "Frontend":
                spec = obj.get("spec", {})

                # Check if module.manifestLocation exists
                module_config = spec.get("module", {})
                if "manifestLocation" in module_config:
                    return True

    return False


def get_module_name_from_frontend_yaml(yaml_path: str = "deploy/frontend.yaml") -> str | None:
    """
    Extract the module name from frontend.yaml file.

    The module name is found at metadata.name in the Frontend object and represents
    the actual module identifier (e.g., "rbac" rather than the repository name
    "insights-rbac-ui").

    Args:
        yaml_path: Path to the frontend.yaml file (default: "deploy/frontend.yaml")

    Returns:
        Module name string, or None if not found

    Raises:
        FileNotFoundError: If frontend.yaml is not found
    """
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"frontend.yaml not found at: {yaml_path}")

    # Read and parse the YAML file
    with open(yaml_path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file: {e}")

    # Navigate to the Frontend object
    if "objects" in data and isinstance(data["objects"], list):
        for obj in data["objects"]:
            if obj.get("kind") == "Frontend":
                # Extract module name from metadata.name
                metadata = obj.get("metadata", {})
                module_name = metadata.get("name")
                if module_name:
                    return module_name

    return None
