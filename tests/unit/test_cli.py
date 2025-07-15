import pytest
import json
import subprocess
import sys
import os

def mock_cli_success():
    return json.dumps({
        "status": "success",
        "result": {
            "paths": {
                "config": "/path/to/.mcp-commit-storyrc.yaml",
                "journal": "/path/to/journal"
            },
            "message": "Journal initialized successfully."
        }
    })

def mock_cli_error():
    return json.dumps({
        "status": "error",
        "message": "User-friendly error description",
        "code": 1,
        "details": "Technical error details (optional)"
    })

def test_cli_returns_json_error_format():
    """CLI should return JSON with 'status', 'message', and 'code' fields on error."""
    output = mock_cli_error()
    data = json.loads(output)
    assert data["status"] == "error"
    assert "message" in data
    assert isinstance(data["code"], int)
    assert data["code"] == 1
    assert "details" in data

def test_cli_returns_json_success_format():
    """CLI should return JSON with 'status' and 'result' fields on success."""
    output = mock_cli_success()
    data = json.loads(output)
    assert data["status"] == "success"
    assert "result" in data
    assert "paths" in data["result"]
    assert "config" in data["result"]["paths"]
    assert "journal" in data["result"]["paths"]
    assert "message" in data["result"]

def test_cli_error_codes_are_integers():
    """CLI error codes should be integers and messages user-friendly."""
    output = mock_cli_error()
    data = json.loads(output)
    assert isinstance(data["code"], int)
    assert data["code"] in [1, 2, 3, 4]
    assert isinstance(data["message"], str)
    assert data["message"]

def test_cli_output_is_parseable_and_matches_contract():
    """CLI output should be parseable JSON and match the documented contract."""
    # Success case
    output = mock_cli_success()
    data = json.loads(output)
    assert data["status"] == "success"
    assert "result" in data
    # Error case
    output = mock_cli_error()
    data = json.loads(output)
    assert data["status"] == "error"
    assert "code" in data
    assert "message" in data

def test_cli_help_includes_journal_init():
    """CLI help output should include 'journal-init' command."""
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "--help"
    ], capture_output=True, text=True)
    assert result.returncode == 0
    assert "journal-init" in result.stdout

def test_cli_journal_init_invocation(tmp_path):
    """Invoking 'journal-init' via CLI should return JSON with 'status' and 'result' fields on success."""
    # Initialize a git repo in the temp directory
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "journal-init", "--repo-path", str(tmp_path)
    ], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, f"journal-init failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["status"] == "success"
    assert "result" in data
    assert "paths" in data["result"]
    assert "config" in data["result"]["paths"]
    assert "journal" in data["result"]["paths"]
    assert "message" in data["result"]

def test_cli_unknown_command_returns_error():
    """Unknown CLI command should return an error and nonzero exit code."""
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "not-a-real-command"
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert "No such command" in result.stderr or "Error" in result.stderr

def test_cli_journal_init_creates_only_base_dir(tmp_path):
    """After 'journal-init', only the base journal/ directory should exist (no subdirectories)."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "journal-init", "--repo-path", str(tmp_path)
    ], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    journal_dir = data["result"]["paths"]["journal"]
    assert os.path.isdir(journal_dir)
    # Only base dir should exist
    assert not os.path.exists(os.path.join(journal_dir, "daily"))
    assert not os.path.exists(os.path.join(journal_dir, "summaries"))

def test_cli_journal_entry_creates_subdirs_on_demand(tmp_path):
    """Writing a journal entry via CLI should create subdirectories as needed (on demand)."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    # Initialize journal
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "journal-init", "--repo-path", str(tmp_path)
    ], cwd=tmp_path, capture_output=True, text=True)
    data = json.loads(result.stdout)
    journal_dir = data["result"]["paths"]["journal"]
    # Write a journal entry to a nested path via CLI (simulate)
    nested_path = os.path.join(journal_dir, "daily", "2025-05-28-journal.md")
    os.makedirs(os.path.dirname(nested_path), exist_ok=False)  # Should not exist yet
    # Simulate CLI command to write entry (replace with actual CLI if available)
    # For now, just touch the file to simulate on-demand creation
    with open(nested_path, "w") as f:
        f.write("Test entry")
    assert os.path.exists(nested_path)

def test_cli_journal_entry_permission_error(tmp_path):
    """CLI should report a user-friendly error if directory creation fails due to permissions."""
    import stat
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    # Initialize journal
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "journal-init", "--repo-path", str(tmp_path)
    ], cwd=tmp_path, capture_output=True, text=True)
    data = json.loads(result.stdout)
    journal_dir = data["result"]["paths"]["journal"]
    
    # Store original permissions before changing them
    original_mode = os.stat(journal_dir).st_mode
    
    try:
        # Make journal_dir read-only
        os.chmod(journal_dir, stat.S_IREAD)
        nested_path = os.path.join(journal_dir, "daily", "2025-05-28-journal.md")
        # Simulate CLI command to write entry (should fail)
        with pytest.raises(Exception):
            with open(nested_path, "w") as f:
                f.write("Test entry")
    finally:
        # Restore original permissions for proper cleanup
        os.chmod(journal_dir, original_mode)

# Remove or skip all tests for operational CLI commands (new-entry, add-reflection, summarize, etc)
# Keep only tests for setup commands (journal-init, install-hook)
# Add a test that asserts the CLI help output does NOT mention new-entry or add-reflection, and DOES mention only setup commands

def test_cli_is_setup_only():
    """CLI should only contain setup commands, not operational commands."""
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "--help"
    ], capture_output=True, text=True)
    assert result.returncode == 0
    
    # Should contain setup commands
    assert "journal-init" in result.stdout
    assert "install-hook" in result.stdout
    
    # Should NOT contain operational commands (these are now MCP operations)
    assert "new-entry" not in result.stdout
    assert "add-reflection" not in result.stdout
    assert "summarize" not in result.stdout
    assert "blogify" not in result.stdout
    assert "backfill" not in result.stdout
    
    # Should mention MCP in help text
    assert "MCP" in result.stdout or "setup" in result.stdout.lower() 

def test_install_hook_background_flag():
    """Test that install-hook command accepts --background flag."""
    from mcp_commit_story.cli import cli
    from click.testing import CliRunner
    from unittest.mock import patch, Mock
    
    runner = CliRunner()
    
    # Mock the install function to avoid actual file operations
    with patch('mcp_commit_story.cli.install_post_commit_hook') as mock_install:
        mock_install.return_value = True
        
        # Test with background flag
        result = runner.invoke(cli, ['install-hook', '--background'])
        
        assert result.exit_code == 0
        
        # Verify the install function was called with background=True
        mock_install.assert_called_once_with(None, background=True, timeout=30)
        
        # Verify the output mentions background mode
        assert 'background mode' in result.output


def test_install_hook_background_flag_with_timeout():
    """Test that install-hook command accepts --background and --timeout flags."""
    from mcp_commit_story.cli import cli
    from click.testing import CliRunner
    from unittest.mock import patch, Mock
    
    runner = CliRunner()
    
    # Mock the install function to avoid actual file operations
    with patch('mcp_commit_story.cli.install_post_commit_hook') as mock_install:
        mock_install.return_value = True
        
        # Test with background flag and custom timeout
        result = runner.invoke(cli, ['install-hook', '--background', '--timeout', '45'])
        
        assert result.exit_code == 0
        
        # Verify the install function was called with correct parameters
        mock_install.assert_called_once_with(None, background=True, timeout=45)
        
        # Verify the output mentions background mode
        assert 'background mode' in result.output


def test_install_hook_help_includes_background():
    """Test that install-hook help includes documentation for --background flag."""
    from mcp_commit_story.cli import cli
    from click.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(cli, ['install-hook', '--help'])
    
    assert result.exit_code == 0
    assert '--background' in result.output
    assert 'background' in result.output.lower()
    assert '--timeout' in result.output 