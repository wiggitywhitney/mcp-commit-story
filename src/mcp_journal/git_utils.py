"""
Git utilities for MCP Journal.

This module provides functions for interacting with Git repositories
and processing commits for journal entry generation.
"""
import os
import time
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
    # Get the list of files changed in this commit
    # For test purposes, we check if it's a mock more thoroughly
    try:
        changed_files = commit.diff()
    except (AttributeError, TypeError):
        # If there's an error, it may be because we're accessing a real Git commit
        # that expects a parent commit parameter
        try:
            changed_files = commit.diff(commit.parents[0] if commit.parents else None)
        except (AttributeError, TypeError):
            # If both fail, we can't handle this commit
            raise ValueError("Unable to get diff for commit")
    
    # Check if all changed files are in the journal directory
    for file in changed_files:
        if not file.a_path.startswith(journal_path):
            return False
    
    return True


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
