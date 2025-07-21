"""
Test suite for OpenAI provider integration.

This module tests the OpenAIProvider class that handles AI API calls for journal generation.
Tests use mocked OpenAI API calls to avoid real API usage during testing.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from src.mcp_commit_story.ai_provider import OpenAIProvider
from src.mcp_commit_story.config import Config


class TestOpenAIProvider:
    """Test the OpenAIProvider class for AI integration."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock config with API key
        self.mock_config = Mock(spec=Config)
        self.mock_config.ai_openai_api_key = 'test-api-key'
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_provider_initialization_with_api_key(self, mock_openai_class):
        """Test that provider initializes correctly with API key."""
        provider = OpenAIProvider(config=self.mock_config)
        
        # Verify OpenAI client was created with correct API key
        mock_openai_class.assert_called_once_with(api_key='test-api-key')
        assert provider is not None
    
    def test_provider_initialization_without_api_key(self):
        """Test that provider raises error when API key is missing."""
        mock_config = Mock(spec=Config)
        mock_config.ai_openai_api_key = ""
        
        with pytest.raises(ValueError, match="OpenAI API key not configured in .mcp-commit-storyrc.yaml"):
            OpenAIProvider(config=mock_config)
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_basic_functionality(self, mock_openai_class):
        """Test basic call method functionality with mocked response."""
        # Setup mock response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test AI response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        
        # Test the call
        prompt = "Test prompt"
        context = {"test": "context"}
        result = provider.call(prompt, context)
        
        # Verify result
        assert result == "Test AI response"
        
        # Verify correct API call was made
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": str(context)}
            ],
            timeout=30
        )
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_with_actual_journal_prompt(self, mock_openai_class):
        """Test call method with actual docstring from generate_summary_section."""
        # Setup mock response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated summary based on context"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        
        # Use actual docstring from journal.py
        prompt = """
        AI Prompt for Summary Section Generation
        
        Purpose: Create a concise narrative summary of the engineering work completed in this commit.
        
        Instructions: Generate a 2-3 sentence summary that captures the essential work accomplished,
        focusing on the main goals achieved and their significance to the project.
        """
        
        context = {
            "git": {"message": "Implement user authentication", "files_changed": 3},
            "chat": {"messages": ["How do I implement JWT?", "Use the jsonwebtoken library"]},
            "commit_hash": "abc123"
        }
        
        result = provider.call(prompt, context)
        
        # Verify result
        assert result == "Generated summary based on context"
        assert len(result) > 0
        
        # Verify API call included the real prompt
        call_args = mock_client.chat.completions.create.call_args
        assert prompt in call_args[1]["messages"][0]["content"]
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_timeout_handling(self, mock_openai_class):
        """Test that call method handles timeout errors gracefully."""
        # Setup mock to raise timeout
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Request timeout")
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        
        # Test graceful degradation
        result = provider.call("test prompt", {"test": "context"})
        
        # Should return empty string on error
        assert result == ""
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_api_error_handling(self, mock_openai_class):
        """Test that call method handles API errors gracefully."""
        # Setup mock to raise API error
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error: Rate limit exceeded")
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        
        # Test graceful degradation
        result = provider.call("test prompt", {"test": "context"})
        
        # Should return empty string on error
        assert result == ""
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_empty_response_handling(self, mock_openai_class):
        """Test handling of empty or None responses from OpenAI."""
        # Setup mock with empty response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        
        result = provider.call("test prompt", {"test": "context"})
        
        # Should handle None response gracefully
        assert result == ""
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_timeout_configuration(self, mock_openai_class):
        """Test that timeout is correctly set to 30 seconds."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Success"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        provider.call("test", {})
        
        # Verify timeout was set correctly
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["timeout"] == 30
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_model_configuration(self, mock_openai_class):
        """Test that gpt-4o-mini model is correctly specified."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Success"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        provider.call("test", {})
        
        # Verify model was set correctly
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
    
    @patch('src.mcp_commit_story.ai_provider.openai.OpenAI')
    def test_call_method_message_structure(self, mock_openai_class):
        """Test that messages are structured correctly for OpenAI API."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Success"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(config=self.mock_config)
        prompt = "System instruction"
        context = {"key": "value"}
        provider.call(prompt, context)
        
        # Verify message structure
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == prompt
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == str(context) 