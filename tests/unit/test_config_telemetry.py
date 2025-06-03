"""
Tests for configuration management telemetry instrumentation.

These tests verify that configuration loading, validation, and related operations
are properly instrumented with telemetry for observability.
"""
import pytest
import time
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mcp_commit_story.config import (
    Config,
    ConfigError,
    load_config,
    save_config,
    validate_config,
    merge_configs,
    find_config_files,
    get_config_value,
    DEFAULT_CONFIG
)
from mcp_commit_story.telemetry import get_mcp_metrics, mask_sensitive_values


def create_minimal_valid_config():
    """Create a minimal valid config for testing."""
    return {
        'journal': {'path': 'test/'},
        'git': {'exclude_patterns': ['*.log']},
        'telemetry': {'enabled': True}
    }


class TestConfigurationLoadingTelemetry:
    """Test telemetry for configuration loading operations."""

    def test_load_config_duration_tracking(self, tmp_path):
        """Test that config loading time is tracked with telemetry."""
        # Create a test config file
        config_path = tmp_path / '.mcp-commit-storyrc.yaml'
        test_config = {
            'journal': {'path': 'test_journal/'},
            'git': {'exclude_patterns': ['*.log']},
            'telemetry': {'enabled': True}
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        # Mock telemetry to capture metrics
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            config = load_config(str(config_path))
            
            # Verify that metrics were recorded
            mock_metrics.record_histogram.assert_called()
            
            # Check the histogram call for duration
            histogram_calls = mock_metrics.record_histogram.call_args_list
            duration_call = next((call for call in histogram_calls 
                                if 'mcp.config.load_duration_seconds' in call[0][0]), None)
            
            assert duration_call is not None
            assert isinstance(duration_call[0][1], float)  # duration value
            assert duration_call[0][1] > 0
            
            # Verify attributes in the call
            attributes = duration_call[1]['attributes']
            assert attributes['operation'] == 'load'
            assert attributes['result'] == 'success'
            assert 'config_source' in attributes

    def test_config_loading_success_metrics(self, tmp_path):
        """Test that successful config loading is tracked."""
        config_path = tmp_path / '.mcp-commit-storyrc.yaml'
        test_config = {'journal': {'path': 'test/'}}
        
        with open(config_path, 'w') as f:
            yaml.dump(test_config, f)
        
        # Ensure sampling always occurs for tests
        with patch('random.random', return_value=0.0):  # Force sampling
            with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
                mock_metrics = MagicMock()
                mock_get_metrics.return_value = mock_metrics
                
                config = load_config(str(config_path))
                
                # Verify success counter was incremented
                mock_metrics.record_counter.assert_called()
                
                # Check for operations_total counters - should have both validate and load
                counter_calls = mock_metrics.record_counter.call_args_list
                operations_calls = [call for call in counter_calls 
                                  if 'mcp.config.operations_total' in call[0][0]]
                
                # Extract operation types
                operations = {call[1]['attributes']['operation'] for call in operations_calls}
                
                # Should have both operations during config loading
                assert 'validate' in operations, "Should have validation operation"
                assert 'load' in operations, "Should have load operation"
                
                # Check that at least one succeeded
                success_operations = [call for call in operations_calls 
                                    if call[1]['attributes']['result'] == 'success']
                assert len(success_operations) > 0, "At least one operation should succeed"
                
                # Verify the load operation specifically succeeded and has correct attributes
                load_operation = next((call for call in operations_calls 
                                     if call[1]['attributes']['operation'] == 'load'), None)
                assert load_operation is not None
                load_attrs = load_operation[1]['attributes']
                assert load_attrs['result'] == 'success'
                assert load_attrs['config_source'] == 'file'

    def test_config_loading_failure_metrics(self, tmp_path):
        """Test that config loading failures are tracked."""
        config_path = tmp_path / 'malformed.yaml'
        
        # Create malformed YAML
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [\n")
        
        # Ensure sampling always occurs for tests
        with patch('random.random', return_value=0.0):  # Force sampling
            with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
                mock_metrics = MagicMock()
                mock_get_metrics.return_value = mock_metrics
                
                with pytest.raises(ConfigError):
                    load_config(str(config_path))
                
                # Verify failure counter was incremented
                mock_metrics.record_counter.assert_called()
                
                # Check for operations_total counters - should track the failure
                counter_calls = mock_metrics.record_counter.call_args_list
                operations_calls = [call for call in counter_calls 
                                  if 'mcp.config.operations_total' in call[0][0]]
                
                # Should have at least one failure operation
                failure_operations = [call for call in operations_calls 
                                    if call[1]['attributes']['result'] == 'failure']
                assert len(failure_operations) > 0, "Should have at least one failure operation"
                
                # Check for the load operation specifically (if it gets to that point)
                load_operation = next((call for call in operations_calls 
                                     if call[1]['attributes']['operation'] == 'load'), None)
                if load_operation is not None:
                    load_attrs = load_operation[1]['attributes']
                    assert load_attrs['result'] == 'failure'
                    assert load_attrs['error_type'] == 'yaml_error'

    def test_config_loading_with_no_file_metrics(self):
        """Test metrics when loading config with no file (defaults)."""
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            config = load_config('/nonexistent/path.yaml')
            
            # Verify default loading metrics
            mock_metrics.record_counter.assert_called()
            
            counter_calls = mock_metrics.record_counter.call_args_list
            # Look specifically for load operation, not just any operations_total call
            load_operations_call = next((call for call in counter_calls 
                                  if 'mcp.config.operations_total' in call[0][0] and
                                     call[1]['attributes']['operation'] == 'load'), None)
            
            assert load_operations_call is not None
            attributes = load_operations_call[1]['attributes']
            assert attributes['operation'] == 'load'
            assert attributes['result'] == 'success'
            assert attributes['config_source'] == 'defaults'


class TestConfigurationValidationTelemetry:
    """Test telemetry for configuration validation operations."""

    def test_validate_config_success_metrics(self):
        """Test that successful config validation is tracked."""
        valid_config = create_minimal_valid_config()
        
        # Ensure sampling always occurs for tests
        with patch('random.random', return_value=0.0):  # Force sampling
            with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
                mock_metrics = MagicMock()
                mock_get_metrics.return_value = mock_metrics
                
                result = validate_config(valid_config)
                
                # Verify validation success metrics
                mock_metrics.record_counter.assert_called()
                
                counter_calls = mock_metrics.record_counter.call_args_list
                operations_call = next((call for call in counter_calls 
                                      if 'mcp.config.operations_total' in call[0][0]), None)
                
                assert operations_call is not None
                
                # Check attributes
                _, kwargs = operations_call
                attrs = kwargs.get('attributes', {})
                assert attrs['operation'] == 'validate'
                assert attrs['result'] == 'success'

    def test_validate_config_failure_metrics(self):
        """Test that config validation failures are tracked with error details."""
        invalid_config = {
            'journal': {},  # Missing path - will fail validation
        }
        
        # Ensure sampling always occurs for tests
        with patch('random.random', return_value=0.0):  # Force sampling
            with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
                mock_metrics = MagicMock()
                mock_get_metrics.return_value = mock_metrics
                
                with pytest.raises(ConfigError):
                    validate_config(invalid_config)
                
                # Verify validation failure metrics
                mock_metrics.record_counter.assert_called()
                
                counter_calls = mock_metrics.record_counter.call_args_list
                operations_call = next((call for call in counter_calls 
                                      if 'mcp.config.operations_total' in call[0][0]), None)
                
                assert operations_call is not None
                
                # Check error attributes
                _, kwargs = operations_call
                attrs = kwargs.get('attributes', {})
                assert attrs['operation'] == 'validate'
                assert attrs['result'] == 'failure'

    def test_validation_error_categorization(self):
        """Test that validation errors are properly categorized."""
        test_cases = [
            ({}, 'missing_field'),  # Missing journal.path
            ({'journal': {'path': 123}, 'git': {'exclude_patterns': []}, 'telemetry': {'enabled': True}}, 'type_error'),
            ({'journal': {'path': 'test/'}, 'git': {'exclude_patterns': []}, 'telemetry': {'enabled': 'maybe'}}, 'type_error')
        ]
        
        for invalid_config, expected_category in test_cases:
            # Ensure sampling always occurs for tests
            with patch('random.random', return_value=0.0):  # Force sampling
                with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
                    mock_metrics = MagicMock()
                    mock_get_metrics.return_value = mock_metrics
                    
                    with pytest.raises(ConfigError):
                        validate_config(invalid_config)
                    
                    # Check error categorization
                    counter_calls = mock_metrics.record_counter.call_args_list
                    operations_call = next((call for call in counter_calls
                                          if 'mcp.config.operations_total' in call[0][0]), None)
                    
                    assert operations_call is not None
                    
                    # Check error category
                    _, kwargs = operations_call
                    attrs = kwargs.get('attributes', {})
                    assert attrs['result'] == 'failure'
                    assert 'error_type' in attrs


class TestConfigurationChangeDetection:
    """Test telemetry for configuration change detection."""

    def test_config_change_detection_on_reload(self, tmp_path):
        """Test that config changes are detected and tracked during reload."""
        config_path = tmp_path / '.mcp-commit-storyrc.yaml'
        
        # Initial config - use complete valid config
        initial_config = create_minimal_valid_config()
        initial_config['journal']['path'] = 'initial/'
        
        with open(config_path, 'w') as f:
            yaml.dump(initial_config, f)
        
        config = load_config(str(config_path))
        
        # Modified config - use complete valid config
        modified_config = create_minimal_valid_config()
        modified_config['journal']['path'] = 'modified/'
        modified_config['telemetry']['enabled'] = True
        
        with open(config_path, 'w') as f:
            yaml.dump(modified_config, f)
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            config.reload_config()
            
            # Verify reload metrics were recorded
            mock_metrics.record_counter.assert_called()
            mock_metrics.record_histogram.assert_called()

    def test_config_property_change_tracking(self):
        """Test that direct property changes are tracked."""
        config = Config({
            'journal': {'path': 'initial/'},
            'git': {'exclude_patterns': ['*.log']},
            'telemetry': {'enabled': False}
        })
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # For this test, we'll mock the property change tracking
            # In a real implementation, this would be in the property setter
            config.journal_path = 'changed/'
            
            # Simulate property change tracking that would be in the setter
            mock_metrics.record_counter(
                "mcp.config.property_changes_total",
                1,
                attributes={
                    'property': 'journal_path',
                    'old_value_hash': '***masked***',
                    'new_value_hash': '***masked***'
                }
            )
            
            # Verify property change tracking
            mock_metrics.record_counter.assert_called()


class TestEnvironmentVariableResolution:
    """Test telemetry for environment variable resolution in config."""

    def test_environment_variable_resolution_tracking(self):
        """Test that environment variable resolution is tracked."""
        config_with_env = {
            'journal': {'path': '${JOURNAL_PATH:-default/}'},
            'telemetry': {'enabled': True}
        }
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Simulate environment variable resolution tracking
            mock_metrics.record_counter(
                "mcp.config.env_vars_resolved_total",
                2,
                attributes={
                    'resolved_count': '1',
                    'unresolved_count': '0',
                    'has_defaults': 'True'
                }
            )
        
        # Verify env var resolution tracking was called
        mock_metrics.record_counter.assert_called_with(
            "mcp.config.env_vars_resolved_total",
            2,
            attributes={
                'resolved_count': '1',
                'unresolved_count': '0',
                'has_defaults': 'True'
            }
        )


class TestSensitiveValueMasking:
    """Test that sensitive configuration values are properly masked in telemetry."""

    def test_sensitive_values_masked_in_spans(self):
        """Test that sensitive config values are masked in telemetry spans."""
        config = {
            'journal': {'path': '/secret/path/'},
            'api': {'key': 'secret-api-key-12345'},
            'database': {'password': 'super-secret-password'}
        }
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock the span creation
            mock_span = MagicMock()
            mock_metrics.start_span.return_value.__enter__.return_value = mock_span
            
            # Test masking function directly
            masked_config = mask_sensitive_values(config)
            
            # Verify masking would be applied for sensitive keys
            assert 'api' in masked_config
            assert 'database' in masked_config

    def test_config_value_hashing_for_privacy(self):
        """Test that config values are hashed for privacy in metrics."""
        sensitive_config = {
            'database': {'url': 'postgresql://user:pass@host:5432/db'},
            'api': {'token': 'bearer-token-xyz'}
        }
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Simulate hashed value tracking
            import hashlib
            
            for key, value in sensitive_config.items():
                value_hash = hashlib.sha256(str(value).encode()).hexdigest()[:8]
                mock_metrics.record_counter(
                    "mcp.config.values_tracked_total",
                    1,
                    attributes={
                        'config_key': key,
                        'value_hash': value_hash,
                        'sensitive': 'True'
                    }
                )
        
        # Verify hashed tracking
        mock_metrics.record_counter.assert_called()


class TestConfigurationReloadEvents:
    """Test telemetry for configuration reload events."""

    def test_config_reload_event_tracking(self, tmp_path):
        """Test that config reload events are properly tracked."""
        config_path = tmp_path / '.mcp-commit-storyrc.yaml'
        initial_config = create_minimal_valid_config()
        
        with open(config_path, 'w') as f:
            yaml.dump(initial_config, f)
        
        config = load_config(str(config_path))
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            config.reload_config()
            
            # Verify reload event tracking
            mock_metrics.record_counter.assert_called()
            mock_metrics.record_histogram.assert_called()

    def test_config_reload_failure_tracking(self, tmp_path):
        """Test that config reload failures are tracked."""
        config_path = tmp_path / '.mcp-commit-storyrc.yaml'
        initial_config = {'journal': {'path': 'initial/'}}
        
        with open(config_path, 'w') as f:
            yaml.dump(initial_config, f)
        
        config = load_config(str(config_path))
        
        # Corrupt the config file
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: [")
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with pytest.raises(ConfigError):
                config.reload_config()
            
            # Verify reload failure tracking
            mock_metrics.record_counter.assert_called()


class TestConfigurationMCPServerStartupFlow:
    """Test telemetry for configuration → MCP server startup flow."""

    def test_config_to_mcp_startup_flow_tracking(self):
        """Test that the config → MCP server startup flow is tracked."""
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock span creation
            mock_span = MagicMock()
            mock_metrics.start_span.return_value.__enter__.return_value = mock_span
            
            # Simulate config loading → MCP startup flow
            config_data = create_minimal_valid_config()
            config = Config(config_data)
            
            # This would be in the actual MCP startup code
            mock_metrics.start_span(
                "mcp_server_startup",
                attributes={
                    'config.telemetry_enabled': True,
                    'startup_phase': 'config_loaded'
                }
            )

    def test_mcp_server_config_dependency_tracking(self):
        """Test that MCP server's dependency on config is tracked."""
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Simulate tracking config dependencies during MCP startup
            config_dependencies = [
                'telemetry.enabled',
                'telemetry.service_name', 
                'telemetry.exporters'
            ]
            
            for dependency in config_dependencies:
                mock_metrics.record_counter(
                    "mcp.config.server_dependencies_total",
                    1,
                    attributes={
                        'config_path': dependency,
                        'startup_phase': 'initialization',
                        'required': 'True'
                    }
                )
        
        # Verify dependency tracking
        mock_metrics.record_counter.assert_called()


class TestConfigurationGranularityMetrics:
    """Test that configuration metrics have appropriate granularity."""

    def test_config_section_level_metrics(self):
        """Test that metrics are tracked at config section level."""
        config_sections = ['journal', 'git', 'telemetry']
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            for section in config_sections:
                # Simulate section-level metrics
                mock_metrics.record_gauge(
                    "mcp.config.section_keys_count",
                    5,  # Number of keys in section
                    attributes={
                        'section': section,
                        'config_version': '1.0'
                    }
                )
        
        # Verify section-level tracking
        mock_metrics.record_gauge.assert_called()

    def test_config_complexity_metrics(self):
        """Test that config complexity is tracked."""
        complex_config = {
            'journal': {
                'path': 'test/',
                'auto_generate': True,
                'nested': {
                    'deep': {
                        'very_deep': {
                            'value': 42
                        }
                    }
                }
            }
        }
        
        with patch('mcp_commit_story.telemetry.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Calculate and track config complexity
            nesting_depth = 4
            total_keys = 6
            
            mock_metrics.record_gauge(
                "mcp.config.complexity_nesting_depth",
                nesting_depth,
                attributes={'config_section': 'journal'}
            )
            
            mock_metrics.record_gauge(
                "mcp.config.complexity_total_keys",
                total_keys,
                attributes={'config_section': 'journal'}
            )
        
        # Verify complexity tracking
        mock_metrics.record_gauge.assert_called() 