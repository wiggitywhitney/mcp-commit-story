"""
Tests for Multi-Exporter Configuration System with Enhanced Design

This module tests the multi-exporter telemetry configuration system including:
- Environment variable precedence hierarchy
- Partial success error handling  
- Comprehensive validation rules
- Multiple exporter support (console, OTLP, Prometheus)
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

from src.mcp_commit_story.multi_exporter import (
    ExporterConfigManager,
    configure_exporters,
    ExporterConfigurationError,
    ValidationError,
    PartialSuccessResult
)

# Shared test configuration
VALID_CONFIG = {
    "telemetry": {
        "enabled": True,
        "service_name": "mcp-journal",
        "exporters": {
            "console": {
                "enabled": True,
                "traces": True,
                "metrics": True
            },
            "otlp": {
                "enabled": True,
                "endpoint": "http://localhost:4317",
                "protocol": "grpc",
                "headers": {
                    "authorization": "Bearer token123"
                },
                "timeout": 30,
                "traces": True,
                "metrics": True
            },
            "prometheus": {
                "enabled": True,
                "port": 8888,
                "endpoint": "/metrics",
                "metrics": True,
                "traces": False
            }
        }
    }
}


class TestExporterConfigManager:
    """Test the ExporterConfigManager with enhanced design features."""

    def setup_method(self):
        """Set up test environment."""
        self.manager = ExporterConfigManager()
        self.valid_config = VALID_CONFIG.copy()

    def test_environment_variable_precedence_hierarchy(self):
        """Test that environment variables follow the correct precedence hierarchy."""
        base_config = self.valid_config.copy()
        
        # Test MCP-specific env vars (highest priority)
        with patch.dict(os.environ, {
            'MCP_PROMETHEUS_PORT': '9999',
            'MCP_CONSOLE_ENABLED': 'false',
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://standard:4317',
            'MCP_OTLP_ENDPOINT': 'http://mcp-specific:4317'
        }):
            resolved_config = self.manager.resolve_configuration(base_config)
            
            # MCP-specific should override standard OTel
            assert resolved_config['telemetry']['exporters']['prometheus']['port'] == 9999
            assert resolved_config['telemetry']['exporters']['console']['enabled'] is False
            assert resolved_config['telemetry']['exporters']['otlp']['endpoint'] == 'http://mcp-specific:4317'

    def test_standard_otel_env_vars_precedence(self):
        """Test that standard OTel env vars override config file values."""
        base_config = self.valid_config.copy()
        
        with patch.dict(os.environ, {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://otel:4317',
            'OTEL_EXPORTER_OTLP_HEADERS': 'x-api-key=secret123'
        }):
            resolved_config = self.manager.resolve_configuration(base_config)
            
            assert resolved_config['telemetry']['exporters']['otlp']['endpoint'] == 'http://otel:4317'
            assert 'x-api-key' in resolved_config['telemetry']['exporters']['otlp']['headers']

    def test_config_file_values_used_when_no_env_vars(self):
        """Test that config file values are used when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            resolved_config = self.manager.resolve_configuration(self.valid_config)
            
            assert resolved_config['telemetry']['exporters']['prometheus']['port'] == 8888
            assert resolved_config['telemetry']['exporters']['otlp']['endpoint'] == 'http://localhost:4317'

    def test_built_in_defaults_lowest_priority(self):
        """Test that built-in defaults are used when nothing else is available."""
        minimal_config = {"telemetry": {"enabled": True}}
        
        with patch.dict(os.environ, {}, clear=True):
            resolved_config = self.manager.resolve_configuration(minimal_config)
            
            # Should get built-in defaults
            assert resolved_config['telemetry']['service_name'] == 'mcp-commit-story'
            assert resolved_config['telemetry']['exporters']['console']['enabled'] is True


class TestValidationRules:
    """Test comprehensive validation rules for exporter configuration."""

    def setup_method(self):
        self.manager = ExporterConfigManager()

    def test_port_range_validation(self):
        """Test port range validation (1-65535)."""
        # Valid port
        config = {"telemetry": {"exporters": {"prometheus": {"port": 8888}}}}
        self.manager.validate_configuration(config)  # Should not raise
        
        # Invalid ports
        with pytest.raises(ValidationError, match="Port must be between 1 and 65535"):
            invalid_config = {"telemetry": {"exporters": {"prometheus": {"port": 0}}}}
            self.manager.validate_configuration(invalid_config)
            
        with pytest.raises(ValidationError, match="Port must be between 1 and 65535"):
            invalid_config = {"telemetry": {"exporters": {"prometheus": {"port": 65536}}}}
            self.manager.validate_configuration(invalid_config)

    def test_endpoint_path_validation(self):
        """Test endpoint must start with '/'."""
        # Valid endpoint
        config = {"telemetry": {"exporters": {"prometheus": {"endpoint": "/metrics"}}}}
        self.manager.validate_configuration(config)  # Should not raise
        
        # Invalid endpoint
        with pytest.raises(ValidationError, match="Endpoint must start with '/'"):
            invalid_config = {"telemetry": {"exporters": {"prometheus": {"endpoint": "metrics"}}}}
            self.manager.validate_configuration(invalid_config)

    def test_protocol_validation(self):
        """Test protocol must be 'grpc' or 'http'."""
        # Valid protocols
        for protocol in ['grpc', 'http']:
            config = {"telemetry": {"exporters": {"otlp": {"protocol": protocol}}}}
            self.manager.validate_configuration(config)  # Should not raise
        
        # Invalid protocol
        with pytest.raises(ValidationError, match="Protocol must be 'grpc' or 'http'"):
            invalid_config = {"telemetry": {"exporters": {"otlp": {"protocol": "invalid"}}}}
            self.manager.validate_configuration(invalid_config)

    def test_timeout_validation(self):
        """Test timeout must be positive integer."""
        # Valid timeout
        config = {"telemetry": {"exporters": {"otlp": {"timeout": 30}}}}
        self.manager.validate_configuration(config)  # Should not raise
        
        # Invalid timeouts
        with pytest.raises(ValidationError, match="Timeout must be a positive integer"):
            invalid_config = {"telemetry": {"exporters": {"otlp": {"timeout": 0}}}}
            self.manager.validate_configuration(invalid_config)
            
        with pytest.raises(ValidationError, match="Timeout must be a positive integer"):
            invalid_config = {"telemetry": {"exporters": {"otlp": {"timeout": -5}}}}
            self.manager.validate_configuration(invalid_config)

    def test_headers_validation(self):
        """Test headers must be valid key-value pairs."""
        # Valid headers
        config = {"telemetry": {"exporters": {"otlp": {"headers": {"key": "value"}}}}}
        self.manager.validate_configuration(config)  # Should not raise
        
        # Invalid headers (not a dict)
        with pytest.raises(ValidationError, match="Headers must be valid key-value pairs"):
            invalid_config = {"telemetry": {"exporters": {"otlp": {"headers": "invalid"}}}}
            self.manager.validate_configuration(invalid_config)


class TestPartialSuccessErrorHandling:
    """Test enhanced error handling with partial success pattern."""

    def setup_method(self):
        self.manager = ExporterConfigManager()
        self.valid_config = VALID_CONFIG.copy()

    @patch('src.mcp_commit_story.multi_exporter.setup_console_exporter')
    @patch('src.mcp_commit_story.multi_exporter.setup_otlp_exporter')  
    @patch('src.mcp_commit_story.multi_exporter.setup_prometheus_exporter')
    def test_partial_success_with_failed_exporter(self, mock_prometheus, mock_otlp, mock_console):
        """Test partial success when one exporter fails."""
        # Setup mocks - console and prometheus succeed, otlp fails
        mock_console.return_value = MagicMock()
        mock_prometheus.return_value = MagicMock()
        mock_otlp.side_effect = Exception("Connection timeout")
        
        result = configure_exporters(self.valid_config)
        
        assert isinstance(result, PartialSuccessResult)
        assert result.status == "partial_success"
        assert "console" in result.successful_exporters
        assert "prometheus" in result.successful_exporters
        assert "otlp" in result.failed_exporters
        assert result.failed_exporters["otlp"]["error"] == "Connection timeout"

    @patch('src.mcp_commit_story.multi_exporter.setup_console_exporter')
    @patch('src.mcp_commit_story.multi_exporter.setup_otlp_exporter')
    @patch('src.mcp_commit_story.multi_exporter.setup_prometheus_exporter')
    def test_complete_success(self, mock_prometheus, mock_otlp, mock_console):
        """Test complete success when all exporters succeed."""
        # Setup mocks - all succeed
        mock_console.return_value = MagicMock()
        mock_prometheus.return_value = MagicMock()
        mock_otlp.return_value = MagicMock()
        
        result = configure_exporters(self.valid_config)
        
        assert isinstance(result, PartialSuccessResult)
        assert result.status == "success"
        assert len(result.successful_exporters) == 3
        assert len(result.failed_exporters) == 0

    @patch('src.mcp_commit_story.multi_exporter.setup_console_exporter')
    @patch('src.mcp_commit_story.multi_exporter.setup_otlp_exporter')
    @patch('src.mcp_commit_story.multi_exporter.setup_prometheus_exporter')
    def test_detailed_error_information(self, mock_prometheus, mock_otlp, mock_console):
        """Test detailed error information in failed exporters."""
        # Setup mock to fail with detailed error
        mock_otlp.side_effect = ConnectionError("Failed to connect to http://localhost:4317 after 10 seconds")
        mock_console.return_value = MagicMock()
        mock_prometheus.return_value = MagicMock()
        
        result = configure_exporters(self.valid_config)
        
        failed_otlp = result.failed_exporters["otlp"]
        assert "Failed to connect" in failed_otlp["error"]
        assert "http://localhost:4317" in failed_otlp["details"]
        assert "10 seconds" in failed_otlp["details"]


class TestMultipleExporterSupport:
    """Test support for multiple exporters simultaneously."""

    def setup_method(self):
        self.manager = ExporterConfigManager()
        self.valid_config = VALID_CONFIG.copy()

    def test_console_exporter_configuration(self):
        """Test console exporter configuration."""
        config = {
            "telemetry": {
                "exporters": {
                    "console": {
                        "enabled": True,
                        "traces": True,
                        "metrics": True
                    }
                }
            }
        }
        
        # Should validate successfully
        self.manager.validate_configuration(config)

    def test_otlp_exporter_configuration(self):
        """Test OTLP exporter configuration with various options."""
        config = {
            "telemetry": {
                "exporters": {
                    "otlp": {
                        "enabled": True,
                        "endpoint": "http://localhost:4317",
                        "protocol": "grpc",
                        "headers": {"authorization": "Bearer token123"},
                        "timeout": 30,
                        "traces": True,
                        "metrics": True
                    }
                }
            }
        }
        
        # Should validate successfully
        self.manager.validate_configuration(config)

    def test_prometheus_exporter_configuration(self):
        """Test Prometheus exporter configuration."""
        config = {
            "telemetry": {
                "exporters": {
                    "prometheus": {
                        "enabled": True,
                        "port": 8888,
                        "endpoint": "/metrics",
                        "metrics": True,
                        "traces": False  # Prometheus doesn't handle traces
                    }
                }
            }
        }
        
        # Should validate successfully
        self.manager.validate_configuration(config)

    def test_multiple_exporters_simultaneously(self):
        """Test configuration with multiple exporters enabled."""
        # Should validate successfully
        self.manager.validate_configuration(self.valid_config)

    def test_selective_exporter_enabling(self):
        """Test enabling only specific exporters."""
        config = {
            "telemetry": {
                "exporters": {
                    "console": {"enabled": True},
                    "otlp": {"enabled": False},
                    "prometheus": {"enabled": True}
                }
            }
        }
        
        # Should validate successfully
        self.manager.validate_configuration(config)


class TestConfigurationIntegration:
    """Test integration with existing configuration system."""

    def test_graceful_degradation_when_exporters_fail(self):
        """Test system continues operating when some exporters fail."""
        # This will be tested in integration tests
        pass

    def test_no_cascading_failures(self):
        """Test that one failed exporter doesn't break the entire system.""" 
        # This will be tested in integration tests
        pass

    def test_detailed_error_logging(self):
        """Test that exporter failures are logged for debugging."""
        # This will be tested in integration tests
        pass 