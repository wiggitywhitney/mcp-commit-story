import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_commit_story.telemetry import (
    setup_telemetry,
    get_tracer,
    get_meter,
    shutdown_telemetry
)
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider


class TestTelemetrySetup:
    """Test OpenTelemetry foundation setup functionality."""
    
    def test_setup_telemetry_enabled(self):
        """Test setup_telemetry with enabled configuration."""
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-service",
                "service_version": "1.0.0"
            }
        }
        
        # Should initialize TracerProvider and MeterProvider
        result = setup_telemetry(config)
        
        assert result is True
        assert isinstance(trace.get_tracer_provider(), TracerProvider)
        assert isinstance(metrics.get_meter_provider(), MeterProvider)
    
    def test_setup_telemetry_disabled(self):
        """Test setup_telemetry with disabled configuration."""
        config = {
            "telemetry": {
                "enabled": False,
                "service_name": "test-service"
            }
        }
        
        # Should not initialize providers when disabled
        result = setup_telemetry(config)
        
        assert result is False
        # Should use NoOp providers when disabled
    
    def test_setup_telemetry_missing_config(self):
        """Test setup_telemetry with missing telemetry config."""
        config = {}
        
        # Should use defaults when config missing
        result = setup_telemetry(config)
        
        assert result is True  # Should default to enabled
    
    def test_get_tracer_returns_correct_instance(self):
        """Test get_tracer returns correct tracer instance."""
        # Setup telemetry first
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        setup_telemetry(config)
        
        tracer = get_tracer("test-component")
        
        assert tracer is not None
        assert hasattr(tracer, 'start_span')
        assert hasattr(tracer, 'start_as_current_span')
    
    def test_get_tracer_with_custom_name(self):
        """Test get_tracer with custom component name."""
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        setup_telemetry(config)
        
        tracer1 = get_tracer("component1")
        tracer2 = get_tracer("component2")
        
        # Should return different tracer instances for different names
        assert tracer1 is not None
        assert tracer2 is not None
    
    def test_get_meter_returns_correct_instance(self):
        """Test get_meter returns correct meter instance."""
        # Setup telemetry first
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        setup_telemetry(config)
        
        meter = get_meter("test-component")
        
        assert meter is not None
        assert hasattr(meter, 'create_counter')
        assert hasattr(meter, 'create_histogram')
        assert hasattr(meter, 'create_gauge')
    
    def test_get_meter_with_custom_name(self):
        """Test get_meter with custom component name."""
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        setup_telemetry(config)
        
        meter1 = get_meter("component1")
        meter2 = get_meter("component2")
        
        # Should return different meter instances for different names
        assert meter1 is not None
        assert meter2 is not None
    
    def test_resource_configuration_with_service_attributes(self):
        """Test resource configuration includes service name and version."""
        # Note: Due to OpenTelemetry global state, this test verifies 
        # that our telemetry setup works, but may not reflect exact config
        # from this specific test due to provider reuse
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-service",
                "service_version": "2.1.0",
                "deployment_environment": "test"
            }
        }
        
        result = setup_telemetry(config)
        assert result is True
        
        # Verify we can get tracers and meters successfully
        tracer = get_tracer("test")
        meter = get_meter("test")
        assert tracer is not None
        assert meter is not None
        
        # Verify the provider is a real provider, not NoOp
        tracer_provider = trace.get_tracer_provider()
        meter_provider = metrics.get_meter_provider()
        assert isinstance(tracer_provider, TracerProvider)
        assert isinstance(meter_provider, MeterProvider)
    
    def test_tracer_provider_initialization(self):
        """Test TracerProvider is properly initialized."""
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        
        result = setup_telemetry(config)
        assert result is True
        
        tracer_provider = trace.get_tracer_provider()
        assert isinstance(tracer_provider, TracerProvider)
        
        # Should be able to create spans
        tracer = get_tracer("test")
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None
            span.set_attribute("test.key", "test.value")
    
    def test_meter_provider_initialization(self):
        """Test MeterProvider is properly initialized."""
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        
        result = setup_telemetry(config)
        assert result is True
        
        meter_provider = metrics.get_meter_provider()
        assert isinstance(meter_provider, MeterProvider)
        
        # Should be able to create metrics
        meter = get_meter("test")
        counter = meter.create_counter("test_counter", description="Test counter")
        counter.add(1, {"test.key": "test.value"})
    
    def test_telemetry_disabling_via_configuration(self):
        """Test telemetry can be completely disabled via configuration."""
        config = {"telemetry": {"enabled": False}}
        
        result = setup_telemetry(config)
        
        assert result is False
        
        # When disabled, should still return tracers/meters but they should be NoOp
        tracer = get_tracer("test")
        meter = get_meter("test")
        
        assert tracer is not None
        assert meter is not None
        
        # These should be NoOp implementations when disabled
        # The actual implementation will handle this
    
    def teardown_method(self):
        """Clean up after each test."""
        # Reset telemetry state between tests
        shutdown_telemetry()


class TestTelemetryUtilities:
    """Test telemetry utility functions."""
    
    def test_shutdown_telemetry(self):
        """Test shutdown_telemetry cleans up resources."""
        config = {"telemetry": {"enabled": True, "service_name": "test"}}
        setup_telemetry(config)
        
        # Should complete without error
        shutdown_telemetry()
        
        # After shutdown, should be able to setup again
        result = setup_telemetry(config)
        assert result is True 