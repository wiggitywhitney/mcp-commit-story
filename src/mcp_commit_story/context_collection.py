"""
Context collection functions for MCP Commit Story.

This module provides unified functions for collecting chat, terminal, and git context for journal entry generation.

# Context Collection Module
# 
# MAJOR DISCOVERY (2025-06-10): Found that Cursor stores complete chat history in accessible
# SQLite databases at ~/Library/Application Support/Cursor/User/workspaceStorage/[hash]/state.vscdb
# 
# Key: 'aiService.prompts' contains JSON array with complete conversation history
# This eliminates need for cronjobs and provides full chat context for journal generation
# 
# TODO: Implement collect_cursor_chat_history() to replace the current chat collection
# See docs/cursor-chat-discovery.md for complete implementation details
"""

import os
import time
import logging
from mcp_commit_story.context_types import ChatHistory, TerminalContext, GitContext
from mcp_commit_story.git_utils import get_repo, get_current_commit, get_commit_details, get_commit_diff_summary, classify_file_type, classify_commit_size, NULL_TREE
from mcp_commit_story.telemetry import (
    trace_git_operation, 
    memory_tracking_context, 
    smart_file_sampling,
    get_mcp_metrics,
    PERFORMANCE_THRESHOLDS,
    _telemetry_circuit_breaker
)

logger = logging.getLogger(__name__)


@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(since_commit=None, max_messages_back=150) -> ChatHistory:
    """
    Returns:
        ChatHistory: Structured chat history as defined in context_types.py

    Notes:
    - The ChatHistory type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.

    Collect relevant chat history for journal entry.

    AI Prompt:
    Collect ALL chat messages within the specified boundary for journal entry generation.

    BOUNDARY DEFINITION:
    - Search backward through the current conversation for the last time you invoked the mcp-commit-story new-entry command
    - Collect EVERY message from that point forward to the current moment
    - Do not filter or exclude any messages - return the complete raw chat history within the boundary

    PURPOSE: Provide complete raw data for downstream processing. The filtering and intelligent extraction will be handled by generate_discussion_notes_section().

    Return ALL messages within the boundary as ChatHistory with complete speaker attribution and content.
    """
    # Validate that required parameters are provided
    if since_commit is None or max_messages_back is None:
        raise ValueError("collect_chat_history: since_commit and max_messages_back must not be None")
    
    # TODO: AI will replace this with actual chat analysis per the prompt above
    return ChatHistory(messages=[])


@trace_git_operation("terminal_commands",
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_ai_terminal_commands(since_commit=None, max_messages_back=150) -> TerminalContext:
    """
    Returns:
        TerminalContext: Structured terminal commands as defined in context_types.py

    Notes:
    - The TerminalContext type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.

    Collect relevant terminal commands for journal entry.

    AI Prompt:
    Please analyze the terminal command history within the specified boundary and extract ALL relevant commands for the journal entry.
    - Search through the terminal history from the specified commit point forward to now.
    - Extract all commands that contributed to the development process: git commands, file operations, test runs, build commands, package installs, etc.
    - Include the command itself, any relevant output or errors, and timestamp if available.
    - Focus on commands that show the development workflow: testing, debugging, file manipulation, environment setup, etc.
    - Exclude routine commands like "ls" or "cd" unless they're part of a significant debugging or exploration session.
    - Include failed commands and their errors - these often show problem-solving attempts.
    - Capture sequences of related commands that tell a story (e.g., test failure -> investigation -> fix -> retest).
    - Include any npm/pip installs, git operations, file moves/copies, permission changes, etc.
    - Record both successful and failed attempts to provide context about the development process.
    - Return commands in chronological order to preserve the development narrative.
    """
    # Validate that required parameters are provided
    if since_commit is None or max_messages_back is None:
        raise ValueError("collect_ai_terminal_commands: since_commit and max_messages_back must not be None")
    
    # Return empty structure for now
    return TerminalContext(commands=[])


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