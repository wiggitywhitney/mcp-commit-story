"""
Message reconstruction functionality for Cursor chat data.

This module provides the reconstruct_chat_history function that combines
user prompts and AI generations into a simple message list without
attempting to pair them chronologically.

Telemetry instrumentation tracks:
- Processing performance against 200ms threshold
- Message counts and data quality metrics
- Malformed data tracking for prompts and generations
"""

from typing import List, Dict, Any
import logging
import time

from opentelemetry import trace

from ..telemetry import trace_mcp_operation, PERFORMANCE_THRESHOLDS

logger = logging.getLogger(__name__)


@trace_mcp_operation("cursor_db.reconstruct_chat")
def reconstruct_chat_history(prompts: List[Dict[str, Any]], generations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Reconstruct chat history from a single database.
    
    Note: User prompts lack timestamps, so messages cannot be paired 
    chronologically. This function returns all messages without attempting 
    to match prompts to generations. The consuming AI will interpret the 
    conversation flow.
    
    Telemetry Metrics Tracked:
        - query_duration_ms: Time for message processing and formatting
        - prompt_count: Number of input prompts processed
        - generation_count: Number of input generations processed
        - malformed_prompts: Count of prompts missing required 'text' field
        - malformed_generations: Count of generations missing 'textDescription'
        - total_messages: Final message count after filtering
        - threshold_exceeded: Boolean if duration > 200ms threshold
    
    Threshold Rationale:
        200ms accounts for processing ~200 messages (100 prompts + 100 generations).
        Higher than extraction functions due to message formatting overhead.
    
    If generation_count == 100, the database may be at capacity.
    Additional messages might exist in other workspace databases.
    
    Args:
        prompts: List of prompt dicts from extract_prompts_data()
        generations: List of generation dicts from extract_generations_data()
        
    Returns:
        dict with 'messages' list and 'metadata' dict
    """
    start_time = time.time()
    span = trace.get_current_span()
    malformed_prompts = 0
    malformed_generations = 0
    
    messages = []
    
    # Process user prompts first (in extraction order)
    for prompt in prompts:
        # Skip malformed prompts that don't have 'text' field
        if 'text' not in prompt:
            malformed_prompts += 1
            logger.warning(f"Skipping malformed prompt data: missing 'text' field")
            continue
            
        user_message = {
            "role": "user",
            "content": prompt['text'],
            "timestamp": None,  # User prompts don't have timestamps
            "type": None       # User prompts don't have type
        }
        messages.append(user_message)
    
    # Process AI generations second (in extraction order)
    for generation in generations:
        # Skip malformed generations that don't have 'textDescription' field
        if 'textDescription' not in generation:
            malformed_generations += 1
            logger.warning(f"Skipping malformed generation data: missing 'textDescription' field")
            continue
            
        assistant_message = {
            "role": "assistant",
            "content": generation['textDescription'],
            "timestamp": generation.get('unixMs'),  # AI generations have timestamps
            "type": generation.get('type')          # AI generations have type (composer/apply)
        }
        messages.append(assistant_message)
    
    # Calculate duration and set telemetry attributes
    duration_ms = (time.time() - start_time) * 1000
    span.set_attribute("query_duration_ms", duration_ms)
    span.set_attribute("prompt_count", len(prompts))
    span.set_attribute("generation_count", len(generations))
    span.set_attribute("malformed_prompts", malformed_prompts)
    span.set_attribute("malformed_generations", malformed_generations)
    span.set_attribute("total_messages", len(messages))
    span.set_attribute("valid_messages", len(messages))  # Same as total_messages since malformed are excluded
    
    # Check performance threshold
    threshold = PERFORMANCE_THRESHOLDS["reconstruct_chat_history"]
    span.set_attribute("threshold_exceeded", duration_ms > threshold)
    if duration_ms > threshold:
        span.set_attribute("threshold_ms", threshold)
    
    # Create metadata with original counts (before any filtering)
    metadata = {
        "prompt_count": len(prompts),
        "generation_count": len(generations)
    }
    
    # Return simple structure with all messages and clean metadata
    return {
        "messages": messages,
        "metadata": metadata
    } 