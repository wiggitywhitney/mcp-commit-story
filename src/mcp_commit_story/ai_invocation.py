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
from mcp_commit_story.config import load_config, ConfigError

logger = logging.getLogger(__name__)


def _generate_api_key_warning(error_type: str = "missing") -> str:
    """
    Generate warning message for API key configuration issues.
    
    Args:
        error_type: Type of error ("missing", "invalid", "placeholder", or "config")
    """
    base_warning = """## ⚠️ AI Configuration Warning
The AI features are currently disabled due to """
    
    if error_type == "config":
        base_warning += "a configuration error. Please check your `.mcp-commit-storyrc.yaml` file."
    elif error_type == "placeholder":
        base_warning += "a placeholder API key. Please replace the placeholder value in your `.mcp-commit-storyrc.yaml` file with a valid API key."
    else:
        base_warning += "a missing or invalid OpenAI API key. Please check your `.mcp-commit-storyrc.yaml` configuration file and ensure you have set a valid API key."

    base_warning += """

To configure your API key:
1. Open `.mcp-commit-storyrc.yaml`
2. Add or update the AI section:
   ```yaml
   ai:
     openai_api_key: "${OPENAI_API_KEY}"  # Use environment variable
   ```
3. Set your OpenAI API key in your environment
"""
    return base_warning


def _is_placeholder_api_key(key: str) -> bool:
    """Check if an API key looks like a placeholder value."""
    placeholders = [
        "your-openai-api-key-here",
        "your-api-key",
        "your_api_key",
        "api-key-here",
        "api_key_here",
        "placeholder",
        "your-key",
        "your_key",
        "key-here",
        "key_here"
    ]
    key = key.lower()
    return any(placeholder in key for placeholder in placeholders)


@trace_mcp_operation("ai.invoke")
def invoke_ai(prompt: str, context: Dict[str, Any], return_warning: bool = False) -> str:
    """
    Call AI provider with prompt and context, including retry logic.
    
    This function wraps the OpenAI provider with:
    - Config-based API key management
    - Retry logic (up to 3 attempts with 1-second delays)
    - Graceful degradation (returns empty string or warning on failure)
    - Telemetry tracking (success, latency, error types)
    - Proper error handling for different failure types
    
    Auth errors (missing/invalid API key) don't trigger retries since they won't resolve.
    Network/temporary errors are retried up to 3 times with 1-second delays.
    
    Telemetry attributes added to existing spans:
    - ai.success: Boolean indicating if the call succeeded
    - ai.latency_ms: Duration in milliseconds
    - ai.error_type: Exception class name if failed (only set on failure)
    - ai.config_load_in_invocation_total: Counter for config loading operations
    - ai.config_load_success: Boolean indicating if config loaded successfully
    
    Args:
        prompt: The system prompt (usually from a function's docstring)
        context: Dictionary containing git, chat, and journal context
        return_warning: If True, return warning message on failure. If False, return empty string.
        
    Returns:
        String response from AI provider, or warning message/empty string if configuration fails
        
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
    current_span = trace.get_current_span()
    
    # Load configuration
    try:
        config = load_config()
        if current_span:
            current_span.set_attribute("ai.config_load_in_invocation_total", 1)
            current_span.set_attribute("ai.config_load_success", True)
            
        # Check for placeholder API key
        if _is_placeholder_api_key(config._ai_openai_api_key):
            logger.warning("AI invocation failed due to placeholder API key")
            return _generate_api_key_warning("placeholder") if return_warning else ""
            
    except ConfigError as e:
        logger.error(f"Failed to load configuration: {e}")
        if current_span:
            current_span.set_attribute("ai.config_load_in_invocation_total", 1)
            current_span.set_attribute("ai.config_load_success", False)
        return _generate_api_key_warning("config") if return_warning else ""
    
    for attempt in range(max_retries):
        try:
            # Create provider with config and make the call
            provider = OpenAIProvider(config=config)
            response = provider.call(prompt, context)
            
            # Success - record telemetry and return
            duration_ms = int((time.time() - start_time) * 1000)
            if current_span:
                current_span.set_attribute("ai.success", True)
                current_span.set_attribute("ai.latency_ms", duration_ms)
            
            return response
            
        except ValueError as e:
            final_error = e
            error_msg = str(e).lower()
            # Auth errors (missing/invalid API key) - don't retry
            if any(msg in error_msg for msg in ["api key", "openai_api_key"]):
                logger.warning(f"AI invocation failed due to API key configuration: {e}")
                return _generate_api_key_warning("invalid") if return_warning else ""
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
                logger.error(f"AI invocation failed after {max_retries} attempts")
                break
    
    # Record failure telemetry
    duration_ms = int((time.time() - start_time) * 1000)
    if current_span:
        current_span.set_attribute("ai.success", False)
        current_span.set_attribute("ai.latency_ms", duration_ms)
        if final_error:
            current_span.set_attribute("ai.error_type", type(final_error).__name__)
    
    return _generate_api_key_warning("missing") if return_warning else "" 