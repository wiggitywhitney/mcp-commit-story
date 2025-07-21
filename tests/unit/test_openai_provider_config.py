"""
Unit tests for OpenAIProvider configuration handling.

Tests the OpenAIProvider's ability to handle API keys through the Config class
rather than environment variables.
"""

import pytest
from unittest.mock import Mock, patch
from mcp_commit_story.ai_provider import OpenAIProvider
from mcp_commit_story.config import Config, ConfigError

def test_openai_provider_init_with_config():
    """Test OpenAIProvider initialization with valid config."""
    mock_config = Mock(spec=Config)
    mock_config.ai_openai_api_key = "test-api-key"
    
    provider = OpenAIProvider(config=mock_config)
    assert provider.client.api_key == "test-api-key"

def test_openai_provider_init_without_config():
    """Test OpenAIProvider initialization fails without config."""
    with pytest.raises(ValueError) as exc:
        OpenAIProvider()
    assert "config parameter is required" in str(exc.value)

def test_openai_provider_init_with_empty_api_key():
    """Test OpenAIProvider initialization fails with empty API key in config."""
    mock_config = Mock(spec=Config)
    mock_config.ai_openai_api_key = ""
    
    with pytest.raises(ValueError) as exc:
        OpenAIProvider(config=mock_config)
    assert "OpenAI API key not configured" in str(exc.value)

def test_openai_provider_init_with_none_api_key():
    """Test OpenAIProvider initialization fails with None API key in config."""
    mock_config = Mock(spec=Config)
    mock_config.ai_openai_api_key = None
    
    with pytest.raises(ValueError) as exc:
        OpenAIProvider(config=mock_config)
    assert "OpenAI API key not configured" in str(exc.value)

def test_openai_provider_call_with_valid_config():
    """Test OpenAIProvider.call() works with valid config."""
    mock_config = Mock(spec=Config)
    mock_config.ai_openai_api_key = "test-api-key"
    
    # Create a properly structured mock response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test response"
    
    with patch('openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = OpenAIProvider(config=mock_config)
        response = provider.call("Test prompt", {"test": "context"})
        
        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once()

def test_openai_provider_call_handles_error():
    """Test OpenAIProvider.call() handles API errors gracefully."""
    mock_config = Mock(spec=Config)
    mock_config.ai_openai_api_key = "test-api-key"
    
    with patch('openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai.return_value = mock_client
        
        provider = OpenAIProvider(config=mock_config)
        response = provider.call("Test prompt", {"test": "context"})
        
        assert response == ""  # Graceful degradation returns empty string 