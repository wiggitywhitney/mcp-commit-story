import pytest
from mcp_commit_story.git_utils import generate_hook_content
import os
import stat
import shutil
from unittest.mock import patch
from mcp_commit_story.git_utils import install_post_commit_hook

def test_basic_hook_content():
    """Should generate a valid post-commit hook with enhanced Python worker."""
    content = generate_hook_content()
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh"
    assert "python -m mcp_commit_story.git_hook_worker" in content, "Enhanced Python worker should be present"
    assert '"$PWD"' in content, "Should pass current directory to worker"
    assert ">/dev/null 2>&1" in content, "Should suppress output"
    assert content.strip().endswith("|| true"), "Should not block commit on error"

def test_custom_command():
    """Should allow custom command(s) in the hook."""
    custom = "echo 'hello world'"
    content = generate_hook_content(custom)
    assert custom in content, "Custom command should be present"
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh"
    assert content.strip().endswith("|| true"), "Should not block commit on error"

def test_proper_shebang():
    """Should use the correct shebang line (to be approved)."""
    content = generate_hook_content()
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh and on its own line"

def test_executable_format():
    """Should ensure the script is in executable format (line endings, permissions)."""
    content = generate_hook_content()
    # Check for Unix line endings only (no \r\n)
    assert "\r" not in content, "Script should use Unix (LF) line endings only"

def test_install_post_commit_hook_fresh_install(tmp_path):
    repo_dir = tmp_path
    hooks_dir = repo_dir / '.git' / 'hooks'
    hooks_dir.mkdir(parents=True)
    hook_path = hooks_dir / 'post-commit'
    if hook_path.exists():
        hook_path.unlink()
    install_post_commit_hook(str(repo_dir))
    assert hook_path.exists()
    with open(hook_path) as f:
        content = f.read()
    assert content.startswith("#!/bin/sh\n")
    assert "python -m mcp_commit_story.git_hook_worker" in content
    assert content.strip().endswith("|| true")

def test_install_post_commit_hook_replacement_creates_backup(tmp_path):
    repo_dir = tmp_path
    hooks_dir = repo_dir / '.git' / 'hooks'
    hooks_dir.mkdir(parents=True)
    hook_path = hooks_dir / 'post-commit'
    # Create an existing hook
    hook_path.write_text('#!/bin/sh\necho old\n')
    with patch('mcp_commit_story.git_utils.backup_existing_hook') as mock_backup:
        mock_backup.return_value = str(hook_path) + '.backup'
        install_post_commit_hook(str(repo_dir))
        mock_backup.assert_called_once_with(str(hook_path))
    assert hook_path.exists()
    with open(hook_path) as f:
        content = f.read()
    assert content.startswith("#!/bin/sh\n")
    assert "python -m mcp_commit_story.git_hook_worker" in content
    assert content.strip().endswith("|| true")

def test_install_post_commit_hook_permission_error_on_hooks_dir(tmp_path):
    repo_dir = tmp_path
    hooks_dir = repo_dir / '.git' / 'hooks'
    hooks_dir.mkdir(parents=True)
    # Store original permissions
    original_mode = os.stat(hooks_dir).st_mode
    try:
        os.chmod(hooks_dir, 0o500)  # Remove write permission
        with pytest.raises(PermissionError):
            install_post_commit_hook(str(repo_dir))
    finally:
        # Restore original permissions for proper cleanup
        os.chmod(hooks_dir, original_mode)

def test_install_post_commit_hook_missing_hooks_dir(tmp_path):
    repo_dir = tmp_path
    hooks_dir = repo_dir / '.git' / 'hooks'
    # Do not create hooks_dir
    with pytest.raises(FileNotFoundError):
        install_post_commit_hook(str(repo_dir))

def test_install_post_commit_hook_sets_executable(tmp_path):
    repo_dir = tmp_path
    hooks_dir = repo_dir / '.git' / 'hooks'
    hooks_dir.mkdir(parents=True)
    hook_path = hooks_dir / 'post-commit'
    if hook_path.exists():
        hook_path.unlink()
    install_post_commit_hook(str(repo_dir))
    mode = os.stat(hook_path).st_mode
    assert mode & stat.S_IXUSR, 'Hook file should be executable by user'
    assert mode & stat.S_IXGRP, 'Hook file should be executable by group'
    assert mode & stat.S_IXOTH, 'Hook file should be executable by others' 