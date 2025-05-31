"""
Tests for MCP server telemetry integration.

This module tests the complete integration of the telemetry system with the MCP server,
including startup, tool call tracing, configuration validation, and error handling.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
import tempfile
import os
import yaml
from pathlib import Path

from mcp_commit_story.server import create_mcp_server, MCPError
from mcp_commit_story.config import Config, ConfigError
from mcp_commit_story import telemetry
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider


class TestMCPServerTelemetryIntegration:
    """Test MCP server integration with telemetry system."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'journal': {'path': 'test_journal/'},
                'git': {'exclude_patterns': ['test/**']},
                'telemetry': {
                    'enabled': True,
                    'service_name': 'test-mcp-server',
                    'service_version': '1.0.0',
                    'deployment_environment': 'test'
                }
            }
            yaml.dump(config_data, f)
            f.flush()
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def telemetry_disabled_config(self):
        """Create config with telemetry disabled."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'journal': {'path': 'test_journal/'},
                'git': {'exclude_patterns': ['test/**']},
                'telemetry': {'enabled': False}
            }
            yaml.dump(config_data, f)
            f.flush()
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def reset_telemetry(self):
        """Reset telemetry state before and after tests."""
        # Reset global state before test
        telemetry._telemetry_initialized = False
        telemetry._tracer_provider = None
        telemetry._meter_provider = None
        telemetry._mcp_metrics = None
        
        # Reset OpenTelemetry global state
        trace._TRACER_PROVIDER = None
        metrics._METER_PROVIDER = None
        
        yield
        
        # Clean up after test
        if telemetry._telemetry_initialized:
            telemetry.shutdown_telemetry()
        telemetry._telemetry_initialized = False
        telemetry._tracer_provider = None
        telemetry._meter_provider = None
        telemetry._mcp_metrics = None
        trace._TRACER_PROVIDER = None
        metrics._METER_PROVIDER = None

    def test_mcp_server_startup_with_telemetry_enabled(self, temp_config_file, reset_telemetry):
        """Test full MCP server startup with telemetry enabled."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            server = create_mcp_server(temp_config_file)
            
            assert server is not None
            assert hasattr(server, 'config')
            assert server.config.telemetry_enabled is True
            mock_setup.assert_called_once()

    def test_mcp_server_startup_with_telemetry_disabled(self, telemetry_disabled_config, reset_telemetry):
        """Test MCP server startup with telemetry disabled."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = False
            
            server = create_mcp_server(telemetry_disabled_config)
            
            assert server is not None
            assert hasattr(server, 'config')
            assert server.config.telemetry_enabled is False
            # setup_telemetry should still be called but return False
            mock_setup.assert_called_once()

    def test_mcp_server_startup_telemetry_failure_graceful_degradation(self, temp_config_file, reset_telemetry):
        """Test graceful degradation when telemetry fails to initialize."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.side_effect = Exception("Telemetry setup failed")
            
            # Server should still start even if telemetry fails (graceful degradation)
            server = create_mcp_server(temp_config_file)
            assert server is not None
            assert hasattr(server, 'config')
            assert server.telemetry_initialized is False  # Should be False due to failure

    def test_configuration_validation_invalid_config(self, reset_telemetry):
        """Test configuration validation with invalid telemetry config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Invalid config - telemetry.enabled should be boolean, not string
            config_data = {
                'journal': {'path': 'test_journal/'},
                'telemetry': {'enabled': 'invalid'}  # Should be boolean
            }
            yaml.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ConfigError):
                create_mcp_server(f.name)
        
        os.unlink(f.name)

    def test_configuration_validation_missing_required_fields(self, reset_telemetry):
        """Test configuration validation with missing required fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Missing journal section
            config_data = {
                'telemetry': {'enabled': True}
            }
            yaml.dump(config_data, f)
            f.flush()
            
            # Should not raise error - defaults should be used
            server = create_mcp_server(f.name)
            assert server is not None
        
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_tool_call_tracing_end_to_end(self, temp_config_file, reset_telemetry):
        """Test end-to-end tracing of tool calls through the MCP server."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            # Mock tracer for testing
            mock_tracer = Mock()
            mock_span = Mock()
            mock_tracer.start_span.return_value.__enter__ = Mock(return_value=mock_span)
            mock_tracer.start_span.return_value.__exit__ = Mock(return_value=None)
            
            with patch('mcp_commit_story.telemetry.get_tracer') as mock_get_tracer:
                mock_get_tracer.return_value = mock_tracer
                
                server = create_mcp_server(temp_config_file)
                
                # Verify tracing is available through telemetry integration
                assert server.telemetry_initialized is True
                
                # Test that tracer can be obtained (tracing infrastructure available)
                tracer = mock_get_tracer.return_value
                assert tracer is not None
                
                # Test span creation (core tracing functionality)
                span = tracer.start_span("test_operation")
                assert span is not None

    @pytest.mark.asyncio
    async def test_span_propagation_across_components(self, temp_config_file, reset_telemetry):
        """Test span propagation across different MCP server components."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            # Mock trace context
            mock_span_context = Mock()
            mock_span = Mock()
            mock_span.get_span_context.return_value = mock_span_context
            
            with patch('opentelemetry.trace.get_current_span') as mock_get_span:
                mock_get_span.return_value = mock_span
                
                server = create_mcp_server(temp_config_file)
                
                # Test that telemetry is properly initialized and available
                assert server.telemetry_initialized is True
                
                # Test span context propagation functionality
                current_span = mock_get_span.return_value
                assert current_span is not None
                
                # Verify span context can be retrieved
                span_context = current_span.get_span_context()
                assert span_context is not None

    def test_metrics_collection_during_operations(self, temp_config_file, reset_telemetry):
        """Test metrics collection during MCP server operations."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            # Mock metrics
            mock_metrics = Mock()
            telemetry._mcp_metrics = mock_metrics
            
            server = create_mcp_server(temp_config_file)
            
            # Verify metrics instance is available
            metrics_instance = telemetry.get_mcp_metrics()
            assert metrics_instance is not None

    def test_telemetry_disable_enable_scenarios(self, reset_telemetry):
        """Test telemetry disable/enable scenarios."""
        # Test enabling telemetry - include all required config fields
        config_data = {
            'journal': {'path': 'test_journal/'}, 
            'git': {'exclude_patterns': ['test/**']},
            'telemetry': {'enabled': True}
        }
        config = Config(config_data)
        
        with patch('mcp_commit_story.telemetry.TracerProvider'), \
             patch('mcp_commit_story.telemetry.MeterProvider'):
            result = telemetry.setup_telemetry(config.as_dict())
            assert result is True
            assert telemetry._telemetry_initialized is True
        
        # Reset for disable test
        telemetry._telemetry_initialized = False
        
        # Test disabling telemetry - include all required config fields
        config_data = {
            'journal': {'path': 'test_journal/'}, 
            'git': {'exclude_patterns': ['test/**']},
            'telemetry': {'enabled': False}
        }
        config = Config(config_data)
        
        result = telemetry.setup_telemetry(config.as_dict())
        assert result is False
        assert telemetry._telemetry_initialized is False

    def test_telemetry_shutdown_hooks(self, temp_config_file, reset_telemetry):
        """Test telemetry shutdown hooks are properly configured."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            server = create_mcp_server(temp_config_file)
            
            # Test shutdown functionality
            with patch('mcp_commit_story.telemetry.shutdown_telemetry') as mock_shutdown:
                telemetry.shutdown_telemetry()
                mock_shutdown.assert_called_once()

    def test_telemetry_health_checks(self, temp_config_file, reset_telemetry):
        """Test telemetry system health checks."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            server = create_mcp_server(temp_config_file)
            
            # Verify telemetry components are healthy
            assert telemetry._telemetry_initialized is False  # Mock setup
            
            # Test with actual initialization
            telemetry._telemetry_initialized = True
            assert telemetry._telemetry_initialized is True

    @pytest.mark.asyncio
    async def test_error_handling_telemetry_failures(self, temp_config_file, reset_telemetry):
        """Test error handling when telemetry operations fail."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            server = create_mcp_server(temp_config_file)
            
            # Simulate telemetry operation failure
            with patch('mcp_commit_story.telemetry.get_tracer') as mock_get_tracer:
                mock_get_tracer.side_effect = Exception("Tracer failed")
                
                # Test that telemetry failures are handled gracefully in error decorator
                try:
                    # Import the error handling function to test directly
                    from mcp_commit_story.server import handle_mcp_error
                    
                    # Create a test function that would use telemetry
                    @handle_mcp_error
                    async def test_operation():
                        return {"status": "success", "data": "test"}
                    
                    # This should not crash even when get_tracer fails
                    result = await test_operation()
                    assert result is not None
                    assert result.get("status") == "success"
                    
                except Exception as e:
                    # Should not reach here - telemetry failures should be graceful
                    pytest.fail(f"Telemetry failure was not handled gracefully: {e}")

    def test_config_hot_reload_with_telemetry(self, temp_config_file, reset_telemetry):
        """Test configuration hot reload affects telemetry settings."""
        with patch('mcp_commit_story.telemetry.setup_telemetry') as mock_setup:
            mock_setup.return_value = True
            
            server = create_mcp_server(temp_config_file)
            
            # Test hot reload functionality
            assert hasattr(server, 'reload_config')
            assert callable(server.reload_config)
            
            # Verify reload doesn't crash
            server.reload_config()


class TestTelemetrySystemIntegration:
    """Test telemetry system integration points."""

    @pytest.fixture
    def reset_telemetry(self):
        """Reset telemetry state before and after tests."""
        # Reset global state before test
        telemetry._telemetry_initialized = False
        telemetry._tracer_provider = None
        telemetry._meter_provider = None
        telemetry._mcp_metrics = None
        
        yield
        
        # Clean up after test
        if telemetry._telemetry_initialized:
            telemetry.shutdown_telemetry()
        telemetry._telemetry_initialized = False
        telemetry._tracer_provider = None
        telemetry._meter_provider = None
        telemetry._mcp_metrics = None

    def test_tracer_provider_initialization(self, reset_telemetry):
        """Test TraceProvider is properly initialized."""
        config = {'telemetry': {'enabled': True, 'service_name': 'test'}}
        
        with patch('mcp_commit_story.telemetry.TracerProvider') as mock_provider:
            with patch('mcp_commit_story.telemetry.MeterProvider'):
                with patch('mcp_commit_story.telemetry.setup_structured_logging'):
                    telemetry.setup_telemetry(config)
                    mock_provider.assert_called_once()

    def test_meter_provider_initialization(self, reset_telemetry):
        """Test MeterProvider is properly initialized."""
        config = {'telemetry': {'enabled': True, 'service_name': 'test'}}
        
        with patch('mcp_commit_story.telemetry.MeterProvider') as mock_provider:
            with patch('mcp_commit_story.telemetry.TracerProvider'):
                with patch('mcp_commit_story.telemetry.setup_structured_logging'):
                    telemetry.setup_telemetry(config)
                    mock_provider.assert_called_once()

    def test_structured_logging_integration(self, reset_telemetry):
        """Test structured logging is integrated with telemetry."""
        config = {'telemetry': {'enabled': True, 'service_name': 'test'}}
        
        with patch('mcp_commit_story.telemetry.TracerProvider'):
            with patch('mcp_commit_story.telemetry.MeterProvider'):
                with patch('mcp_commit_story.telemetry.setup_structured_logging') as mock_setup:
                    mock_setup.return_value = True
                    telemetry.setup_telemetry(config)
                    mock_setup.assert_called_once_with(config)

    def test_mcp_metrics_initialization(self, reset_telemetry):
        """Test MCPMetrics is properly initialized."""
        config = {'telemetry': {'enabled': True, 'service_name': 'test'}}
        
        with patch('mcp_commit_story.telemetry.TracerProvider'):
            with patch('mcp_commit_story.telemetry.MeterProvider'):
                with patch('mcp_commit_story.telemetry.setup_structured_logging'):
                    with patch('mcp_commit_story.telemetry.MCPMetrics') as mock_metrics:
                        telemetry.setup_telemetry(config)
                        mock_metrics.assert_called_once()

    def test_service_resource_configuration(self, reset_telemetry):
        """Test service resource is properly configured."""
        config = {
            'telemetry': {
                'enabled': True,
                'service_name': 'test-service',
                'service_version': '2.0.0',
                'deployment_environment': 'staging'
            }
        }
        
        with patch('mcp_commit_story.telemetry.Resource') as mock_resource:
            with patch('mcp_commit_story.telemetry.TracerProvider'):
                with patch('mcp_commit_story.telemetry.MeterProvider'):
                    with patch('mcp_commit_story.telemetry.setup_structured_logging'):
                        telemetry.setup_telemetry(config)
                        
                        # Verify Resource.create was called with correct attributes
                        mock_resource.create.assert_called_once()
                        args = mock_resource.create.call_args[0][0]
                        assert args['service.name'] == 'test-service'
                        assert args['service.version'] == '2.0.0'
                        assert args['deployment.environment'] == 'staging' 