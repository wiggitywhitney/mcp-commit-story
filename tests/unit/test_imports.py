import importlib
import pytest

MODULES = [
    'mcp_commit_story.cli',
    'mcp_commit_story.server',
    'mcp_commit_story.journal',
    'mcp_commit_story.git_utils',
    'mcp_commit_story.config',
]

@pytest.mark.parametrize('module_name', MODULES)
def test_module_import(module_name):
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Failed to import {module_name}: {e}")
