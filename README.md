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
- **App Caddyfile**: Generates Caddy server configuration for serving your application's static files
  - Route matchers for exact paths and subpaths
  - URI stripping and index.html rewriting
  - Serves files from `/srv/dist`
- **Proxy Caddyfile**: Generates reverse proxy configuration for the frontend development proxy
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
plumber <app_name> <repo_url> <pipeline_template> [--fec-config <path>]
```

**Arguments:**
- `app_name`: Name of the application (e.g., "learning-resources")
- `repo_url`: Git URL of the repository (e.g., "https://github.com/user/repo.git")
- `pipeline_template`: Path to the pipeline template file (e.g., "template/pipeline_template.yaml")
- `--fec-config`: (Optional) Path to fec.config.js file (default: "fec.config.js")

**Example:**
```bash
plumber learning-resources \
  https://github.com/RedHatInsights/learning-resources.git \
  template/konflux_pipeline_template.yaml \
  --fec-config fec_configs/fec.config.js
```

**Example Output:**
```
Hello from plumber!
App Name: learning-resources
Repo URL: https://github.com/RedHatInsights/learning-resources.git
Pipeline Template: template/pipeline_template.yaml
Found appUrl in fec_configs/fec.config.js: ['/settings/learning-resources', '/openshift/learning-resources', ...]

Generated proxy Caddyfile:
# Caddyfile template for frontend-development-proxy sidecar
# Note:
# Port 9912 - Resources from insights-chrome-dev image
# Port 8000 - Resources from application to test

@root path /
handle @root {
    reverse_proxy 127.0.0.1:9912
}
...

Generated app Caddyfile:
:8000 {
    @settings_learning_resources_match {
        path /settings/learning-resources /settings/learning-resources/
    }
    handle @settings_learning_resources_match {
        uri strip_prefix /settings/learning-resources
        rewrite / /index.html
        file_server * {
            root /srv/dist
        }
    }
    ...
}

Generated pipeline file: /tmp/learning-resources-pipeline.yaml
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
# Generates pipeline at /tmp/learning-resources-pipeline.yaml
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

caddyfile_config = generate_app_caddyfile(
    app_url_value=app_urls,
    app_name="learning-resources",
    app_port="8000"
)
print(caddyfile_config)
```

#### Generate Frontend Proxy Caddyfile

```python

from generation import generate_frontend_proxy_caddyfile

app_urls = [
    "/settings/learning-resources",
    "/openshift/learning-resources",
    "/insights/learning-resources",
]

caddyfile_config = generate_frontend_proxy_caddyfile(
    app_url_value=app_urls,
    app_name="learning-resources",
    app_port="8000",
    chrome_port="9912"
)
print(caddyfile_config)
```

## Templates

### Pipeline Template (`template/pipeline_template.yaml`)

Tekton PipelineRun template with placeholders:
- `{{app_name}}`: Replaced with the application name
- `{{repo_url}}`: Replaced with the repository URL
- `{{app_caddy_file}}`: Replaced with generated app Caddyfile content
- `{{proxy_caddy_file}}`: Replaced with generated proxy Caddyfile content

### Proxy Caddy Template (`template/proxy_caddy.template.j2`)

Jinja2 template for generating Caddyfile configurations with variables:
- `app_name`: Application name
- `app_port`: Port for the application (default: 8000)
- `chrome_port`: Port for Chrome resources (default: 9912)
- `route_prefixes`: List of route paths from appUrl

## Testing

The project includes a comprehensive test suite with 20 tests covering all functionality.

Run all tests:
```bash
pytest tests/ -v
```

Run specific test files:
```bash
pytest tests/test_pipeline_validation.py -v  # Pipeline YAML validation tests
pytest tests/test_app_caddyfile.py -v        # App Caddyfile generation tests
pytest tests/test_generate_pipeline.py -v    # Pipeline generation tests
```

Run with coverage:
```bash
pytest tests/ --cov=main
```

### Test Coverage

- **Pipeline Generation**: Template substitution, special characters, YAML validation
- **App Caddyfile**: Route generation, port configuration, structure validation
- **Proxy Caddyfile**: Template rendering, route handling, custom ports
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
├── template/
│   ├── pipeline_template.yaml           # Tekton pipeline template
│   ├── proxy_caddy.template.j2          # Proxy Caddyfile Jinja2 template
│   └── app_caddy.template.j2            # App Caddyfile template (empty - generated programmatically)
├── tests/
│   ├── test_pipeline_validation.py      # Pipeline YAML validation tests
│   ├── test_app_caddyfile.py            # App Caddyfile generation tests
│   ├── test_generate_pipeline.py        # Pipeline template substitution tests
│   ├── test_get_app_url.py              # fec.config.js parsing tests
│   ├── test_generate_frontend_proxy_caddyfile.py  # Proxy generation tests
│   └── test_proxy_caddy_template.py     # Proxy template rendering tests
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

## How It Works

1. **Read Configuration**: Plumber reads your application's `fec.config.js` file and extracts the `appUrl` array
2. **Generate App Caddyfile**: Creates a Caddy server configuration with route handlers for each URL
3. **Generate Proxy Caddyfile**: Creates a reverse proxy configuration using the Jinja2 template
4. **Embed in Pipeline**: Both Caddyfiles are embedded into the Tekton pipeline template with proper YAML indentation
5. **Validate**: The generated pipeline is validated to ensure it's syntactically correct YAML
6. **Output**: A complete Tekton PipelineRun YAML is written to `/tmp/<app_name>-pipeline.yaml`
