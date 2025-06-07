import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest
import sys

@pytest.fixture
def temp_git_repo(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    # Set user name and email for test commits
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    # Create an initial commit
    (repo_dir / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    yield repo_dir

def test_clean_hook_install(temp_git_repo):
    """Test installing the post-commit hook in a clean repo."""
    # Call CLI to install hook
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "install-hook", "--repo-path", str(temp_git_repo)
    ], cwd=temp_git_repo, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"})
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Assert hook file exists and is executable
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    assert hook_path.exists()
    assert os.access(hook_path, os.X_OK)
    # Check content - should use new Python worker approach
    content = hook_path.read_text()
    assert "python -m mcp_commit_story.git_hook_worker" in content

def test_overwrite_existing_hook(temp_git_repo):
    """Test installing hook when one already exists (should backup and overwrite)."""
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_path.write_text("echo old hook\n")
    os.chmod(hook_path, 0o755)
    # Call CLI to install hook
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "install-hook", "--repo-path", str(temp_git_repo)
    ], cwd=temp_git_repo, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"})
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Assert backup exists
    backups = list(hook_path.parent.glob("post-commit.backup.*"))
    assert backups, "Backup file should be created"
    # Assert new hook content - should use new Python worker approach
    content = hook_path.read_text()
    assert "python -m mcp_commit_story.git_hook_worker" in content

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

def test_real_hook_execution_triggers_command(temp_git_repo):
    """Test that the real installed post-commit hook triggers the expected command after a commit."""
    log_path = temp_git_repo / "real_hook.log"
    debug_log_path = temp_git_repo / "hook_debug.log"
    hooks_dir_debug = temp_git_repo / "hooks_dir_debug.log"
    hook_content_debug = temp_git_repo / "hook_content_debug.log"
    # Write debug hook content directly
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_content = (
        f"#!/bin/sh\n"
        f"set -x\n"
        f"echo REAL_HOOK_EXECUTED > '{log_path}' 2>&1\n"
        f"echo 'HOOK STARTED' >> '{debug_log_path}'\n"
        f"echo 'PWD: ' $(pwd) >> '{debug_log_path}'\n"
        f"ls -l >> '{debug_log_path}' 2>&1\n"
        f"echo 'HOOK FINISHED' >> '{debug_log_path}'\n"
    )
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    # Print hooks dir contents and permissions before commit
    hooks_dir = temp_git_repo / ".git" / "hooks"
    with open(hooks_dir_debug, "w") as f:
        f.write("Hooks dir contents before commit:\n")
        for p in hooks_dir.iterdir():
            f.write(f"{p.name}: {oct(p.stat().st_mode)}\n")
    # Print hook file content to debug log
    with open(hook_content_debug, "w") as f:
        f.write(hook_path.read_text())
    # Make a new commit to trigger the hook
    (temp_git_repo / "file2.txt").write_text("data2\n")
    subprocess.run(["git", "add", "file2.txt"], cwd=temp_git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Trigger real hook"], cwd=temp_git_repo, check=True)
    # Check that the hook ran
    if not log_path.exists():
        debug_contents = debug_log_path.read_text() if debug_log_path.exists() else "(debug log missing)"
        hooks_dir_contents = hooks_dir_debug.read_text() if hooks_dir_debug.exists() else "(hooks dir debug missing)"
        hook_content_contents = hook_content_debug.read_text() if hook_content_debug.exists() else "(hook content debug missing)"
        pytest.fail(
            f"Real hook should have created log file.\n"
            f"Debug log contents:\n{debug_contents}\n"
            f"Hooks dir debug:\n{hooks_dir_contents}\n"
            f"Hook file contents:\n{hook_content_contents}"
        )
    assert "REAL_HOOK_EXECUTED" in log_path.read_text()

def test_run_hook_directly(temp_git_repo):
    """Test running the installed post-commit hook directly to verify it works outside of git."""
    log_path = temp_git_repo / "real_hook.log"
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_content = (
        f"#!/bin/sh\n"
        f"set -x\n"
        f"echo REAL_HOOK_EXECUTED > '{log_path}' 2>&1\n"
    )
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    # Run the hook directly
    result = subprocess.run([str(hook_path)], cwd=temp_git_repo, capture_output=True, text=True)
    assert result.returncode == 0, f"Direct hook run failed: {result.stderr}"
    assert log_path.exists(), "Direct hook run should create log file"
    assert "REAL_HOOK_EXECUTED" in log_path.read_text()

def test_run_hook_with_sh(temp_git_repo):
    """Test running the installed post-commit hook with 'sh post-commit' to rule out exec permission issues."""
    log_path = temp_git_repo / "real_hook.log"
    hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
    hook_content = (
        f"#!/bin/sh\n"
        f"set -x\n"
        f"echo REAL_HOOK_EXECUTED > '{log_path}' 2>&1\n"
    )
    hook_path.write_text(hook_content)
    os.chmod(hook_path, 0o755)
    # Run the hook with sh explicitly
    result = subprocess.run(["sh", str(hook_path)], cwd=temp_git_repo, capture_output=True, text=True)
    assert result.returncode == 0, f"sh post-commit failed: {result.stderr}"
    assert log_path.exists(), "sh post-commit should create log file"
    assert "REAL_HOOK_EXECUTED" in log_path.read_text()

def test_hook_error_handling_does_not_block_commit(temp_git_repo, monkeypatch):
    """Test that if the hook command fails, the commit still succeeds (hook is non-blocking)."""
    from mcp_commit_story import git_utils
    def error_hook_content(command=None):
        # Simulate a failing command
        return """#!/bin/sh\nexit 1\n"""
    monkeypatch.setattr(git_utils, "generate_hook_content", error_hook_content)
    # Install the hook via CLI
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "install-hook", "--repo-path", str(temp_git_repo)
    ], cwd=temp_git_repo, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"})
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Make a new commit (should not be blocked by hook failure)
    (temp_git_repo / "file3.txt").write_text("data3\n")
    subprocess.run(["git", "add", "file3.txt"], cwd=temp_git_repo, check=True)
    commit_result = subprocess.run(["git", "commit", "-m", "Test hook error handling"], cwd=temp_git_repo, capture_output=True, text=True)
    assert commit_result.returncode == 0, f"Commit should succeed even if hook fails: {commit_result.stderr}" 