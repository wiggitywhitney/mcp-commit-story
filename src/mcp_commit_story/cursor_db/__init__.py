"""
Cursor database integration package.

This package provides functionality for detecting, connecting to, and querying
Cursor's SQLite workspace databases across different platforms.
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional

from .platform import (
    PlatformType,
    CursorPathError,
    detect_platform,
    get_cursor_workspace_paths,
    validate_workspace_path,
    get_primary_workspace_path
)
from .query_executor import execute_cursor_query
from .message_extraction import (
    extract_prompts_data,
    extract_generations_data
)
from .message_reconstruction import reconstruct_chat_history
from .message_limiting import (
    limit_chat_messages,
    DEFAULT_MAX_HUMAN_MESSAGES,
    DEFAULT_MAX_AI_MESSAGES
)
from ..telemetry import trace_mcp_operation

@trace_mcp_operation("cursor_db.query_chat_database")
def query_cursor_chat_database() -> Dict:
    """
    Query the Cursor chat database and return complete chat history with workspace metadata.
    
    This function orchestrates all cursor_db components to provide a complete view of
    the chat history with workspace information. It's designed for Python interpreter
    execution (git hooks, background processes) rather than AI assistant interaction.
    
    The function auto-detects the primary Cursor workspace, constructs the database path,
    extracts prompts and generations data, and reconstructs the complete chat history
    with additional workspace metadata for automation workflows.
    
    Returns:
        Dict: Complete chat data with the following structure:
            {
                "workspace_info": {
                    "workspace_path": str | None,  # Auto-detected workspace path
                    "database_path": str | None,   # Constructed as workspace/.cursor/state.vscdb
                    "last_updated": str | None,    # ISO format timestamp of database modification
                    "total_messages": int          # Count of messages in chat_history
                },
                "chat_history": List[Dict]  # Complete message list from reconstruct_chat_history()
                    # Each message: {"role": str, "content": str, "timestamp": str, ...}
            }
    
    Examples:
        Basic usage in git hooks or automation scripts:
        
        >>> from mcp_commit_story.cursor_db import query_cursor_chat_database
        >>> 
        >>> # Get complete chat history with workspace metadata
        >>> result = query_cursor_chat_database()
        >>> 
        >>> # Check if workspace was found and has chat data
        >>> if result['workspace_info']['workspace_path']:
        ...     print(f"Found workspace: {result['workspace_info']['workspace_path']}")
        ...     print(f"Total messages: {result['workspace_info']['total_messages']}")
        ...     
        ...     # Process chat history if available
        ...     if result['workspace_info']['total_messages'] > 0:
        ...         for message in result['chat_history']:
        ...             print(f"{message['role']}: {message['content'][:50]}...")
        ... else:
        ...     print("No Cursor workspace detected")
        
        Integration in background processes:
        
        >>> import json
        >>> 
        >>> # Serialize for JSON output (e.g., for external tools)
        >>> result = query_cursor_chat_database()
        >>> json_output = json.dumps(result, indent=2)
        >>> 
        >>> # Use in conditional workflows
        >>> if result['workspace_info']['total_messages'] > 10:
        ...     # Process substantial chat history
        ...     pass
    
    Performance:
        - Target threshold: 500ms (sum of component operation thresholds)
        - Combines: workspace detection (auto), data extraction (~200ms), reconstruction (~200ms)
        - No caching in initial implementation for data freshness
        - Gracefully handles missing workspace/database without blocking
        - Performance metrics tracked via OpenTelemetry for monitoring
    
    Error Handling:
        This function never raises exceptions. Instead, it returns a well-formed
        empty structure with appropriate None values when errors occur:
        
        - No workspace detected: workspace_path=None, total_messages=0
        - Database file missing: database_path set but chat_history=[]
        - Database access errors: Returns empty chat_history, logs error in telemetry
        - Malformed data: Partial results with available data, errors tracked
        
        All errors are captured in telemetry spans for debugging and monitoring.
    
    Integration Notes:
        - Designed for git hooks: lightweight, no user interaction required
        - Suitable for background processes: graceful error handling, no exceptions
        - Auto-detection: no configuration needed, works across platforms
        - JSON-serializable output: compatible with external tool integration
        - Telemetry instrumented: performance and error tracking built-in
    """
    start_time = time.time()
    
    # Initialize empty result structure
    result = {
        "workspace_info": {
            "workspace_path": None,
            "database_path": None,
            "last_updated": None,
            "total_messages": 0
        },
        "chat_history": []
    }
    
    try:
        # Step 1: Get workspace path using existing function
        workspace_path = get_primary_workspace_path()
        if not workspace_path:
            return result
        
        workspace_str = str(workspace_path)
        result["workspace_info"]["workspace_path"] = workspace_str
        
        # Step 2: Construct database path inline (simple!)
        db_path = os.path.join(workspace_str, ".cursor", "state.vscdb")
        result["workspace_info"]["database_path"] = db_path
        
        # Step 3: Check if database exists
        if not os.path.exists(db_path):
            return result
        
        # Step 4: Get database last modified time
        try:
            last_modified = os.path.getmtime(db_path)
            result["workspace_info"]["last_updated"] = datetime.fromtimestamp(last_modified).isoformat()
        except (OSError, ValueError):
            pass  # Keep None if we can't get timestamp
        
        # Step 5: Extract data using existing functions
        prompts_data = extract_prompts_data(db_path)
        generations_data = extract_generations_data(db_path)
        
        # Step 6: Reconstruct chat history
        chat_history = reconstruct_chat_history(prompts_data, generations_data)
        result["chat_history"] = chat_history
        result["workspace_info"]["total_messages"] = len(chat_history)
        
        # Step 7: Add telemetry attributes
        try:
            from opentelemetry import trace
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.set_attribute("workspace_path", workspace_str)
                current_span.set_attribute("database_path", db_path)
                current_span.set_attribute("total_messages", len(chat_history))
                
                # Check performance threshold (500ms)
                duration_ms = (time.time() - start_time) * 1000
                current_span.set_attribute("query_duration_ms", int(duration_ms))
                current_span.set_attribute("threshold_exceeded", duration_ms > 500)
        except Exception:
            # Ignore telemetry errors
            pass
        
        return result
        
    except Exception as e:
        # Graceful error handling - return empty structure with telemetry
        try:
            from opentelemetry import trace
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.set_attribute("error.type", type(e).__name__)
                current_span.set_attribute("error.category", "database_access")
        except Exception:
            # Ignore telemetry errors
            pass
        
        return result

__all__ = [
    'PlatformType',
    'CursorPathError', 
    'detect_platform',
    'get_cursor_workspace_paths',
    'validate_workspace_path',
    'execute_cursor_query',
    'extract_prompts_data',
    'extract_generations_data',
    'reconstruct_chat_history',
    'limit_chat_messages',
    'DEFAULT_MAX_HUMAN_MESSAGES',
    'DEFAULT_MAX_AI_MESSAGES',
    'query_cursor_chat_database'
] 