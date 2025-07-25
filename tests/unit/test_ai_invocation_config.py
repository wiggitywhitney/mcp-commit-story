"""
Tests for config-based AI invocation functionality.

Tests the integration of the config system with AI invocation, including API key validation,
warning message generation, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from mcp_commit_story.ai_invocation import invoke_ai
from mcp_commit_story.config import Config, ConfigError


class TestConfigBasedAIInvocation:
    """Test cases for config-based AI invocation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a real config with test API key
        self.valid_config = Config({
            'ai': {
                'openai_api_key': 'test-api-key'
            }
        })
    
    @patch('mcp_commit_story.ai_invocation.load_config')
    @patch('mcp_commit_story.ai_invocation.OpenAIProvider')
    def test_successful_ai_call_with_config(self, mock_provider_class, mock_load_config):
        """Test successful AI call with valid config."""
        # Setup mocks
        mock_load_config.return_value = self.valid_config
        mock_provider = Mock()
        mock_provider.call.return_value = "Generated content"
        mock_provider_class.return_value = mock_provider
        
        # Execute
        result = invoke_ai("Test prompt", {})
        
        # Verify
        mock_load_config.assert_called_once()
        mock_provider_class.assert_called_once_with(config=self.valid_config)
        assert result == "Generated content"
        assert "⚠️ AI Configuration Warning" not in result
    
    @patch('mcp_commit_story.ai_invocation.load_config')
    @patch('mcp_commit_story.ai_invocation.OpenAIProvider')
    def test_missing_api_key_adds_warning(self, mock_provider_class, mock_load_config):
        """Test that missing API key adds warning message to output."""
        # Setup mocks with empty API key
        empty_config = Config({
            'ai': {
                'openai_api_key': ''
            }
        })
        mock_load_config.return_value = empty_config
        mock_provider_class.side_effect = ValueError("OpenAI API key not configured")
        
        # Execute with return_warning=True
        result = invoke_ai("Test prompt", {}, return_warning=True)
        
        # Verify warning message is added
        assert "## ⚠️ AI Configuration Warning" in result
        assert "missing or invalid OpenAI API key" in result
        assert ".mcp-commit-storyrc.yaml" in result
        assert "${OPENAI_API_KEY}" in result
    
    @patch('mcp_commit_story.ai_invocation.load_config')
    def test_config_loading_failure(self, mock_load_config):
        """Test handling of config loading failure."""
        # Setup mock
        mock_load_config.side_effect = ConfigError("Failed to load config")
        
        # Execute with return_warning=True
        result = invoke_ai("Test prompt", {}, return_warning=True)
        
        # Verify warning message is added
        assert "## ⚠️ AI Configuration Warning" in result
        assert "configuration error" in result
        assert ".mcp-commit-storyrc.yaml" in result
    
    @patch('mcp_commit_story.ai_invocation.load_config')
    @patch('mcp_commit_story.ai_invocation.OpenAIProvider')
    def test_telemetry_for_config_loading(self, mock_provider_class, mock_load_config):
        """Test that config loading operations are tracked in telemetry."""
        # Setup mocks
        mock_load_config.return_value = self.valid_config
        mock_provider = Mock()
        mock_provider.call.return_value = "Generated content"
        mock_provider_class.return_value = mock_provider
        
        # Mock telemetry span
        mock_span = Mock()
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            # Execute
            invoke_ai("Test prompt", {})
            
            # Verify telemetry
            mock_span.set_attribute.assert_any_call("ai.config_load_in_invocation_total", 1)
            mock_span.set_attribute.assert_any_call("ai.config_load_success", True)
    
    @patch('mcp_commit_story.ai_invocation.load_config')
    @patch('mcp_commit_story.ai_invocation.OpenAIProvider')
    def test_invalid_api_key_adds_warning(self, mock_provider_class, mock_load_config):
        """Test that invalid API key adds warning message to output."""
        # Setup mocks with invalid API key
        invalid_config = Config({
            'ai': {
                'openai_api_key': 'invalid-key'
            }
        })
        mock_load_config.return_value = invalid_config
        mock_provider_class.side_effect = ValueError("Invalid API key")
        
        # Execute with return_warning=True
        result = invoke_ai("Test prompt", {}, return_warning=True)
        
        # Verify warning message is added
        assert "## ⚠️ AI Configuration Warning" in result
        assert "missing or invalid OpenAI API key" in result
        assert ".mcp-commit-storyrc.yaml" in result
        assert "${OPENAI_API_KEY}" in result
    
    @patch('mcp_commit_story.ai_invocation.load_config')
    @patch('mcp_commit_story.ai_invocation.OpenAIProvider')
    def test_placeholder_api_key_adds_warning(self, mock_provider_class, mock_load_config):
        """Test that placeholder API key values add warning message."""
        # The Config class itself rejects placeholder keys, so we test that the ConfigError
        # is handled properly and results in a warning message
        mock_load_config.side_effect = ConfigError("OpenAI API key appears to be a placeholder: 'your-openai-api-key-here'. Please set a valid API key.")
        
        # Execute with return_warning=True
        result = invoke_ai("Test prompt", {}, return_warning=True)
        
        # Verify warning message is added
        assert "## ⚠️ AI Configuration Warning" in result
        assert "configuration error" in result
        assert ".mcp-commit-storyrc.yaml" in result
        assert "${OPENAI_API_KEY}" in result 