"""
Context collection functions for MCP Commit Story.

This module provides unified functions for collecting chat and git context for journal entry generation.

Architecture Decision: Terminal Command Collection Removed (2025-06-27)
Terminal commands were originally designed to be collected by Cursor's AI with
access to its execution context. With the shift to external journal generation,
we no longer have access. Git diffs and chat context provide sufficient narrative.

Journal context collection functionality is implemented via collect_recent_journal_context(commit).
This function reads from journal/daily/YYYY-MM-DD-journal.md files and extracts recent
reflection sections, manual context additions, and cross-references with git commits
to provide structured context for journal generation.
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp_commit_story.context_types import ChatHistory, GitContext, RecentJournalContext
from mcp_commit_story.git_utils import get_repo, get_current_commit, get_commit_details, get_commit_diff_summary, classify_file_type, classify_commit_size, NULL_TREE
from mcp_commit_story.telemetry import (
    trace_git_operation, 
    trace_mcp_operation,
    memory_tracking_context, 
    smart_file_sampling,
    get_mcp_metrics,
    PERFORMANCE_THRESHOLDS,
    _telemetry_circuit_breaker
)

# Import cursor_db for chat history collection
from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.ai_context_filter import filter_chat_for_commit

import re

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for journal parsing (performance optimization)
_JOURNAL_ENTRY_PATTERN = re.compile(r'^## (\d{1,2}:\d{2} (?:AM|PM)) — Git Commit: ([a-zA-Z0-9]+)', re.MULTILINE)
_CAPTURE_REFLECTION_PATTERN = re.compile(r'^### (\d{1,2}:\d{2} (?:AM|PM)|[\d:]+) — (?:AI Context Capture|Reflection)', re.MULTILINE)
_SECTION_BOUNDARY_PATTERN = re.compile(r'^##+ (?:\d{1,2}:\d{2} (?:AM|PM)|[\d:]+) —', re.MULTILINE)


@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(
    commit=None,
    since_commit=None, 
    max_messages_back=150
) -> ChatHistory:
    """
    Collect relevant chat history for journal entry using AI-powered context filtering.
    
    Uses commit-based time window filtering via query_cursor_chat_database() with Composer
    integration and AI-powered conversation boundary detection. The system automatically
    identifies where work for the current commit begins and filters out irrelevant conversation
    history from previous development work.

    AI Filtering Process:
    - Analyzes conversation context to identify where current commit work begins
    - Uses git context, previous commits, and conversation flow for boundary detection
    - Provides confidence scoring and reasoning for transparency
    - Conservative error handling: falls back to unfiltered messages on AI failures
    - Tracks filtering effectiveness through telemetry metrics

    Args:
        commit: Git commit object to use for time window calculation and AI filtering (preferred)
        since_commit: Commit reference (legacy compatibility - superseded by commit parameter)
        max_messages_back: Historical compatibility parameter (no longer used with Composer integration)

    Returns:
        ChatHistory: Structured chat history with AI-filtered, commit-relevant messages

    Raises:
        ValueError: If neither commit nor since_commit is provided

    Note:
        No artificial message limits are applied. Composer's commit-based time windows 
        provide naturally scoped conversation context, and AI filtering removes irrelevant
        conversation history to ensure journal entries contain only relevant context.
        
    Telemetry:
        Tracks AI filtering effectiveness including message reduction rates, success/failure
        rates, and filtering performance metrics for monitoring and optimization.
    """
    # Validate required parameters
    if commit is None and since_commit is None:
        raise ValueError("collect_chat_history: either commit or since_commit must be provided")
    if max_messages_back is None:
        raise ValueError("collect_chat_history: max_messages_back must not be None")
    
    try:
        # Get chat history from Composer via cursor database, passing commit object
        chat_data = query_cursor_chat_database(commit=commit)
        
        # Extract chat messages directly - no limiting applied
        chat_messages = chat_data.get('chat_history', [])
        
        # Apply AI filtering if we have messages and a commit object
        if chat_messages and commit is not None:
            # Telemetry: Track filtering effectiveness
            from opentelemetry import trace
            span = trace.get_current_span()
            messages_before = len(chat_messages)
            
            try:
                # Collect git context for AI filtering
                git_context = collect_git_context(commit_hash=commit.hexsha)
                filtered_messages = filter_chat_for_commit(chat_messages, commit, git_context)
                
                # Update to use filtered messages
                chat_messages = filtered_messages
                
                # Telemetry: Track filtering success and effectiveness
                messages_after = len(chat_messages)
                reduction_count = messages_before - messages_after
                reduction_percentage = (reduction_count / messages_before * 100) if messages_before > 0 else 0
                
                # Set telemetry attributes for filtering effectiveness
                if span:
                    span.set_attribute("ai_filter.messages_before", messages_before)
                    span.set_attribute("ai_filter.messages_after", messages_after)
                    span.set_attribute("ai_filter.reduction_count", reduction_count)
                    span.set_attribute("ai_filter.reduction_percentage", round(reduction_percentage, 2))
                    span.set_attribute("ai_filter.success", True)
                
                logger.info(f"AI filtering: {messages_before} → {messages_after} messages ({reduction_percentage:.1f}% reduction)")
                
            except Exception as e:
                # Conservative error handling: log error but continue with unfiltered messages
                logger.warning(f"AI context filtering failed, using unfiltered messages: {e}")
                
                # Telemetry: Track filtering failure
                if span:
                    span.set_attribute("ai_filter.messages_before", messages_before)
                    span.set_attribute("ai_filter.messages_after", messages_before)  # No filtering applied
                    span.set_attribute("ai_filter.reduction_count", 0)
                    span.set_attribute("ai_filter.reduction_percentage", 0.0)
                    span.set_attribute("ai_filter.success", False)
                    span.set_attribute("ai_filter.error_type", type(e).__name__)
        
        # Convert to ChatHistory format with enhanced data preservation
        messages = []
        for msg in chat_messages:
            # Preserve enhanced Composer metadata in the conversion
            message_data = {
                'speaker': 'Human' if msg.get('role') == 'user' else 'Assistant',
                'text': sanitize_chat_content(msg.get('content', ''))  # SECURITY: Sanitize chat content before journal generation
            }
            
            # Preserve additional metadata from Composer if available
            if 'timestamp' in msg:
                message_data['timestamp'] = msg['timestamp']
            
            if 'bubbleId' in msg:
                message_data['bubbleId'] = msg['bubbleId']
                
            if 'composerId' in msg:
                message_data['composerId'] = msg['composerId']
            
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


def sanitize_chat_content(content: Optional[str]) -> str:
    """
    Sanitize potentially sensitive information from chat content before journal generation.
    
    Prevents API keys, tokens, passwords, and other secrets from being accidentally logged
    in journal entries by applying comprehensive pattern-based sanitization.
    
    Patterns reused from telemetry.sanitize_for_telemetry() with focus on chat content:
    - API keys and tokens (preserve first 8 chars for readability)
    - JSON Web Tokens (JWT)
    - Bearer tokens in headers
    - Environment variable assignments
    - Database connection strings
    - GitHub tokens
    
    Args:
        content: Chat message content to sanitize, can be None
        
    Returns:
        Sanitized content with sensitive data replaced by *** markers,
        empty string if content is None
        
    Examples:
        >>> sanitize_chat_content("My API key is sk_1234567890abcdef1234567890abcdef")
        'My API key is sk_12345***'
        
        >>> sanitize_chat_content("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature")
        'Bearer jwt.***'
    """
    if content is None:
        return ""
    
    if not content.strip():
        return content
    
    str_value = str(content)
    
    # Order matters! Apply most specific patterns first to avoid conflicts
    
    # 1. JSON Web Tokens (JWT) - three base64 segments separated by dots
    # Must be specific to avoid false positives on version numbers
    str_value = re.sub(
        r'\beyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]{4,}\.[A-Za-z0-9-_]+\b', 
        'jwt.***', 
        str_value
    )
    
    # 2. GitHub tokens (specific prefixes)
    str_value = re.sub(
        r'\b(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9]{36,}\b',
        lambda m: m.group(1) + m.group(0)[4:8] + '***',
        str_value
    )
    
    # 3. API keys with common prefixes (sk_, pk_, etc.)
    str_value = re.sub(
        r'\b(sk_|pk_|rk_|ak_)[A-Za-z0-9_]{12,}\b',
        lambda m: m.group(0)[:8] + '***',
        str_value
    )
    
    # 4. Bearer tokens in headers (after JWT so JWT gets specific handling)
    # Don't match if already contains jwt.*** replacement
    str_value = re.sub(
        r'(Bearer\s+)(?!jwt\.\*\*\*)[A-Za-z0-9\-._~+/]+=*', 
        r'\1***', 
        str_value, 
        flags=re.IGNORECASE
    )
    
    # 5. Long alphanumeric strings that look like API keys/tokens (32+ chars, not version numbers)
    # Be more conservative - only if it looks like a token (no dots, longer than 32 chars)
    str_value = re.sub(
        r'\b[A-Za-z0-9]{32,}\b', 
        lambda m: m.group(0)[:8] + '***' if '.' not in m.group(0) else m.group(0), 
        str_value
    )
    
    # 6. Environment variable patterns (API_KEY=value, etc.)
    str_value = re.sub(
        r'(export\s+)?[A-Z_]+(KEY|SECRET|TOKEN|PASSWORD|AUTH)=[^\s]+', 
        r'\1***=***', 
        str_value
    )
    
    # 7. Database passwords in connection strings
    str_value = re.sub(
        r'(password|pwd|secret)=([^;,\s]+)', 
        r'\1=***', 
        str_value, 
        flags=re.IGNORECASE
    )
    
    # 8. Database connection strings (mongodb://user:pass@host, postgres://user:pass@host)
    str_value = re.sub(
        r'(mongodb|postgres|mysql)://[^@]*@', 
        r'\1://***:***@', 
        str_value
    )
    
    # 9. API endpoints with credentials (https://user:pass@example.com)
    str_value = re.sub(
        r'(https?://)[^@/]+:[^@/]+@', 
        r'\1***:***@', 
        str_value
    )
    
    # 10. Auth tokens in URLs (?token=abc123, &key=def456)
    str_value = re.sub(
        r'(token|auth|key|secret)=[^&\s]+', 
        r'\1=***', 
        str_value, 
        flags=re.IGNORECASE
    )
    
    return str_value


@trace_mcp_operation("context.collect_recent_journal")
def collect_recent_journal_context(commit) -> RecentJournalContext:
    """
    Collect recent journal context to enrich commit journal generation.
    
    Extracts the most recent journal entry plus any AI captures/reflections added after
    that entry to provide relevant context while avoiding duplication. Uses the commit's
    date to determine which journal file to examine, following existing codebase patterns.
    
    Uses regex patterns for maintainable section parsing and implements comprehensive 
    telemetry tracking with graceful error handling.
    
    Args:
        commit: Git commit object containing date information for journal file selection
        
    Returns:
        RecentJournalContext: Structured context with latest entry, additional context,
                             and metadata about the collection process
                             
    Example:
        commit = repo.commit('abc123')
        context = collect_recent_journal_context(commit)
        
        if context['latest_entry']:
            print(f"Latest entry: {len(context['latest_entry'])} chars")
        print(f"Additional context sections: {len(context['additional_context'])}")
    """
    start_time = time.time()
    
    # Extract commit date for journal file selection
    commit_date_str = commit.committed_datetime.strftime('%Y-%m-%d')
    
    # Initialize telemetry tracking
    from opentelemetry import trace
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("journal.commit_date", commit_date_str)
        # Handle cases where commit object doesn't have hexsha (like in tests)
        if hasattr(commit, 'hexsha') and commit.hexsha:
            current_span.set_attribute("journal.commit_hash", commit.hexsha[:8])
        else:
            current_span.set_attribute("journal.commit_hash", "unknown")
    
    try:
        # Import required utilities
        from mcp_commit_story.journal_generate import get_journal_file_path, JournalParser
        
        # Get journal file path using commit date
        relative_file_path = get_journal_file_path(commit_date_str, "daily")
        journal_file_path = Path(relative_file_path)
        
        # Check if journal file exists
        if not journal_file_path.exists():
            if current_span:
                current_span.set_attribute("journal.file_exists", False)
            
            return RecentJournalContext(
                latest_entry=None,
                additional_context=[],
                metadata={
                    'file_exists': False,
                    'latest_entry_found': False,
                    'additional_context_count': 0,
                    'date': commit_date_str,
                    'parser_sections': 0
                }
            )
        
        if current_span:
            current_span.set_attribute("journal.file_exists", True)
        
        # Read journal file content
        try:
            with open(journal_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read journal file {journal_file_path}: {e}")
            if current_span:
                current_span.set_attribute("journal.read_error", str(e))
            
            return RecentJournalContext(
                latest_entry=None,
                additional_context=[],
                metadata={
                    'file_exists': False,
                    'latest_entry_found': False,
                    'additional_context_count': 0,
                    'date': commit_date_str,
                    'parser_sections': 0
                }
            )
        
        if current_span:
            current_span.set_attribute("journal.content_length", len(content))
        
        # Parse journal content to identify sections
        
        # Find the most recent journal entry (last one in the file)
        entry_matches = list(_JOURNAL_ENTRY_PATTERN.finditer(content))
        latest_entry = None
        latest_entry_end_pos = 0
        
        if entry_matches:
            # Get the last entry match (most recent)
            latest_entry_match = entry_matches[-1]
            latest_entry_start = latest_entry_match.start()
            
            # Find where this entry ends (start of next section or end of file)
            next_section_pos = len(content)
            
            # Look for the next section starting with ## (any section, not just entries)
            next_section_match = _SECTION_BOUNDARY_PATTERN.search(content[latest_entry_start + 1:])
            if next_section_match:
                next_section_pos = latest_entry_start + 1 + next_section_match.start()
            
            # Extract the latest entry content
            latest_entry = content[latest_entry_start:next_section_pos].strip()
            latest_entry_end_pos = next_section_pos
            
            if current_span:
                current_span.set_attribute("journal.latest_entry_length", len(latest_entry))
        
        # Find captures/reflections added after the latest entry
        additional_context = []
        capture_matches = list(_CAPTURE_REFLECTION_PATTERN.finditer(content))
        
        for match in capture_matches:
            capture_start = match.start()
            
            # Only include captures that come after the latest entry
            # Use >= instead of > to include sections that start exactly at the boundary
            if capture_start >= latest_entry_end_pos:
                # Find where this capture/reflection ends
                capture_end_pos = len(content)
                
                # Look for the next section
                next_section_match = _SECTION_BOUNDARY_PATTERN.search(content[capture_start + 1:])
                if next_section_match:
                    capture_end_pos = capture_start + 1 + next_section_match.start()
                
                # Extract the capture/reflection content
                capture_content = content[capture_start:capture_end_pos].strip()
                additional_context.append(capture_content)
        
        # Record success metrics
        duration = time.time() - start_time
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_operation_duration(
                "context.recent_journal_collection_duration_seconds",
                duration,
                operation_type="journal_context_collection"
            )
            metrics.record_counter(
                "context.recent_journal_operations_total",
                value=1,
                attributes={
                    "operation_type": "journal_context_collection",
                    "success": "true"
                }
            )
        
        if current_span:
            current_span.set_attribute("journal.latest_entry_found", latest_entry is not None)
            current_span.set_attribute("journal.additional_context_count", len(additional_context))
        
        return RecentJournalContext(
            latest_entry=latest_entry,
            additional_context=additional_context,
            metadata={
                'file_exists': True,
                'latest_entry_found': latest_entry is not None,
                'additional_context_count': len(additional_context),
                'date': commit_date_str,
                'parser_sections': len(entry_matches) + len(capture_matches)
            }
        )
        
    except Exception as e:
        # Record error metrics
        duration = time.time() - start_time
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_counter(
                "context.recent_journal_operations_total",
                value=1,
                attributes={
                    "operation_type": "journal_context_collection",
                    "success": "false"
                }
            )
        
        if current_span:
            current_span.set_attribute("error.category", "journal_context_collection_failed")
            current_span.set_attribute("error.message", str(e))
        
        logger.error(f"Failed to collect recent journal context: {e}")
        
        # Return empty context on error
        return RecentJournalContext(
            latest_entry=None,
            additional_context=[],
            metadata={
                'file_exists': False,
                'latest_entry_found': False,
                'additional_context_count': 0,
                'date': commit_date_str,
                'parser_sections': 0
            }
        ) 