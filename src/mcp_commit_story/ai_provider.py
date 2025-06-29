"""
AI Provider module for journal generation.

This module provides a simple interface to OpenAI's API for generating journal
content from prompts and context. Designed for use in git hooks with graceful
degradation when AI is unavailable.
"""

import os
import openai
from typing import Dict, Any


class OpenAIProvider:
    """
    Simple OpenAI provider for AI-powered journal generation.
    
    Provides a single call() method that sends prompts and context to OpenAI
    and returns string responses. Handles errors gracefully by returning
    empty strings, allowing the journal generation to continue with
    programmatic sections only.
    """
    
    def __init__(self):
        """
        Initialize the OpenAI provider.
        
        Raises:
            ValueError: If OPENAI_API_KEY environment variable is not set.
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = openai.OpenAI(api_key=api_key)
    
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
            >>> provider = OpenAIProvider()
            >>> prompt = "Generate a summary of these changes"
            >>> context = {"git": {"message": "Fix bug in auth"}}
            >>> response = provider.call(prompt, context)
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": str(context)}
                ],
                timeout=30
            )
            
            # Handle case where response content is None
            content = response.choices[0].message.content
            return content if content is not None else ""
            
        except Exception as e:
            # Graceful degradation - return empty string on any error
            # This allows journal generation to continue with programmatic sections
            return "" 