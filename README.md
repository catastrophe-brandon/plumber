# plumber

Hackathon tool - Automatically set up your pipeline for CI/CD testing with Konflux/Playwright.

## Overview

Plumber automates the process of generating Tekton pipeline configurations and Caddyfile proxy configurations for frontend applications in the Konflux/OpenShift environment.

## Features

### Pipeline Generation
- Generate Tekton PipelineRun configurations from templates
- Substitute application name and repository URL into pipeline YAML
- Support for custom pipeline templates

### Frontend Proxy Configuration
- Extract `appUrl` routes from `fec.config.js` files
- Generate Caddyfile configurations for frontend-development-proxy sidecar
- Support for custom ports and multiple route paths
- Automatic route handling for Chrome and application resources

### Configuration Extraction
- Parse `fec.config.js` files to extract application URLs
- Support for JSON-based configuration files

## Installation

```bash
# Install dependencies
uv pip install -e .

# Install dev dependencies (includes pytest, ruff)
uv pip install -e ".[dev]"
```

## Usage

### Command Line

```bash
python main.py <app_name> <repo_url> <pipeline_template>
```

**Arguments:**
- `app_name`: Name of the application (e.g., "learning-resources")
- `repo_url`: Git URL of the repository (e.g., "https://github.com/user/repo.git")
- `pipeline_template`: Path to the pipeline template file (e.g., "template/template.yaml")

**Example:**
```bash
python main.py learning-resources https://github.com/RedHatInsights/learning-resources.git template/template.yaml
```

### Python API

#### Generate Pipeline from Template

```python
from main import generate_pipeline_from_template

output_path = generate_pipeline_from_template(
    pipeline_template_path="template/template.yaml",
    app_name="my-app",
    repo_url="https://github.com/user/repo.git"
)
print(f"Generated pipeline: {output_path}")
```

#### Extract appUrl from fec.config.js

```python
from main import get_app_url_from_fec_config

# Use default path (fec.config.js in current directory)
app_urls = get_app_url_from_fec_config()

# Or specify a custom path
app_urls = get_app_url_from_fec_config("path/to/fec.config.js")
```

#### Generate Frontend Proxy Caddyfile

```python
from main import generate_frontend_proxy_caddyfile

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

### Pipeline Template (`template/template.yaml`)

Tekton PipelineRun template with placeholders:
- `{{app_name}}`: Replaced with the application name
- `{{repo_url}}`: Replaced with the repository URL

### Proxy Caddy Template (`template/proxy_caddy.template.j2`)

Jinja2 template for generating Caddyfile configurations with variables:
- `app_name`: Application name
- `app_port`: Port for the application (default: 8000)
- `chrome_port`: Port for Chrome resources (default: 9912)
- `route_prefixes`: List of route paths from appUrl

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_generate_pipeline.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=main
```

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
├── main.py                          # Main application code
├── template/
│   ├── template.yaml                # Tekton pipeline template
│   ├── proxy_caddy.template.j2      # Caddyfile template
│   └── app_caddy.template.j2        # App-specific Caddyfile template
├── tests/
│   ├── test_generate_pipeline.py
│   ├── test_get_app_url.py
│   ├── test_generate_frontend_proxy_caddyfile.py
│   └── test_proxy_caddy_template.py
├── pyproject.toml                   # Project configuration
└── README.md                        # This file
```

## Requirements

- Python >= 3.12
- jinja2 >= 3.0.0

## Development

Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

This includes:
- pytest >= 7.0.0
- ruff >= 0.14.0
