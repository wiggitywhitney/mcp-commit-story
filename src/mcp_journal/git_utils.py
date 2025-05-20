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


def is_git_repo(path: Optional[str] = None) -> bool:
    """
    Check if the specified path is a Git repository.
    
    Args:
        path: Path to check, defaults to current directory
        
    Returns:
        True if the path is a Git repository, False otherwise
    """
    if path is None:
        path = os.getcwd()
    
    # Check for .git directory
    git_dir = os.path.join(path, '.git')
    return os.path.exists(git_dir)


def get_repo(path: Optional[str] = None) -> 'git.Repo':
    """
    Get a Git repository object for the specified path.
    
    Args:
        path: Path to repository, defaults to current directory
        
    Returns:
        Git repository object
        
    Raises:
        git.InvalidGitRepositoryError: If the path is not a Git repository
        ImportError: If GitPython is not installed
    """
    if not GIT_AVAILABLE:
        raise ImportError("GitPython not installed. Run: pip install gitpython")
    
    if path is None:
        path = os.getcwd()
    
    return git.Repo(path)


def get_current_commit(repo: Optional['git.Repo'] = None) -> 'git.Commit':
    """
    Get the current commit (HEAD) from a repository.
    
    Args:
        repo: Git repository object, if None will be obtained from current directory
        
    Returns:
        Current commit object
        
    Raises:
        git.InvalidGitRepositoryError: If the repository is invalid
    """
    if repo is None:
        repo = get_repo()
    
    return repo.head.commit


def is_journal_only_commit(commit: 'git.Commit', journal_path: str) -> bool:
    """
    Check if a commit only modifies journal files.
    
    This is used to prevent recursion when generating journal entries
    for commits that only modify journal files.
    
    Args:
        commit: Git commit object to check
        journal_path: Base path for journal files
        
    Returns:
        True if all modified files are in the journal directory
    """
    try:
        changed_files = commit.diff()
    except (AttributeError, TypeError):
        try:
            changed_files = commit.diff(commit.parents[0] if commit.parents else None)
        except (AttributeError, TypeError):
            raise ValueError("Unable to get diff for commit")
    file_paths = [file.a_path for file in changed_files]
    result = all(f.startswith(journal_path) for f in file_paths) if file_paths else False
    print(f"[DEBUG is_journal_only_commit] Commit {getattr(commit, 'hexsha', '?')} files: {file_paths} result: {result}")
    return result


def get_commit_details(commit: 'git.Commit') -> Dict[str, Any]:
    """
    Extract relevant details from a commit.
    
    Args:
        commit: Git commit object
        
    Returns:
        Dictionary with commit details:
            - hash: Commit hash
            - message: Commit message
            - timestamp: Commit timestamp (Unix timestamp)
            - datetime: Commit datetime (formatted string)
            - author: Author name and email
            - stats: File statistics (insertions, deletions, files changed)
    """
    # Convert Unix timestamp to datetime
    dt = datetime.fromtimestamp(commit.committed_date)
    
    # Get file statistics
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


def is_blob_binary(blob):
    """Heuristic to detect if a git.Blob is binary: checks for null bytes in the first 1024 bytes.
    This is 'good enough' for journal/summary purposes in production, but may not work for new files in temp repos due to GitPython limitations, so is not tested in unit tests.
    """
    if blob is None:
        return False
    try:
        data = blob.data_stream.read(1024)
        return b'\0' in data
    except Exception:
        return False


def get_commit_diff_summary(commit):
    """
    Generate a simplified summary of file changes in a commit.
    Good practice: Prefer diff.change_type if set, fallback to blob presence/content comparison.
    Handles added, deleted, modified, renamed, and binary files. Logs ambiguous cases.
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
        # 1. Prefer change_type if set
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
            # Compare blob content for modification
            if is_blob_binary(diff.a_blob) or is_blob_binary(diff.b_blob):
                summary_lines.append(f"{fname}: binary file changed")
            elif diff.a_blob and diff.b_blob and diff.a_blob.hexsha != diff.b_blob.hexsha:
                summary_lines.append(f"{fname}: modified")
            else:
                summary_lines.append(f"{fname}: changed (no content diff)")
        elif change_type == 'R':
            summary_lines.append(f"{diff.a_path} → {diff.b_path}: renamed")
        # 2. Fallback: Use parent/commit tree to distinguish added/deleted/modified
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
                # Final tweak: ensure binary detection for new files
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
                # Ambiguous case
                print(f"[WARN] Ambiguous diff for {fname}: {diff}")
                summary_lines.append(f"{fname}: changed (ambiguous)")
    return "\n".join(summary_lines)


def backup_existing_hook(hook_path: str) -> Optional[str]:
    """
    Backup an existing Git hook file by copying it to a timestamped backup file.
    Preserves file permissions. Returns the backup path, or None if no backup was needed.
    Raises PermissionError if the filesystem is read-only.
    """
    if not os.path.exists(hook_path):
        return None
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    backup_path = f"{hook_path}.backup.{timestamp}"
    # Copy file and preserve permissions
    shutil.copy2(hook_path, backup_path)
    return backup_path


def install_post_commit_hook(repo_path: str = None) -> None:
    """
    Install the post-commit hook in the given repo's .git/hooks directory.
    - If a hook exists, back it up using backup_existing_hook.
    - Write the new hook content (shebang, commands).
    - Set the hook file as executable.
    - Handle errors (missing repo, permissions, etc.).
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
    # Backup existing hook if present
    if os.path.exists(hook_path):
        backup_existing_hook(hook_path)
    # Write new hook content
    hook_content = "#!/bin/sh\necho 'Post-commit hook triggered'\n"
    with open(hook_path, 'w') as f:
        f.write(hook_content)
    # Set executable permissions
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def get_commits_since_last_entry(repo, journal_path: str):
    """
    Find the most recent commit that modified the journal, get all commits strictly after that point,
    filter out commits that only modified the journal, and return the list of commits that need entries.
    Args:
        repo: GitPython Repo object
        journal_path: Path to the journal directory (relative or absolute)
    Returns:
        List of git.Commit objects that need journal entries, in chronological order
    """
    journal_rel = os.path.relpath(journal_path, repo.working_tree_dir)
    commits = list(repo.iter_commits('HEAD'))  # Newest to oldest
    # If the tip is a journal-only commit, nothing to do
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
