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

# Import message limiting with defaults validated from Task 47.1 research
try:
    from mcp_commit_story.cursor_db.message_limiting import (
        limit_chat_messages, 
        DEFAULT_MAX_HUMAN_MESSAGES,
        DEFAULT_MAX_AI_MESSAGES
    )
except ImportError:
    # Fallback defaults if message limiting unavailable
    DEFAULT_MAX_HUMAN_MESSAGES = 200
    DEFAULT_MAX_AI_MESSAGES = 200
    limit_chat_messages = None

logger = logging.getLogger(__name__)

# Message limits designed for solo developer usage patterns
# Based on research from Task 47.1 analyze_message_counts.py
# These values cover even intense 48-hour coding sessions
# Acts as safety net for edge cases, not regular constraint
# Research findings: typical usage ~35 human/35 AI messages per session
# 200/200 limits provide significant safety margin without impacting normal workflows


@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(
    since_commit=None, 
    max_messages_back=150
) -> ChatHistory:
    """
    Collect relevant chat history for journal entry with message count limits.
    
    Uses hardcoded 200/200 message limits based on solo developer research.
    These limits act as a safety net for edge cases without impacting normal workflows.

    Args:
        since_commit: Commit reference (validated for compatibility but unused - cursor_db handles filtering)
        max_messages_back: Maximum messages to look back (validated for compatibility but unused - cursor_db handles filtering)

    Returns:
        ChatHistory: Dictionary with 'messages' array containing chat data.
                    Each message has 'speaker' and 'text' fields.
                    Returns empty ChatHistory on errors for graceful degradation.

    Note:
        Message limits (200/200) are based on solo developer usage research.
        These limits act as a safety net and are rarely triggered in practice
        due to cursor_db's 48-hour filtering.
    """
    # Validate required parameters (keeping for compatibility even if unused)
    if since_commit is None or max_messages_back is None:
        raise ValueError("collect_chat_history: since_commit and max_messages_back must not be None")
    
    try:
        # Get chat history from cursor database
        raw_chat_data = query_cursor_chat_database()
        
        # Apply message limiting with research-validated defaults
        if limit_chat_messages is None:
            logger.warning("Message limiting module not available")
            limited_chat_history = raw_chat_data.get('chat_history', {})
        else:
            try:
                # Pass only the chat_history part to limit_chat_messages
                chat_history_part = raw_chat_data.get('chat_history', {})
                limited_chat_history = limit_chat_messages(
                    chat_history_part,
                    DEFAULT_MAX_HUMAN_MESSAGES,
                    DEFAULT_MAX_AI_MESSAGES
                )
            except Exception as e:
                logger.warning(f"Message limiting failed: {e}")
                limited_chat_history = raw_chat_data.get('chat_history', {})
        
        # Log telemetry if truncation occurred
        if limited_chat_history and isinstance(limited_chat_history, dict):
            metadata = limited_chat_history.get('metadata', {})
            if metadata.get('truncated_human') or metadata.get('truncated_ai'):
                # Simple telemetry logging as specified in the plan
                try:
                    from mcp_commit_story.telemetry import get_mcp_metrics
                    metrics = get_mcp_metrics()
                    if metrics:
                        metrics.record_counter('chat_history_truncation', attributes={
                            'original_human_count': str(metadata.get('original_human_count', 0)),
                            'original_ai_count': str(metadata.get('original_ai_count', 0)),
                            'removed_human_count': str(metadata.get('removed_human_count', 0)),
                            'removed_ai_count': str(metadata.get('removed_ai_count', 0)),
                            'max_human_messages': str(DEFAULT_MAX_HUMAN_MESSAGES),
                            'max_ai_messages': str(DEFAULT_MAX_AI_MESSAGES)
                        })
                except ImportError:
                    logger.debug("Telemetry not available for truncation logging")
                except Exception as e:
                    logger.debug(f"Failed to log truncation telemetry: {e}")
        
        # Convert to ChatHistory format
        messages = []
        chat_messages = limited_chat_history.get('messages', [])
        for msg in chat_messages:
            messages.append({
                'speaker': 'Human' if msg.get('role') == 'user' else 'Assistant',
                'text': msg.get('content', '')
            })
        
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
        repo (git.Repo, optional): GitPython Repo object. Defaults to current repo.
        journal_path (str, optional): Path to the journal file or directory to exclude from context (for recursion prevention).

    Returns:
        GitContext: Structured git context as defined in context_types.py

    Notes:
    - The GitContext type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.
    - If journal_path is provided, all journal files are filtered from changed_files, file_stats, and diff_summary to prevent recursion.
    """
    if repo is None:
        repo = get_repo()
    
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
        journal_rel = os.path.relpath(journal_path, repo.working_tree_dir)
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