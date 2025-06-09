"""
Git utilities for MCP Journal.

This module provides functions for interacting with Git repositories
and processing commits for journal entry generation.
"""
import os
import time
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Import git library conditionally to handle environments where it might not be available
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

# SHA for the empty tree object in Git (used for initial commit diffs)
NULL_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

from mcp_commit_story.context_types import GitContext


def is_git_repo(path: Optional[str] = None) -> bool:
    """
    Determine if the specified path is a Git repository.

    Args:
        path (str, optional): Path to check. Defaults to current directory.

    Returns:
        bool: True if the path is a Git repository, False otherwise.
    """
    if path is None:
        path = os.getcwd()
    git_dir = os.path.join(path, '.git')
    return os.path.exists(git_dir)


def get_repo(path: Optional[str] = None) -> 'git.Repo':
    """
    Get a GitPython Repo object for the specified path.

    Args:
        path (str, optional): Path to repository. Defaults to current directory.

    Returns:
        git.Repo: Git repository object.

    Raises:
        git.InvalidGitRepositoryError: If the path is not a Git repository.
        ImportError: If GitPython is not installed.
    """
    if not GIT_AVAILABLE:
        raise ImportError("GitPython not installed. Run: pip install gitpython")
    if path is None:
        path = os.getcwd()
    return git.Repo(path)


def get_current_commit(repo: Optional['git.Repo'] = None) -> 'git.Commit':
    """
    Get the current (HEAD) commit from a repository.

    Args:
        repo (git.Repo, optional): Git repository object. If None, uses current directory.

    Returns:
        git.Commit: Current commit object.

    Raises:
        git.InvalidGitRepositoryError: If the repository is invalid.
    """
    if repo is None:
        repo = get_repo()
    return repo.head.commit


def is_journal_only_commit(commit: 'git.Commit', journal_path: str) -> bool:
    """
    Determine if a commit only modifies files in the journal directory.

    Args:
        commit (git.Commit): Commit to check.
        journal_path (str): Base path for journal files (relative to repo root).

    Returns:
        bool: True if all changed files are in the journal directory, False otherwise.
    """
    try:
        changed_files = commit.diff()
    except (AttributeError, TypeError):
        try:
            changed_files = commit.diff(commit.parents[0] if commit.parents else None)
        except (AttributeError, TypeError):
            raise ValueError("Unable to get diff for commit")
    file_paths = [file.a_path for file in changed_files]
    return all(f.startswith(journal_path) for f in file_paths) if file_paths else False


def get_commit_details(commit: 'git.Commit') -> Dict[str, Any]:
    """
    Extract relevant details from a commit for reporting or journal entry generation.

    Args:
        commit (git.Commit): Commit to extract details from.

    Returns:
        dict: Dictionary with commit details (hash, message, timestamp, datetime, author, stats).
    """
    dt = datetime.fromtimestamp(commit.committed_date)
    stats = {
        'files': len(commit.stats.files),
        'insertions': sum(file_stats['insertions'] for file_stats in commit.stats.files.values()),
        'deletions': sum(file_stats['deletions'] for file_stats in commit.stats.files.values())
    }
    return {
        'hash': commit.hexsha,
        'message': commit.message,
        'timestamp': commit.committed_date,
        'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
        'author': f"{commit.author.name} <{commit.author.email}>",
        'stats': stats
    }


def is_blob_binary(blob) -> bool:
    """
    Heuristically determine if a git.Blob is binary.

    Args:
        blob (git.Blob): Blob object to check.

    Returns:
        bool: True if the blob is likely binary, False otherwise.

    Notes:
        Checks for null bytes in the first 1024 bytes. May not work for new files in temp repos due to GitPython limitations.
    """
    if blob is None:
        return False
    try:
        data = blob.data_stream.read(1024)
        return b'\0' in data
    except Exception:
        return False


def get_commit_diff_summary(commit) -> str:
    """
    Generate a human-readable summary of file changes in a commit.

    Args:
        commit (git.Commit): Commit to summarize.

    Returns:
        str: Summary of file changes (added, deleted, modified, renamed, binary, etc.).

    Notes:
        - Prefers diff.change_type if available, falls back to blob/content comparison.
        - Handles ambiguous cases and logs warnings.
    """
    parent = commit.parents[0] if commit.parents else None
    diffs = commit.diff(parent, create_patch=True)
    if not diffs:
        return "No changes in this commit."
    parent_tree = parent.tree if parent else None
    commit_tree = commit.tree
    summary_lines = []
    for diff in diffs:
        fname = diff.b_path or diff.a_path
        change_type = getattr(diff, 'change_type', None)
        if change_type == 'A':
            if is_blob_binary(diff.b_blob):
                summary_lines.append(f"{fname}: binary file added")
            else:
                summary_lines.append(f"{fname}: added")
        elif change_type == 'D':
            if is_blob_binary(diff.a_blob):
                summary_lines.append(f"{fname}: binary file deleted")
            else:
                summary_lines.append(f"{fname}: deleted")
        elif change_type == 'M':
            if is_blob_binary(diff.a_blob) or is_blob_binary(diff.b_blob):
                summary_lines.append(f"{fname}: binary file changed")
            elif diff.a_blob and diff.b_blob and diff.a_blob.hexsha != diff.b_blob.hexsha:
                summary_lines.append(f"{fname}: modified")
            else:
                summary_lines.append(f"{fname}: changed (no content diff)")
        elif change_type == 'R':
            summary_lines.append(f"{diff.a_path} → {diff.b_path}: renamed")
        else:
            in_parent = False
            in_commit = False
            if parent_tree:
                try:
                    parent_tree[fname]
                    in_parent = True
                except KeyError:
                    in_parent = False
            try:
                commit_tree[fname]
                in_commit = True
            except KeyError:
                in_commit = False
            if in_parent and not in_commit:
                if is_blob_binary(diff.a_blob):
                    summary_lines.append(f"{fname}: binary file deleted (fallback)")
                else:
                    summary_lines.append(f"{fname}: deleted (fallback)")
            elif in_commit and not in_parent:
                if diff.b_blob and is_blob_binary(diff.b_blob):
                    summary_lines.append(f"{fname}: binary file added (fallback)")
                else:
                    summary_lines.append(f"{fname}: added (fallback)")
            elif in_parent and in_commit:
                if is_blob_binary(diff.a_blob) or is_blob_binary(diff.b_blob):
                    summary_lines.append(f"{fname}: binary file modified (fallback)")
                elif diff.a_blob and diff.b_blob and diff.a_blob.hexsha != diff.b_blob.hexsha:
                    summary_lines.append(f"{fname}: modified (fallback)")
                else:
                    summary_lines.append(f"{fname}: changed (fallback, no content diff)")
            else:
                summary_lines.append(f"{fname}: changed (ambiguous)")
    return "\n".join(summary_lines)


def generate_hook_content(command: str = None) -> str:
    """
    Generate the content for a portable Git post-commit hook script.

    Args:
        command (str, optional): Custom command to run in the hook. 
                               If None, uses enhanced Python worker for daily summary triggering.
                               If provided, uses legacy behavior for backwards compatibility.

    Returns:
        str: The complete hook script content as a string.

    Design:
        - Uses '#!/bin/sh' for maximum portability.
        - Default behavior: Calls Python worker for journal entries + daily summary triggering.
        - Custom command: Uses legacy behavior for backwards compatibility.
        - Runs the specified command, redirecting all output to /dev/null.
        - Appends '|| true' to ensure the hook never blocks a commit, even on error.
        - Keeps the script lightweight and non-intrusive, as recommended for Git hooks.
    """
    if command is not None:
        # Legacy behavior for backwards compatibility
        return f"#!/bin/sh\n{command} >/dev/null 2>&1 || true\n"
    else:
        # Enhanced behavior with Python worker for daily summary triggering
        return f'#!/bin/sh\npython -m mcp_commit_story.git_hook_worker "$PWD" >/dev/null 2>&1 || true\n'


def backup_existing_hook(hook_path: str) -> Optional[str]:
    """
    Backup an existing Git hook file by copying it to a timestamped backup file.

    Args:
        hook_path (str): Path to the hook file.

    Returns:
        str or None: Path to the backup file, or None if no backup was needed.

    Raises:
        PermissionError: If the filesystem is read-only.
    """
    if not os.path.exists(hook_path):
        return None
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    backup_path = f"{hook_path}.backup.{timestamp}"
    shutil.copy2(hook_path, backup_path)
    return backup_path


def install_post_commit_hook(repo_path: str = None) -> Optional[str]:
    """
    Install or replace the post-commit hook in the given repo's .git/hooks directory.

    Args:
        repo_path (str, optional): Path to the repo. Defaults to current directory.

    Returns:
        str or None: Path to the backup file if a backup was made, otherwise None.

    Raises:
        FileNotFoundError: If the hooks directory does not exist.
        PermissionError: If the hooks directory is not writable.
    """
    import stat
    if repo_path is None:
        repo_path = os.getcwd()
    hooks_dir = os.path.join(repo_path, '.git', 'hooks')
    if not os.path.isdir(hooks_dir):
        raise FileNotFoundError(f"Hooks directory not found: {hooks_dir}")
    if not os.access(hooks_dir, os.W_OK):
        raise PermissionError(f"Hooks directory is not writable: {hooks_dir}")
    hook_path = os.path.join(hooks_dir, 'post-commit')
    backup_path = None
    if os.path.exists(hook_path):
        backup_path = backup_existing_hook(hook_path)
    hook_content = generate_hook_content()
    with open(hook_path, 'w') as f:
        f.write(hook_content)
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return backup_path


def get_commits_since_last_entry(repo, journal_path: str) -> list:
    """
    Find all code commits that need journal entries since the last journal-modifying commit.

    Args:
        repo (git.Repo): GitPython Repo object.
        journal_path (str): Path to the journal directory (relative or absolute).

    Returns:
        list: List of git.Commit objects that need journal entries, in chronological order (oldest to newest).

    Notes:
        - If the tip is a journal-only commit, returns an empty list (prevents duplicate entries).
        - Filters out commits that only modify journal files.
    """
    journal_rel = os.path.relpath(journal_path, repo.working_tree_dir)
    commits = list(repo.iter_commits('HEAD'))  # Newest to oldest
    if commits and is_journal_only_commit(commits[0], journal_rel):
        return []
    last_journal_commit_idx = None
    for idx, commit in enumerate(commits):
        for file in commit.stats.files:
            if file.startswith(journal_rel):
                last_journal_commit_idx = idx
                break
        if last_journal_commit_idx is not None:
            break
    if last_journal_commit_idx is not None:
        candidate_commits = commits[:last_journal_commit_idx]
    else:
        candidate_commits = commits
    candidate_commits = list(reversed(candidate_commits))
    result = []
    for commit in candidate_commits:
        if not is_journal_only_commit(commit, journal_rel):
            result.append(commit)
    return result


def classify_file_type(filename):
    """Classify file as source, config, docs, or tests based on extension and name."""
    ext = os.path.splitext(filename)[1].lower()
    name = os.path.basename(filename).lower()
    if name.startswith('test_') or name.endswith('_test.py') or name.endswith('_test.js') or name.endswith('_test.ts') or name.startswith('test'):
        return 'tests'
    if ext in {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.rb', '.go', '.rs'}:
        return 'source'
    if ext in {'.yaml', '.yml', '.json', '.ini', '.cfg', '.env'} or 'config' in name:
        return 'config'
    if ext in {'.md', '.rst', '.txt'} or 'readme' in name or 'docs' in name:
        return 'docs'
    return 'source'  # Default to source if unknown


def classify_commit_size(insertions, deletions):
    """Classify commit size as small, medium, or large based on total lines changed."""
    total = insertions + deletions
    if total < 10:
        return 'small'
    elif total < 50:
        return 'medium'
    else:
        return 'large'
