"""
Tests for AI configuration section in config system.

Tests the AI section in DEFAULT_CONFIG and Config class initialization with validation.
"""
import os
import pytest
from unittest.mock import patch, Mock

from src.mcp_commit_story.config import Config, ConfigError, DEFAULT_CONFIG


class TestAIConfigSection:
    """Test AI configuration section functionality."""

    def test_default_config_has_ai_section(self):
        """Test that DEFAULT_CONFIG includes AI section with openai_api_key."""
        assert 'ai' in DEFAULT_CONFIG
        assert 'openai_api_key' in DEFAULT_CONFIG['ai']
        assert DEFAULT_CONFIG['ai']['openai_api_key'] == ''

    def test_config_init_with_valid_ai_section(self):
        """Test Config initialization with valid AI section."""
        config_data = {
            'ai': {
                'openai_api_key': 'sk-test123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            config = Config(config_data)
            assert hasattr(config, '_ai')
            assert config._ai['openai_api_key'] == 'sk-test123456789'

    def test_config_init_with_env_var_interpolation_in_ai_config(self):
        """Test Config initialization with environment variable interpolation in AI config."""
        config_data = {
            'ai': {
                'openai_api_key': '${OPENAI_API_KEY}'
            }
        }
        resolved_data = {
            'ai': {
                'openai_api_key': 'sk-resolved123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=resolved_data):
            config = Config(config_data)
            assert config._ai['openai_api_key'] == 'sk-resolved123456789'

    def test_config_init_with_missing_api_key_succeeds(self):
        """Test that missing API key in AI section succeeds with graceful degradation."""
        config_data = {
            'ai': {}
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            config = Config(config_data)
            assert hasattr(config, '_ai')
            assert config._ai['openai_api_key'] == ''  # Filled with default

    def test_config_init_with_empty_api_key_succeeds(self):
        """Test that empty API key succeeds with graceful degradation."""
        config_data = {
            'ai': {
                'openai_api_key': ''
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            config = Config(config_data)
            assert hasattr(config, '_ai')
            assert config._ai['openai_api_key'] == ''

    def test_config_init_with_placeholder_api_key_raises_error(self):
        """Test that placeholder API key values are detected and rejected."""
        placeholder_values = [
            'your-openai-api-key-here',
            'YOUR_OPENAI_API_KEY_HERE',
            'placeholder',
            'PLACEHOLDER',
            'change-me',
            'CHANGE_ME'
        ]
        
        for placeholder in placeholder_values:
            config_data = {
                'ai': {
                    'openai_api_key': placeholder
                }
            }
            with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
                with pytest.raises(ConfigError, match="appears to be a placeholder"):
                    Config(config_data)

    def test_config_init_with_invalid_ai_section_type_raises_error(self):
        """Test that invalid AI section structure raises ConfigError."""
        config_data = {
            'ai': 'not_a_dict'
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            with pytest.raises(ConfigError, match="'ai' section must be a dict"):
                Config(config_data)

    def test_config_init_with_invalid_api_key_type_raises_error(self):
        """Test that invalid API key type raises ConfigError."""
        config_data = {
            'ai': {
                'openai_api_key': 123
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            with pytest.raises(ConfigError, match="'ai.openai_api_key' must be a string"):
                Config(config_data)

    def test_config_ai_section_included_in_as_dict(self):
        """Test that AI section is included in Config.as_dict() output."""
        config_data = {
            'ai': {
                'openai_api_key': 'sk-test123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            config = Config(config_data)
            config_dict = config.as_dict()
            assert 'ai' in config_dict
            assert config_dict['ai']['openai_api_key'] == 'sk-test123456789'

    def test_config_ai_section_accessible_via_dict_access(self):
        """Test that AI section is accessible via dict-like access."""
        config_data = {
            'ai': {
                'openai_api_key': 'sk-test123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            config = Config(config_data)
            assert 'ai' in config
            assert config['ai']['openai_api_key'] == 'sk-test123456789'

    def test_config_ai_validation_with_resolved_env_vars(self):
        """Test that validation occurs after environment variable resolution."""
        config_data = {
            'ai': {
                'openai_api_key': '${OPENAI_API_KEY}'
            }
        }
        
        # Test case 1: Environment variable resolves to placeholder - should fail
        resolved_data_placeholder = {
            'ai': {
                'openai_api_key': 'your-openai-api-key-here'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=resolved_data_placeholder):
            with pytest.raises(ConfigError, match="appears to be a placeholder"):
                Config(config_data)
        
        # Test case 2: Environment variable resolves to valid key - should succeed
        resolved_data_valid = {
            'ai': {
                'openai_api_key': 'sk-valid123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=resolved_data_valid):
            config = Config(config_data)
            assert config._ai['openai_api_key'] == 'sk-valid123456789'
        
        # Test case 3: Environment variable resolves to empty - should succeed (graceful degradation)
        resolved_data_empty = {
            'ai': {
                'openai_api_key': ''
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=resolved_data_empty):
            config = Config(config_data)
            assert config._ai['openai_api_key'] == ''

    def test_config_merges_ai_section_with_defaults(self):
        """Test that AI section properly merges with defaults."""
        config_data = {
            'ai': {
                'openai_api_key': 'sk-test123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            config = Config(config_data)
            # Verify AI section has the configured value
            assert config._ai['openai_api_key'] == 'sk-test123456789'
            # Verify other sections still have defaults
            assert config._journal['path'] == 'journal/'
            assert config._telemetry['enabled'] == False


class TestAIConfigValidationTelemetry:
    """Test telemetry for AI configuration validation."""

    @patch('src.mcp_commit_story.config.get_mcp_metrics')
    def test_ai_validation_success_telemetry(self, mock_get_metrics):
        """Test that successful AI validation increments success counter."""
        mock_metrics = Mock()
        mock_get_metrics.return_value = mock_metrics
        
        config_data = {
            'ai': {
                'openai_api_key': 'sk-test123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            Config(config_data)
            
        mock_metrics.record_counter.assert_called_with('config.ai_validation_total', 1, {'status': 'success'})

    @patch('src.mcp_commit_story.config.get_mcp_metrics')
    def test_ai_validation_failure_telemetry(self, mock_get_metrics):
        """Test that failed AI validation increments failure counter."""
        mock_metrics = Mock()
        mock_get_metrics.return_value = mock_metrics
        
        config_data = {
            'ai': {
                'openai_api_key': 'placeholder'  # Placeholder key should fail validation
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            with pytest.raises(ConfigError):
                Config(config_data)
                
        mock_metrics.record_counter.assert_called_with('config.ai_validation_total', 1, {'status': 'failure'})

    @patch('src.mcp_commit_story.config.get_mcp_metrics')
    def test_ai_validation_telemetry_handles_none_metrics(self, mock_get_metrics):
        """Test that AI validation gracefully handles None metrics."""
        mock_get_metrics.return_value = None
        
        config_data = {
            'ai': {
                'openai_api_key': 'sk-test123456789'
            }
        }
        with patch('src.mcp_commit_story.config.resolve_env_vars', return_value=config_data):
            # Should not raise an error even when metrics is None
            config = Config(config_data)
            assert config._ai['openai_api_key'] == 'sk-test123456789' 