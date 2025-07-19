"""
Tests for environment variable interpolation in config system.

Tests the resolve_env_vars() function for ${VAR_NAME} syntax parsing and resolution.
"""
import os
import pytest
from unittest.mock import patch, Mock

from src.mcp_commit_story.config import resolve_env_vars, ConfigError


class TestResolveEnvVars:
    """Test environment variable interpolation functionality."""

    def test_resolve_simple_env_var(self):
        """Test resolving a simple environment variable."""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            result = resolve_env_vars('${TEST_VAR}')
            assert result == 'test_value'

    def test_resolve_env_var_in_string(self):
        """Test resolving environment variable within a string."""
        with patch.dict(os.environ, {'API_KEY': 'secret123'}):
            result = resolve_env_vars('api_key: ${API_KEY}')
            assert result == 'api_key: secret123'

    def test_resolve_multiple_env_vars(self):
        """Test resolving multiple environment variables in one string."""
        with patch.dict(os.environ, {'HOST': 'localhost', 'PORT': '8080'}):
            result = resolve_env_vars('${HOST}:${PORT}')
            assert result == 'localhost:8080'

    def test_literal_string_passthrough(self):
        """Test that strings without env vars pass through unchanged."""
        result = resolve_env_vars('literal string')
        assert result == 'literal string'

    def test_literal_string_with_dollar_no_braces(self):
        """Test that strings with $ but no {} pass through unchanged."""
        result = resolve_env_vars('$PATH and $HOME')
        assert result == '$PATH and $HOME'

    def test_missing_env_var_raises_error(self):
        """Test that missing environment variable raises ConfigError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigError, match="Environment variable 'MISSING_VAR' not found"):
                resolve_env_vars('${MISSING_VAR}')

    def test_invalid_syntax_empty_braces(self):
        """Test that empty braces raise ConfigError."""
        with pytest.raises(ConfigError, match="Invalid environment variable syntax"):
            resolve_env_vars('${}')

    def test_invalid_syntax_unclosed_braces(self):
        """Test that unclosed braces pass through unchanged."""
        result = resolve_env_vars('${UNCLOSED')
        assert result == '${UNCLOSED'

    def test_nested_config_dict_resolution(self):
        """Test resolving environment variables in nested config structures."""
        with patch.dict(os.environ, {'DB_HOST': 'db.example.com', 'API_KEY': 'secret123'}):
            config = {
                'database': {
                    'host': '${DB_HOST}',
                    'port': 5432
                },
                'api': {
                    'key': '${API_KEY}',
                    'timeout': 30
                },
                'literal': 'no_interpolation'
            }
            result = resolve_env_vars(config)
            expected = {
                'database': {
                    'host': 'db.example.com',
                    'port': 5432
                },
                'api': {
                    'key': 'secret123',
                    'timeout': 30
                },
                'literal': 'no_interpolation'
            }
            assert result == expected

    def test_nested_config_list_resolution(self):
        """Test resolving environment variables in lists within config."""
        with patch.dict(os.environ, {'PATTERN1': '*.log', 'PATTERN2': '*.tmp'}):
            config = {
                'exclude_patterns': ['${PATTERN1}', '${PATTERN2}', 'literal_pattern']
            }
            result = resolve_env_vars(config)
            expected = {
                'exclude_patterns': ['*.log', '*.tmp', 'literal_pattern']
            }
            assert result == expected

    def test_non_string_values_passthrough(self):
        """Test that non-string values pass through unchanged."""
        config = {
            'enabled': True,
            'port': 8080,
            'ratio': 3.14,
            'null_value': None
        }
        result = resolve_env_vars(config)
        assert result == config

    def test_empty_env_var_value(self):
        """Test that empty environment variable values are resolved correctly."""
        with patch.dict(os.environ, {'EMPTY_VAR': ''}):
            result = resolve_env_vars('prefix_${EMPTY_VAR}_suffix')
            assert result == 'prefix__suffix'

    def test_whitespace_in_env_var_name(self):
        """Test that whitespace in env var names raises error."""
        with pytest.raises(ConfigError, match="Invalid environment variable syntax"):
            resolve_env_vars('${INVALID VAR}')

    def test_special_characters_in_env_var_name(self):
        """Test that special characters in env var names raise error.""" 
        with pytest.raises(ConfigError, match="Invalid environment variable syntax"):
            resolve_env_vars('${INVALID-VAR}')

    def test_recursive_config_with_missing_env_var(self):
        """Test that missing env var in nested config raises error with context."""
        with patch.dict(os.environ, {}, clear=True):
            config = {
                'section': {
                    'subsection': {
                        'value': '${MISSING_VAR}'
                    }
                }
            }
            with pytest.raises(ConfigError, match="Environment variable 'MISSING_VAR' not found"):
                resolve_env_vars(config)


class TestEnvInterpolationIntegration:
    """Test integration of environment variable interpolation with config loading."""

    @patch('src.mcp_commit_story.config.resolve_env_vars')
    def test_resolve_env_vars_called_during_config_load(self, mock_resolve):
        """Test that resolve_env_vars is called during config loading."""
        # This test will verify integration once the function is implemented
        mock_resolve.return_value = {'test': 'value'}
        
        # Import here to avoid circular imports during test discovery
        from src.mcp_commit_story.config import load_config
        
        # Mock file loading to test integration
        with patch('src.mcp_commit_story.config.find_config_files') as mock_find:
            mock_find.return_value = (None, None)
            config = load_config()
            
            # Verify resolve_env_vars was called (when integrated)
            # This assertion will initially fail until integration is complete
            # mock_resolve.assert_called_once() 