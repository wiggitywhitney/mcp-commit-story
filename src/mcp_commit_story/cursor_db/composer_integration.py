"""
Composer integration utilities for cursor_db.

This module provides helper functions for integrating with Cursor's Composer
databases using the workspace detection and time window functionality.
"""

import os
import time
from pathlib import Path
from typing import Tuple, Optional
import git

from ..git_utils import get_repo, get_current_commit
from .workspace_detection import detect_workspace_for_repo, WorkspaceMatch
from ..commit_time_window import get_commit_time_window as _get_commit_time_window


def get_current_commit_hash(repo_path: Optional[str] = None) -> str:
    """
    Get the current commit hash from a git repository.
    
    Args:
        repo_path: Optional path to repository. Defaults to current directory.
        
    Returns:
        str: Current commit hash (40-character hex string)
        
    Raises:
        git.InvalidGitRepositoryError: If not a valid git repository
        Exception: If unable to get current commit
    """
    try:
        repo = get_repo(repo_path)
        current_commit = get_current_commit(repo)
        return current_commit.hexsha
    except Exception as e:
        raise Exception(f"Failed to get current commit hash: {e}")


def get_commit_time_window(commit_hash: str, repo_path: Optional[str] = None) -> Tuple[int, int]:
    """
    Get time window for a commit (start and end timestamps in milliseconds).
    
    This is a wrapper around commit_time_window.get_commit_time_window() that
    returns a simplified tuple format for cursor_db integration.
    
    Args:
        commit_hash: Hash of the commit to analyze
        repo_path: Optional path to repository. Defaults to current directory.
        
    Returns:
        Tuple[int, int]: (start_timestamp_ms, end_timestamp_ms)
        
    Raises:
        Exception: If unable to calculate time window
    """
    try:
        repo = get_repo(repo_path)
        time_window_result = _get_commit_time_window(repo, commit_hash)
        
        if time_window_result is None:
            # Fall back to 24-hour window
            current_time_ms = int(time.time() * 1000)
            start_time_ms = current_time_ms - (24 * 60 * 60 * 1000)  # 24 hours ago
            return (start_time_ms, current_time_ms)
        
        # Extract start and end from the time window result
        start_timestamp_ms = time_window_result.get('start_timestamp_ms')
        end_timestamp_ms = time_window_result.get('end_timestamp_ms')
        
        if start_timestamp_ms is None or end_timestamp_ms is None:
            # Fall back to 24-hour window
            current_time_ms = int(time.time() * 1000)
            start_time_ms = current_time_ms - (24 * 60 * 60 * 1000)
            return (start_time_ms, current_time_ms)
            
        return (start_timestamp_ms, end_timestamp_ms)
        
    except Exception as e:
        # Fall back to 24-hour window on any error
        current_time_ms = int(time.time() * 1000)
        start_time_ms = current_time_ms - (24 * 60 * 60 * 1000)
        return (start_time_ms, current_time_ms)


def find_workspace_composer_databases(repo_path: Optional[str] = None) -> Tuple[str, str]:
    """
    Find Composer workspace and global database paths for a repository.
    
    Uses workspace detection to find the appropriate Cursor workspace,
    then constructs the database paths for both workspace and global databases.
    
    Args:
        repo_path: Optional path to repository. Defaults to current directory.
        
    Returns:
        Tuple[str, str]: (workspace_db_path, global_db_path)
        
    Raises:
        Exception: If unable to find Composer databases
    """
    try:
        if repo_path is None:
            repo_path = os.getcwd()
            
        # Use workspace detection to find the matching workspace
        workspace_match: WorkspaceMatch = detect_workspace_for_repo(repo_path)
        
        # Use the actual workspace database path found by detection
        # workspace_match.path already contains the full correct path
        workspace_db_path = workspace_match.path
        
        # Construct global database path using the same base directory as workspace
        # For macOS: /Users/user/Library/Application Support/Cursor/User/workspaceStorage/hash/state.vscdb
        # Global:    /Users/user/Library/Application Support/Cursor/User/globalStorage/state.vscdb
        # Go up from hash/state.vscdb to hash/ to workspaceStorage/ to parent (Cursor/User/)
        cursor_base = workspace_match.path.parent.parent.parent  
        global_db_path = cursor_base / "globalStorage" / "state.vscdb"
        
        # Verify databases exist
        if not workspace_db_path.exists():
            raise Exception(f"Workspace database not found: {workspace_db_path}")
            
        if not global_db_path.exists():
            raise Exception(f"Global database not found: {global_db_path}")
            
        return (str(workspace_db_path), str(global_db_path))
        
    except Exception as e:
        raise Exception(f"Failed to find Composer databases: {e}") 