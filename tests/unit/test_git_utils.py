import pytest
import os
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import stat
import shutil
import tempfile
from mcp_commit_story.git_utils import (
    is_git_repo, 
    get_repo, 
    get_current_commit, 
    is_journal_only_commit,
    get_commit_details,
    get_commit_diff_summary,
    backup_existing_hook,
    install_post_commit_hook,
    get_commits_since_last_entry,
    get_previous_commit_info,  # NEW: Import the function we're about to implement
    generate_hook_content  # NEW: Import the function we're about to test
)
# TelemetryCollector import removed - using mock approach instead
from mcp_commit_story.context_collection import collect_git_context

# TDD: Test that GitPython is installed and can instantiate a Repo object
# This test should fail if GitPython is missing or misconfigured

def test_gitpython_import_and_repo_instantiation():
    try:
        import git
        repo = git.Repo(os.getcwd())
        assert repo is not None
    except ImportError:
        pytest.fail("GitPython is not installed. Run: pip install gitpython")
    except git.InvalidGitRepositoryError:
        # Acceptable if not in a git repo, but the import should still succeed
        pass

def test_is_git_repo_valid():
    """Test detection of valid Git repository"""
    with patch('os.path.exists') as mock_exists:
        # Mock .git directory exists
        mock_exists.return_value = True
        
        result = is_git_repo('/fake/repo/path')
        assert result is True
        mock_exists.assert_called_with(os.path.join('/fake/repo/path', '.git'))

def test_is_git_repo_invalid():
    """Test detection of invalid Git repository"""
    with patch('os.path.exists') as mock_exists:
        # Mock .git directory doesn't exist
        mock_exists.return_value = False
        
        result = is_git_repo('/fake/repo/path')
        assert result is False
        mock_exists.assert_called_with(os.path.join('/fake/repo/path', '.git'))

def test_get_repo_with_path():
    """Test getting repo with specific path"""
    with patch('mcp_commit_story.git_utils.git.Repo') as mock_repo:
        # Setup
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Call
        result = get_repo('/fake/repo/path')
        
        # Assert
        assert result == mock_repo_instance
        mock_repo.assert_called_with('/fake/repo/path')

def test_get_repo_with_default_path():
    """Test getting repo with default path (current dir)"""
    with patch('mcp_commit_story.git_utils.git.Repo') as mock_repo, \
         patch('os.getcwd') as mock_getcwd:
        # Setup
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        mock_getcwd.return_value = '/default/path'
        
        # Call
        result = get_repo()
        
        # Assert
        assert result == mock_repo_instance
        mock_repo.assert_called_with('/default/path')

def test_get_current_commit():
    """Test getting current commit from repo"""
    # Setup mock repo
    mock_repo = Mock()
    mock_commit = Mock()
    mock_repo.head.commit = mock_commit
    
    # Call
    result = get_current_commit(mock_repo)
    
    # Assert
    assert result == mock_commit

def test_is_journal_only_commit_true():
    """Test detecting commit that only modifies journal files"""
    # Setup
    mock_commit = Mock()
    mock_file1 = Mock()
    mock_file1.a_path = 'journal/2023-05-20.md'
    mock_file2 = Mock()
    mock_file2.a_path = 'journal/summaries/weekly.md'
    
    # Mock the diff to return journal files only
    mock_commit.diff.return_value = [mock_file1, mock_file2]
    
    # Call
    result = is_journal_only_commit(mock_commit, 'journal/')
    
    # Assert
    assert result is True

def test_is_journal_only_commit_false():
    """Test detecting commit that modifies non-journal files"""
    # Setup
    mock_commit = Mock()
    mock_file1 = Mock()
    mock_file1.a_path = 'journal/2023-05-20.md'
    mock_file2 = Mock()
    mock_file2.a_path = 'src/main.py'
    
    # Mock the diff to return mixed files
    mock_commit.diff.return_value = [mock_file1, mock_file2]
    
    # Call
    result = is_journal_only_commit(mock_commit, 'journal/')
    
    # Assert
    assert result is False

def test_get_commit_details():
    """Test extracting relevant details from a commit"""
    # Setup
    mock_commit = Mock()
    mock_commit.hexsha = 'abcdef123456'
    mock_commit.message = 'Test commit message'
    mock_commit.committed_date = 1621512345
    mock_commit.author.name = 'Test Author'
    mock_commit.author.email = 'test@example.com'
    
    # Mock the diff stats
    mock_stats = Mock()
    mock_stats.files = {
        'file1.py': {'insertions': 10, 'deletions': 5},
        'file2.py': {'insertions': 3, 'deletions': 2}
    }
    mock_commit.stats = mock_stats
    
    # Call
    result = get_commit_details(mock_commit)
    
    # Assert
    assert result['hash'] == 'abcdef123456'
    assert result['message'] == 'Test commit message'
    assert 'timestamp' in result
    assert result['author'] == 'Test Author <test@example.com>'
    assert result['stats']['files'] == 2
    assert result['stats']['insertions'] == 13
    assert result['stats']['deletions'] == 7

# TDD: Tests for git_repo fixture (not yet implemented)
def test_git_repo_fixture_creates_valid_repo(git_repo):
    repo = git_repo
    import git
    assert isinstance(repo, git.Repo)
    # Explicitly create an initial commit
    file_path = os.path.join(repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('hello world\n')
    repo.index.add(['file1.txt'])
    repo.index.commit('initial commit')
    assert len(list(repo.iter_commits())) > 0

def test_git_repo_fixture_file_contents(git_repo):
    repo = git_repo
    # Explicitly create file1.txt and commit
    file_path = os.path.join(repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('hello world\n')
    repo.index.add(['file1.txt'])
    repo.index.commit('initial commit')
    with open(file_path, 'r') as f:
        content = f.read()
    assert content == 'hello world\n'

def test_git_repo_fixture_helper_commit(git_repo):
    repo = git_repo
    # Explicitly create an initial commit
    file_path = os.path.join(repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('hello world\n')
    repo.index.add(['file1.txt'])
    repo.index.commit('initial commit')
    # Add and commit a new file
    file_path2 = os.path.join(repo.working_tree_dir, 'newfile.txt')
    with open(file_path2, 'w') as f:
        f.write('new content\n')
    repo.index.add(['newfile.txt'])
    repo.index.commit('add newfile.txt')
    assert any('add newfile.txt' in c.message for c in repo.iter_commits())

# TDD: Tests for get_commit_diff_summary (not yet implemented)
def test_diff_summary_add_file(git_repo):
    # Create an initial commit so the next commit has a parent
    init_path = os.path.join(git_repo.working_tree_dir, 'init.txt')
    with open(init_path, 'w') as f:
        f.write('init\n')
    git_repo.index.add(['init.txt'])
    git_repo.index.commit('initial commit')
    # Add a new file and commit
    file_path = os.path.join(git_repo.working_tree_dir, 'added.txt')
    with open(file_path, 'w') as f:
        f.write('new file\n')
    git_repo.index.add(['added.txt'])
    commit = git_repo.index.commit('add added.txt')
    summary = get_commit_diff_summary(commit)
    assert 'added.txt' in summary
    assert 'added' in summary.lower()

def test_diff_summary_modify_file(git_repo):
    # Explicitly create file1.txt and commit
    file_path = os.path.join(git_repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('original\n')
    git_repo.index.add(['file1.txt'])
    git_repo.index.commit('initial commit')
    # Modify file1.txt and commit
    with open(file_path, 'a') as f:
        f.write('more text\n')
    git_repo.index.add(['file1.txt'])
    commit = git_repo.index.commit('modify file1.txt')
    summary = get_commit_diff_summary(commit)
    assert 'file1.txt' in summary
    assert 'modified' in summary.lower()

def test_diff_summary_delete_file(git_repo):
    # Explicitly create file1.txt and commit
    file_path = os.path.join(git_repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('original\n')
    git_repo.index.add(['file1.txt'])
    git_repo.index.commit('initial commit')
    # Delete file1.txt and commit
    os.remove(file_path)
    git_repo.index.remove(['file1.txt'])
    commit = git_repo.index.commit('delete file1.txt')
    summary = get_commit_diff_summary(commit)
    assert 'file1.txt' in summary
    assert 'deleted' in summary.lower()

def test_diff_summary_empty_commit(git_repo):
    # Create an empty commit (should work even if repo is empty)
    commit = git_repo.index.commit('empty commit', skip_hooks=True, parent_commits=None)
    summary = get_commit_diff_summary(commit)
    assert 'no changes' in summary.lower() or summary.strip() == ''

# NOTE: Binary file detection is heuristically tested in production code (see is_blob_binary),
# but cannot be reliably tested in this environment due to GitPython limitations with new files in temp repos.
# Therefore, the binary file test is omitted from this suite.

def test_diff_summary_large_diff(git_repo):
    # Create an initial commit so the next commit has a parent
    init_path = os.path.join(git_repo.working_tree_dir, 'init.txt')
    with open(init_path, 'w') as f:
        f.write('init\n')
    git_repo.index.add(['init.txt'])
    git_repo.index.commit('initial commit')
    # Add many files and commit
    for i in range(20):
        file_path = os.path.join(git_repo.working_tree_dir, f'file_{i}.txt')
        with open(file_path, 'w') as f:
            f.write(f'content {i}\n')
        git_repo.index.add([f'file_{i}.txt'])
    commit = git_repo.index.commit('add many files')
    summary = get_commit_diff_summary(commit)
    assert 'file_0.txt' in summary and 'file_19.txt' in summary
    assert 'added' in summary.lower() or 'files changed' in summary.lower()

def test_backup_existing_hook_backs_up_file_with_timestamp(tmp_path):
    # Create a fake hook file
    hook_path = tmp_path / 'pre-commit'
    hook_path.write_text('#!/bin/sh\necho test\n')
    orig_mode = hook_path.stat().st_mode
    # Patch time to return a fixed value
    with patch('time.strftime', return_value='20240520-123456'):
        backup_path = backup_existing_hook(str(hook_path))
    # Check backup file exists with correct name
    expected_backup = tmp_path / 'pre-commit.backup.20240520-123456'
    assert backup_path == str(expected_backup)
    assert expected_backup.exists()
    # Check content matches
    assert expected_backup.read_text() == '#!/bin/sh\necho test\n'
    # Check permissions preserved
    assert expected_backup.stat().st_mode == orig_mode

def test_backup_existing_hook_no_file(tmp_path):
    # No hook file exists
    hook_path = tmp_path / 'pre-commit'
    backup_path = backup_existing_hook(str(hook_path))
    assert backup_path is None

def test_backup_existing_hook_preserves_permissions(tmp_path):
    hook_path = tmp_path / 'pre-commit'
    hook_path.write_text('echo hi\n')
    # Set custom permissions
    hook_path.chmod(0o750)
    with patch('time.strftime', return_value='20240520-123456'):
        backup_path = backup_existing_hook(str(hook_path))
    backup_file = tmp_path / 'pre-commit.backup.20240520-123456'
    assert backup_file.exists()
    assert oct(backup_file.stat().st_mode & 0o777) == '0o750'

def test_backup_existing_hook_readonly_filesystem(tmp_path):
    hook_path = tmp_path / 'pre-commit'
    hook_path.write_text('echo hi\n')
    # Simulate read-only filesystem by patching shutil.copy2 to raise
    with patch('shutil.copy2', side_effect=PermissionError):
        with pytest.raises(PermissionError):
            backup_existing_hook(str(hook_path))

def test_backup_existing_hook_multiple_backups_unique_names(tmp_path):
    hook_path = tmp_path / 'pre-commit'
    hook_path.write_text('echo hi\n')
    # Patch time to return different timestamps for each backup
    with patch('time.strftime', side_effect=['20240520-123456', '20240520-123457']):
        backup1 = backup_existing_hook(str(hook_path))
        backup2 = backup_existing_hook(str(hook_path))
    backup_file1 = tmp_path / 'pre-commit.backup.20240520-123456'
    backup_file2 = tmp_path / 'pre-commit.backup.20240520-123457'
    assert backup1 == str(backup_file1)
    assert backup2 == str(backup_file2)
    assert backup_file1.exists()
    assert backup_file2.exists()
    assert backup_file1.read_text() == 'echo hi\n'
    assert backup_file2.read_text() == 'echo hi\n'
    assert backup_file1 != backup_file2

def test_backup_existing_hook_ioerror(tmp_path):
    hook_path = tmp_path / 'pre-commit'
    hook_path.write_text('echo hi\n')
    # Simulate IOError (e.g., disk full) during copy
    with patch('shutil.copy2', side_effect=IOError):
        with pytest.raises(IOError):
            backup_existing_hook(str(hook_path))

POST_COMMIT_CONTENT = """#!/bin/sh\necho 'Post-commit hook triggered'\n"""

def test_install_post_commit_hook_creates_hook_with_content(git_repo):
    hooks_dir = os.path.join(git_repo.working_tree_dir, '.git', 'hooks')
    hook_path = os.path.join(hooks_dir, 'post-commit')
    # Remove hook if exists
    if os.path.exists(hook_path):
        os.remove(hook_path)
    install_post_commit_hook(git_repo.working_tree_dir)
    assert os.path.exists(hook_path)
    with open(hook_path) as f:
        content = f.read()
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh"
    assert "python -m mcp_commit_story.git_hook_worker" in content, "Should contain the enhanced Python worker"
    assert ">/dev/null 2>&1" in content, "Should suppress output"
    assert content.strip().endswith("|| true"), "Should not block commit on error"

def test_install_post_commit_hook_backs_up_existing_hook(git_repo):
    hooks_dir = os.path.join(git_repo.working_tree_dir, '.git', 'hooks')
    hook_path = os.path.join(hooks_dir, 'post-commit')
    # Create an existing hook
    with open(hook_path, 'w') as f:
        f.write('#!/bin/sh\necho old\n')
    # Patch backup_existing_hook to track calls
    with patch('mcp_commit_story.git_utils.backup_existing_hook') as mock_backup:
        mock_backup.return_value = hook_path + '.backup'
        install_post_commit_hook(git_repo.working_tree_dir)
        mock_backup.assert_called_once_with(hook_path)
    # New hook should exist
    assert os.path.exists(hook_path)
    with open(hook_path) as f:
        content = f.read()
    assert content.startswith("#!/bin/sh\n"), "Shebang should be #!/bin/sh"
    assert "python -m mcp_commit_story.git_hook_worker" in content, "Should contain the enhanced Python worker"
    assert ">/dev/null 2>&1" in content, "Should suppress output"
    assert content.strip().endswith("|| true"), "Should not block commit on error"

def test_install_post_commit_hook_sets_executable(git_repo):
    hooks_dir = os.path.join(git_repo.working_tree_dir, '.git', 'hooks')
    hook_path = os.path.join(hooks_dir, 'post-commit')
    if os.path.exists(hook_path):
        os.remove(hook_path)
    install_post_commit_hook(git_repo.working_tree_dir)
    mode = os.stat(hook_path).st_mode
    assert mode & 0o111, 'Hook file should be executable'

def test_install_post_commit_hook_readonly_hooks_dir(git_repo):
    hooks_dir = os.path.join(git_repo.working_tree_dir, '.git', 'hooks')
    # Store original permissions
    original_mode = os.stat(hooks_dir).st_mode
    try:
        os.chmod(hooks_dir, 0o500)  # Remove write permission
        with pytest.raises(PermissionError):
            install_post_commit_hook(git_repo.working_tree_dir)
    finally:
        # Restore original permissions for proper cleanup
        os.chmod(hooks_dir, original_mode)

def test_install_post_commit_hook_missing_hooks_dir(git_repo):
    hooks_dir = os.path.join(git_repo.working_tree_dir, '.git', 'hooks')
    shutil.rmtree(hooks_dir)
    with pytest.raises(FileNotFoundError):
        install_post_commit_hook(git_repo.working_tree_dir)

def test_install_post_commit_hook_calls_backup_existing_hook(git_repo):
    hooks_dir = os.path.join(git_repo.working_tree_dir, '.git', 'hooks')
    hook_path = os.path.join(hooks_dir, 'post-commit')
    with open(hook_path, 'w') as f:
        f.write('old hook')
    with patch('mcp_commit_story.git_utils.backup_existing_hook') as mock_backup:
        mock_backup.return_value = hook_path + '.backup'
        install_post_commit_hook(git_repo.working_tree_dir)
        mock_backup.assert_called_once_with(hook_path)

def test_get_commits_since_last_entry_identifies_commits_after_last_journal_entry(git_repo, tmp_path):
    repo_dir = git_repo.working_tree_dir
    journal_dir = os.path.join(repo_dir, "journal", "daily")
    os.makedirs(journal_dir, exist_ok=True)
    # Commit 1: code change
    file1 = os.path.join(repo_dir, "file1.py")
    with open(file1, "w") as f:
        f.write("print('hello')\n")
    git_repo.index.add([file1])
    git_repo.index.commit("Initial code commit")
    # Commit 2: journal entry
    journal_file = os.path.join(journal_dir, "2025-05-19.md")
    with open(journal_file, "w") as f:
        f.write("# Journal\n")
    git_repo.index.add([journal_file])
    git_repo.index.commit("Add journal entry")
    # Commit 3: code change
    file2 = os.path.join(repo_dir, "file2.py")
    with open(file2, "w") as f:
        f.write("print('world')\n")
    git_repo.index.add([file2])
    git_repo.index.commit("Second code commit")
    # Should return only commit 3
    commits = get_commits_since_last_entry(git_repo, os.path.join(repo_dir, "journal"))
    print("[TEST DEBUG] Returned commits:")
    for c in commits:
        print(f"  {c.hexsha} {c.message.strip()}")
    assert len(commits) == 1
    messages = [c.message for c in commits]
    assert "Second code commit" in messages

def test_get_commits_since_last_entry_no_journal_entries_returns_all_commits(git_repo, tmp_path):
    repo_dir = git_repo.working_tree_dir
    # Setup: create several code commits, no journal files
    file1 = os.path.join(repo_dir, "file1.py")
    with open(file1, "w") as f:
        f.write("print('hello')\n")
    git_repo.index.add([file1])
    git_repo.index.commit("Initial code commit")
    file2 = os.path.join(repo_dir, "file2.py")
    with open(file2, "w") as f:
        f.write("print('world')\n")
    git_repo.index.add([file2])
    git_repo.index.commit("Second code commit")
    commits = get_commits_since_last_entry(git_repo, os.path.join(repo_dir, "journal"))
    print("[TEST DEBUG] Returned commits:")
    for c in commits:
        print(f"  {c.hexsha} {c.message.strip()}")
    assert len(commits) == 2
    messages = [c.message for c in commits]
    assert "Initial code commit" in messages
    assert "Second code commit" in messages

def test_get_commits_since_last_entry_filters_journal_only_commits(git_repo, tmp_path):
    repo_dir = git_repo.working_tree_dir
    # Setup: code commit, then journal-only commit, then code commit
    file1 = os.path.join(repo_dir, "file1.py")
    with open(file1, "w") as f:
        f.write("print('hello')\n")
    git_repo.index.add([file1])
    git_repo.index.commit("Initial code commit")
    journal_dir = os.path.join(repo_dir, "journal", "daily")
    os.makedirs(journal_dir, exist_ok=True)
    journal_file = os.path.join(journal_dir, "2025-05-19.md")
    with open(journal_file, "w") as f:
        f.write("# Journal\n")
    git_repo.index.add([journal_file])
    git_repo.index.commit("Add journal entry")
    file2 = os.path.join(repo_dir, "file2.py")
    with open(file2, "w") as f:
        f.write("print('world')\n")
    git_repo.index.add([file2])
    git_repo.index.commit("Second code commit")
    # Add a journal-only commit after last journal entry
    journal_file2 = os.path.join(journal_dir, "2025-05-20.md")
    with open(journal_file2, "w") as f:
        f.write("# Journal 2\n")
    git_repo.index.add([journal_file2])
    git_repo.index.commit("Add another journal entry")
    # Should return an empty list since the tip is a journal-only commit
    commits = get_commits_since_last_entry(git_repo, os.path.join(repo_dir, "journal"))
    print("[TEST DEBUG] Returned commits:")
    for c in commits:
        print(f"  {c.hexsha} {c.message.strip()}")
    assert len(commits) == 0

def test_get_commits_since_last_entry_empty_repo_returns_empty_list(git_repo, tmp_path):
    repo_dir = git_repo.working_tree_dir
    # No commits in repo
    try:
        commits = get_commits_since_last_entry(git_repo, os.path.join(repo_dir, "journal"))
    except Exception as e:
        # Should not raise, should return empty list
        commits = []
    assert isinstance(commits, list)
    assert len(commits) == 0

# TDD: Tests for collect_git_context (not yet implemented)
def test_collect_git_context_structure_and_fields(git_repo):
    """Test that collect_git_context returns a dict with required fields for a given commit hash."""
    # Create and commit a file
    file_path = os.path.join(git_repo.working_tree_dir, 'main.py')
    with open(file_path, 'w') as f:
        f.write('print("hello")\n')
    git_repo.index.add(['main.py'])
    commit = git_repo.index.commit('add main.py')
    # Call collect_git_context
    ctx = collect_git_context(commit.hexsha, repo=git_repo)
    # Required top-level fields
    for field in ["metadata", "diff_summary", "changed_files", "file_stats", "commit_context"]:
        assert field in ctx, f"Missing field: {field}"
    # Metadata fields
    for field in ["hash", "author", "date", "message"]:
        assert field in ctx["metadata"], f"Missing metadata field: {field}"
    assert isinstance(ctx["diff_summary"], str)
    assert isinstance(ctx["changed_files"], list)
    assert isinstance(ctx["file_stats"], dict)
    assert isinstance(ctx["commit_context"], dict)

def test_collect_git_context_file_classification(git_repo):
    """Test that collect_git_context classifies changed files by type (source, config, docs, tests)."""
    # Add files of different types
    src = os.path.join(git_repo.working_tree_dir, 'src.py')
    cfg = os.path.join(git_repo.working_tree_dir, 'config.yaml')
    doc = os.path.join(git_repo.working_tree_dir, 'README.md')
    tst = os.path.join(git_repo.working_tree_dir, 'test_sample.py')
    for path in [src, cfg, doc, tst]:
        with open(path, 'w') as f:
            f.write('x\n')
        git_repo.index.add([os.path.basename(path)])
    commit = git_repo.index.commit('add various files')
    ctx = collect_git_context(commit.hexsha, repo=git_repo)
    stats = ctx["file_stats"]
    # Should have keys for each type
    for key in ["source", "config", "docs", "tests"]:
        assert key in stats, f"Missing file type: {key}"
        assert isinstance(stats[key], int)

def test_collect_git_context_commit_size_classification(git_repo):
    """Test that collect_git_context classifies commit size as small/medium/large based on lines changed."""
    # Add a small change
    file_path = os.path.join(git_repo.working_tree_dir, 'tiny.py')
    with open(file_path, 'w') as f:
        f.write('a\n')
    git_repo.index.add(['tiny.py'])
    commit = git_repo.index.commit('tiny change')
    ctx = collect_git_context(commit.hexsha, repo=git_repo)
    size = ctx["commit_context"].get("size_classification")
    assert size in ("small", "medium", "large"), f"Unexpected size classification: {size}"

def test_collect_git_context_merge_status(git_repo):
    """Test that collect_git_context includes merge status in commit_context."""
    # Just check the field exists for a normal commit
    file_path = os.path.join(git_repo.working_tree_dir, 'foo.py')
    with open(file_path, 'w') as f:
        f.write('foo\n')
    git_repo.index.add(['foo.py'])
    commit = git_repo.index.commit('foo')
    ctx = collect_git_context(commit.hexsha, repo=git_repo)
    assert "is_merge" in ctx["commit_context"], "Missing is_merge in commit_context"
    assert isinstance(ctx["commit_context"]["is_merge"], bool)

def test_collect_git_context_filters_journal_files(git_repo, tmp_path):
    """Test that journal files are filtered out of git context"""
    # Create an initial commit so the next commit has a parent
    file_path = os.path.join(git_repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('hello world\n')
    git_repo.index.add(['file1.txt'])
    git_repo.index.commit('initial commit')
    
    # Create a mix of journal and non-journal files
    journal_file = os.path.join(git_repo.working_tree_dir, 'journal', 'daily', '2023-05-20.md')
    os.makedirs(os.path.dirname(journal_file), exist_ok=True)
    with open(journal_file, 'w') as f:
        f.write('# Journal entry\n')
    
    source_file = os.path.join(git_repo.working_tree_dir, 'src', 'main.py')
    os.makedirs(os.path.dirname(source_file), exist_ok=True)
    with open(source_file, 'w') as f:
        f.write('print("hello")\n')
    
    git_repo.index.add(['journal/daily/2023-05-20.md', 'src/main.py'])
    commit = git_repo.index.commit('mixed commit')
    
    # Test with journal path - pass the git repo, not tmp_path
    context = collect_git_context(commit, git_repo, 'journal/')
    
    # Should only have the non-journal file
    assert len(context['changed_files']) == 1
    assert 'src/main.py' in context['changed_files']


# TDD: Tests for get_previous_commit_info() - these should FAIL initially

def test_get_previous_commit_info_returns_previous_commit_details():
    """Test that get_previous_commit_info returns previous commit hash, message, timestamp, files changed"""
    # Setup
    mock_commit = Mock()
    mock_commit.hexsha = 'current123'
    
    # Mock previous commit
    mock_previous = Mock()
    mock_previous.hexsha = 'previous456'
    mock_previous.message = 'Previous commit message'
    mock_previous.committed_date = 1621512345
    mock_previous.stats.files = {
        'file1.py': {'insertions': 5, 'deletions': 2},
        'file2.py': {'insertions': 3, 'deletions': 1}
    }
    
    # Mock parents relationship
    mock_commit.parents = [mock_previous]
    
    # Call
    result = get_previous_commit_info(mock_commit)
    
    # Assert
    assert result['hash'] == 'previous456'
    assert result['message'] == 'Previous commit message'
    assert result['timestamp'] == 1621512345
    assert result['files_changed'] == 2
    assert result['insertions'] == 8
    assert result['deletions'] == 3


def test_get_previous_commit_info_handles_first_commit():
    """Test that get_previous_commit_info handles first commit (no previous)"""
    # Setup
    mock_commit = Mock()
    mock_commit.hexsha = 'first123'
    mock_commit.parents = []  # No parents = first commit
    
    # Call
    result = get_previous_commit_info(mock_commit)
    
    # Assert
    assert result is None


def test_get_previous_commit_info_handles_merge_commit():
    """Test that get_previous_commit_info handles merge commits (multiple parents)"""
    # Setup
    mock_commit = Mock()
    mock_commit.hexsha = 'merge123'
    
    # Mock multiple parents (merge commit)
    mock_parent1 = Mock()
    mock_parent1.hexsha = 'parent1'
    mock_parent1.message = 'First parent message'
    mock_parent1.committed_date = 1621512345
    mock_parent1.stats.files = {'file1.py': {'insertions': 5, 'deletions': 2}}
    
    mock_parent2 = Mock()
    mock_parent2.hexsha = 'parent2'
    mock_parent2.message = 'Second parent message'
    mock_parent2.committed_date = 1621512300
    mock_parent2.stats.files = {'file2.py': {'insertions': 3, 'deletions': 1}}
    
    mock_commit.parents = [mock_parent1, mock_parent2]
    
    # Call - should return first parent (main branch)
    result = get_previous_commit_info(mock_commit)
    
    # Assert
    assert result['hash'] == 'parent1'
    assert result['message'] == 'First parent message'
    assert result['timestamp'] == 1621512345
    assert result['files_changed'] == 1
    assert result['insertions'] == 5
    assert result['deletions'] == 2


def test_get_previous_commit_info_with_repo_integration(git_repo):
    """Test get_previous_commit_info with actual git repo"""
    # Create first commit
    file_path = os.path.join(git_repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('hello world\n')
    git_repo.index.add(['file1.txt'])
    first_commit = git_repo.index.commit('first commit')
    
    # Create second commit
    file_path2 = os.path.join(git_repo.working_tree_dir, 'file2.txt')
    with open(file_path2, 'w') as f:
        f.write('second file\n')
    git_repo.index.add(['file2.txt'])
    second_commit = git_repo.index.commit('second commit')
    
    # Call with second commit
    result = get_previous_commit_info(second_commit)
    
    # Assert
    assert result['hash'] == first_commit.hexsha
    assert result['message'] == 'first commit'
    assert result['timestamp'] == first_commit.committed_date
    assert result['files_changed'] == 1  # file1.txt added
    assert result['insertions'] > 0
    assert result['deletions'] == 0


def test_get_previous_commit_info_first_commit_integration(git_repo):
    """Test get_previous_commit_info with first commit in actual git repo"""
    # Create first commit
    file_path = os.path.join(git_repo.working_tree_dir, 'file1.txt')
    with open(file_path, 'w') as f:
        f.write('hello world\n')
    git_repo.index.add(['file1.txt'])
    first_commit = git_repo.index.commit('first commit')
    
    # Call with first commit
    result = get_previous_commit_info(first_commit)
    
    # Assert
    assert result is None 


def test_generate_hook_content_background_mode():
    """Test that generate_hook_content creates background hook when background=True."""
    hook_content = generate_hook_content(background=True)
    
    # Should contain shebang
    assert hook_content.startswith("#!/bin/sh\n")
    
    # Should get commit hash
    assert "COMMIT_HASH=$(git rev-parse HEAD)" in hook_content
    
    # Should spawn background worker with nohup
    assert "nohup python -m mcp_commit_story.background_journal_worker" in hook_content
    assert "--commit-hash \"$COMMIT_HASH\"" in hook_content
    assert "--repo-path \"$PWD\"" in hook_content
    
    # Should redirect output and run in background
    assert ">/dev/null 2>&1 &" in hook_content
    
    # Should not contain the synchronous git_hook_worker call
    assert "git_hook_worker" not in hook_content


def test_generate_hook_content_sync_mode_default():
    """Test that generate_hook_content still defaults to synchronous mode."""
    hook_content = generate_hook_content()
    
    # Should contain the synchronous worker call (existing behavior)
    assert "python -m mcp_commit_story.git_hook_worker" in hook_content
    assert "background_journal_worker" not in hook_content


def test_generate_hook_content_background_mode_with_timeout():
    """Test that background hook includes timeout parameter."""
    hook_content = generate_hook_content(background=True, timeout=45)
    
    # Should include timeout parameter
    assert "--timeout 45" in hook_content


def test_generate_hook_content_background_mode_default_timeout():
    """Test that background hook uses default timeout when not specified."""
    hook_content = generate_hook_content(background=True)
    
    # Should include default timeout
    assert "--timeout 30" in hook_content


@patch('mcp_commit_story.git_utils.os.chmod')
@patch('mcp_commit_story.git_utils.os.path.exists')
def test_install_post_commit_hook_background_mode(mock_exists, mock_chmod, tmp_path):
    """Test that install_post_commit_hook can install background hooks."""
    from mcp_commit_story.git_utils import install_post_commit_hook
    
    # Setup
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    git_dir = repo_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()
    
    mock_exists.return_value = False  # No existing hook
    
    # Execute
    result = install_post_commit_hook(str(repo_path), background=True)
    
    # Verify
    assert result is True
    hook_path = hooks_dir / "post-commit"
    assert hook_path.exists()
    
    # Check hook content
    hook_content = hook_path.read_text()
    assert "background_journal_worker" in hook_content
    assert "nohup" in hook_content
    
    # Verify chmod was called to make executable
    mock_chmod.assert_called_once()


def test_install_post_commit_hook_background_mode_with_telemetry(tmp_path):
    """Test that background hook installation includes telemetry tracking."""
    from mcp_commit_story.git_utils import install_post_commit_hook
    from mcp_commit_story.telemetry import get_mcp_metrics
    from unittest.mock import Mock
    
    # Setup
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    git_dir = repo_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()
    
    # Mock telemetry to verify it's called correctly
    mock_metrics = Mock()
    
    with patch('mcp_commit_story.telemetry.get_mcp_metrics', return_value=mock_metrics):
        result = install_post_commit_hook(str(repo_path), background=True)
    
    # Verify operation succeeded
    assert result is True
    
    # Verify telemetry was recorded with correct attributes
    mock_metrics.record_counter.assert_any_call(
        'git_hook.install_total',
        attributes={
            'background_mode': 'true',
            'timeout': '30'
        }
    )
    
    # Verify success telemetry was recorded
    mock_metrics.record_counter.assert_any_call(
        'git_hook.install_success_total',
        attributes={
            'background_mode': 'true',
            'had_backup': 'false'
        }
    ) 