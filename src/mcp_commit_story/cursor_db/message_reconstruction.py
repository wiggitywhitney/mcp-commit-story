"""
Message reconstruction functionality for Cursor chat data.

This module provides the reconstruct_chat_history function that combines
user prompts and AI generations into a simple message list without
attempting to pair them chronologically.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def reconstruct_chat_history(prompts: List[Dict[str, Any]], generations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Reconstruct chat history from a single database.
    
    Note: User prompts lack timestamps, so messages cannot be paired 
    chronologically. This function returns all messages without attempting 
    to match prompts to generations. The consuming AI will interpret the 
    conversation flow.
    
    If generation_count == 100, the database may be at capacity.
    Additional messages might exist in other workspace databases.
    
    Args:
        prompts: List of prompt dicts from extract_prompts_data()
        generations: List of generation dicts from extract_generations_data()
        
    Returns:
        dict with 'messages' list and 'metadata' dict
    """
    messages = []
    
    # Process user prompts first (in extraction order)
    for prompt in prompts:
        # Skip malformed prompts that don't have 'text' field
        if 'text' not in prompt:
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
            logger.warning(f"Skipping malformed generation data: missing 'textDescription' field")
            continue
            
        assistant_message = {
            "role": "assistant",
            "content": generation['textDescription'],
            "timestamp": generation.get('unixMs'),  # AI generations have timestamps
            "type": generation.get('type')          # AI generations have type (composer/apply)
        }
        messages.append(assistant_message)
    
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