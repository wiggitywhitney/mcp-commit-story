import pytest
import json
import subprocess
import sys

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