"""
Telemetry utilities for journal operations.

Contains utility functions for consistent telemetry and logging across journal operations.
"""
import os
import logging
from typing import Any
from ..telemetry import get_mcp_metrics

logger = logging.getLogger(__name__)


def _add_ai_generation_telemetry(section_type: str, journal_context, start_time: float):
    """
    Utility function to add consistent telemetry for AI generation operations.
    
    Args:
        section_type: The type of section being generated (e.g., 'summary', 'accomplishments')
        journal_context: The journal context being processed
        start_time: The timestamp when generation started
    """
    from opentelemetry import trace
    
    # Add semantic conventions for AI generation telemetry
    current_span = trace.get_current_span()
    if current_span:
        # Calculate context size
        context_size = 0
        if journal_context:
            if hasattr(journal_context, 'chat_history') and journal_context.get('chat_history'):
                context_size += len(journal_context['chat_history'].get('messages', []))

            if hasattr(journal_context, 'file_changes') and journal_context.get('file_changes'):
                context_size += len(journal_context['file_changes'])
        
        current_span.set_attribute("journal.context_size", context_size)
        current_span.set_attribute("journal.entry_id", journal_context.get('commit_hash', 'unknown') if journal_context else 'unknown')
        # AI model info would be added here if available from context


def _record_ai_generation_metrics(section_type: str, duration: float, success: bool, error_category: str = None):
    """
    Utility function to record AI generation metrics consistently.
    
    Args:
        section_type: The type of section being generated
        duration: Time taken for generation
        success: Whether the operation succeeded
        error_category: Category of error if operation failed
    """
    from opentelemetry import trace
    
    metrics = get_mcp_metrics()
    if metrics:
        if success:
            metrics.record_operation_duration(
                "journal.ai_generation_duration_seconds",
                duration,
                section_type=section_type,
                operation_type="ai_generation"
            )
        
        metrics.record_tool_call(
            "journal.generation_operations_total",
            success=success,
            section_type=section_type
        )
    
    if not success and error_category:
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute("error.category", error_category)


def log_ai_agent_interaction(context_sent: Any, response_received: Any, debug_mode: bool = False):
    """
    Simple logging of AI interactions for debugging integration issues.
    
    This utility function provides visibility into AI agent interactions without
    interfering with normal operation. Useful for troubleshooting when AI responses
    don't match expectations or when debugging context size issues.
    
    Args:
        context_sent: The context/prompt data sent to the AI
        response_received: The response received from the AI
        debug_mode: Whether to log debug information (can be set via environment)
    
    Usage:
        # In AI generation functions:
        result = ai_generate_section(context)
        log_ai_agent_interaction(context, result, debug_mode=True)
        return result
    """
    # Check environment variable if debug_mode not explicitly set
    if not debug_mode:
        debug_mode = os.getenv('MCP_DEBUG_AI_INTERACTIONS', 'false').lower() in ('true', '1', 'yes')
    
    if debug_mode:
        context_size = len(str(context_sent)) if context_sent else 0
        response_type = type(response_received).__name__
        response_size = len(str(response_received)) if response_received else 0
        
        logger.debug(f"AI Interaction Debug:")
        logger.debug(f"  Context size: {context_size} characters")
        logger.debug(f"  Response type: {response_type}")
        logger.debug(f"  Response size: {response_size} characters")
        
        # Add telemetry if available
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_counter(
                "ai_interactions_logged_total",
                1,
                attributes={
                    "context_size_bucket": _get_size_bucket(context_size),
                    "response_type": response_type
                }
            )


def _get_size_bucket(size: int) -> str:
    """Helper function to bucket sizes for telemetry."""
    if size < 1000:
        return "small"
    elif size < 10000:
        return "medium" 
    elif size < 100000:
        return "large"
    else:
        return "xlarge" 