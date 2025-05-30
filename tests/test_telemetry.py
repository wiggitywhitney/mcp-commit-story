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
    
    def test_format_span_attributes(self):
        """Test span attribute formatting"""
        # This is a placeholder test
        pass


class TestAutoInstrumentation:
    """Test OpenTelemetry auto-instrumentation configuration and integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # First, set up telemetry for testing
        self.telemetry_config = {
            'telemetry': {
                'enabled': True,
                'service_name': 'test-auto-instrumentation'
            }
        }
        setup_telemetry(self.telemetry_config)
        
        self.test_config = {
            'telemetry': {
                'enabled': True,
                'auto_instrumentation': {
                    'enabled': True,
                    'preset': 'custom',  # Use custom preset to respect individual settings
                    'instrumentors': {
                        'requests': True,
                        'aiohttp': True,
                        'asyncio': True,
                        'logging': True
                        # Removed sqlalchemy as per approval
                    }
                }
            }
        }
        
        # Additional config for testing presets
        self.minimal_preset_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'preset': 'minimal'
                }
            }
        }
        
        self.comprehensive_preset_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'preset': 'comprehensive'
                }
            }
        }
    
    def teardown_method(self):
        """Clean up after each test"""
        shutdown_telemetry()
    
    def test_enable_auto_instrumentation_with_all_instrumentors(self):
        """Test enabling auto-instrumentation with all approved instrumentors"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        # This should enable all configured instrumentors
        result = enable_auto_instrumentation(self.test_config)
        
        # Should return information about enabled instrumentors
        assert result is not None
        assert 'enabled_instrumentors' in result
        assert 'requests' in result['enabled_instrumentors']
        # Note: aiohttp requires aiohttp library to be installed, may not be available
        assert 'asyncio' in result['enabled_instrumentors']
        assert 'logging' in result['enabled_instrumentors']
        # Check if aiohttp failed gracefully
        if 'aiohttp' not in result['enabled_instrumentors']:
            assert 'aiohttp' in result['failed_instrumentors']
    
    def test_selective_instrumentor_enabling(self):
        """Test selective enabling of specific instrumentors"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        # Configure only requests instrumentation
        selective_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'preset': 'custom',
                    'instrumentors': {
                        'requests': True,
                        'aiohttp': False,
                        'asyncio': False,
                        'logging': False
                    }
                }
            }
        }
        
        result = enable_auto_instrumentation(selective_config)
        
        assert 'requests' in result['enabled_instrumentors']
        assert 'aiohttp' not in result['enabled_instrumentors']
        assert 'asyncio' not in result['enabled_instrumentors']
        assert 'logging' not in result['enabled_instrumentors']
    
    def test_disabled_auto_instrumentation(self):
        """Test that auto-instrumentation can be completely disabled"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        disabled_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': False
                }
            }
        }
        
        result = enable_auto_instrumentation(disabled_config)
        
        assert result['enabled_instrumentors'] == []
        assert result['status'] == 'disabled'
    
    def test_http_request_tracing_requests(self):
        """Test that HTTP requests via requests library are traced"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation, get_tracer
        
        enable_auto_instrumentation(self.test_config)
        
        # Mock a requests call and verify span creation
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test_requests") as span:
            # This would normally make an HTTP request
            # For testing, we'll verify the instrumentation is set up
            assert span is not None
            # Note: Real span validation would require a test exporter
            # For now, we verify the tracer can create spans
    
    def test_http_request_tracing_aiohttp(self):
        """Test that HTTP requests via aiohttp are traced"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation, get_tracer
        
        enable_auto_instrumentation(self.test_config)
        
        # Mock an aiohttp call and verify span creation
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test_aiohttp") as span:
            # This would normally make an async HTTP request
            assert span is not None
    
    def test_asyncio_operation_tracing(self):
        """Test that asyncio operations are traced"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation, get_tracer
        
        enable_auto_instrumentation(self.test_config)
        
        # Mock asyncio operation and verify span creation
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test_asyncio") as span:
            # This would normally be an async operation
            assert span is not None
    
    def test_sqlalchemy_instrumentation_when_enabled(self):
        """Test that SQLAlchemy instrumentation is not included by default"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        # Even if someone tries to enable SQLAlchemy, it should be gracefully skipped
        sqlalchemy_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'instrumentors': {
                        'sqlalchemy': True
                    }
                }
            }
        }
        
        result = enable_auto_instrumentation(sqlalchemy_config)
        
        # SQLAlchemy should either be skipped or handled gracefully
        assert 'failed_instrumentors' in result or 'sqlalchemy' not in result['enabled_instrumentors']
    
    def test_graceful_fallback_for_missing_instrumentors(self):
        """Test graceful handling when instrumentor packages are not available"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        # Test with a non-existent instrumentor
        fallback_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'instrumentors': {
                        'nonexistent_library': True,
                        'requests': True
                    }
                }
            }
        }
        
        result = enable_auto_instrumentation(fallback_config)
        
        # Should succeed with available instrumentors
        assert 'requests' in result['enabled_instrumentors']
        # Should gracefully skip unavailable ones
        assert 'nonexistent_library' not in result['enabled_instrumentors']
        assert 'failed_instrumentors' in result
        assert 'nonexistent_library' in result['failed_instrumentors']
    
    def test_instrumentor_configuration_validation(self):
        """Test validation of instrumentor configuration"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        # Invalid configuration should be handled gracefully
        invalid_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'instrumentors': "invalid_format"  # Should be dict
                }
            }
        }
        
        result = enable_auto_instrumentation(invalid_config)
        
        # Should handle invalid config gracefully (not error out)
        # The implementation treats string as custom preset, resulting in no instrumentors
        assert result['status'] == 'enabled'
        assert result['enabled_instrumentors'] == []
    
    def test_preset_minimal_configuration(self):
        """Test 'minimal' preset provides basic instrumentors"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        result = enable_auto_instrumentation(self.minimal_preset_config)
        
        # Minimal preset should include requests and logging
        assert 'requests' in result['enabled_instrumentors']
        assert 'logging' in result['enabled_instrumentors']
        # Should be a subset of all available instrumentors
        assert len(result['enabled_instrumentors']) <= 4
    
    def test_preset_comprehensive_configuration(self):
        """Test 'comprehensive' preset enables all available instrumentors"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        result = enable_auto_instrumentation(self.comprehensive_preset_config)
        
        # Comprehensive preset should include all approved instrumentors that can be enabled
        expected_available = ['requests', 'asyncio', 'logging']
        for instrumentor in expected_available:
            assert instrumentor in result['enabled_instrumentors']
        
        # aiohttp may fail if aiohttp library not installed, which is acceptable
        assert 'aiohttp' in result['enabled_instrumentors'] or 'aiohttp' in result['failed_instrumentors']
    
    def test_preset_custom_allows_individual_control(self):
        """Test 'custom' preset respects individual instrumentor settings"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        custom_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'preset': 'custom',
                    'instrumentors': {
                        'requests': True,
                        'aiohttp': False,
                        'asyncio': True,
                        'logging': False
                    }
                }
            }
        }
        
        result = enable_auto_instrumentation(custom_config)
        
        # Should respect individual settings
        assert 'requests' in result['enabled_instrumentors']
        assert 'aiohttp' not in result['enabled_instrumentors']
        assert 'asyncio' in result['enabled_instrumentors']
        assert 'logging' not in result['enabled_instrumentors']
    
    def test_logging_instrumentation_correlation(self):
        """Test that logging instrumentation provides trace correlation"""
        from mcp_commit_story.telemetry import enable_auto_instrumentation
        
        logging_config = {
            'telemetry': {
                'auto_instrumentation': {
                    'enabled': True,
                    'instrumentors': {
                        'logging': True
                    }
                }
            }
        }
        
        result = enable_auto_instrumentation(logging_config)
        
        assert 'logging' in result['enabled_instrumentors']
        # Logging should provide trace correlation capabilities
        assert result['logging_trace_correlation'] is True


class TestMCPMetricsCollection:
    """Test MCP-specific metrics collection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Set up telemetry for testing
        self.telemetry_config = {
            'telemetry': {
                'enabled': True,
                'service_name': 'test-mcp-metrics'
            }
        }
        setup_telemetry(self.telemetry_config)
        
    def test_mcp_metrics_class_initialization(self):
        """Test MCPMetrics class can be initialized"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        assert metrics is not None
        assert hasattr(metrics, 'record_tool_call')
        assert hasattr(metrics, 'record_operation_duration')
        
    def test_record_tool_call_success(self):
        """Test recording successful tool calls"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record successful tool calls
        metrics.record_tool_call("file_read", success=True)
        metrics.record_tool_call("file_write", success=True)
        metrics.record_tool_call("git_status", success=True)
        
        # Should not raise any exceptions
        # Actual metric values will be verified through exporters
        
    def test_record_tool_call_failure(self):
        """Test recording failed tool calls"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record failed tool calls
        metrics.record_tool_call("file_read", success=False)
        metrics.record_tool_call("network_request", success=False, error_type="timeout")
        
        # Should not raise any exceptions
        
    def test_record_operation_duration(self):
        """Test recording operation duration metrics"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record various operation durations
        metrics.record_operation_duration("journal_generation", 1.5)
        metrics.record_operation_duration("context_collection", 0.25)
        metrics.record_operation_duration("file_processing", 2.1)
        
        # Should not raise any exceptions
        
    def test_metric_labels_and_attributes(self):
        """Test that metric labels and values are correctly set"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record metrics with specific attributes
        metrics.record_tool_call("git_log", success=True, repository="test-repo")
        metrics.record_operation_duration("ai_processing", 3.2, model="gpt-4", operation_type="generation")
        
        # Labels should be properly applied (verified through metric inspection)
        # This is a behavioral test - implementation will validate the labels
        
    def test_metric_export_format(self):
        """Test that metrics are exported in the correct format"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record some metrics
        metrics.record_tool_call("test_tool", success=True)
        metrics.record_operation_duration("test_operation", 1.0)
        
        # Get metric data for verification
        metric_data = metrics.get_metric_data()
        
        assert metric_data is not None
        assert "tool_calls_total" in metric_data
        assert "operation_duration_seconds" in metric_data
        
    def test_counter_increments(self):
        """Test that counters increment correctly"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record multiple calls to the same tool
        metrics.record_tool_call("file_read", success=True)
        metrics.record_tool_call("file_read", success=True)
        metrics.record_tool_call("file_read", success=False)
        
        # Get counter values
        counter_data = metrics.get_counter_values()
        
        assert counter_data["tool_calls_total"]["file_read"]["success"] == 2
        assert counter_data["tool_calls_total"]["file_read"]["failure"] == 1
        
    def test_histogram_recordings(self):
        """Test that histogram metrics record duration properly"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record multiple durations for the same operation
        durations = [0.1, 0.5, 1.0, 2.5, 5.0]
        for duration in durations:
            metrics.record_operation_duration("test_operation", duration)
        
        # Get histogram data
        histogram_data = metrics.get_histogram_data()
        
        assert "operation_duration_seconds" in histogram_data
        assert histogram_data["operation_duration_seconds"]["test_operation"]["count"] == 5
        assert histogram_data["operation_duration_seconds"]["test_operation"]["sum"] == sum(durations)
        
    def test_gauge_updates(self):
        """Test gauge metrics for state tracking"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Update gauge values
        metrics.set_active_operations(3)
        metrics.set_queue_size(15)
        metrics.set_memory_usage_mb(128.5)
        
        # Get gauge values
        gauge_data = metrics.get_gauge_values()
        
        assert gauge_data["active_operations"] == 3
        assert gauge_data["queue_size"] == 15
        assert gauge_data["memory_usage_mb"] == 128.5
        
    def test_metric_naming_convention(self):
        """Test that metrics follow proper naming conventions"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Get all metric names
        metric_names = metrics.get_metric_names()
        
        # Verify naming convention (should use mcp. prefix and follow OpenTelemetry guidelines)
        expected_metrics = [
            "mcp.tool_calls_total",
            "mcp.operation_duration_seconds", 
            "mcp.active_operations",
            "mcp.queue_size",
            "mcp.memory_usage_bytes"
        ]
        
        for expected_metric in expected_metrics:
            assert expected_metric in metric_names
            
    def test_semantic_metric_attributes(self):
        """Test that semantic attributes are properly applied to metrics"""
        from mcp_commit_story.telemetry import MCPMetrics
        
        metrics = MCPMetrics()
        
        # Record metrics with semantic attributes
        metrics.record_tool_call(
            "file_operation", 
            success=True,
            tool_type="filesystem",
            operation_type="read",
            file_type="json"
        )
        
        # Verify attributes are recorded
        metric_attributes = metrics.get_metric_attributes("mcp.tool_calls_total")
        
        assert "tool_name" in metric_attributes
        assert "success" in metric_attributes  
        assert "tool_type" in metric_attributes
        assert "operation_type" in metric_attributes
        assert "file_type" in metric_attributes 