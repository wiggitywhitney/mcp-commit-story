"""
Journal handlers for manual context capture and knowledge documentation.

This module provides handlers for capturing AI context and knowledge that can be
included in future journal entries, enabling developers to preserve insights
and knowledge across AI sessions.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .journal import get_journal_file_path, append_to_journal_file
from .config import load_config
from .telemetry import trace_mcp_operation, get_mcp_metrics
from .ai_invocation import invoke_ai


def _categorize_capture_context_error(error: Exception) -> str:
    """
    Categorize capture context operation errors for telemetry.
    
    Args:
        error: The exception that occurred
        
    Returns:
        Error category string for telemetry
    """
    if isinstance(error, PermissionError):
        return "permission_error"
    elif isinstance(error, OSError):
        return "file_system_error"
    elif isinstance(error, UnicodeError):
        return "encoding_error"
    elif isinstance(error, ValueError):
        return "validation_error"
    else:
        return "unknown_error"


def _record_capture_context_metrics(operation: str, duration: float, success: bool, 
                                   content_length: int = None, error_category: str = None) -> None:
    """
    Record comprehensive metrics for capture context operations.
    
    Args:
        operation: The operation being measured
        duration: Duration in seconds
        success: Whether the operation succeeded
        content_length: Length of captured content (optional)
        error_category: Error category if failed (optional)
    """
    metrics = get_mcp_metrics()
    if not metrics:
        return
    
    # Performance threshold warning (100ms as per telemetry standards)
    PERFORMANCE_THRESHOLD = 0.1  # 100ms
    if duration > PERFORMANCE_THRESHOLD:
        import logging
        logging.warning(f"Capture context operation '{operation}' took {duration:.3f}s (>{PERFORMANCE_THRESHOLD:.1f}s threshold)")
    
    # Record operation counter with attributes
    counter_attrs = {
        'operation': operation,
        'operation_type': 'manual_input',
        'content_type': 'ai_context',
        'status': 'success' if success else 'error'
    }
    
    if not success and error_category:
        counter_attrs['error_category'] = error_category
    
    if content_length is not None:
        counter_attrs['content_length'] = content_length
    
    metrics.record_counter('mcp.capture_context.operations_total', 1, attributes=counter_attrs)
    
    # Record duration
    metrics.record_operation_duration(
        'mcp.capture_context.duration_seconds',
        duration,
        operation_type='manual_input'
    )


def format_ai_knowledge_capture(knowledge_text: str) -> str:
    """
    Format AI knowledge capture with unified header format and separator.
    
    Args:
        knowledge_text: The AI knowledge content to format
        
    Returns:
        Formatted knowledge capture string with separator and unified header
        
    Format:
        \n\n____\n\n### H:MM AM/PM — AI Knowledge Capture\n\n[knowledge_text]
    """
    timestamp = datetime.now().strftime("%I:%M %p").lstrip('0')
    return f"\n\n____\n\n### {timestamp} — AI Knowledge Capture\n\n{knowledge_text}"


def generate_ai_knowledge_dump() -> str:
    """
    Generate a comprehensive AI knowledge dump using the approved prompt.
    
    Returns:
        AI-generated knowledge dump or fallback message on error
    """
    approved_prompt = """Provide a comprehensive knowledge capture of your current understanding of this project, recent development insights, and key context that would help a fresh AI understand where we are and how we got here. Focus on context that would be valuable for future journal entries."""
    
    try:
        return invoke_ai(approved_prompt, {})
    except Exception as e:
        # Return fallback message on AI failure
        return f"Unable to generate AI knowledge dump due to error: {str(e)}"


@trace_mcp_operation("capture_context.handle_journal", attributes={
    "operation_type": "manual_input",
    "content_type": "ai_context"
})
def handle_journal_capture_context(text: Optional[str]) -> Dict[str, Any]:
    """
    Handle requests to capture AI context for journal entries.
    
    This function supports dual-mode operation to accommodate both manual input
    and automated AI knowledge dumping. Uses the unified journal header format
    with separator (____) for consistency across all journal entry types.
    
    Technical decisions:
    - Dual-mode design allows flexibility for both user-driven and AI-driven context capture
    - Returns structured Dict rather than raising exceptions for better MCP integration
    - Leverages existing journal infrastructure (append_to_journal_file, get_journal_file_path)
    - Includes comprehensive telemetry for operation monitoring and debugging
    
    Args:
        text: Optional text to capture. If None, generates AI knowledge dump
        
    Returns:
        Dict with status, file_path, and optional error
        
    Example:
        # Capture provided text
        result = handle_journal_capture_context("Important context to remember")
        
        # Generate AI knowledge dump
        result = handle_journal_capture_context(None)
        
        # Handle response
        if result["status"] == "success":
            print(f"Context saved to {result['file_path']}")
        else:
            print(f"Error: {result['error']}")
    """
    start_time = time.time()
    
    try:
        # Add span attributes for telemetry
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("capture_context.mode", "ai_dump" if text is None else "user_text")
        
        # Handle dual-mode operation
        if text is None:
            # No text provided - generate AI knowledge dump
            text = generate_ai_knowledge_dump()
            mode = "ai_dump"
        elif not text.strip():
            # Empty text parameter
            return {
                "status": "error",
                "file_path": None,
                "error": "Text parameter cannot be empty"
            }
        else:
            mode = "user_text"
        
        # Add content attributes to span
        if current_span:
            current_span.set_attribute("capture_context.content_length", len(text))
        
        # Load configuration
        config = load_config()
        
        # Determine today's journal file path
        today = datetime.now().strftime("%Y-%m-%d")
        relative_file_path = get_journal_file_path(today, "daily")
        
        # Fix double "journal/" prefix bug similar to reflection_core.py
        if relative_file_path.startswith("journal/"):
            relative_file_path = relative_file_path[8:]  # Remove "journal/" prefix
        
        journal_path = Path(config.journal_path) / relative_file_path
        
        # Format the captured context with unified header format
        formatted_context = format_ai_knowledge_capture(text)
        
        # Append to journal file using existing infrastructure
        append_to_journal_file(formatted_context, str(journal_path))
        
        # Record success metrics
        duration = time.time() - start_time
        _record_capture_context_metrics(
            operation="capture_context",
            duration=duration,
            success=True,
            content_length=len(text)
        )
        
        return {
            "status": "success",
            "file_path": str(journal_path),
            "error": None
        }
        
    except Exception as e:
        # Record error metrics
        error_category = _categorize_capture_context_error(e)
        duration = time.time() - start_time
        _record_capture_context_metrics(
            operation="capture_context",
            duration=duration,
            success=False,
            content_length=len(text) if text else 0,
            error_category=error_category
        )
        
        # Add error attributes to span
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("error.category", error_category)
        
        return {
            "status": "error",
            "file_path": None,
            "error": str(e)
        } 