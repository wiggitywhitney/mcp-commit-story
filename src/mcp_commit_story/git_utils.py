"""
Git utilities for MCP Journal.

This module provides functions for interacting with Git repositories
and processing commits for journal entry generation.
"""
import os
import time
import shutil
import re
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
from mcp_commit_story.telemetry import trace_git_operation


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


@trace_git_operation("get_previous_commit_info")
def get_previous_commit_info(commit: 'git.Commit') -> Optional[Dict[str, Any]]:
    """
    Extract relevant details from the previous commit (first parent) for context filtering.

    Args:
        commit (git.Commit): Commit to get previous commit info for.

    Returns:
        dict or None: Dictionary with previous commit details (hash, message, timestamp, files_changed, 
                     insertions, deletions) or None if this is the first commit.
    """
    # Handle first commit (no parents)
    if not commit.parents:
        return None
    
    # Get first parent (main branch for merge commits)
    previous_commit = commit.parents[0]
    
    # Calculate stats
    stats = {
        'files': len(previous_commit.stats.files),
        'insertions': sum(file_stats['insertions'] for file_stats in previous_commit.stats.files.values()),
        'deletions': sum(file_stats['deletions'] for file_stats in previous_commit.stats.files.values())
    }
    
    return {
        'hash': previous_commit.hexsha,
        'message': previous_commit.message,
        'timestamp': previous_commit.committed_date,
        'files_changed': stats['files'],
        'insertions': stats['insertions'],
        'deletions': stats['deletions']
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


def generate_hook_content(command: str = None, background: bool = False, timeout: int = 30) -> str:
    """
    Generate the content for a portable Git post-commit hook script.

    Args:
        command (str, optional): Custom command to run in the hook. 
                               If None, uses enhanced Python worker for daily summary triggering.
                               If provided, uses legacy behavior for backwards compatibility.
        background (bool, optional): If True, spawn journal generation in background 
                                   to avoid blocking git commits. Defaults to False.
        timeout (int, optional): Timeout in seconds for background worker. Defaults to 30.

    Returns:
        str: The complete hook script content as a string.

    Design:
        - Uses '#!/bin/sh' for maximum portability.
        - Default behavior: Calls Python worker for journal entries + daily summary triggering.
        - Background mode: Spawns background worker that doesn't block git operations.
        - Custom command: Uses legacy behavior for backwards compatibility.
        - Runs the specified command, redirecting all output to /dev/null.
        - Appends '|| true' to ensure the hook never blocks a commit, even on error.
        - Keeps the script lightweight and non-intrusive, as recommended for Git hooks.
    """
    if command is not None:
        # Legacy behavior for backwards compatibility
        return f"#!/bin/sh\n{command} >/dev/null 2>&1 || true\n"
    elif background:
        # Background mode - spawn detached background worker
        return f'''#!/bin/sh
# Get the current commit hash
COMMIT_HASH=$(git rev-parse HEAD)

# Spawn background journal worker (detached from git process)
nohup python -m mcp_commit_story.background_journal_worker \\
    --commit-hash "$COMMIT_HASH" \\
    --repo-path "$PWD" \\
    --timeout {timeout} \\
    >/dev/null 2>&1 &
'''
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


def install_post_commit_hook(repo_path: str = None, background: bool = False, timeout: int = 30) -> bool:
    """
    Install or replace the post-commit hook in the given repo's .git/hooks directory.

    Args:
        repo_path (str, optional): Path to the repo. Defaults to current directory.
        background (bool, optional): If True, install hook that runs journal generation 
                                   in background to avoid blocking git commits. Defaults to False.
        timeout (int, optional): Timeout in seconds for background worker. Defaults to 30.

    Returns:
        bool: True if hook was installed successfully, False otherwise.

    Raises:
        FileNotFoundError: If the hooks directory does not exist.
        PermissionError: If the hooks directory is not writable.
    """
    import stat
    from .telemetry import get_mcp_metrics
    
    if repo_path is None:
        repo_path = os.getcwd()
    
    # Record telemetry
    metrics = get_mcp_metrics()
    if metrics:
        metrics.record_counter(
            'git_hook.install_total',
            attributes={
                'background_mode': str(background).lower(),
                'timeout': str(timeout)
            }
        )
    
    hooks_dir = os.path.join(repo_path, '.git', 'hooks')
    if not os.path.isdir(hooks_dir):
        raise FileNotFoundError(f"Hooks directory not found: {hooks_dir}")
    if not os.access(hooks_dir, os.W_OK):
        raise PermissionError(f"Hooks directory is not writable: {hooks_dir}")
    
    hook_path = os.path.join(hooks_dir, 'post-commit')
    backup_path = None
    if os.path.exists(hook_path):
        backup_path = backup_existing_hook(hook_path)
    
    # Generate hook content with background mode support
    hook_content = generate_hook_content(background=background, timeout=timeout)
    
    with open(hook_path, 'w') as f:
        f.write(hook_content)
    
    # Make hook executable
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    # Record success telemetry
    if metrics:
        metrics.record_counter(
            'git_hook.install_success_total',
            attributes={
                'background_mode': str(background).lower(),
                'had_backup': str(backup_path is not None).lower()
            }
        )
    
    return True


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


@trace_git_operation("is_generated_file",
                    performance_thresholds={"duration": 0.1},
                    error_categories=["filesystem", "regex"])
def is_generated_file(file_path: str) -> bool:
    """
    Determine if a file should be excluded from diff analysis as generated/build content.
    
    **Telemetry Integration:**
    This function uses @trace_git_operation decorator to track performance and errors:
    - Performance threshold: 100ms (function should complete quickly)
    - Error categories: ["filesystem", "regex"] for pattern matching issues
    - Automatically tracks execution duration and success/failure status
    
    **Prerequisites:**
    - No external dependencies required
    - Works with any file path string (relative or absolute)
    
    **Technical Context:**
    Generated files are typically not meaningful for code analysis and can add noise
    to diff collection. This function identifies common patterns like build artifacts,
    dependency lock files, and compiled assets that should be filtered out.
    
    **Detection Patterns:**
    - Minified files: `*.min.js`, `*.min.css`
    - Package managers: `package-lock.json`, `yarn.lock`  
    - Python artifacts: `__pycache__/`, `*.pyc`
    - Build directories: `build/`, `dist/`, `node_modules/`
    
    **Complete Example:**
    ```python
    from mcp_commit_story.git_utils import is_generated_file
    
    # Check various file types
    files_to_check = [
        "src/main.py",           # False - source code
        "package-lock.json",     # True - generated lock file
        "dist/bundle.min.js",    # True - minified build output
        "build/assets/style.css", # True - build directory
        "README.md",             # False - documentation
        "__pycache__/module.pyc" # True - Python cache
    ]
    
    for file_path in files_to_check:
        is_generated = is_generated_file(file_path)
        print(f"{file_path}: {'SKIP' if is_generated else 'INCLUDE'}")
    
    # Use in filtering workflows
    source_files = [f for f in all_files if not is_generated_file(f)]
    ```
    
    **Extension Guidelines:**
    To add new patterns, extend the `generated_patterns` list with regex patterns:
    ```python
    # Example: Add pattern for .NET build artifacts
    generated_patterns.append(r'bin/')
    generated_patterns.append(r'obj/')
    ```
    
    Args:
        file_path: File path to analyze (str, can be relative or absolute path)
        
    Returns:
        bool: True if file matches generated file patterns, False for source files
        
    Examples:
        >>> is_generated_file("src/main.py")
        False
        >>> is_generated_file("package-lock.json") 
        True
        >>> is_generated_file("BUILD/output.js")
        True
    """
    generated_patterns = [
        r'\.min\.(js|css)$',
        r'package-lock\.json$',
        r'yarn\.lock$',
        r'__pycache__/',
        r'\.pyc$',
        r'build/',
        r'dist/',
        r'node_modules/'
    ]
    
    # Convert to lowercase for case-insensitive matching
    file_path_lower = file_path.lower()
    
    return any(re.search(pattern, file_path_lower) for pattern in generated_patterns)


@trace_git_operation("get_commit_file_diffs",
                    performance_thresholds={"duration": 3.0},
                    error_categories=["git", "filesystem", "memory"])
def get_commit_file_diffs(
    repo: 'git.Repo', 
    commit: 'git.Commit', 
    max_file_size: int = 10 * 1024, 
    max_total_size: int = 50 * 1024
) -> Dict[str, str]:
    """
    Extract diff content for all files changed in a commit with intelligent size management.
    
    **Telemetry Integration:**
    This function uses @trace_git_operation decorator with comprehensive monitoring:
    - Performance threshold: 3.0s for large repository operations
    - Error categories: ["git", "filesystem", "memory"] for proper error classification
    - Tracks metrics: file counts, diff sizes, truncation events, adaptive sizing decisions
    - Available span attributes: files.processed, results.total_size_bytes, results.has_truncation
    
    **Prerequisites:**
    - GitPython must be installed: `pip install gitpython`
    - Repository must be a valid git repository
    - Commit must exist in the repository
    
    **Adaptive Size Limits:**
    The function automatically adjusts per-file limits based on the total number of changed files:
    - ≤5 files: 10KB per file (optimized for detailed analysis)
    - 6-20 files: 2.5KB per file (balanced detail vs performance)  
    - >20 files: 1KB per file, max 50 files (performance-first with sampling)
    
    **Technical Context:**
    This design prevents memory exhaustion on large commits while maximizing detail 
    for typical development workflows. Binary files and generated files (package-lock.json,
    build artifacts) are automatically filtered to focus on meaningful code changes.
    
    **Complete Example:**
    ```python
    from mcp_commit_story.git_utils import get_commit_file_diffs, get_repo, get_current_commit
    
    # Get repository and current commit
    repo = get_repo("/path/to/repository")
    commit = get_current_commit(repo)
    
    # Extract diffs with default limits
    diffs = get_commit_file_diffs(repo, commit)
    
    # Process results
    for file_path, diff_content in diffs.items():
        if file_path == "__truncated__":
            print("Some diffs were omitted due to size limits")
        elif file_path == "__error__":
            print(f"Error occurred: {diff_content}")
        else:
            print(f"{file_path}: {len(diff_content)} bytes of diff")
    
    # Custom size limits for large repositories
    large_repo_diffs = get_commit_file_diffs(
        repo, commit, 
        max_file_size=5*1024,  # 5KB per file
        max_total_size=25*1024  # 25KB total
    )
    ```
    
    **Error Handling:**
    - Returns {"__error__": "description"} for critical failures
    - Returns {"__truncated__": "message"} when size limits are exceeded
    - Individual file errors are captured as {"file.py": "[Error extracting diff: ...]"}
    
    **Performance Characteristics:**
    - Typical execution: <100ms for commits with <10 files
    - Large commits (>50 files): <500ms due to sampling and limits
    - Memory usage: Bounded by max_total_size parameter
    
    Args:
        repo: GitPython repository object (required, must be valid git repo)
        commit: GitPython commit object (required, must exist in repo)
        max_file_size: Base limit for individual file diffs in bytes (adaptive logic overrides this)
        max_total_size: Hard limit for total diff content in bytes (default: 50KB)
        
    Returns:
        Dict[str, str]: File path to diff content mapping. Special keys:
        - "__error__": Indicates a critical failure with error message
        - "__truncated__": Indicates some content was omitted due to size limits
        
    Raises:
        ImportError: If GitPython is not installed
        AttributeError: If repo or commit objects are invalid
    """
    if not GIT_AVAILABLE:
        raise ImportError("GitPython not installed. Run: pip install gitpython")
    
    # Add telemetry attributes for monitoring
    from opentelemetry import trace
    span = trace.get_current_span()
    
    file_diffs = {}
    total_size = 0
    
    # Get parent commit (or None for initial commit)
    parent = commit.parents[0] if commit.parents else None
    
    # Set basic span attributes
    span.set_attribute("git.commit_hash", commit.hexsha[:8])  # First 8 chars for privacy
    span.set_attribute("git.has_parent", parent is not None)
    span.set_attribute("operation.max_file_size", max_file_size)
    span.set_attribute("operation.max_total_size", max_total_size)
    
    try:
        # Get all diff items first to count them for adaptive limits
        if parent:
            diff_items = list(commit.diff(parent, create_patch=True))
        else:
            diff_items = list(commit.diff(NULL_TREE, create_patch=True))
        
        # Filter out binary and generated files first
        filtered_diff_items = []
        for diff_item in diff_items:
            # Get file path (prefer b_path for new files, fall back to a_path for deleted files)
            file_path = diff_item.b_path or diff_item.a_path
            if not file_path:
                continue
            
            # Skip binary files - check if the diff_item represents a binary file
            # For GitPython, we need to check if the blobs are binary
            is_binary = False
            if diff_item.a_blob and is_blob_binary(diff_item.a_blob):
                is_binary = True
            elif diff_item.b_blob and is_blob_binary(diff_item.b_blob):
                is_binary = True
            
            if is_binary:
                continue
                
            # Skip generated files
            if is_generated_file(file_path):
                continue
                
            filtered_diff_items.append(diff_item)
        
        # Apply adaptive size limits based on file count
        file_count = len(filtered_diff_items)
        original_file_count = len(diff_items)
        binary_files_filtered = sum(1 for item in diff_items if 
                                   (item.a_blob and is_blob_binary(item.a_blob)) or
                                   (item.b_blob and is_blob_binary(item.b_blob)))
        generated_files_filtered = original_file_count - binary_files_filtered - file_count
        
        # Set telemetry attributes for file analysis
        span.set_attribute("files.total_original", original_file_count)
        span.set_attribute("files.binary_filtered", binary_files_filtered)
        span.set_attribute("files.generated_filtered", generated_files_filtered)
        span.set_attribute("files.processed", file_count)
        
        if file_count <= 5:
            # ≤5 files: 10KB per file
            adaptive_max_file_size = 10 * 1024
            span.set_attribute("adaptive_sizing.category", "small_commit")
        elif file_count <= 20:
            # 6-20 files: 2.5KB per file
            adaptive_max_file_size = int(2.5 * 1024)
            span.set_attribute("adaptive_sizing.category", "medium_commit")
        else:
            # >20 files: 1KB per file with 50 file ceiling
            adaptive_max_file_size = 1 * 1024
            filtered_diff_items = filtered_diff_items[:50]  # Limit to 50 files
            span.set_attribute("adaptive_sizing.category", "large_commit")
            span.set_attribute("files.truncated_to", 50)
        
        span.set_attribute("adaptive_sizing.file_limit_bytes", adaptive_max_file_size)
        
        # Process each filtered diff item
        for diff_item in filtered_diff_items:
            file_path = diff_item.b_path or diff_item.a_path
            
            try:
                # Get the diff content
                if hasattr(diff_item, 'diff') and diff_item.diff:
                    diff_content = diff_item.diff.decode('utf-8', errors='replace')
                else:
                    # Fallback if diff content is not available
                    diff_content = f"[Unable to extract diff for {file_path}]"
                
                # Apply file size limits
                if len(diff_content) > adaptive_max_file_size:
                    # Truncate with message
                    diff_content = diff_content[:adaptive_max_file_size] + "\n[... diff truncated due to size limits ...]"
                
                # Check if adding this diff would exceed total size limit
                if total_size + len(diff_content) > max_total_size:
                    # If we've already collected some diffs, stop here
                    if file_diffs:
                        file_diffs["__truncated__"] = "Additional diffs omitted due to total size limits"
                        break
                    # If this is the first diff and it's already too large, include it truncated
                    remaining_size = max_total_size - total_size
                    if remaining_size > 0:
                        diff_content = diff_content[:remaining_size] + "\n[... remaining diffs truncated due to size limits ...]"
                
                # Add to collection
                file_diffs[file_path] = diff_content
                total_size += len(diff_content)
                
            except Exception as e:
                # Handle individual file diff errors gracefully
                file_diffs[file_path] = f"[Error extracting diff: {str(e)}]"
                total_size += len(file_diffs[file_path])
    
    except Exception as e:
        # Handle overall diff extraction errors
        span.set_attribute("operation.success", False)
        span.set_attribute("error.type", type(e).__name__)
        return {"__error__": f"Error extracting commit diffs: {str(e)}"}
    
    # Set final telemetry attributes
    span.set_attribute("operation.success", True)
    span.set_attribute("results.files_with_diffs", len([k for k in file_diffs.keys() if not k.startswith("__")]))
    span.set_attribute("results.total_size_bytes", total_size)
    span.set_attribute("results.has_truncation", "__truncated__" in file_diffs)
    span.set_attribute("results.has_errors", any(k.startswith("__") for k in file_diffs.keys()))
    
    return file_diffs
