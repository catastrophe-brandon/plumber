# plumber

Hackathon tool - Automatically generate Kubernetes ConfigMaps with Caddy configurations for frontend application testing.

## Overview

Plumber automates the process of generating Kubernetes ConfigMap YAML files containing Caddyfile configurations for frontend applications. It reads your application's `fec.config.js` file, extracts route configurations, and generates ConfigMaps ready to be used in any testing environment (Tekton, Kubernetes, Minikube, etc.).

## Features

### ConfigMap Generation
- Generate Kubernetes ConfigMap YAML files with embedded Caddyfile configurations
- Two separate ConfigMaps: one for the application server, one for the frontend proxy
- User-specified ConfigMap names for flexibility
- YAML validation to ensure syntactically correct output

### Caddyfile Generation
- **App Caddyfile**: Uses Jinja2 template to generate Caddy server configuration for serving your application's static files
  - Template-based configuration with TLS and metrics support
  - Route matchers for exact paths and subpaths
  - URI stripping and index.html rewriting
  - Serves files from `/srv/dist`
- **Proxy Routes Caddyfile**: Generates reverse proxy route snippets for the frontend development proxy
  - Routes Chrome resources to port 9912
  - Routes application resources to port 8000
  - Handles multiple route prefixes

### Configuration Extraction
- Parse JavaScript `fec.config.js` files to extract application URLs
- Handles both single and double quotes
- Removes trailing commas for JSON compatibility
- Supports complex route configurations

## Installation

```bash
# Install the package
uv pip install -e .

# This makes the `plumber` command available globally
```

## Usage

### Command Line Interface

Once installed, you can use the `plumber` command from anywhere:

```bash
plumber <app_name> <repo_url> \
  --app-configmap-name <name> \
  --proxy-configmap-name <name> \
  [--fec-config <path>] \
  [--namespace <namespace>]
```

**Arguments:**
- `app_name`: Name of the application (e.g., "learning-resources")
- `repo_url`: Git URL of the repository (e.g., "https://github.com/user/repo.git")
- `--app-configmap-name`: (Required) Name for the app Caddy ConfigMap
- `--proxy-configmap-name`: (Required) Name for the proxy routes Caddy ConfigMap
- `--fec-config`: (Optional) Path to fec.config.js file (default: "fec.config.js")
- `--namespace`: (Optional) Kubernetes namespace for the ConfigMaps

**Example:**
```bash
plumber learning-resources \
  https://github.com/RedHatInsights/learning-resources.git \
  --app-configmap-name learning-resources-app-caddy \
  --proxy-configmap-name learning-resources-proxy-caddy \
  --fec-config fec_configs/fec.config.js \
  --namespace hcc-platex-services-tenant
```

**Example Output:**
```
Hello from plumber!
App Name: learning-resources
Repo URL: https://github.com/RedHatInsights/learning-resources.git
App ConfigMap Name: learning-resources-app-caddy
Proxy ConfigMap Name: learning-resources-proxy-caddy
Namespace: hcc-platex-services-tenant
Found appUrl in fec_configs/fec.config.js: ['/settings/learning-resources', '/openshift/learning-resources', ...]

Generated app Caddy ConfigMap: /Users/you/learning-resources-app-caddy.yaml
Generated proxy Caddy ConfigMap: /Users/you/learning-resources-proxy-caddy.yaml
```

The generated ConfigMap files will be created in your current directory and are ready to be applied to any Kubernetes cluster.

### Python API

#### Complete ConfigMap Generation

```python
from extraction import get_app_url_from_fec_config
from generation import generate_app_caddy_configmap, generate_proxy_caddy_configmap

# Get app URLs from fec.config.js
app_urls = get_app_url_from_fec_config("path/to/fec.config.js")

# Generate app Caddy ConfigMap
app_configmap_path = generate_app_caddy_configmap(
    configmap_name="my-app-caddy",
    app_url_value=app_urls,
    app_name="my-app",
)

# Generate proxy Caddy ConfigMap
proxy_configmap_path = generate_proxy_caddy_configmap(
    configmap_name="my-proxy-caddy",
    app_url_value=app_urls,
    app_name="my-app",
)

print(f"Generated: {app_configmap_path}")
print(f"Generated: {proxy_configmap_path}")
```

#### Extract appUrl from fec.config.js

```python
from extraction import get_app_url_from_fec_config

# Use default path (fec.config.js in current directory)
app_urls = get_app_url_from_fec_config()

# Or specify a custom path
app_urls = get_app_url_from_fec_config("path/to/fec.config.js")
# Returns: ['/settings/my-app', '/openshift/my-app', ...]
```

#### Generate App Caddyfile

```python
from generation import generate_app_caddyfile

app_urls = [
    "/settings/learning-resources",
    "/openshift/learning-resources",
    "/learning-resources",
]

# Uses app_caddy.template.j2 to generate Caddyfile
caddyfile_config = generate_app_caddyfile(
    app_url_value=app_urls,
    app_name="learning-resources",
)
print(caddyfile_config)
```

#### Generate Proxy Routes Caddyfile

```python
from generation import generate_proxy_routes_caddyfile

app_urls = [
    "/settings/learning-resources",
    "/openshift/learning-resources",
    "/insights/learning-resources",
]

# Generates Caddyfile route snippets for proxy using template
caddyfile_config = generate_proxy_routes_caddyfile(
    app_url_value=app_urls,
    app_name="learning-resources",
    app_port="8000",
    chrome_port="9912"
)
print(caddyfile_config)
```

## Generated ConfigMap Structure

### App ConfigMap Structure

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: <user-specified-name>
  namespace: <optional-namespace>
data:
  Caddyfile: |
    <caddy configuration content>
```

### Proxy ConfigMap Structure

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: <user-specified-name>
  namespace: <optional-namespace>
data:
  routes: |
    <caddy routes configuration>
```

**Key Differences:**
- **App ConfigMap** uses `Caddyfile` as the data key
- **Proxy ConfigMap** uses `routes` as the data key (matching production deployment patterns)
- Both support optional namespace in metadata

### Example App ConfigMap

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: learning-resources-app-caddy
  namespace: hcc-platex-services-tenant
data:
  Caddyfile: |
    # Caddyfile config for the application undergoing testing (This is NOT JSON)
    {
      	auto_https disable_redirects
      	servers {
      		metrics
      	}
    }

    :9000 {
      	metrics /metrics
    }

    :8000 {
      	log

      	# Handle main app route
      	@app_match {
      		path /apps/learning-resources*
      	}
      	handle @app_match {
      		uri strip_prefix /apps/learning-resources
      		file_server * {
      			root /srv/dist
      			browse
      		}
      	}
        ...
    }
```

### Example Proxy ConfigMap

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: learning-resources-proxy-caddy
  namespace: hcc-platex-services-tenant
data:
  routes: |
    @root path /
    handle @root {
        reverse_proxy 127.0.0.1:9912
    }

    handle /index.html {
        reverse_proxy 127.0.0.1:9912
    }

    handle /apps/chrome* {
        reverse_proxy 127.0.0.1:9912
    }

    handle /apps/learning-resources* {
        reverse_proxy 127.0.0.1:8000
    }

    handle /settings/learning-resources* {
        reverse_proxy 127.0.0.1:9912
    }
    ...
```

**Note:** The proxy ConfigMap uses `routes` as the data key instead of `Caddyfile` to match production deployment patterns.

## Using the ConfigMaps

Apply the generated ConfigMaps to your Kubernetes cluster:

```bash
kubectl apply -f learning-resources-app-caddy.yaml
kubectl apply -f learning-resources-proxy-caddy.yaml
```

Mount them in your pods:

```yaml
volumes:
  - name: app-caddy-config
    configMap:
      name: learning-resources-app-caddy
  - name: proxy-caddy-config
    configMap:
      name: learning-resources-proxy-caddy

containers:
  - name: app
    volumeMounts:
      - name: app-caddy-config
        mountPath: /etc/caddy
  - name: proxy
    volumeMounts:
      - name: proxy-caddy-config
        mountPath: /etc/caddy
```

## Templates

### App Caddy Template (`template/app_caddy.template.j2`)

Jinja2 template for generating the application sidecar Caddyfile with variables:
- `app_name`: Application name
- `route_path_prefixes`: List of route prefixes extracted from appUrl (e.g., `["settings", "openshift", "iam"]`)

Generates a complete Caddyfile with:
- Global TLS and metrics configuration
- Metrics server on port 9000
- Application server on port 8000
- Route handlers for each route prefix

### Proxy Caddy Template (`template/proxy_caddy.template.j2`)

Jinja2 template for generating frontend proxy Caddyfile with variables:
- `app_name`: Application name
- `app_port`: Port for application resources
- `chrome_port`: Port for Chrome/shell resources
- `route_prefixes`: List of route paths from appUrl

## Testing

The project includes a comprehensive test suite covering all functionality.

Run all tests:
```bash
pytest tests/ -v
```

Run specific test files:
```bash
pytest tests/test_configmap_generation.py -v  # ConfigMap generation tests
pytest tests/test_cli_arguments.py -v         # CLI argument parsing tests
pytest tests/test_get_app_url.py -v           # fec.config.js parsing tests
```

Run with coverage:
```bash
pytest tests/ --cov=generation --cov=extraction --cov=main
```

### Test Coverage

- **ConfigMap Generation**: ConfigMap structure, YAML validation, naming
- **CLI Arguments**: Argument parsing, required fields, defaults
- **Proxy Routes**: Caddyfile snippet generation, route handling, custom ports
- **Config Parsing**: JavaScript parsing, trailing comma handling, quote normalization
- **Integration Tests**: Full end-to-end ConfigMap generation with fec.config.js

## Code Quality

Format code:
```bash
ruff format .
```

Check linting:
```bash
ruff check .
```

Auto-fix linting issues:
```bash
ruff check . --fix
```

## CI/CD

GitHub Actions workflow (`.github/workflows/test.yml`) runs automatically on push and pull requests:
- Installs dependencies using `uv`
- Runs ruff linter
- Runs ruff formatter check
- Executes all tests with pytest

## Project Structure

```
plumber/
├── main.py                              # Main application code with CLI entry point
├── extraction/
│   └── __init__.py                      # fec.config.js parsing functions
├── generation/
│   └── __init__.py                      # Caddyfile and ConfigMap generation functions
├── template/
│   ├── app_caddy.template.j2            # App Caddyfile Jinja2 template
│   └── proxy_caddy.template.j2          # Proxy Caddyfile Jinja2 template
├── scripts/
│   └── generate_configmaps.sh           # Example script for generating ConfigMaps
├── tests/
│   ├── test_configmap_generation.py     # ConfigMap YAML generation tests
│   ├── test_cli_arguments.py            # CLI argument parsing tests
│   ├── test_get_app_url.py              # fec.config.js parsing tests
│   ├── test_generate_frontend_proxy_caddyfile.py  # Proxy generation tests
│   └── test_proxy_caddy_template.py     # Proxy template rendering tests
├── fec_configs/                         # Sample fec.config.js files for testing
├── pyproject.toml                       # Project configuration with CLI entry point
└── README.md                            # This file
```

## Requirements

- Python >= 3.12
- jinja2 >= 3.0.0
- gitpython >= 3.1.0
- pyyaml >= 6.0.0 (for YAML validation in tests)

## Development

Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

This includes:
- pytest >= 7.0.0
- ruff >= 0.14.0
- pyyaml >= 6.0.0

## How It Works

1. **Read Configuration**: Plumber reads your application's `fec.config.js` file and extracts the `appUrl` array
2. **Extract Route Prefixes**: Analyzes the appUrl routes to extract route prefixes (e.g., `settings`, `openshift`, `iam`)
3. **Generate App Caddyfile**: Uses the `app_caddy.template.j2` Jinja2 template to create a complete Caddy server configuration
4. **Generate Proxy Routes**: Uses the `proxy_caddy.template.j2` Jinja2 template to create reverse_proxy directives for the frontend proxy
5. **Wrap in ConfigMaps**: Both Caddyfile configurations are wrapped in Kubernetes ConfigMap YAML structures
6. **Output**: Two complete ConfigMap YAML files are written to the current directory

## Benefits

- **Reusable**: ConfigMaps can be used with any pipeline system (Tekton, GitHub Actions, Jenkins, etc.)
- **Flexible**: User-specified ConfigMap names for easy integration
- **Portable**: Works with Kubernetes, Minikube, OpenShift, and other Kubernetes-compatible platforms
- **Maintainable**: Template-based generation makes it easy to update configurations
- **Well-tested**: Comprehensive test suite ensures reliability
