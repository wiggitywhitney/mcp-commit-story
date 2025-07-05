"""
Cursor database integration package.

This package provides functionality for detecting, connecting to, and querying
Cursor's SQLite workspace databases across different platforms.
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional, Any

# Optional OpenTelemetry import with graceful degradation
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    HAS_TELEMETRY = True
except ImportError:
    HAS_TELEMETRY = False
    trace = None
    StatusCode = None
    Status = None

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
from .exceptions import (
    CursorDatabaseError,
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError,
    CursorDatabaseSchemaError,
    CursorDatabaseQueryError
)
from .workspace_detection import WorkspaceDetectionError, detect_workspace_for_repo
from .query_executor import execute_cursor_query
from .message_extraction import (
    extract_prompts_data,
    extract_generations_data
)
# message_reconstruction module removed - Composer provides chronological data
# Message limiting removed - using Composer's precise commit-based time windows
# Conditional telemetry imports
try:
    from ..telemetry import trace_mcp_operation, get_mcp_metrics
except ImportError:
    # Fallback when telemetry is not available
    def trace_mcp_operation(name):
        def decorator(func):
            return func
        return decorator
    
    def get_mcp_metrics():
        return None

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
logger = logging.getLogger(__name__)

# Create tracer only if telemetry is available
if HAS_TELEMETRY and trace:
    tracer = trace.get_tracer(__name__)
else:
    tracer = None

# Simple circuit breaker for repeated failures
class _CircuitBreaker:
    """Simple circuit breaker to prevent cascading failures."""
    def __init__(self, failure_threshold: int = 3, auto_reset_after_calls: int = 5):
        self.failure_threshold = failure_threshold
        self.auto_reset_after_calls = auto_reset_after_calls
        self.failure_count = 0
        self.is_open = False
        self.call_count_since_open = 0
    
    def record_failure(self):
        """Record a failure and check if circuit should open."""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            self.call_count_since_open = 0
    
    def record_success(self):
        """Record a success and reset failure count."""
        self.failure_count = 0
        self.is_open = False
        self.call_count_since_open = 0
    
    def should_reject(self) -> bool:
        """Check if circuit breaker should reject the request."""
        if self.is_open:
            self.call_count_since_open += 1
            # Auto-reset after some calls to allow recovery
            if self.call_count_since_open > self.auto_reset_after_calls:
                self.reset()
                return False
            return True
        return False
    
    def reset(self):
        """Reset the circuit breaker to closed state."""
        self.failure_count = 0
        self.is_open = False
        self.call_count_since_open = 0

# Global circuit breaker instance (threshold=5 to allow test scenarios to run)
_circuit_breaker = _CircuitBreaker(failure_threshold=5)

def reset_circuit_breaker():
    """Reset the circuit breaker for testing purposes."""
    global _circuit_breaker
    _circuit_breaker.reset()

@trace_mcp_operation("cursor_db.query_composer")
def query_cursor_chat_database(commit=None) -> Dict[str, Any]:
    """
    Query Cursor's Composer databases to get complete chat history with enhanced metadata.
    
    Uses commit-based time windows and workspace detection to retrieve precisely 
    relevant chat messages from Cursor's Composer databases. Includes comprehensive
    telemetry for monitoring performance and debugging.
    
    Args:
        commit: Git commit object to use for time window calculation. If None, 
                uses current HEAD commit (legacy behavior).
    
    Returns:
        Dict containing:
        - workspace_info: Enhanced workspace and database metadata with time windows
        - chat_history: List of enhanced chat messages with timestamps and session names
        
    Raises:
        Exception: If critical database operations fail (graceful degradation)
    """
    # Check circuit breaker first
    if _circuit_breaker.should_reject():
        return {
            "workspace_info": {
                "workspace_database_path": None,
                "global_database_path": None,
                "total_messages": 0,
                "time_window_start": int(time.time() * 1000) - (24 * 60 * 60 * 1000),
                "time_window_end": int(time.time() * 1000),
                "time_window_strategy": "circuit_breaker_fallback",
                "strategy": "fallback",
                "commit_hash": None,
                "last_updated": datetime.now().isoformat(),
                "circuit_breaker_active": True,
                "error_info": {
                    "error_type": "CircuitBreakerOpen",
                    "message": "Circuit breaker is open due to repeated failures",
                    "category": "circuit_breaker"
                }
            },
            "chat_history": []
        }
    
    metrics = get_mcp_metrics()
    start_time = time.time()
    
    # Get current span if telemetry is available
    span = None
    if HAS_TELEMETRY and trace:
        span = trace.get_current_span()
    
    workspace_db_path = None
    global_db_path = None
    commit_hash = None
    time_window_strategy = "commit_based"
    start_timestamp_ms = None
    end_timestamp_ms = None
    
    try:
        # Step 1: Get commit hash for time window calculation
        try:
            if commit is not None:
                # Use provided commit object
                commit_hash = commit.hexsha
                if span:
                    span.set_attribute("cursor.commit_provided", True)
                if span:
                    span.set_attribute("cursor.commit_hash", commit_hash)
            else:
                # Fall back to detecting current commit (legacy behavior)
                commit_hash = get_current_commit_hash()
                if span:
                    span.set_attribute("cursor.commit_provided", False)
                if span:
                    span.set_attribute("cursor.commit_hash", commit_hash or "unknown")
        except Exception as e:
            # Fall back to 24-hour window if git operations fail
            time_window_strategy = "24_hour_fallback"
            current_time_ms = int(time.time() * 1000)
            start_timestamp_ms = current_time_ms - (24 * 60 * 60 * 1000)  # 24 hours ago
            end_timestamp_ms = current_time_ms
            if span:
                    span.set_attribute("cursor.commit_detected", False)
            if span:
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
            if span:
                    span.set_attribute("cursor.workspace_detected", bool(workspace_db_path))
            if span:
                    span.set_attribute("cursor.global_database_detected", bool(global_db_path))
            if span:
                    span.set_attribute("cursor.workspace_database_path", workspace_db_path or "none")
        except (WorkspaceDetectionError, CursorDatabaseError) as e:
            # Record failure in circuit breaker
            _circuit_breaker.record_failure()
            
            # Database not found - return graceful degradation with error info
            if span:
                    span.set_attribute("cursor.workspace_detected", False)
            if span:
                    span.set_attribute("cursor.detection_error", str(e))
            if span and HAS_TELEMETRY and Status and StatusCode:
                span.set_status(Status(StatusCode.ERROR, f"Workspace detection failed: {e}"))
            
            # Set telemetry error attributes
            if span:
                    span.set_attribute("error.type", e.__class__.__name__)
            if isinstance(e, CursorDatabaseNotFoundError):
                if span:
                    span.set_attribute("error.category", "database_not_found")
            elif isinstance(e, CursorDatabaseAccessError):
                if span:
                    span.set_attribute("error.category", "database_access")
            elif isinstance(e, CursorDatabaseSchemaError):
                if span:
                    span.set_attribute("error.category", "database_schema")
            elif isinstance(e, CursorDatabaseQueryError):
                if span:
                    span.set_attribute("error.category", "database_query")
            elif isinstance(e, WorkspaceDetectionError):
                if span:
                    span.set_attribute("error.category", "workspace_detection")
            else:
                if span:
                    span.set_attribute("error.category", "database_error")
            
            # Record exception for distributed tracing
            if span:
                span.record_exception(e)
            
            # Log error with context and troubleshooting hints
            context_info = getattr(e, 'context', {})
            path_info = context_info.get('path', 'unknown')
            log_message = f"Database detection failed: {e}"
            if path_info and path_info != 'unknown':
                log_message += f" (path: {path_info})"
                
            # Log as ERROR for database not found since it affects functionality significantly
            if isinstance(e, CursorDatabaseNotFoundError):
                logger.error(log_message, extra={
                    'error_type': e.__class__.__name__,
                    'error_category': 'database_detection',
                    'path': path_info,
                    'troubleshooting_hint': getattr(e, 'troubleshooting_hint', None)
                })
            else:
                logger.warning(log_message, extra={
                    'error_type': e.__class__.__name__,
                    'error_category': 'database_detection',
                    'path': path_info,
                    'troubleshooting_hint': getattr(e, 'troubleshooting_hint', None)
                })
            
            if metrics:
                metrics.record_counter(
                    "mcp.cursor.errors_total",
                    1,
                    attributes={"error_category": "workspace_detection"}
                )
            
            # Build error info from exception context
            error_info = {
                "error_type": e.__class__.__name__,
                "message": str(e),
                "category": "database_detection"
            }
            
            # Add specific context from exception if available
            if hasattr(e, 'context') and e.context:
                for key, value in e.context.items():
                    if key not in ['timestamp', 'platform', 'platform_version', 'python_version']:
                        error_info[key] = value
            
            # Handle WorkspaceDetectionError special attributes
            if isinstance(e, WorkspaceDetectionError):
                if hasattr(e, 'repo_path') and e.repo_path:
                    error_info['repo_path'] = e.repo_path
                if hasattr(e, 'candidates_scanned') and e.candidates_scanned is not None:
                    error_info['candidates_scanned'] = e.candidates_scanned
                if hasattr(e, 'fallback_attempted') and e.fallback_attempted is not None:
                    error_info['fallback_attempted'] = e.fallback_attempted
            
            # Add troubleshooting hint if available
            if hasattr(e, 'troubleshooting_hint') and e.troubleshooting_hint:
                error_info["troubleshooting_hint"] = e.troubleshooting_hint
            
            return {
                "workspace_info": {
                    "workspace_database_path": None,
                    "global_database_path": None,
                    "total_messages": 0,
                    "time_window_start": start_timestamp_ms,
                    "time_window_end": end_timestamp_ms,
                    "time_window_strategy": time_window_strategy,
                    "strategy": "fallback",  # Indicate fallback strategy used due to error
                    "commit_hash": commit_hash,
                    "last_updated": datetime.now().isoformat(),
                    "error_info": error_info
                },
                "chat_history": []
            }
        
        # Step 4: Create ComposerChatProvider and retrieve messages
        try:
            # Import here to avoid circular import
            from ..composer_chat_provider import ComposerChatProvider
            provider = ComposerChatProvider(workspace_db_path, global_db_path)
            chat_messages = provider.getChatHistoryForCommit(start_timestamp_ms, end_timestamp_ms)
            
            # Set success attributes
            if span:
                    span.set_attribute("cursor.messages_retrieved", len(chat_messages))
            if span:
                    span.set_attribute("cursor.database_type", "composer")
            if span:
                    span.set_attribute("cursor.success", True)
            
            # Record success in circuit breaker
            _circuit_breaker.record_success()
            
        except Exception as e:
            # Record failure in circuit breaker
            _circuit_breaker.record_failure()
            
            # Provider error - return graceful degradation with database paths preserved
            if span:
                    span.set_attribute("cursor.provider_error", str(e))
            if span and HAS_TELEMETRY and Status and StatusCode:
                span.set_status(Status(StatusCode.ERROR, f"Composer provider failed: {e}"))
            
            # Determine error category based on exception type
            error_category = "composer_provider"
            if isinstance(e, CursorDatabaseAccessError):
                error_category = "database_access"
            elif isinstance(e, CursorDatabaseSchemaError):
                error_category = "database_schema"
            elif isinstance(e, CursorDatabaseQueryError):
                error_category = "database_query"
            
            # Log error with context
            logger.error(f"Composer provider failed: {e}", extra={
                'error_type': e.__class__.__name__,
                'error_category': error_category,
                'workspace_database_path': workspace_db_path,
                'global_database_path': global_db_path,
                'troubleshooting_hint': getattr(e, 'troubleshooting_hint', None)
            })
            
            if metrics:
                metrics.record_counter(
                    "mcp.cursor.errors_total",
                    1,
                    attributes={"error_category": error_category}
                )
            
            # Build error info from exception context
            error_info = {
                "error_type": e.__class__.__name__,
                "message": str(e),
                "category": error_category
            }
            
            # Add specific context from exception if available
            if hasattr(e, 'context') and e.context:
                for key, value in e.context.items():
                    if key not in ['timestamp', 'platform', 'platform_version', 'python_version']:
                        error_info[key] = value
            
            # Add troubleshooting hint if available
            if hasattr(e, 'troubleshooting_hint') and e.troubleshooting_hint:
                error_info["troubleshooting_hint"] = e.troubleshooting_hint
            
            return {
                "workspace_info": {
                    "workspace_database_path": workspace_db_path,
                    "global_database_path": global_db_path,
                    "total_messages": 0,
                    "time_window_start": start_timestamp_ms,
                    "time_window_end": end_timestamp_ms,
                    "time_window_strategy": time_window_strategy,
                    "commit_hash": commit_hash,
                    "last_updated": datetime.now().isoformat(),
                    "error_info": error_info
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
            "chat_history": chat_messages  # Enhanced messages with timestamps, bubbleId, etc.
        }
        
    except Exception as e:
        # Record failure in circuit breaker
        _circuit_breaker.record_failure()
        
        # Ultimate fallback - graceful error handling
        error_category = "unknown"
        if isinstance(e, CursorDatabaseError):
            error_category = "database_error"
        elif isinstance(e, WorkspaceDetectionError):
            error_category = "workspace_detection"
        elif isinstance(e, (GitCommandError, BadName)):
            error_category = "git_error"
            
        span.set_attribute("error.category", error_category)
        if span and HAS_TELEMETRY and Status and StatusCode:
            span.set_status(Status(StatusCode.ERROR, str(e)))
        
        if metrics:
            metrics.record_counter(
                "mcp.cursor.errors_total",
                1,
                attributes={"error_category": error_category}
            )
        
        # Graceful degradation with comprehensive logging
        logger.error(f"Composer query failed: {e}", extra={
            'error_type': e.__class__.__name__,
            'error_category': error_category,
            'troubleshooting_hint': getattr(e, 'troubleshooting_hint', None)
        })
        
        # Build error info from exception context
        error_info = {
            "error_type": e.__class__.__name__,
            "message": str(e),
            "category": error_category
        }
        
        # Add specific context from exception if available
        if hasattr(e, 'context') and e.context:
            for key, value in e.context.items():
                if key not in ['timestamp', 'platform', 'platform_version', 'python_version']:
                    error_info[key] = value
        
        # Add troubleshooting hint if available
        if hasattr(e, 'troubleshooting_hint') and e.troubleshooting_hint:
            error_info["troubleshooting_hint"] = e.troubleshooting_hint
        
        return {
            "workspace_info": {
                "workspace_database_path": workspace_db_path if 'workspace_db_path' in locals() else None,
                "global_database_path": global_db_path if 'global_db_path' in locals() else None,
                "total_messages": 0,
                "time_window_start": start_timestamp_ms,
                "time_window_end": end_timestamp_ms,
                "time_window_strategy": "error_fallback",
                "strategy": "fallback",  # Indicate fallback strategy used due to error
                "commit_hash": commit_hash if 'commit_hash' in locals() else None,
                "last_updated": datetime.now().isoformat(),
                "error_info": error_info
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
    # Exception classes
    'CursorDatabaseError',
    'CursorDatabaseNotFoundError',
    'CursorDatabaseAccessError',
    'CursorDatabaseSchemaError',
    'CursorDatabaseQueryError',
    'WorkspaceDetectionError',
    'detect_workspace_for_repo',
    # Telemetry
    'tracer',
    # Circuit breaker
    'reset_circuit_breaker'
] 