"""
Chat Context Manager for Enhanced Journal Generation.

This module provides enhanced chat context collection functionality that builds
upon the existing cursor_db integration to provide richer metadata for journal
generation, including time windows, session names, and performance monitoring.
"""

import logging
from typing import List, Dict, Any, Union, Optional

from .cursor_db import query_cursor_chat_database
from .context_types import ChatMessage, TimeWindow, ChatContextData
from .telemetry import trace_mcp_operation

logger = logging.getLogger(__name__)


@trace_mcp_operation("extract_chat_for_commit")
def extract_chat_for_commit() -> ChatContextData:
    """Extract enhanced chat context for the current commit with metadata.
    
    This function serves as a thin orchestration layer that calls the existing
    query_cursor_chat_database function and transforms the response into the
    enhanced ChatContextData format with additional metadata.
    
    Returns:
        ChatContextData: Enhanced chat context with time window, session names,
                        and metadata for journal generation.
                        Returns empty data structure on any errors.
    
    Performance:
        Designed to complete under 500ms threshold for responsive journal generation.
        
    Telemetry:
        Creates spans and attributes for monitoring chat context collection performance.
        Works with or without OpenTelemetry installed.
    """
    try:
        # Call existing cursor_db functionality
        logger.debug("Calling query_cursor_chat_database for chat context")
        raw_data = query_cursor_chat_database()
        
        # Transform the response data
        transformed_data = _transform_chat_data(raw_data)
        
        logger.info(
            f"Successfully extracted {len(transformed_data['messages'])} messages "
            f"from {len(transformed_data['session_names'])} sessions"
        )
        
        return transformed_data
        
    except Exception as e:
        logger.warning(f"Failed to extract chat context: {e}", extra={
            'error_type': e.__class__.__name__,
            'error_category': 'chat_context_extraction',
            'troubleshooting_hint': getattr(e, 'troubleshooting_hint', None)
        })
        
        # Build error info for metadata
        error_info = {
            "error_type": e.__class__.__name__,
            "message": str(e),
            "category": "chat_context_extraction"
        }
        
        # Add specific context from exception if available
        if hasattr(e, 'context') and e.context:
            for key, value in e.context.items():
                if key not in ['timestamp', 'platform', 'platform_version', 'python_version']:
                    error_info[key] = value
        
        # Add troubleshooting hint if available
        if hasattr(e, 'troubleshooting_hint') and e.troubleshooting_hint:
            error_info["troubleshooting_hint"] = e.troubleshooting_hint
        
        # Return empty ChatContextData with error info for graceful degradation
        return _create_empty_chat_context_data(error_info=error_info)


def _transform_chat_data(raw_data: Dict[str, Any]) -> ChatContextData:
    """Transform raw query response to enhanced ChatContextData format.
    
    Args:
        raw_data: Response from query_cursor_chat_database containing 'chat_history'
                 and 'workspace_info' keys.
                 
    Returns:
        ChatContextData: Transformed data with enhanced metadata.
    """
    chat_history = raw_data.get('chat_history', [])
    workspace_info = raw_data.get('workspace_info', {})
    
    # Transform messages from role/content to speaker/text format
    messages = []
    session_names = set()
    
    for msg in chat_history:
        # Skip malformed messages
        if not msg.get('role') or not msg.get('content'):
            logger.debug(f"Skipping malformed message: {msg}")
            continue
            
        # Transform role to speaker format
        speaker = _transform_role_to_speaker(msg['role'])
        if not speaker:
            logger.debug(f"Skipping message with unknown role: {msg['role']}")
            continue
            
        # Build enhanced ChatMessage
        enhanced_message = ChatMessage(
            speaker=speaker,
            text=msg['content']
        )
        
        # Add optional fields if available
        if 'timestamp' in msg:
            enhanced_message['timestamp'] = msg['timestamp']
            

            
        messages.append(enhanced_message)
    
    # Build time window from workspace_info
    time_window = _build_time_window(workspace_info)
    
    # Gather metadata
    metadata = {
        'message_count': len(messages),
        'source': 'cursor_chat_database',
        'has_timestamps': any('timestamp' in msg for msg in messages),
        'has_session_names': len(session_names) > 0
    }
    
    return ChatContextData(
        messages=messages,
        time_window=time_window,
        session_names=list(session_names),
        metadata=metadata
    )


def _transform_role_to_speaker(role: str) -> Optional[str]:
    """Transform chat role to speaker format.
    
    Args:
        role: Raw role from chat system (e.g., 'user', 'assistant')
        
    Returns:
        Optional[str]: Transformed speaker ('Human', 'Assistant') or None if unknown
    """
    role_mapping = {
        'user': 'Human',
        'assistant': 'Assistant'
    }
    return role_mapping.get(role.lower())


def _build_time_window(workspace_info: Dict[str, Any]) -> TimeWindow:
    """Build TimeWindow from workspace_info data.
    
    Args:
        workspace_info: Workspace information from query_cursor_chat_database
        
    Returns:
        TimeWindow: Time window information with calculated duration
    """
    start_ms = workspace_info.get('start_timestamp_ms', 0)
    end_ms = workspace_info.get('end_timestamp_ms', 0)
    strategy = workspace_info.get('strategy', 'fallback')
    
    # Calculate duration in hours
    duration_hours = 0.0
    if start_ms and end_ms and end_ms > start_ms:
        duration_ms = end_ms - start_ms
        duration_hours = duration_ms / (1000 * 60 * 60)  # Convert ms to hours
    
    return TimeWindow(
        start_timestamp_ms=start_ms,
        end_timestamp_ms=end_ms,
        strategy=strategy,
        duration_hours=duration_hours
    )


def _create_empty_chat_context_data(error_info: Optional[Dict[str, Any]] = None) -> ChatContextData:
    """Create empty ChatContextData for graceful error handling.
    
    Args:
        error_info: Optional error information to include in metadata
    
    Returns:
        ChatContextData: Empty data structure with fallback time window and optional error info
    """
    fallback_time_window = TimeWindow(
        start_timestamp_ms=0,
        end_timestamp_ms=0,
        strategy='fallback',
        duration_hours=0.0
    )
    
    metadata = {}
    if error_info:
        metadata['error_info'] = error_info
    
    return ChatContextData(
        messages=[],
        time_window=fallback_time_window,
        session_names=[],
        metadata=metadata
    ) 