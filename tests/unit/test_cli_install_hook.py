import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from mcp_commit_story.cli import cli

# Note: CliRunner doesn't properly propagate return-based exit codes
# We test JSON output instead, which contains error codes

@patch('mcp_commit_story.cli.install_post_commit_hook')
def test_cli_install_hook_success(mock_install):
    runner = CliRunner()
    mock_install.return_value = None
    result = runner.invoke(cli, ['install-hook'])
    data = json.loads(result.output)
    assert data["status"] == "success"
    assert "hook" in data["result"]["message"].lower()
    assert result.output.strip().startswith('{') and result.output.strip().endswith('}')

@patch('mcp_commit_story.cli.install_post_commit_hook', side_effect=FileNotFoundError('Not a git repo'))
def test_cli_install_hook_not_git_repo(mock_install):
    runner = CliRunner()
    result = runner.invoke(cli, ['install-hook'])
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["code"] == 4  # filesystem error
    assert 'not a git repo' in data["message"].lower()
    assert result.output.strip().startswith('{') and result.output.strip().endswith('}')

@patch('mcp_commit_story.cli.install_post_commit_hook', side_effect=PermissionError('Hooks dir not writable'))
def test_cli_install_hook_hooks_dir_not_writable(mock_install):
    runner = CliRunner()
    result = runner.invoke(cli, ['install-hook'])
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["code"] == 1  # general error
    assert 'writable' in data["message"].lower()
    assert result.output.strip().startswith('{') and result.output.strip().endswith('}')

@patch('mcp_commit_story.cli.install_post_commit_hook', side_effect=FileExistsError('Hook already installed'))
def test_cli_install_hook_already_installed(mock_install):
    runner = CliRunner()
    result = runner.invoke(cli, ['install-hook'])
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["code"] == 2  # already_initialized
    assert 'already' in data["message"].lower()
    assert result.output.strip().startswith('{') and result.output.strip().endswith('}')

# Output format test (should always be JSON)
def test_cli_install_hook_output_format(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr('mcp_commit_story.cli.install_post_commit_hook', lambda *a, **kw: None)
    result = runner.invoke(cli, ['install-hook'])
    assert result.output.strip().startswith('{') and result.output.strip().endswith('}')

@patch('mcp_commit_story.cli.install_post_commit_hook')
def test_cli_install_hook_with_backup(mock_install):
    runner = CliRunner()
    mock_install.return_value = True  # Simulate successful installation
    result = runner.invoke(cli, ['install-hook'])
    data = json.loads(result.output)
    assert data["status"] == "success"
    assert "synchronous mode" in data["result"]["message"]
    assert data["result"]["background_mode"] == False 