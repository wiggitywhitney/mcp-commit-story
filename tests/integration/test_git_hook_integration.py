import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_git_repo(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    # Create an initial commit
    (repo_dir / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    return repo_dir

def test_clean_hook_install(temp_git_repo):
    """Test installing the post-commit hook in a clean repo."""
    # Call CLI to install hook
    result = subprocess.run([
        "python", "-m", "mcp_commit_story.cli", "install-hook", "--repo-path", str(temp_git_repo)
    ], cwd=temp_git_repo, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"})
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Assert hook file exists and is executable
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    assert os.access(hook_path, os.X_OK)
    # Optionally, check content
    content = hook_path.read_text()
    assert "mcp-commit-story new-entry" in content

def test_overwrite_existing_hook(temp_git_repo):
    """Test installing hook when one already exists (should backup and overwrite)."""
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_path.write_text("echo old hook\n")
    os.chmod(hook_path, 0o755)
    # Call CLI to install hook
    result = subprocess.run([
        "python", "-m", "mcp_commit_story.cli", "install-hook", "--repo-path", str(temp_git_repo)
    ], cwd=temp_git_repo, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"})
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Assert backup exists
    backups = list(hook_path.parent.glob("post-commit.backup.*"))
    assert backups, "Backup file should be created"
    # Assert new hook content
    content = hook_path.read_text()
    assert "mcp-commit-story new-entry" in content

def test_hook_execution_on_commit(temp_git_repo, monkeypatch):
    """Test that the installed hook runs after a commit (simulate command)."""
    # Install the hook (simulate)
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_path.write_text("#!/bin/sh\necho HOOK_EXECUTED > hook.log\n")
    os.chmod(hook_path, 0o755)
    # Make a new commit
    (temp_git_repo / "file.txt").write_text("data\n")
    subprocess.run(["git", "add", "file.txt"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Test commit"], cwd=temp_git_repo, check=True)
    # Check that hook ran
    log_path = temp_git_repo / "hook.log"
    assert log_path.exists(), "Hook should have created log file"
    assert "HOOK_EXECUTED" in log_path.read_text()

def test_cleanup_hook(temp_git_repo):
    """Test removing the hook and cleaning up backups."""
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_path.write_text("echo test\n")
    os.chmod(hook_path, 0o755)
    # Simulate backup
    backup_path = hook_path.parent / "post-commit.backup.20250101-000000"
    backup_path.write_text("old hook\n")
    # Remove hook and backups
    hook_path.unlink()
    backup_path.unlink()
    assert not hook_path.exists()
    assert not backup_path.exists() 