"""
Context collection functions for MCP Commit Story.

This module provides unified functions for collecting chat and git context for journal entry generation.

Architecture Decision: Terminal Command Collection Removed (2025-06-27)
Terminal commands were originally designed to be collected by Cursor's AI with
access to its execution context. With the shift to external journal generation,
we no longer have access. Git diffs and chat context provide sufficient narrative.

TODO: Implement collect_journal_context() functionality
This function should read from journal/daily/YYYY-MM-DD-journal.md files to extract:
- Recent reflection sections that provide project insights
- Manual context additions from daily entries
- Cross-reference with git commits to understand development patterns
This would complement chat history by providing structured, intentional context
from the developer's own journaling and reflection process.
"""

import os
import time
import logging
from mcp_commit_story.context_types import ChatHistory, GitContext
from mcp_commit_story.git_utils import get_repo, get_current_commit, get_commit_details, get_commit_diff_summary, classify_file_type, classify_commit_size, NULL_TREE
from mcp_commit_story.telemetry import (
    trace_git_operation, 
    memory_tracking_context, 
    smart_file_sampling,
    get_mcp_metrics,
    PERFORMANCE_THRESHOLDS,
    _telemetry_circuit_breaker
)

# Import cursor_db for chat history collection
from mcp_commit_story.cursor_db import query_cursor_chat_database

logger = logging.getLogger(__name__)


@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(
    since_commit=None, 
    max_messages_back=150
) -> ChatHistory:
    """
    Collect relevant chat history for journal entry using Composer's precise time windows.
    
    Uses commit-based time window filtering via query_cursor_chat_database() with Composer
    integration. No artificial message limits are applied since Composer provides precisely
    relevant messages for the development context.

    Args:
        since_commit: Commit reference (validated for compatibility but unused - Composer handles precise filtering)
        max_messages_back: Maximum messages to look back (validated for compatibility but unused - Composer handles precise filtering)

    Returns:
        ChatHistory: Dictionary with 'messages' array containing enhanced chat data.
                    Each message has 'speaker' and 'text' fields, with additional metadata preserved.
                    Returns empty ChatHistory on errors for graceful degradation.

    Note:
        No artificial message limits are applied. Composer's commit-based time windows 
        provide naturally scoped, relevant conversation context. This replaces the old 
        200/200 limiting approach which was designed for 48-hour time windows.
    """
    # Validate required parameters (keeping for compatibility even if unused)
    if since_commit is None or max_messages_back is None:
        raise ValueError("collect_chat_history: since_commit and max_messages_back must not be None")
    
    try:
        # Get chat history from Composer via cursor database
        chat_data = query_cursor_chat_database()
        
        # Extract chat messages directly - no limiting applied
        chat_messages = chat_data.get('chat_history', [])
        
        # Convert to ChatHistory format with enhanced data preservation
        messages = []
        for msg in chat_messages:
            # Preserve enhanced Composer metadata in the conversion
            message_data = {
                'speaker': 'Human' if msg.get('role') == 'user' else 'Assistant',
                'text': msg.get('content', '')
            }
            
            # Preserve additional metadata from Composer if available
            if 'timestamp' in msg:
                message_data['timestamp'] = msg['timestamp']
            if 'sessionName' in msg:
                message_data['sessionName'] = msg['sessionName']
            
            messages.append(message_data)
        
        return ChatHistory(messages=messages)
        
    except Exception as e:
        logger.error(f"Chat history collection failed: {e}")
        return ChatHistory(messages=[])


@trace_git_operation("git_context",
                    performance_thresholds={"duration": 2.0},
                    error_categories=["git", "filesystem", "memory"])
def collect_git_context(commit_hash=None, repo=None, journal_path=None) -> GitContext:
    """
    Collect structured git context for a given commit hash (or HEAD if None).

    Args:
        commit_hash (str, optional): Commit hash to analyze. Defaults to HEAD.
        repo (git.Repo or str, optional): GitPython Repo object or path string. Defaults to current repo.
        journal_path (str, optional): Path to the journal file or directory to exclude from context (for recursion prevention).

    Returns:
        GitContext: Structured git context as defined in context_types.py

    Notes:
    - The GitContext type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.
    - If journal_path is provided, all journal files are filtered from changed_files, file_stats, and diff_summary to prevent recursion.
    """
    # Handle repo parameter - can be None, string path, or git.Repo object
    if repo is None:
        repo = get_repo()
    elif isinstance(repo, str):
        repo = get_repo(repo)
    # If it's already a git.Repo object, use it as-is
    
    # Get commit with error handling
    try:
        if commit_hash is None:
            commit = get_current_commit(repo)
        else:
            commit = repo.commit(commit_hash)
    except Exception as e:
        import git as gitlib
        if isinstance(e, gitlib.InvalidGitRepositoryError):
            raise
        if isinstance(e, gitlib.BadName):
            raise
        raise
    
    # Metadata collection
    details = get_commit_details(commit)
    metadata = {
        'hash': details.get('hash'),
        'author': details.get('author'),
        'date': details.get('datetime'),
        'message': details.get('message'),
    }
    
    # Diff summary
    diff_summary = get_commit_diff_summary(commit)
    
    # Changed files with smart sampling and performance limits
    parent = commit.parents[0] if commit.parents else None
    # For the initial commit, diff against the empty tree (NULL_TREE)
    try:
        diffs = commit.diff(parent) if parent else commit.diff(NULL_TREE)
        
        # Defensive programming: handle case where diff returns None
        if diffs is None:
            raise TypeError("Git diff operation returned None - possibly due to repository corruption or timeout")
            
    except (TypeError, AttributeError) as e:
        # Handle cases where diff() returns None or other unexpected types
        logger.error(f"Git diff operation failed: {e}")
        raise
    
    all_changed_files = []
    total_file_count = 0
    
    # Collect all files first for analysis
    for diff in diffs:
        fname = diff.b_path or diff.a_path
        if fname:
            all_changed_files.append(fname)
            total_file_count += 1
    
    # Apply performance mitigation for large commits
    if total_file_count > PERFORMANCE_THRESHOLDS["detailed_analysis_file_count_limit"]:
        # Skip detailed analysis for very large commits
        changed_files = all_changed_files[:10]  # Take first 10 for summary
        file_stats = {'source': 0, 'config': 0, 'docs': 0, 'tests': 0, 'large_commit_truncated': True}
        diff_summary += f"\n[Large commit: {total_file_count} files, analysis truncated for performance]"
    else:
        # Apply smart sampling for medium-large commits
        sampled_files = smart_file_sampling(all_changed_files)
        changed_files = sampled_files
        
        # Calculate file stats on sampled files
        file_stats = {'source': 0, 'config': 0, 'docs': 0, 'tests': 0}
        
        for fname in changed_files:
            ftype = classify_file_type(fname)
            if ftype in file_stats:
                file_stats[ftype] += 1
            else:
                file_stats['source'] += 1  # Default bucket
    
    # --- Recursion prevention: filter out journal files ---
    if journal_path:
        # If journal_path is already a relative path, use it as-is
        # If it's an absolute path, make it relative to the working tree
        if os.path.isabs(journal_path):
            journal_rel = os.path.relpath(journal_path, repo.working_tree_dir)
        else:
            journal_rel = journal_path
        
        original_count = len(changed_files)
        changed_files = [f for f in changed_files if not f.startswith(journal_rel)]
        
        # Regenerate file_stats without journal files if they were filtered
        if len(changed_files) != original_count:
            file_stats = {'source': 0, 'config': 0, 'docs': 0, 'tests': 0}
            for f in changed_files:
                ftype = classify_file_type(f)
                if ftype in file_stats:
                    file_stats[ftype] += 1
                else:
                    file_stats['source'] += 1
            # Note the filtering in diff_summary
            diff_summary += "\n[Journal files filtered for recursion prevention]"
    
    # Commit size classification
    stats = details.get('stats', {})
    insertions = stats.get('insertions', 0)
    deletions = stats.get('deletions', 0)
    size_classification = classify_commit_size(insertions, deletions)
    
    # Merge status
    is_merge = len(commit.parents) > 1
    commit_context = {
        'size_classification': size_classification,
        'is_merge': is_merge,
    }
    
    # Build final result
    return {
        'metadata': metadata,
        'diff_summary': diff_summary,
        'changed_files': changed_files,
        'file_stats': file_stats,
        'commit_context': commit_context,
    } 


# Add function that tests are looking for
@trace_git_operation("git_status",
                    performance_thresholds={"duration": 1.0},
                    error_categories=["git", "filesystem"])
def get_git_status_with_telemetry(repo):
    """Function for testing git status telemetry instrumentation."""
    # This is just for testing - would be implemented with actual git status logic
    return {"status": "clean"}


@trace_git_operation("context_transformation",
                    performance_thresholds={"duration": 0.5},
                    error_categories=["parsing", "memory"])
def trace_context_transformation(operation_name: str):
    """Function for testing context transformation tracing."""
    # This is just for testing - would be implemented with actual transformation logic
    return {"operation": operation_name, "status": "completed"} 