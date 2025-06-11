"""Unit tests for MCP server entry point (__main__.py)."""

import pytest
import sys
import signal
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the module we'll be testing
from mcp_commit_story.__main__ import main, validate_server_config, setup_server_telemetry
from mcp_commit_story.config import ConfigError


class TestMCPServerEntryPoint:
    """Test cases for MCP server entry point functionality."""

    def test_main_function_successful_startup_and_shutdown(self):
        """Test main() function with successful server startup and shutdown."""
        
        with patch('mcp_commit_story.__main__.setup_server_telemetry') as mock_setup_telemetry, \
             patch('mcp_commit_story.__main__.validate_server_config') as mock_validate_config, \
             patch('mcp_commit_story.__main__.create_mcp_server') as mock_create_server, \
             patch('mcp_commit_story.__main__.get_mcp_metrics') as mock_metrics:
            
            # Setup mocks
            mock_config = Mock()
            mock_config.telemetry_enabled = True
            mock_validate_config.return_value = mock_config
            mock_setup_telemetry.return_value = True
            
            mock_server = Mock()
            mock_server.run.return_value = 0
            mock_create_server.return_value = mock_server
            
            mock_metrics_instance = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Execute
            exit_code = main()
            
            # Verify
            assert exit_code == 0
            mock_validate_config.assert_called_once()
            mock_setup_telemetry.assert_called_once_with(mock_config)
            mock_create_server.assert_called_once()
            mock_server.run.assert_called_once()
            mock_metrics_instance.record_counter.assert_any_call("server_start_attempt", 1)
            mock_metrics_instance.record_counter.assert_any_call("server_started", 1)
            mock_metrics_instance.record_counter.assert_any_call("server_shutdown", 1)

    def test_main_function_startup_failure_with_invalid_config(self):
        """Test main() function handles startup failure with invalid configuration."""
        
        with patch('mcp_commit_story.__main__.validate_server_config') as mock_validate_config, \
             patch('mcp_commit_story.__main__.get_mcp_metrics') as mock_metrics:
            
            # Setup mocks - config validation fails
            mock_validate_config.return_value = False
            mock_metrics_instance = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Execute
            exit_code = main()
            
            # Verify
            assert exit_code == 2  # Should return config error code
            mock_validate_config.assert_called_once()
            mock_metrics_instance.record_counter.assert_any_call("server_config_error", 1)

    def test_main_function_graceful_shutdown_handling(self):
        """Test main() function handles graceful shutdown signals."""
        
        with patch('mcp_commit_story.__main__.setup_server_telemetry') as mock_setup_telemetry, \
             patch('mcp_commit_story.__main__.validate_server_config') as mock_validate_config, \
             patch('mcp_commit_story.__main__.create_mcp_server') as mock_create_server, \
             patch('mcp_commit_story.__main__.get_mcp_metrics') as mock_metrics:
            
            # Setup mocks
            mock_config = Mock()
            mock_config.telemetry_enabled = True
            mock_validate_config.return_value = mock_config
            mock_setup_telemetry.return_value = True
            
            mock_server = Mock()
            mock_server.run.side_effect = KeyboardInterrupt()
            mock_create_server.return_value = mock_server
            
            mock_metrics_instance = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Execute
            exit_code = main()
            
            # Verify
            assert exit_code == 130  # Standard SIGINT exit code
            mock_metrics_instance.record_counter.assert_any_call("server_keyboard_interrupt", 1)

    def test_main_function_exit_code_validation(self):
        """Test main() function returns proper exit codes for different scenarios."""
        
        # Test server returns non-zero exit code
        with patch('mcp_commit_story.__main__.setup_server_telemetry') as mock_setup_telemetry, \
             patch('mcp_commit_story.__main__.validate_server_config') as mock_validate_config, \
             patch('mcp_commit_story.__main__.create_mcp_server') as mock_create_server, \
             patch('mcp_commit_story.__main__.get_mcp_metrics') as mock_metrics:
            
            # Setup mocks
            mock_config = Mock()
            mock_config.telemetry_enabled = True
            mock_validate_config.return_value = mock_config
            mock_setup_telemetry.return_value = True
            
            mock_server = Mock()
            mock_server.run.return_value = 5  # Non-zero exit code
            mock_create_server.return_value = mock_server
            
            mock_metrics_instance = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            exit_code = main()
            assert exit_code == 5

    def test_validate_server_config_function(self):
        """Test validate_server_config() function for configuration validation."""
        
        with patch('mcp_commit_story.__main__.load_config') as mock_load_config:
            # Test valid configuration
            mock_config = Mock()
            mock_config.telemetry_enabled = True
            mock_load_config.return_value = mock_config
            
            result = validate_server_config()
            assert result == mock_config
            mock_load_config.assert_called_once_with(None)

    def test_setup_server_telemetry_function(self):
        """Test setup_server_telemetry() function for telemetry initialization."""
        
        with patch('mcp_commit_story.__main__.setup_telemetry') as mock_setup_telemetry:
            # Test with Config object
            mock_config = Mock()
            mock_config.as_dict.return_value = {"telemetry": {"enabled": True}}
            mock_setup_telemetry.return_value = True
            
            result = setup_server_telemetry(mock_config)
            assert result is True
            mock_setup_telemetry.assert_called_once_with({"telemetry": {"enabled": True}})
            
            # Test with dictionary
            config_dict = {"telemetry": {"enabled": False}}
            mock_setup_telemetry.return_value = False
            
            result = setup_server_telemetry(config_dict)
            assert result is False
            mock_setup_telemetry.assert_called_with(config_dict)

    def test_telemetry_recording_for_all_server_events(self):
        """Test that telemetry is properly recorded for all server events."""
        
        with patch('mcp_commit_story.__main__.setup_server_telemetry') as mock_setup_telemetry, \
             patch('mcp_commit_story.__main__.validate_server_config') as mock_validate_config, \
             patch('mcp_commit_story.__main__.create_mcp_server') as mock_create_server, \
             patch('mcp_commit_story.__main__.get_mcp_metrics') as mock_metrics:
            
            # Setup mocks
            mock_config = Mock()
            mock_config.telemetry_enabled = True
            mock_validate_config.return_value = mock_config
            mock_setup_telemetry.return_value = True
            
            mock_server = Mock()
            mock_server.run.return_value = 0
            mock_create_server.return_value = mock_server
            
            mock_metrics_instance = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Execute
            main()
            
            # Verify all expected telemetry calls
            expected_calls = [
                ("server_start_attempt", 1),
                ("server_started", 1),
                ("server_shutdown", 1)
            ]
            
            for metric_name, value in expected_calls:
                mock_metrics_instance.record_counter.assert_any_call(metric_name, value)

    def test_server_startup_with_telemetry_failure(self):
        """Test server startup behavior when telemetry setup fails."""
        
        with patch('mcp_commit_story.__main__.validate_server_config') as mock_validate_config, \
             patch('mcp_commit_story.__main__.setup_server_telemetry') as mock_setup_telemetry, \
             patch('mcp_commit_story.__main__.get_mcp_metrics') as mock_metrics:
            
            # Setup mocks
            mock_config = Mock()
            mock_config.telemetry_enabled = True
            mock_validate_config.return_value = mock_config
            mock_setup_telemetry.side_effect = Exception("Telemetry setup failed")
            
            mock_metrics_instance = Mock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Execute
            exit_code = main()
            
            # Verify - should fail due to telemetry setup failure (fail-fast approach)
            assert exit_code == 1
            mock_metrics_instance.record_counter.assert_any_call("server_startup_error", 1)


class TestMCPServerConfigValidation:
    """Test configuration validation functionality."""

    def test_validate_config_with_missing_required_keys(self):
        """Test configuration validation with missing required keys."""
        
        with patch('mcp_commit_story.__main__.load_config') as mock_load_config:
            # Test empty/invalid config triggers ConfigError
            mock_load_config.side_effect = ConfigError("Missing required configuration keys")
            
            result = validate_server_config()
            assert result is False

    def test_validate_config_with_invalid_tools_path(self):
        """Test configuration validation with invalid tools path."""
        
        with patch('mcp_commit_story.__main__.load_config') as mock_load_config:
            # Test invalid config triggers ConfigError  
            mock_load_config.side_effect = ConfigError("Invalid tools path")
            
            result = validate_server_config()
            assert result is False

    def test_validate_config_exception_handling(self):
        """Test configuration validation handles exceptions gracefully."""
        
        with patch('mcp_commit_story.__main__.load_config') as mock_load_config:
            # Force an exception during validation
            mock_load_config.side_effect = OSError("Permission denied")
            
            result = validate_server_config()
            assert result is False 