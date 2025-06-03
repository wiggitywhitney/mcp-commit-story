"""Core reflection functionality for manual reflection addition.

This module provides the core components for adding manual reflections to journal entries:
- format_reflection: Formats reflection text with timestamp and proper structure
- add_reflection_to_journal: Adds formatted reflection to journal files with proper separation
- add_manual_reflection: Main entry point for adding manual reflections with config loading

The implementation follows the on-demand directory creation pattern and uses \n\n separation
for sections as established in the existing codebase. All operations are instrumented with
comprehensive telemetry including duration tracking, error categorization, and span attributes.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Union, Dict, Any

# Import existing directory utility and telemetry
from .journal import ensure_journal_directory, get_journal_file_path
from .config import load_config
from .telemetry import trace_mcp_operation, get_mcp_metrics


def _categorize_reflection_error(error: Exception) -> str:
    """
    Categorize reflection operation errors for telemetry.
    
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
        if "date" in str(error).lower():
            return "invalid_date_format"
        return "validation_error"
    else:
        return "unknown_error"


def _validate_reflection_date(date_str: str) -> bool:
    """
    Validate reflection date format and constraints.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If date format is invalid or date is in the future
    """
    import re
    from datetime import datetime, date
    
    # Check format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
    
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        raise ValueError(f"Invalid date: {date_str}. {str(e)}")
    
    # Check if date is in the future
    today = date.today()
    if parsed_date > today:
        raise ValueError(f"Future date not allowed: {date_str}. Reflections can only be added for today or past dates")
    
    return True


def _record_reflection_metrics(operation: str, duration: float, success: bool, 
                              content_length: int = None, error_category: str = None) -> None:
    """
    Record comprehensive metrics for reflection operations with performance warnings.
    
    Args:
        operation: The operation being measured
        duration: Duration in seconds
        success: Whether the operation succeeded
        content_length: Length of reflection content (optional)
        error_category: Error category if failed (optional)
    """
    metrics = get_mcp_metrics()
    if not metrics:
        return
    
    # Performance threshold warning (100ms as approved)
    PERFORMANCE_THRESHOLD = 0.1  # 100ms
    if duration > PERFORMANCE_THRESHOLD:
        import logging
        logging.warning(f"Reflection operation '{operation}' took {duration:.3f}s (>{PERFORMANCE_THRESHOLD:.1f}s threshold)")
    
    # Record operation counter with attributes
    counter_attrs = {
        'operation': operation,
        'operation_type': 'manual_input',
        'content_type': 'reflection',
        'status': 'success' if success else 'error'
    }
    
    if not success and error_category:
        counter_attrs['error_category'] = error_category
    
    if content_length is not None:
        counter_attrs['content_length'] = content_length
    
    metrics.record_counter('mcp.reflection.operations_total', **counter_attrs)
    
    # Record duration
    metrics.record_operation_duration(
        'mcp.reflection.duration_seconds',
        duration,
        operation=operation,
        operation_type='manual_input'
    )


def format_reflection(reflection_text: str) -> str:
    """
    Format a reflection with timestamp and proper structure.
    
    Args:
        reflection_text: The user's reflection content
        
    Returns:
        Formatted reflection string with H2 header, timestamp, and double newlines
        
    Format:
        \n\n## Reflection (YYYY-MM-DD HH:MM:SS)\n\n[reflection_text]
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"\n\n## Reflection ({timestamp})\n\n{reflection_text}"


@trace_mcp_operation("reflection.add_to_journal", attributes={
    "operation_type": "file_write", 
    "content_type": "reflection",
    "file_type": "markdown"
})
def add_reflection_to_journal(journal_path: Union[str, Path], reflection_text: str) -> bool:
    """
    Add a reflection to a journal entry file with telemetry instrumentation.
    
    This function follows the on-demand directory creation pattern and uses \n\n
    separation for sections as established in the existing codebase.
    
    Args:
        journal_path: Path to the journal file (will be created if doesn't exist)
        reflection_text: The reflection content to add
        
    Returns:
        True if successful
        
    Raises:
        OSError: If directory creation or file writing fails
    """
    start_time = time.time()
    error_category = None
    
    try:
        # Add span attributes for telemetry
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("file.path", Path(journal_path).name)  # Only filename for privacy
            current_span.set_attribute("file.extension", Path(journal_path).suffix)
            current_span.set_attribute("reflection.content_length", len(reflection_text))
        
        # Ensure parent directory exists using existing utility
        ensure_journal_directory(journal_path)
        
        # Format the reflection
        formatted_reflection = format_reflection(reflection_text)
        
        # Append to file with UTF-8 encoding
        with open(journal_path, 'a', encoding='utf-8') as f:
            f.write(formatted_reflection)
        
        # Record success metrics
        duration = time.time() - start_time
        _record_reflection_metrics(
            operation="add_to_journal",
            duration=duration,
            success=True,
            content_length=len(reflection_text)
        )
        
        return True
        
    except Exception as e:
        # Record error metrics
        error_category = _categorize_reflection_error(e)
        duration = time.time() - start_time
        _record_reflection_metrics(
            operation="add_to_journal",
            duration=duration,
            success=False,
            content_length=len(reflection_text),
            error_category=error_category
        )
        
        # Add error attributes to span
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("error.category", error_category)
        
        raise


@trace_mcp_operation("reflection.add_manual", attributes={
    "operation_type": "manual_input",
    "content_type": "reflection"
})
def add_manual_reflection(reflection_text: str, date: str) -> Dict[str, Any]:
    """
    Add a manual reflection to the journal for a specific date.
    
    This is the main entry point for adding manual reflections, providing
    comprehensive telemetry and error handling. Returns structured responses
    rather than raising exceptions for better MCP integration.
    
    Leverages existing journal infrastructure including get_journal_file_path()
    and ensure_journal_directory() functions.
    
    Args:
        reflection_text: The reflection content to add
        date: Date in YYYY-MM-DD format
        
    Returns:
        Dict with status, file_path, and optional error
        
    Example:
        result = add_manual_reflection("Today was productive", "2025-01-02")
        if result["status"] == "success":
            print(f"Reflection added to {result['file_path']}")
    """
    start_time = time.time()
    
    try:
        # Validate date format and constraints first
        _validate_reflection_date(date)
        
        # Add span attributes for telemetry
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("reflection.date", date)
        
        # Load configuration
        config = load_config()
        
        # Use existing get_journal_file_path function (as per implementation notes)
        relative_file_path = get_journal_file_path(date, "daily")
        
        # Fix double "journal/" prefix bug: get_journal_file_path returns "journal/daily/..."
        # but config.journal_path is also "journal", so we need to remove the prefix
        if relative_file_path.startswith("journal/"):
            relative_file_path = relative_file_path[8:]  # Remove "journal/" prefix
        
        journal_path = Path(config.journal_path) / relative_file_path
        
        # Add reflection to journal using existing infrastructure
        add_reflection_to_journal(journal_path, reflection_text)
        
        # Record success metrics
        duration = time.time() - start_time
        _record_reflection_metrics(
            operation="add_manual",
            duration=duration,
            success=True,
            content_length=len(reflection_text)
        )
        
        return {
            "status": "success",
            "file_path": str(journal_path),
            "error": None
        }
        
    except Exception as e:
        # Record error metrics
        error_category = _categorize_reflection_error(e)
        duration = time.time() - start_time
        _record_reflection_metrics(
            operation="add_manual",
            duration=duration,
            success=False,
            content_length=len(reflection_text),
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