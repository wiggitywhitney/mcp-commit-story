import importlib
import pytest

MODULES = [
    'mcp_journal.cli',
    'mcp_journal.server',
    'mcp_journal.journal',
    'mcp_journal.git_utils',
    'mcp_journal.config',
]

@pytest.mark.parametrize('module_name', MODULES)
def test_module_import(module_name):
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Failed to import {module_name}: {e}")
