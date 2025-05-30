import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import asyncio
import functools

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
from opentelemetry.trace import Status, StatusCode


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


class TestMCPOperationInstrumentationDecorators:
    """Test MCP operation instrumentation decorators (Task 4.2)."""
    
    def setup_method(self):
        """Set up telemetry for each test."""
        config = {"telemetry": {"enabled": True, "service_name": "test-mcp"}}
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after each test."""
        shutdown_telemetry()
    
    def test_trace_mcp_operation_decorator_on_sync_function(self):
        """Test @trace_mcp_operation(name) decorator on synchronous function."""
        # Import the decorator that should exist (will fail until implemented)
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_sync_operation")
        def sync_function(x, y):
            return x + y
        
        # Execute the decorated function
        result = sync_function(2, 3)
        
        # Verify the function still works correctly
        assert result == 5
        
        # Note: Additional span verification would require a test exporter
        # For now, we verify the decorator doesn't break function execution
    
    def test_trace_mcp_operation_decorator_on_function_that_raises_exception(self):
        """Test decorator on function that raises exception."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_exception_operation")
        def function_that_raises():
            raise ValueError("Test error")
        
        # Should propagate the exception
        with pytest.raises(ValueError, match="Test error"):
            function_that_raises()
    
    def test_trace_mcp_operation_decorator_on_async_function(self):
        """Test decorator on async function."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_async_operation")
        async def async_function(x, y):
            await asyncio.sleep(0.001)  # Minimal delay
            return x * y
        
        # Execute the decorated async function
        result = asyncio.run(async_function(3, 4))
        
        # Verify the function still works correctly
        assert result == 12
    
    def test_trace_mcp_operation_span_attributes_correctly_set(self):
        """Test span attributes are correctly set."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        # This test would require a test exporter to capture spans
        # For now, we test that the decorator can be applied and called
        @trace_mcp_operation("test_attributes_operation")
        def function_with_attributes():
            return "success"
        
        result = function_with_attributes()
        assert result == "success"
    
    def test_trace_mcp_operation_span_context_propagation(self):
        """Test span context propagation to child operations."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("parent_operation")
        def parent_function():
            return child_function()
        
        @trace_mcp_operation("child_operation")
        def child_function():
            return "child_result"
        
        # Execute parent which calls child
        result = parent_function()
        assert result == "child_result"
    
    def test_trace_mcp_operation_error_recording_in_spans(self):
        """Test error recording in spans."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_error_recording")
        def function_with_error():
            raise RuntimeError("Test runtime error")
        
        # Error should be recorded in span and exception should propagate
        with pytest.raises(RuntimeError, match="Test runtime error"):
            function_with_error()
    
    def test_trace_mcp_operation_custom_attribute_addition(self):
        """Test custom attribute addition via decorator."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        # Test with custom attributes parameter (API to be designed)
        @trace_mcp_operation("test_custom_attrs", attributes={"custom.key": "custom.value"})
        def function_with_custom_attrs():
            return "custom_result"
        
        result = function_with_custom_attrs()
        assert result == "custom_result"
    
    def test_trace_mcp_operation_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_metadata")
        def original_function():
            """Original docstring."""
            return "original"
        
        # Verify function metadata is preserved
        assert original_function.__name__ == "original_function"
        assert "Original docstring" in original_function.__doc__
        
        # Verify function still works
        result = original_function()
        assert result == "original"
    
    def test_trace_mcp_operation_with_function_args_and_kwargs(self):
        """Test decorator works with functions that have args and kwargs."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_args_kwargs")
        def function_with_args_kwargs(a, b, *args, c=None, **kwargs):
            return {
                "a": a,
                "b": b, 
                "args": args,
                "c": c,
                "kwargs": kwargs
            }
        
        result = function_with_args_kwargs(1, 2, 3, 4, c=5, d=6, e=7)
        
        assert result["a"] == 1
        assert result["b"] == 2
        assert result["args"] == (3, 4)
        assert result["c"] == 5
        assert result["kwargs"] == {"d": 6, "e": 7}
    
    def test_trace_mcp_operation_async_exception_handling(self):
        """Test async function exception handling in decorator."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test_async_exception")
        async def async_function_with_error():
            await asyncio.sleep(0.001)
            raise ValueError("Async test error")
        
        # Should propagate the exception in async context
        with pytest.raises(ValueError, match="Async test error"):
            asyncio.run(async_function_with_error())


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