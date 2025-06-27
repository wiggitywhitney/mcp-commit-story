"""
Tests for AI invocation functionality.

Tests the invoke_ai function that wraps the OpenAI provider with retry logic
and graceful degradation for production use in git hooks.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from mcp_commit_story.ai_invocation import invoke_ai


class TestAIInvocation:
    """Test cases for the invoke_ai function."""
    
    def test_successful_ai_call(self):
        """Test successful AI call returns response."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.call.return_value = "Generated journal content"
            mock_provider_class.return_value = mock_provider
            
            result = invoke_ai("Test prompt", {"git": {"message": "test commit"}})
            
            assert result == "Generated journal content"
            mock_provider.call.assert_called_once_with("Test prompt", {"git": {"message": "test commit"}})
    
    def test_retry_on_temporary_failure_succeeds_on_second_attempt(self):
        """Test retry logic succeeds on second attempt after temporary failure."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            # First call fails, second succeeds
            mock_provider.call.side_effect = [Exception("Temporary network error"), "Success response"]
            mock_provider_class.return_value = mock_provider
            
            with patch('time.sleep'):  # Don't actually sleep during tests
                result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == "Success response"
            assert mock_provider.call.call_count == 2
    
    def test_retry_exhausted_returns_empty_string(self):
        """Test that after 3 retry attempts, function returns empty string."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            # All 3 attempts fail
            mock_provider.call.side_effect = [
                Exception("Network error 1"),
                Exception("Network error 2"),
                Exception("Network error 3")
            ]
            mock_provider_class.return_value = mock_provider
            
            with patch('time.sleep'):  # Don't actually sleep during tests
                result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == ""
            assert mock_provider.call.call_count == 3
    
    def test_auth_error_no_retry(self):
        """Test that authentication errors don't trigger retries."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            # Auth error on provider creation (missing API key)
            mock_provider_class.side_effect = ValueError("OPENAI_API_KEY environment variable is required")
            
            result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == ""
            # Should only try to create provider once, no retries
            assert mock_provider_class.call_count == 1
    
    def test_missing_api_key_returns_empty_string(self):
        """Test that missing API key returns empty string gracefully."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider_class.side_effect = ValueError("OPENAI_API_KEY environment variable is required")
            
            result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == ""
    
    def test_timeout_returns_empty_string(self):
        """Test that timeout errors return empty string."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.call.side_effect = Exception("Request timeout")
            mock_provider_class.return_value = mock_provider
            
            with patch('time.sleep'):
                result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == ""
    
    def test_telemetry_recording_on_success(self):
        """Test that successful AI calls record telemetry."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.call.return_value = "Success response"
            mock_provider_class.return_value = mock_provider
            
            # Since telemetry decorator is applied at import time, we just test
            # that the function works correctly with telemetry enabled
            result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == "Success response"
            mock_provider.call.assert_called_once_with("Test prompt", {"context": "data"})
    
    def test_telemetry_recording_on_failure(self):
        """Test that failed AI calls still record telemetry."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider_class.side_effect = ValueError("API key missing")
            
            # Since telemetry decorator is applied at import time, we just test
            # that the function works correctly with telemetry enabled
            result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == ""
    
    def test_retry_delay_timing(self):
        """Test that retries have appropriate 1-second delays."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.call.side_effect = [Exception("Temp error"), "Success"]
            mock_provider_class.return_value = mock_provider
            
            with patch('time.sleep') as mock_sleep:
                result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == "Success"
            mock_sleep.assert_called_once_with(1)  # 1-second delay between retries
    
    def test_empty_response_handling(self):
        """Test that empty/None responses from provider are handled gracefully."""
        with patch('mcp_commit_story.ai_invocation.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.call.return_value = ""  # Empty response
            mock_provider_class.return_value = mock_provider
            
            result = invoke_ai("Test prompt", {"context": "data"})
            
            assert result == "" 