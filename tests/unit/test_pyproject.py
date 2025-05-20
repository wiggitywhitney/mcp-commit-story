import os
import pytest
import toml

REQUIRED_METADATA = {
    'name': 'mcp-commit-story',
    'requires-python': '>=3.10',
}

REQUIRED_RUNTIME_DEPS = [
    'mcp',
    'click',
    'pyyaml',
    'gitpython',
    'python-dateutil',
    'opentelemetry-api',
    'opentelemetry-sdk',
    'opentelemetry-exporter-otlp',
]

REQUIRED_DEV_DEPS = [
    'pytest',
    'pytest-mock',
    'pytest-cov',
    'pytest-watch',
    'black',
    'flake8',
    'mypy',
]

def test_pyproject_toml_exists():
    assert os.path.isfile('pyproject.toml'), "Missing pyproject.toml file"

def test_pyproject_metadata_and_dependencies():
    data = toml.load('pyproject.toml')
    # Check build system
    assert 'build-system' in data, "Missing [build-system] section"
    # Check project metadata
    project = data.get('project', {})
    for key, val in REQUIRED_METADATA.items():
        assert key in project, f"Missing project metadata: {key}"
        if key == 'requires-python':
            assert val in project[key], f"Incorrect Python version: {project[key]}"
    # Check runtime dependencies
    runtime_deps = project.get('dependencies', [])
    for dep in REQUIRED_RUNTIME_DEPS:
        assert any(dep in d for d in runtime_deps), f"Missing runtime dependency: {dep}"
    # Check dev dependencies (optional-dependencies.dev)
    opt_deps = project.get('optional-dependencies', {}).get('dev', [])
    for dep in REQUIRED_DEV_DEPS:
        assert any(dep in d for d in opt_deps), f"Missing dev dependency: {dep}"
