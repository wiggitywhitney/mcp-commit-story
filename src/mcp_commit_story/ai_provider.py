"""
AI Provider module for journal generation.

This module provides a simple interface to OpenAI's API for generating journal
content from prompts and context. Designed for use in git hooks with graceful
degradation when AI is unavailable.
"""

import os
import openai
import logging
from typing import Dict, Any, Optional
from mcp_commit_story.config import Config
from mcp_commit_story.telemetry import get_mcp_metrics

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """
    Simple OpenAI provider for AI-powered journal generation.
    
    Provides a single call() method that sends prompts and context to OpenAI
    and returns string responses. Handles errors gracefully by returning
    empty strings, allowing the journal generation to continue with
    programmatic sections only.
    
    The provider requires a Config object containing the OpenAI API key in the
    ai.openai_api_key field. This key should be configured in the project's
    .mcp-commit-storyrc.yaml file, either directly or using environment variable
    interpolation (${OPENAI_API_KEY}).
    
    Example configuration:
        ai:
          openai_api_key: "sk-..."
        # OR using environment variable:
        ai:
          openai_api_key: "${OPENAI_API_KEY}"
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the OpenAI provider.
        
        Args:
            config: Config object containing OpenAI API key configuration.
                   The key should be configured in the ai.openai_api_key field
                   of the .mcp-commit-storyrc.yaml file.
            
        Raises:
            ValueError: If config is not provided or API key is not configured
            
        Example:
            >>> config = load_config()  # Load from .mcp-commit-storyrc.yaml
            >>> provider = OpenAIProvider(config=config)
        """
        metrics = get_mcp_metrics()
        
        try:
            if config is None:
                raise ValueError("config parameter is required")
            
            api_key = config.ai_openai_api_key
            if not api_key:
                raise ValueError("OpenAI API key not configured in .mcp-commit-storyrc.yaml")
            
            self.client = openai.OpenAI(api_key=api_key)
            
            # Record successful initialization
            if metrics:
                metrics.record_counter('ai.provider_initialization_total', 1, {'status': 'success'})
                
        except Exception as e:
            # Record failed initialization
            if metrics:
                metrics.record_counter('ai.provider_initialization_total', 1, {'status': 'failure'})
            raise
    
    def call(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Send prompt and context to OpenAI and return the response.
        
        This method structures the prompt as a system message and the context
        as a user message, sends them to OpenAI's gpt-4o-mini model, and
        returns the response content.
        
        Args:
            prompt: The system prompt (usually from a function's docstring)
            context: Dictionary containing git, chat, and journal context
            
        Returns:
            String response from OpenAI, or empty string if any error occurs
            
        Examples:
            >>> provider = OpenAIProvider(config=config)
            >>> prompt = "Generate a summary of these changes"
            >>> context = {"git": {"message": "Fix bug in auth"}}
            >>> response = provider.call(prompt, context)
        """
        try:
            # Debug logging for 400 errors
            prompt_size = len(prompt)
            context_str = str(context)
            context_size = len(context_str)
            
            if prompt_size > 50000:  # 50KB
                print(f"WARNING: Large prompt size: {prompt_size:,} characters")
            if context_size > 10000:  # 10KB  
                print(f"WARNING: Large context size: {context_size:,} characters")
                
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": context_str}
                ],
                timeout=30
            )
            
            # Handle case where response content is None
            content = response.choices[0].message.content
            return content if content is not None else ""
            
        except Exception as e:
            # Enhanced error logging for intermittent failure diagnosis
            import os
            import logging
            logger = logging.getLogger(__name__)
            
            # Log comprehensive error details
            logger.error(f"=== OpenAI API Error Details ===")
            logger.error(f"Full error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error module: {type(e).__module__}")
            
            # Log response details if available
            if hasattr(e, 'response'):
                response = e.response
                logger.error(f"Response status: {getattr(response, 'status_code', 'N/A')}")
                logger.error(f"Response reason: {getattr(response, 'reason', 'N/A')}")
                logger.error(f"Response headers: {getattr(response, 'headers', 'N/A')}")
                logger.error(f"Response text: {getattr(response, 'text', 'N/A')[:300]}")
            
            # Log environment context during failure
            logger.error(f"Working directory: {os.getcwd()}")
            logger.error(f"PATH: {os.environ.get('PATH', 'N/A')[:200]}...")
            logger.error(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'N/A')}")
            
            # Log system context
            import time
            logger.error(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.error(f"Process PID: {os.getpid()}")
            
            # Log prompt/context sizes for debugging large payload issues
            logger.error(f"Prompt size: {prompt_size:,} characters")
            logger.error(f"Context size: {context_size:,} characters")
            
            # Print to console for immediate visibility during git hooks
            print(f"=== ENHANCED AI ERROR LOG ===")
            print(f"Error: {e}")
            print(f"Type: {type(e).__name__}")
            print(f"Time: {time.strftime('%H:%M:%S')}")
            print(f"Working dir: {os.getcwd()}")
            if hasattr(e, 'response'):
                print(f"HTTP Status: {getattr(e.response, 'status_code', 'N/A')}")
            print(f"================================")
            
            # Graceful degradation - return empty string on any error
            # This allows journal generation to continue with programmatic sections
            return "" 