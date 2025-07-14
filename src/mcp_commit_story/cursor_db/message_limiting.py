"""
Message limiting functionality for cursor_db package.

This module provides message count limiting designed for solo developer usage patterns.
Based on research showing typical usage of ~35 human/35 AI messages per database,
the default limits of 200/200 act as a safety net against edge cases without
impacting normal development workflows.

Research findings:
- 910 total messages analyzed across 7 databases
- 457 human messages (50.2%), 453 AI messages (49.8%)
- Conservative 200/200 limits provide significant safety margin
- Designed to protect against automation/testing edge cases
"""

from typing import Dict, List, Any, Optional
import copy
from ..telemetry import trace_mcp_operation


# Default limits based on performance research for message filtering
# These values cover even intense development periods while acting as safety net
DEFAULT_MAX_HUMAN_MESSAGES = 200
DEFAULT_MAX_AI_MESSAGES = 200


@trace_mcp_operation("chat.limit_messages")
def limit_chat_messages(
    chat_history: Dict[str, Any], 
    max_human_messages: int, 
    max_ai_messages: int
) -> Dict[str, Any]:
    """
    Limit chat history to specified maximum message counts by role.
    
    Keeps the most recent messages when truncation is needed, maintaining
    chronological order. Designed for solo developer usage patterns where
    200/200 limits provide safety net against edge cases.
    
    Args:
        chat_history: Dictionary with 'messages' list and optional 'metadata'
        max_human_messages: Maximum number of human messages to keep
        max_ai_messages: Maximum number of AI messages to keep
    
    Returns:
        Dictionary with limited messages and metadata including truncation info:
        {
            'messages': [...],  # Limited message list
            'metadata': {
                'truncated_human': bool,
                'truncated_ai': bool, 
                'removed_human_count': int,
                'removed_ai_count': int,
                'original_human_count': int,
                'original_ai_count': int,
                # ... any existing metadata preserved
            }
        }
    
    Examples:
        >>> history = {'messages': [{'role': 'user', 'content': 'Hi'}]}
        >>> limited = limit_chat_messages(history, 100, 100)
        >>> limited['metadata']['truncated_human']  # False - under limit
        False
    """
    # Get current telemetry span for setting attributes
    from opentelemetry import trace
    span = trace.get_current_span()
    
    # Handle missing or malformed input
    if not isinstance(chat_history, dict):
        chat_history = {}
    
    messages = chat_history.get('messages', [])
    existing_metadata = chat_history.get('metadata', {})
    
    # Handle missing messages gracefully
    if not isinstance(messages, list):
        messages = []
    
    # Separate messages by role
    human_messages = []
    ai_messages = []
    other_messages = []  # Messages with unexpected/missing roles
    
    for msg in messages:
        if not isinstance(msg, dict):
            continue
            
        role = msg.get('role', '')
        if role == 'user':
            human_messages.append(msg)
        elif role == 'assistant':
            ai_messages.append(msg)
        else:
            # Preserve messages with other/missing roles
            other_messages.append(msg)
    
    # Count original messages
    original_human_count = len(human_messages)
    original_ai_count = len(ai_messages)
    
    # Set telemetry attributes
    span.set_attribute("original_message_count", len(messages))
    span.set_attribute("human_message_count", original_human_count)
    span.set_attribute("ai_message_count", original_ai_count)
    
    # Determine if truncation is needed
    human_truncated = original_human_count > max_human_messages
    ai_truncated = original_ai_count > max_ai_messages
    
    # Keep most recent messages (end of list)
    # Handle zero limits properly - empty slice when limit is 0
    if max_human_messages == 0:
        kept_human_messages = []
        removed_human_count = original_human_count
    elif human_truncated:
        kept_human_messages = human_messages[-max_human_messages:]
        removed_human_count = original_human_count - max_human_messages
    else:
        kept_human_messages = human_messages
        removed_human_count = 0
    
    if max_ai_messages == 0:
        kept_ai_messages = []
        removed_ai_count = original_ai_count
    elif ai_truncated:
        kept_ai_messages = ai_messages[-max_ai_messages:]
        removed_ai_count = original_ai_count - max_ai_messages
    else:
        kept_ai_messages = ai_messages
        removed_ai_count = 0
    
    # Recombine messages while maintaining chronological order
    # We need to merge the kept messages back into chronological order
    all_kept_messages = kept_human_messages + kept_ai_messages + other_messages
    
    # Sort by original index to maintain chronological order
    # Create a mapping of message content to original index
    original_indices = {}
    for i, msg in enumerate(messages):
        # Use message content as key (assuming it's unique enough)
        key = (msg.get('role', ''), msg.get('content', ''), str(msg))
        original_indices[key] = i
    
    def get_original_index(msg):
        key = (msg.get('role', ''), msg.get('content', ''), str(msg))
        return original_indices.get(key, float('inf'))
    
    final_messages = sorted(all_kept_messages, key=get_original_index)
    
    # Set telemetry attributes for truncation
    span.set_attribute("human_truncated", human_truncated)
    span.set_attribute("ai_truncated", ai_truncated)
    span.set_attribute("removed_human_count", removed_human_count)
    span.set_attribute("removed_ai_count", removed_ai_count)
    
    # Create result with preserved metadata plus truncation info
    result_metadata = copy.deepcopy(existing_metadata)
    result_metadata.update({
        'truncated_human': human_truncated,
        'truncated_ai': ai_truncated,
        'removed_human_count': removed_human_count,
        'removed_ai_count': removed_ai_count,
        'original_human_count': original_human_count,
        'original_ai_count': original_ai_count
    })
    
    return {
        'messages': final_messages,
        'metadata': result_metadata
    } 