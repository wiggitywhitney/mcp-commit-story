"""
AI Function Executor for Journal Generation

Executes AI functions by using their docstrings as prompts and parsing
the responses into appropriate return types. Follows approved design decisions:
- JSON context injection format
- Minimal parsing strategy
- Empty default values matching existing stubs
"""

import json
import inspect
import logging
from typing import Any, Callable, Dict, Union
import re

from .ai_invocation import invoke_ai
from .context_types import (
    JournalContext,
    SummarySection,
    TechnicalSynopsisSection, 
    AccomplishmentsSection,
    FrustrationsSection,
    ToneMoodSection,
    DiscussionNotesSection,
    CommitMetadataSection
)

logger = logging.getLogger(__name__)


def execute_ai_function(func: Callable, journal_context: JournalContext) -> Any:
    """
    Execute function by passing its docstring as prompt to AI.
    
    Args:
        func: Function with docstring to use as AI prompt
        journal_context: Journal context data to provide to AI
        
    Returns:
        Appropriate section type based on function name, or default values on failure
        
    Uses approved design decisions:
    - JSON context injection for clean object structure access
    - Minimal parsing strategy trusting AI to follow detailed prompts
    - Empty default values matching existing stub implementations
    """
    try:
        # Extract docstring using inspect.getdoc
        prompt = inspect.getdoc(func)
        if not prompt:
            logger.warning(f"Function {func.__name__} has no docstring")
            return _get_default_result(func.__name__)
        
        # Format context as JSON
        context_json = json.dumps(journal_context, indent=2, default=str)
        full_prompt = f"{prompt}\n\nThe journal_context object has the following structure:\n```json\n{context_json}\n```"
        
        # Call AI (from Task 57.2)
        response = invoke_ai(full_prompt, {})
        
        # Parse with minimal logic
        return parse_response(func.__name__, response)
        
    except Exception as e:
        logger.warning(f"AI function execution failed for {func.__name__}: {e}")
        return _get_default_result(func.__name__)


def parse_response(func_name: str, ai_response: str) -> Union[Dict[str, Any], Any]:
    """
    Parse AI response based on function name using minimal parsing strategy.
    
    Args:
        func_name: Name of the function to determine return type
        ai_response: Raw AI response text
        
    Returns:
        Parsed result matching the function's expected return type
    """
    if not ai_response or not ai_response.strip():
        return _get_default_result(func_name)
    
    try:
        response = ai_response.strip()
        
        # Minimal parsing logic based on function name
        if func_name == "generate_summary_section":
            return SummarySection(summary=response)
            
        elif func_name == "generate_technical_synopsis_section":
            return TechnicalSynopsisSection(technical_synopsis=response)
            
        elif func_name == "generate_accomplishments_section":
            # Split by newlines, minimal cleanup
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return AccomplishmentsSection(accomplishments=lines)
            
        elif func_name == "generate_frustrations_section":
            # Split by newlines, minimal cleanup
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return FrustrationsSection(frustrations=lines)
            
        elif func_name == "generate_tone_mood_section":
            # Simple pattern matching for "Mood: X" and "Indicators: Y"
            mood = ""
            indicators = ""
            
            # Look for mood pattern
            mood_match = re.search(r'mood:\s*(.+?)(?:\n|$)', response, re.IGNORECASE | re.MULTILINE)
            if mood_match:
                mood = mood_match.group(1).strip()
            
            # Look for indicators pattern  
            indicators_match = re.search(r'indicators:\s*(.+?)(?:\n|$)', response, re.IGNORECASE | re.MULTILINE)
            if indicators_match:
                indicators = indicators_match.group(1).strip()
            
            # If no patterns found, use sections of response
            if not mood and not indicators:
                lines = [line.strip() for line in response.split('\n') if line.strip()]
                if len(lines) >= 1:
                    mood = lines[0]
                if len(lines) >= 2:
                    indicators = lines[1]
            
            return ToneMoodSection(mood=mood, indicators=indicators)
            
        elif func_name == "generate_discussion_notes_section":
            # Split by newlines, minimal cleanup
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            return DiscussionNotesSection(discussion_notes=lines)
            
        elif func_name == "generate_commit_metadata_section":
            # For metadata, try to parse key-value pairs, fallback to empty dict
            metadata = {}
            try:
                # Look for key: value patterns
                for line in response.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
            except Exception:
                # Fallback to empty metadata on parse failure
                pass
            return CommitMetadataSection(commit_metadata=metadata)
            
        else:
            logger.warning(f"Unknown function name for parsing: {func_name}")
            return _get_default_result(func_name)
            
    except Exception as e:
        logger.warning(f"Failed to parse response for {func_name}: {e}")
        return _get_default_result(func_name)


def _get_default_result(func_name: str) -> Union[Dict[str, Any], Any]:
    """
    Get default empty result matching existing stub implementations.
    
    Uses same defaults as existing stub implementations in journal.py (lines 934-1486):
    - SummarySection(summary="")
    - AccomplishmentsSection(accomplishments=[])
    - etc.
    """
    if func_name == "generate_summary_section":
        return SummarySection(summary="")
        
    elif func_name == "generate_technical_synopsis_section":
        return TechnicalSynopsisSection(technical_synopsis="")
        
    elif func_name == "generate_accomplishments_section":
        return AccomplishmentsSection(accomplishments=[])
        
    elif func_name == "generate_frustrations_section":
        return FrustrationsSection(frustrations=[])
        
    elif func_name == "generate_tone_mood_section":
        return ToneMoodSection(mood="", indicators="")
        
    elif func_name == "generate_discussion_notes_section":
        return DiscussionNotesSection(discussion_notes=[])
        
    elif func_name == "generate_commit_metadata_section":
        return CommitMetadataSection(commit_metadata={})
        
    else:
        # Fallback for unknown function types
        logger.warning(f"No default result defined for function: {func_name}")
        return {} 