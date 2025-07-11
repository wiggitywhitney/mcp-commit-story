"""
Shared AI utilities for journal section generation.

This module provides utilities for AI-powered journal section generation,
replacing the ai_function_executor.py abstraction layer with direct API calls.
"""

import json
import logging
from typing import Dict, Any, Optional
from mcp_commit_story.context_types import JournalContext

logger = logging.getLogger(__name__)


def format_ai_prompt(docstring: str, context: Optional[JournalContext]) -> str:
    """
    Format AI prompt with JSON context for direct invocation.
    
    This function replaces the ai_function_executor.py abstraction layer
    by providing a simple way to format prompts for direct OpenAI API calls.
    
    Args:
        docstring: The prompt text (usually from a function's docstring)
        context: Journal context data to provide to AI, or None
        
    Returns:
        Formatted prompt string ready for AI invocation
        
    Examples:
        >>> context = JournalContext(git={'metadata': {'hash': 'abc123'}}, chat=None, journal=None)
        >>> prompt = format_ai_prompt("Generate a summary", context)
        >>> print(prompt)
        Generate a summary
        
        The journal_context object has the following structure:
        ```json
        {
          "git": {
            "metadata": {
              "hash": "abc123"
            }
          },
          "chat": null,
          "journal": null
        }
        ```
    """
    try:
        # Start with the docstring
        if not docstring:
            docstring = ""
        
        # Handle None context gracefully
        if context is None:
            context_json = json.dumps(None, indent=2)
        else:
            # Format context as JSON with proper indentation
            context_json = json.dumps(context, indent=2, default=str)
        
        # Format the complete prompt using the same structure as ai_function_executor
        full_prompt = f"{docstring}\n\nThe journal_context object has the following structure:\n```json\n{context_json}\n```"
        
        return full_prompt
        
    except Exception as e:
        logger.warning(f"Error formatting AI prompt: {e}")
        # Fallback to basic formatting
        return f"{docstring}\n\nContext: {str(context)}" 