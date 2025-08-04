"""Integration tests for config-based AI workflow.

Tests the complete workflow:
1. Config loading with environment variable interpolation
2. AI section validation
3. OpenAI provider initialization
4. AI invocation with config-based API key
"""

import os
import tempfile
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from mcp_commit_story.config import load_config, Config, ConfigError
from mcp_commit_story.ai_provider import OpenAIProvider
from mcp_commit_story.ai_invocation import invoke_ai
from tests.integration.test_telemetry_validation_integration import (
    TelemetryCollector,
    isolated_telemetry_environment
)


@pytest.fixture
def test_telemetry_collector():
    """Create a test telemetry collector."""
    collector = TelemetryCollector()
    yield collector
    collector.reset()


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config file with environment variable interpolation
        config = {
            'ai': {
                'openai_api_key': '${OPENAI_API_KEY}'
            }
        }
        
        config_file = Path(tmpdir) / ".mcp-commit-storyrc.yaml"
        config_file.write_text(yaml.dump(config))
        
        yield {
            'tmpdir': tmpdir,
            'config_file': config_file
        }


class TestAIConfigIntegration:
    """Test the complete config-based AI workflow."""
    
    def test_successful_config_based_ai_workflow(self, temp_config_dir):
        """Test successful end-to-end workflow with environment variable."""
        # Set up test environment
        os.environ['OPENAI_API_KEY'] = 'test-api-key-12345'
        
        # Create a mock span
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        
        with patch('mcp_commit_story.config.load_config') as mock_load_config, \
             patch('mcp_commit_story.ai_provider.OpenAIProvider.call') as mock_call, \
             patch('mcp_commit_story.ai_invocation._is_placeholder_api_key', return_value=False), \
             patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            # Mock successful AI response
            mock_call.return_value = "Test AI response"
            
            # Mock config loading to use our test config
            mock_config = Config({
                'ai': {
                    'openai_api_key': 'test-api-key-12345'
                }
            })
            mock_load_config.return_value = mock_config
            
            # Test AI invocation with config
            result = invoke_ai(
                "Test prompt",
                {"context": "test"},
                return_warning=True
            )
            
            assert result == "Test AI response"
            assert "⚠️ AI Configuration Warning" not in result
            
            # Verify OpenAIProvider was initialized with config
            mock_call.assert_called_once()
            
            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("ai.config_load_in_invocation_total", 1)
            mock_span.set_attribute.assert_any_call("ai.config_load_success", True)
            mock_span.set_attribute.assert_any_call("ai.success", True)
            
            # Clean up
            del os.environ['OPENAI_API_KEY']
    
    def test_missing_environment_variable_handling(self, temp_config_dir):
        """Test error handling when environment variable is not set."""
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
            
        with pytest.raises(ConfigError) as exc_info:
            config = load_config(temp_config_dir['config_file'])
            
        assert "Environment variable 'OPENAI_API_KEY' not found" in str(exc_info.value)
    
    def test_invalid_api_key_detection(self, temp_config_dir):
        """Test detection of invalid/placeholder API keys."""
        os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'
        
        with pytest.raises(ConfigError) as exc_info:
            config = load_config(temp_config_dir['config_file'])
            
        assert "appears to be a placeholder" in str(exc_info.value)
        
        # Clean up
        del os.environ['OPENAI_API_KEY']
    
    def test_telemetry_validation(self, temp_config_dir, isolated_telemetry_environment):
        """Test telemetry collection during config-based AI operations."""
        os.environ['OPENAI_API_KEY'] = 'test-api-key-12345'
        
        # Create a mock span
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        
        with patch('mcp_commit_story.config.load_config') as mock_load_config, \
             patch('mcp_commit_story.ai_provider.OpenAIProvider.call') as mock_call, \
             patch('mcp_commit_story.ai_invocation._is_placeholder_api_key', return_value=False), \
             patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            
            # Mock successful AI response
            mock_call.return_value = "Test AI response"
            
            # Mock config loading to use our test config
            mock_config = Config({
                'ai': {
                    'openai_api_key': 'test-api-key-12345'
                }
            })
            mock_load_config.return_value = mock_config
            
            # Test AI invocation
            result = invoke_ai(
                "Test prompt",
                {"context": "test"},
                return_warning=True
            )
            
            # Verify span attributes were set
            mock_span.set_attribute.assert_any_call("ai.config_load_in_invocation_total", 1)
            mock_span.set_attribute.assert_any_call("ai.config_load_success", True)
            mock_span.set_attribute.assert_any_call("ai.success", True)
            
            # Clean up
            del os.environ['OPENAI_API_KEY']
    
    def test_config_only_approach_validation(self, temp_config_dir):
        """Test that direct environment variable access is removed."""
        os.environ['OPENAI_API_KEY'] = 'test-api-key-12345'
        
        # Create a mock span
        mock_span = MagicMock()
        mock_span.set_attribute = MagicMock()
        
        with patch('mcp_commit_story.config.load_config') as mock_load_config, \
             patch('mcp_commit_story.ai_provider.OpenAIProvider.call') as mock_call, \
             patch('mcp_commit_story.ai_invocation._is_placeholder_api_key', return_value=False), \
             patch('opentelemetry.trace.get_current_span', return_value=mock_span), \
             patch('os.getenv') as mock_getenv:
            
            mock_call.return_value = "Test AI response"
            
            # Mock config loading to use our test config
            mock_config = Config({
                'ai': {
                    'openai_api_key': 'test-api-key-12345'
                }
            })
            mock_load_config.return_value = mock_config
            
            # Test AI invocation
            result = invoke_ai(
                "Test prompt",
                {"context": "test"},
                return_warning=True
            )
            
            # Verify os.getenv was not called directly for OPENAI_API_KEY
            for call in mock_getenv.call_args_list:
                assert call[0][0] != 'OPENAI_API_KEY', "Direct environment variable access detected"
            
            # Clean up
            del os.environ['OPENAI_API_KEY'] 