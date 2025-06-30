"""
Cursor database integration package.

This package provides functionality for detecting, connecting to, and querying
Cursor's SQLite workspace databases across different platforms.
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional, Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from git.exc import GitCommandError, BadName
import logging

from .platform import (
    PlatformType,
    CursorPathError,
    detect_platform,
    get_cursor_workspace_paths,
    validate_workspace_path,
    get_primary_workspace_path
)
from .exceptions import CursorDatabaseError
from .workspace_detection import WorkspaceDetectionError
from .query_executor import execute_cursor_query
from .message_extraction import (
    extract_prompts_data,
    extract_generations_data
)
# message_reconstruction module removed - Composer provides chronological data
# Message limiting removed - using Composer's precise commit-based time windows
from ..telemetry import trace_mcp_operation, get_mcp_metrics
from .multiple_database_discovery import (
    discover_all_cursor_databases, 
    get_recent_databases, 
    extract_from_multiple_databases
)
from .composer_integration import (
    get_current_commit_hash,
    get_commit_time_window,
    find_workspace_composer_databases
)
from ..composer_chat_provider import ComposerChatProvider

logger = logging.getLogger(__name__)

@trace_mcp_operation("cursor_db.query_composer")
def query_cursor_chat_database() -> Dict[str, Any]:
    """
    Query Cursor's Composer databases to get complete chat history with enhanced metadata.
    
    Uses commit-based time windows and workspace detection to retrieve precisely 
    relevant chat messages from Cursor's Composer databases. Includes comprehensive
    telemetry for monitoring performance and debugging.
    
    Returns:
        Dict containing:
        - workspace_info: Enhanced workspace and database metadata with time windows
        - chat_history: List of enhanced chat messages with timestamps and session names
        
    Raises:
        Exception: If critical database operations fail (graceful degradation)
    """
    metrics = get_mcp_metrics()
    start_time = time.time()
    span = trace.get_current_span()
    
    workspace_db_path = None
    global_db_path = None
    commit_hash = None
    time_window_strategy = "commit_based"
    start_timestamp_ms = None
    end_timestamp_ms = None
    
    try:
        # Step 1: Get current commit hash for time window calculation
        try:
            commit_hash = get_current_commit_hash()
            span.set_attribute("cursor.commit_detected", True)
            span.set_attribute("cursor.commit_hash", commit_hash or "unknown")
        except Exception as e:
            # Fall back to 24-hour window if git operations fail
            time_window_strategy = "24_hour_fallback"
            current_time_ms = int(time.time() * 1000)
            start_timestamp_ms = current_time_ms - (24 * 60 * 60 * 1000)  # 24 hours ago
            end_timestamp_ms = current_time_ms
            span.set_attribute("cursor.commit_detected", False)
            span.set_attribute("cursor.git_error", str(e))
        
        # Step 2: Calculate time window based on commit (or use fallback)
        if commit_hash and start_timestamp_ms is None:
            try:
                start_timestamp_ms, end_timestamp_ms = get_commit_time_window(commit_hash)
                time_window_strategy = "commit_based"
            except Exception as e:
                # Fall back to 24-hour window
                time_window_strategy = "commit_window_fallback"
                current_time_ms = int(time.time() * 1000)
                start_timestamp_ms = current_time_ms - (24 * 60 * 60 * 1000)
                end_timestamp_ms = current_time_ms
        
        # Calculate duration and set telemetry attributes
        duration_hours = (end_timestamp_ms - start_timestamp_ms) / (1000 * 60 * 60) if start_timestamp_ms and end_timestamp_ms else 24
        span.set_attribute("time_window.strategy", time_window_strategy)
        span.set_attribute("time_window.duration_hours", round(duration_hours, 2))
        span.set_attribute("time_window.start_timestamp_ms", start_timestamp_ms)
        span.set_attribute("time_window.end_timestamp_ms", end_timestamp_ms)
        
        # Step 3: Find Composer databases using workspace detection
        try:
            workspace_db_path, global_db_path = find_workspace_composer_databases()
            span.set_attribute("cursor.workspace_detected", bool(workspace_db_path))
            span.set_attribute("cursor.global_database_detected", bool(global_db_path))
            span.set_attribute("cursor.workspace_database_path", workspace_db_path or "none")
        except (WorkspaceDetectionError, CursorDatabaseError) as e:
            # Database not found - return graceful degradation
            span.set_attribute("cursor.workspace_detected", False)
            span.set_attribute("cursor.detection_error", str(e))
            span.set_status(Status(StatusCode.ERROR, f"Workspace detection failed: {e}"))
            
            if metrics:
                metrics.record_counter(
                    "mcp.cursor.errors_total",
                    1,
                    attributes={"error_category": "workspace_detection"}
                )
            
            return {
                "workspace_info": {
                    "workspace_database_path": None,
                    "global_database_path": None,
                    "total_messages": 0,
                    "time_window_start": start_timestamp_ms,
                    "time_window_end": end_timestamp_ms,
                    "time_window_strategy": time_window_strategy,
                    "commit_hash": commit_hash,
                    "last_updated": datetime.now().isoformat()
                },
                "chat_history": []
            }
        
        # Step 4: Create ComposerChatProvider and retrieve messages
        try:
            provider = ComposerChatProvider(workspace_db_path, global_db_path)
            chat_messages = provider.getChatHistoryForCommit(start_timestamp_ms, end_timestamp_ms)
            
            # Set success attributes
            span.set_attribute("cursor.messages_retrieved", len(chat_messages))
            span.set_attribute("cursor.database_type", "composer")
            span.set_attribute("cursor.success", True)
            
        except Exception as e:
            # Provider error - return graceful degradation with database paths preserved
            span.set_attribute("cursor.provider_error", str(e))
            span.set_status(Status(StatusCode.ERROR, f"Composer provider failed: {e}"))
            
            if metrics:
                metrics.record_counter(
                    "mcp.cursor.errors_total",
                    1,
                    attributes={"error_category": "composer_provider"}
                )
            
            return {
                "workspace_info": {
                    "workspace_database_path": workspace_db_path,
                    "global_database_path": global_db_path,
                    "total_messages": 0,
                    "time_window_start": start_timestamp_ms,
                    "time_window_end": end_timestamp_ms,
                    "time_window_strategy": time_window_strategy,
                    "commit_hash": commit_hash,
                    "last_updated": datetime.now().isoformat()
                },
                "chat_history": []
            }
        
        # Record success metrics
        duration = time.time() - start_time
        if metrics:
            metrics.record_histogram(
                "mcp.cursor.query_duration_seconds",
                duration,
                attributes={
                    "database_type": "composer",
                    "strategy": time_window_strategy
                }
            )
            
            metrics.record_counter(
                "mcp.cursor.messages_total",
                len(chat_messages),
                attributes={"source": "composer"}
            )
        
        # Step 5: Build enhanced response with all metadata
        return {
            "workspace_info": {
                "workspace_database_path": workspace_db_path,
                "global_database_path": global_db_path,
                "total_messages": len(chat_messages),
                "time_window_start": start_timestamp_ms,
                "time_window_end": end_timestamp_ms,
                "time_window_strategy": time_window_strategy,
                "commit_hash": commit_hash,
                "last_updated": datetime.now().isoformat()
            },
            "chat_history": chat_messages  # Enhanced messages with timestamps, sessionName, etc.
        }
        
    except Exception as e:
        # Ultimate fallback - graceful error handling
        error_category = "unknown"
        if isinstance(e, CursorDatabaseError):
            error_category = "database_error"
        elif isinstance(e, WorkspaceDetectionError):
            error_category = "workspace_detection"
        elif isinstance(e, (GitCommandError, BadName)):
            error_category = "git_error"
            
        span.set_attribute("error.category", error_category)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        
        if metrics:
            metrics.record_counter(
                "mcp.cursor.errors_total",
                1,
                attributes={"error_category": error_category}
            )
        
        # Graceful degradation
        logger.error(f"Composer query failed: {e}", extra={
            'error_type': e.__class__.__name__,
            'error_category': error_category
        })
        
        return {
            "workspace_info": {
                "workspace_database_path": workspace_db_path,
                "global_database_path": global_db_path,
                "total_messages": 0,
                "time_window_start": start_timestamp_ms,
                "time_window_end": end_timestamp_ms,
                "time_window_strategy": "error_fallback",
                "commit_hash": commit_hash,
                "last_updated": datetime.now().isoformat()
            },
            "chat_history": []
        }

__all__ = [
    'PlatformType',
    'CursorPathError', 
    'detect_platform',
    'get_cursor_workspace_paths',
    'validate_workspace_path',
    'execute_cursor_query',
    'extract_prompts_data',
    'extract_generations_data',
    # 'reconstruct_chat_history' - removed, Composer provides chronological data
    'query_cursor_chat_database',
    'get_primary_workspace_path',
    'discover_all_cursor_databases',
    'get_recent_databases',
    'extract_from_multiple_databases',
    'get_current_commit_hash',
    'get_commit_time_window',
    'find_workspace_composer_databases',
    'ComposerChatProvider'
] 