# plumber

Hackathon tool - Automatically set up your pipeline for CI/CD testing with Konflux/Playwright.

## Overview

Plumber automates the process of generating Tekton pipeline configurations and Caddyfile proxy configurations for frontend applications in the Konflux/OpenShift environment. It reads your application's `fec.config.js` file, extracts route configurations, and generates complete Tekton pipelines with embedded Caddyfile configurations for both the application server and frontend proxy.

## Features

### Pipeline Generation
- Generate Tekton PipelineRun configurations from templates
- Substitute application name and repository URL into pipeline YAML
- Automatically embed generated Caddyfile configurations
- YAML validation to ensure syntactically correct pipelines

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
plumber <app_name> <repo_url> (--pipeline-template <path> | --minikube-template <path>) [--fec-config <path>]
```

**Arguments:**
- `app_name`: Name of the application (e.g., "learning-resources")
- `repo_url`: Git URL of the repository (e.g., "https://github.com/user/repo.git")
- `--pipeline-template`: Path to the Konflux pipeline template file (mutually exclusive with `--minikube-template`)
- `--minikube-template`: Path to the Minikube pipeline template file (mutually exclusive with `--pipeline-template`)
- `--fec-config`: (Optional) Path to fec.config.js file (default: "fec.config.js")

**Example (Konflux):**
```bash
plumber learning-resources \
  https://github.com/RedHatInsights/learning-resources.git \
  --pipeline-template template/konflux_pipeline_template.yaml \
  --fec-config fec_configs/fec.config.js
```

**Example (Minikube):**
```bash
plumber learning-resources \
  https://github.com/RedHatInsights/learning-resources.git \
  --minikube-template template/minikube_pipeline_template.yaml \
  --fec-config fec_configs/fec.config.js
```

**Example Output:**
```
Hello from plumber!
App Name: learning-resources
Repo URL: https://github.com/RedHatInsights/learning-resources.git
Pipeline Type: konflux
Pipeline Template: template/konflux_pipeline_template.yaml
Found appUrl in fec_configs/fec.config.js: ['/settings/learning-resources', '/openshift/learning-resources', ...]

Generated proxy routes Caddyfile:
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

Generated app Caddyfile:
# Caddyfile config for the application undergoing testing (This is NOT JSON)
{
  	{$CADDY_TLS_MODE}
  	auto_https disable_redirects
  	servers {
  		metrics
  	}
}

:9000 {
  	metrics /metrics
}

:8000 {
  	{$CADDY_TLS_CERT}
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

Generated pipeline file: /Users/btweed/repos/hackathon/plumber/learning-resources-pull-request.yaml
```

The generated pipeline file will be a complete, syntactically valid Tekton PipelineRun YAML with all route configurations embedded.

### Python API

#### Complete Pipeline Generation

```python
from main import run_plumber

run_plumber(
    app_name="learning-resources",
    repo_url="https://github.com/RedHatInsights/learning-resources.git",
    pipeline_template="template/konflux_pipeline_template.yaml",
    fec_config_path="fec_configs/fec.config.js"
)
# Generates pipeline at ./learning-resources-pull-request.yaml (in current directory)
```

#### Generate Pipeline from Template

```python

from generation import generate_pipeline_from_template

output_path = generate_pipeline_from_template(
    pipeline_template_path="template/konflux_pipeline_template.yaml",
    app_name="my-app",
    repo_url="https://github.com/user/repo.git",
    app_caddy_file="# App Caddyfile content",
    proxy_caddy_file="# Proxy Caddyfile content"
)
print(f"Generated pipeline: {output_path}")
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

# Generates Caddyfile route snippets for proxy
caddyfile_config = generate_proxy_routes_caddyfile(
    app_url_value=app_urls,
    app_name="learning-resources",
    app_port="8000",
    chrome_port="9912"
)
print(caddyfile_config)
```

## Templates

### Pipeline Templates

**Konflux Pipeline** (`template/konflux_pipeline_template.yaml`)
Tekton PipelineRun template for Konflux with placeholders:
- `{{app_name}}`: Replaced with the application name
- `{{repo_url}}`: Replaced with the repository URL
- `{{generation_date}}`: Replaced with the date and time the pipeline was generated
- `{{app_caddy_file}}`: Replaced with generated app Caddyfile content
- `{{proxy_caddy_file}}`: Replaced with generated proxy routes Caddyfile snippets

**Minikube Pipeline** (`template/minikube_pipeline_template.yaml`)
Tekton PipelineRun template for Minikube with the same placeholders as Konflux:
- `{{app_name}}`: Replaced with the application name
- `{{repo_url}}`: Replaced with the repository URL
- `{{generation_date}}`: Replaced with the date and time the pipeline was generated
- `{{app_caddy_file}}`: Replaced with generated app Caddyfile content
- `{{proxy_caddy_file}}`: Replaced with generated proxy routes Caddyfile snippets

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

Jinja2 template for generating frontend proxy Caddyfile (currently not used; proxy routes are generated programmatically)

## Testing

The project includes a comprehensive test suite with 23 tests covering all functionality.

Run all tests:
```bash
pytest tests/ -v
```

Run specific test files:
```bash
pytest tests/test_pipeline_validation.py -v  # Pipeline YAML validation tests
pytest tests/test_cli_arguments.py -v        # CLI argument parsing tests
pytest tests/test_generate_pipeline.py -v    # Pipeline generation tests
```

Run with coverage:
```bash
pytest tests/ --cov=main
```

### Test Coverage

- **Pipeline Generation**: Template substitution, special characters, YAML validation
- **CLI Arguments**: Dual pipeline support, mutually exclusive options, argument parsing
- **Proxy Routes**: Caddyfile snippet generation, route handling, custom ports
- **Config Parsing**: JavaScript parsing, trailing comma handling, quote normalization
- **Integration Tests**: Full end-to-end pipeline generation with fec.config.js

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
│   └── __init__.py                      # Caddyfile and pipeline generation functions
├── template/
│   ├── konflux_pipeline_template.yaml   # Tekton pipeline template for Konflux
│   ├── minikube_pipeline_template.yaml  # Tekton pipeline template for Minikube
│   ├── app_caddy.template.j2            # App Caddyfile Jinja2 template
│   └── proxy_caddy.template.j2          # Proxy Caddyfile Jinja2 template (unused)
├── scripts/
│   ├── generate_konflux_pipeline.sh    # Example script for Konflux pipeline
│   └── generate_minikube_pipeline.sh    # Example script for Minikube pipeline
├── tests/
│   ├── test_pipeline_validation.py      # Pipeline YAML validation tests
│   ├── test_cli_arguments.py            # CLI argument parsing tests
│   ├── test_generate_pipeline.py        # Pipeline template substitution tests
│   ├── test_get_app_url.py              # fec.config.js parsing tests
│   ├── test_minikube_pipeline.py        # Minikube pipeline generation tests
│   ├── test_generate_frontend_proxy_caddyfile.py  # Proxy generation tests (unused function)
│   └── test_proxy_caddy_template.py     # Proxy template rendering tests (unused template)
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
3. **Generate App Caddyfile**: Uses the `app_caddy.template.j2` Jinja2 template to create a complete Caddy server configuration with:
   - Global TLS and metrics configuration
   - Route handlers for each route prefix
   - Environment-based routing support
4. **Generate Proxy Routes**: Programmatically generates Caddyfile route snippets for the frontend proxy with reverse_proxy directives
5. **Embed in Pipeline**: Both Caddyfile configurations are embedded into the selected Tekton pipeline template (Konflux or Minikube) with proper YAML indentation
6. **Add Metadata**: Adds the current generation date and time to the pipeline header
7. **Validate**: The generated pipeline is validated to ensure it's syntactically correct YAML
8. **Output**: A complete Tekton PipelineRun YAML is written to the current directory as `<app_name>-pull-request.yaml`
