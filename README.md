# plumber

Hackathon tool - Automatically generate Kubernetes ConfigMaps with Caddy configurations for frontend application testing.

## Overview

Plumber automates the process of generating Kubernetes ConfigMap YAML files containing Caddyfile configurations for frontend applications. It reads your application's configuration files (`frontend.yaml` or `fec.config.js`), extracts route configurations, and generates ConfigMaps ready to be used in any testing environment (Tekton, Kubernetes, Minikube, etc.).

## Intended Use Case: Federated Modules

**IMPORTANT**: Plumber is designed specifically for **federated modules** (micro-frontends) that are loaded into a shell application, NOT for standalone applications with their own navigation.

### What are Federated Modules?
Federated modules are micro-frontend components that:
- Export components via module federation (typically using `fed-mods.json` manifest)
- Are loaded into a shell application (like insights-chrome or HCC chrome)
- Do NOT have their own top-level navigation or shell
- Serve static assets from paths like `/apps/<app-name>/`

### Examples of Federated Modules:
- `insights-rbac-ui` - Loaded into chrome shell, serves from `/apps/rbac/`
- `learning-resources` - Loaded into chrome shell, serves from `/apps/learning-resources/`

### What Plumber is NOT for:
- Standalone applications with their own shell/navigation
- Applications that serve their own `index.html` at the root path
- Applications that don't use module federation

## Critical Guidelines

### 🚫 DO NOT Manually Edit Generated ConfigMaps

**NEVER manually edit or craft ConfigMaps when troubleshooting issues.** This is a critical anti-pattern that leads to:
- Configuration drift between generated and deployed configs
- Difficult-to-debug routing issues
- Lost changes when ConfigMaps are regenerated
- Inconsistent behavior across environments

**Instead, when troubleshooting:**
1. Fix the source configuration (`frontend.yaml` or `fec.config.js`)
2. Re-run Plumber to regenerate ConfigMaps
3. Review the new output for correctness
4. Submit the regenerated ConfigMaps

### ✅ Always Validate Generated ConfigMaps

After generating ConfigMaps, **use Claude Code or Claude to review the ConfigMap content** for potential issues:

**Recommended Validation Workflow:**
```bash
# After running Plumber, ask Claude to review the generated ConfigMaps:
# "Please review the generated ConfigMaps and check for errant navigation paths"
```

**Claude will check for:**
- Navigation routes (like `/iam/*`, `/settings/*`, `/insights/*`) appearing in the proxy ConfigMap
- Routes that should go to the chrome shell being sent to your app (port 8000)
- Missing wildcards on app routes (should be `/apps/myapp*` not `/apps/myapp`)
- Overly broad path patterns that capture unintended routes

**Example of CORRECT proxy ConfigMap (v2 - no chrome sidecar):**
```yaml
data:
  routes: |
    # Only route app-specific requests to the local container
    # All other requests fall through to the catch-all handler which proxies to HCC_ENV_URL
    handle /apps/rbac* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /settings/rbac* {
        reverse_proxy 127.0.0.1:8000
    }
```

**Example of INCORRECT proxy ConfigMap (errant navigation paths):**
```yaml
data:
  routes: |
    # ❌ BAD: Navigation routes should NOT be here
    handle /iam* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /settings* {  # ❌ BAD: Too broad, includes all settings
        reverse_proxy 127.0.0.1:8000
    }
```

**If Issues are Found:**
1. 🚫 **DO NOT manually edit the ConfigMap** - this defeats the purpose of automated generation
2. ✅ **Submit an issue to the Plumber repository**: https://github.com/catastrophe-brandon/plumber/issues
   - Include the generated ConfigMap content
   - Describe what routes are incorrect
   - Include your `frontend.yaml` or `fec.config.js` content
   - Explain the expected vs. actual behavior
3. ✅ The Plumber maintainers will fix the generation logic to handle your use case correctly

## Features

### ConfigMap Generation
- Generate Kubernetes ConfigMap YAML files with embedded Caddyfile configurations
- Two separate ConfigMaps: one for the application server, one for the frontend proxy
- User-specified ConfigMap names for flexibility
- Automatic YAML validation using yamllint after generation
  - Validates all generated ConfigMaps
  - Fails the generation process if validation fails
  - Ensures files pass pipeline linters (no trailing spaces, valid syntax)

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
- **Frontend YAML Support**: Parse `frontend.yaml` (or `frontend.yml`) to extract paths from:
  - `spec.frontend.paths[]`
  - `spec.module.modules[].routes[].pathname`
- **FEC Config Support**: Parse JavaScript `fec.config.js` files to extract application URLs
  - Supports both string and array formats: `appUrl: '/path'` or `appUrl: ['/path1', '/path2']`
  - Handles both single and double quotes
  - Removes trailing commas for JSON compatibility
- **Priority Order**: Checks `frontend.yaml` first (for older repos), falls back to `fec.config.js`, then defaults
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
  [--frontend-yaml <path>] \
  [--fec-config <path>] \
  [--namespace <namespace>]
```

**Arguments:**
- `app_name`: Name of the application (e.g., "learning-resources")
- `repo_url`: Git URL of the repository (e.g., "https://github.com/user/repo.git")
- `--app-configmap-name`: (Required) Name for the app Caddy ConfigMap
- `--proxy-configmap-name`: (Required) Name for the proxy routes Caddy ConfigMap
- `--frontend-yaml`: (Optional) Path to frontend.yaml file (default: "deploy/frontend.yaml")
- `--fec-config`: (Optional) Path to fec.config.js file (default: "fec.config.js")
- `--namespace`: (Optional) Kubernetes namespace for the ConfigMaps

**Note:** Plumber checks `--frontend-yaml` first, then falls back to `--fec-config` if frontend.yaml is not found or doesn't contain paths.

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

#### Extract paths from frontend.yaml

```python
from extraction import get_app_url_from_frontend_yaml

# Use default path (deploy/frontend.yaml in current directory)
app_urls = get_app_url_from_frontend_yaml()

# Or specify a custom path
app_urls = get_app_url_from_frontend_yaml("path/to/deploy/frontend.yaml")
# Returns: ['/apps/my-app', '/staging/my-app', ...]
```

#### Extract appUrl from fec.config.js

```python
from extraction import get_app_url_from_fec_config

# Use default path (fec.config.js in current directory)
app_urls = get_app_url_from_fec_config()

# Or specify a custom path
app_urls = get_app_url_from_fec_config("path/to/fec.config.js")
# Returns: ['/settings/my-app', '/openshift/my-app', ...]
# Supports both string and array formats for appUrl
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
        reverse_proxy 127.0.0.1:8000
    }
    ...
```

**Note:** The proxy ConfigMap uses `routes` as the data key instead of `Caddyfile` to match production deployment patterns. All application routes from `appUrl` are proxied to port 8000 (the app container), while Chrome/shell resources are proxied to port 9912.

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
- `app_urls`: List of exact application URL paths (e.g., `["/settings/my-app", "/staging/my-app", "/apps/my-app"]`)

Generates a complete Caddyfile with:
- Global TLS and metrics configuration
- Metrics server on port 9000
- Application server on port 8000
- Route handlers for each exact URL path from configuration files

### Proxy Caddy Template (`template/proxy_caddy.template.j2`)

Jinja2 template for generating frontend proxy Caddyfile with variables:
- `app_name`: Application name
- `app_port`: Port for application resources (default: 8000)
- `chrome_port`: Port for Chrome/shell resources (default: 9912)
- `route_prefixes`: List of exact route paths to proxy to the application

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
│   └── __init__.py                      # frontend.yaml and fec.config.js parsing functions
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
- yamllint >= 1.35.0 (for YAML validation of generated ConfigMaps)
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

### Git Hooks

Set up pre-commit hooks to automatically run linting and formatting checks:
```bash
./scripts/setup-git-hooks.sh
```

This installs a pre-commit hook that:
- Runs `ruff check .` before each commit
- Runs `ruff format . --check` before each commit
- Prevents commits if issues are found

To bypass the hook (not recommended), use:
```bash
git commit --no-verify
```

## How It Works

1. **Read Configuration**: Plumber first checks for `frontend.yaml`, then falls back to `fec.config.js` to extract application paths
   - **frontend.yaml**: Extracts from `spec.frontend.paths[]` and `spec.module.modules[].routes[].pathname`
   - **fec.config.js**: Extracts the `appUrl` value (supports both string and array formats)
2. **Generate App Caddyfile**: Uses the `app_caddy.template.j2` Jinja2 template to create a complete Caddy server configuration
   - Creates route handlers for each exact URL path from the configuration
   - Handles path stripping, index.html rewriting, and static file serving
3. **Generate Proxy Routes**: Uses the `proxy_caddy.template.j2` Jinja2 template to create reverse_proxy directives for the frontend proxy
   - Routes all application paths to port 8000 (the test app container)
   - Routes Chrome/shell resources to port 9912
4. **Wrap in ConfigMaps**: Both Caddyfile configurations are wrapped in Kubernetes ConfigMap YAML structures
5. **Validate YAML**: Each generated ConfigMap is automatically validated using yamllint
   - Uses relaxed validation rules
   - Fails immediately if validation errors are found (trailing spaces, syntax errors, etc.)
   - Ensures generated files will pass pipeline linters
6. **Output**: Two complete, validated ConfigMap YAML files are written to the current directory

## Benefits

- **Reusable**: ConfigMaps can be used with any pipeline system (Tekton, GitHub Actions, Jenkins, etc.)
- **Flexible**: User-specified ConfigMap names for easy integration
- **Portable**: Works with Kubernetes, Minikube, OpenShift, and other Kubernetes-compatible platforms
- **Maintainable**: Template-based generation makes it easy to update configurations
- **Well-tested**: Comprehensive test suite ensures reliability
