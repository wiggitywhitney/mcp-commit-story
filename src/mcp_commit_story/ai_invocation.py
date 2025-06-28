"""
AI Invocation module for reliable AI calls with retry logic.

This module provides the invoke_ai function that wraps the OpenAI provider
with retry logic and graceful degradation for production use in git hooks.
"""

import time
import logging
from typing import Dict, Any
from mcp_commit_story.ai_provider import OpenAIProvider
from mcp_commit_story.telemetry import trace_mcp_operation

logger = logging.getLogger(__name__)


@trace_mcp_operation("ai.invoke")
def invoke_ai(prompt: str, context: Dict[str, Any]) -> str:
    """
    Call AI provider with prompt and context, including retry logic.
    
    This function wraps the OpenAI provider with:
    - Retry logic (up to 3 attempts with 1-second delays)
    - Graceful degradation (returns empty string on failure)
    - Telemetry tracking (success, latency, error types)
    - Proper error handling for different failure types
    
    Auth errors (missing API key) don't trigger retries since they won't resolve.
    Network/temporary errors are retried up to 3 times with 1-second delays.
    
    Telemetry attributes added to existing spans:
    - ai.success: Boolean indicating if the call succeeded
    - ai.latency_ms: Duration in milliseconds
    - ai.error_type: Exception class name if failed (only set on failure)
    
    Args:
        prompt: The system prompt (usually from a function's docstring)
        context: Dictionary containing git, chat, and journal context
        
    Returns:
        String response from AI provider, or empty string if all attempts fail
        
    Examples:
        >>> result = invoke_ai("Generate a summary", {"git": {"message": "Fix bug"}})
        >>> print(result)  # "Fixed authentication bug in user login flow"
        
        >>> result = invoke_ai("Bad prompt", {})  # If API fails
        >>> print(result)  # "" (empty string, graceful degradation)
    """
    from opentelemetry import trace
    
    # Start timing for telemetry
    start_time = time.time()
    max_retries = 3
    retry_delay = 1  # seconds
    final_error = None
    
    for attempt in range(max_retries):
        try:
            # Create provider and make the call
            provider = OpenAIProvider()
            response = provider.call(prompt, context)
            
            # Success - record telemetry and return
            duration_ms = int((time.time() - start_time) * 1000)
            current_span = trace.get_current_span()
            if current_span:
                current_span.set_attribute("ai.success", True)
                current_span.set_attribute("ai.latency_ms", duration_ms)
            
            return response
            
        except ValueError as e:
            final_error = e
            # Auth errors (missing API key) - don't retry
            if "OPENAI_API_KEY" in str(e):
                logger.warning(f"AI invocation failed due to missing API key: {e}")
                break
            else:
                # Other ValueError types might be retryable
                logger.warning(f"AI invocation failed with ValueError (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    break
                    
        except Exception as e:
            final_error = e
            # Network errors, timeouts, and other temporary failures
            logger.warning(f"AI invocation failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                # All retries exhausted
                logger.error(f"AI invocation failed after {max_retries} attempts, returning empty string")
                break
    
    # Record failure telemetry
    duration_ms = int((time.time() - start_time) * 1000)
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("ai.success", False)
        current_span.set_attribute("ai.latency_ms", duration_ms)
        if final_error:
            current_span.set_attribute("ai.error_type", type(final_error).__name__)
    
    return "" 