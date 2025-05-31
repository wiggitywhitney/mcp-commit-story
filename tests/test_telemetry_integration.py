"""
Integration tests for telemetry setup that work with real providers.

These tests complement unit tests and ensure the telemetry system works end-to-end.
They verify that the telemetry setup functions create functional OpenTelemetry components.

Usage:
    # Run just telemetry unit tests (fast)
    pytest tests/test_telemetry.py -v
    
    # Run just telemetry integration tests (comprehensive)
    pytest tests/test_telemetry_integration.py -v
    
    # Run both
    pytest tests/test_telemetry*.py -v
"""

import pytest
from opentelemetry import trace, metrics


class TestTelemetryIntegration:
    """
    Integration tests for telemetry setup that work with real providers.
    These complement unit tests and ensure the telemetry system works end-to-end.
    """
    
    def test_telemetry_creates_functional_spans(self, otel_integration_setup):
        """Test that telemetry setup creates spans that actually work."""
        tracer = otel_integration_setup['tracer']
        
        # Test span creation and context
        with tracer.start_as_current_span("functional_test") as span:
            span_context = span.get_span_context()
            
            # Verify span has valid, non-zero IDs
            assert span_context.trace_id != 0
            assert span_context.span_id != 0
            
            # Verify span can accept attributes
            span.set_attribute("test.attribute", "test.value")
            span.set_attribute("test.number", 42)
            span.set_attribute("test.boolean", True)
            
            # Verify we can get current span
            current_span = trace.get_current_span()
            assert current_span == span
            
            # Verify span context is consistent
            current_context = current_span.get_span_context()
            assert current_context.trace_id == span_context.trace_id
            assert current_context.span_id == span_context.span_id
    
    def test_telemetry_with_your_setup_function(self, otel_integration_setup):
        """
        Test that your actual telemetry functions work.
        This verifies integration without trying to modify global state.
        """
        from src.mcp_commit_story.telemetry import get_tracer, get_meter
        
        # Your telemetry system should return functional tracers/meters
        # Note: These use global providers, so we test their basic functionality
        tracer = get_tracer("integration_test")
        meter = get_meter("integration_test")
        
        assert tracer is not None
        assert meter is not None
        
        # Test that our independent tracer from the fixture works properly
        # (This is the real integration test - the fixture tracer should work)
        fixture_tracer = otel_integration_setup['tracer']
        with fixture_tracer.start_as_current_span("setup_test_span") as span:
            assert span.get_span_context().trace_id != 0
            assert span.get_span_context().span_id != 0
            
            # Test nested spans work properly
            with fixture_tracer.start_as_current_span("nested_span") as nested:
                nested_context = nested.get_span_context()
                span_context = span.get_span_context()
                
                # Should have same trace but different spans
                assert nested_context.trace_id == span_context.trace_id
                assert nested_context.span_id != span_context.span_id
        
        # Verify the production functions return the expected types
        # (Even if they use global providers that might be proxy objects)
        assert hasattr(tracer, 'start_span')
        assert hasattr(tracer, 'start_as_current_span') 
        assert hasattr(meter, 'create_counter')
    
    def test_meter_functionality(self, otel_integration_setup):
        """Test that meters can create and use instruments properly."""
        meter_provider = otel_integration_setup['meter_provider']
        meter = meter_provider.get_meter("test_meter")
        
        # Test counter creation and usage
        counter = meter.create_counter("test_counter", description="Test counter")
        counter.add(1, {"operation": "test"})
        counter.add(5, {"operation": "test", "status": "success"})
        
        # Test histogram creation and usage
        histogram = meter.create_histogram("test_histogram", description="Test histogram")
        histogram.record(100.5, {"endpoint": "/test"})
        histogram.record(250.0, {"endpoint": "/test"})
        
        # Test gauge creation (if available)
        try:
            gauge = meter.create_gauge("test_gauge", description="Test gauge")
            # Note: Gauge API might differ between versions
        except AttributeError:
            # Gauge might not be available in all OpenTelemetry versions
            pass
        
        # All operations should complete without error
        assert True  # If we get here, all metric operations succeeded
    
    def test_span_processors_work(self, otel_integration_setup):
        """Test that span processors are actually processing spans."""
        tracer = otel_integration_setup['tracer']
        tracer_provider = otel_integration_setup['tracer_provider']
        
        # Verify tracer provider has processors
        assert len(tracer_provider._active_span_processor._span_processors) > 0
        
        # Create a span that should be processed
        with tracer.start_as_current_span("processed_span") as span:
            span.set_attribute("test.processed", True)
            span.set_status(trace.Status(trace.StatusCode.OK, "Test completed"))
        
        # Span should have been processed (we can't easily verify export without 
        # a test exporter, but we can verify the span was created properly)
        assert True
    
    def test_trace_context_propagation(self, otel_integration_setup):
        """Test that trace context propagates correctly across operations."""
        tracer = otel_integration_setup['tracer']
        
        def child_operation():
            """Simulate a child operation that should inherit trace context."""
            current_span = trace.get_current_span()
            return current_span.get_span_context()
        
        def nested_operation():
            """Simulate a nested operation with its own span."""
            with tracer.start_as_current_span("nested_operation") as span:
                span.set_attribute("nested", True)
                return child_operation()
        
        # Start a parent span
        with tracer.start_as_current_span("parent_operation") as parent_span:
            parent_context = parent_span.get_span_context()
            
            # Call child operation - should inherit parent context
            child_context = child_operation()
            assert child_context.trace_id == parent_context.trace_id
            
            # Call nested operation - should create new span in same trace
            nested_context = nested_operation()
            assert nested_context.trace_id == parent_context.trace_id
            assert nested_context.span_id != parent_context.span_id
    
    def test_error_recording_and_status(self, otel_integration_setup):
        """Test that errors are properly recorded in spans."""
        tracer = otel_integration_setup['tracer']
        
        with tracer.start_as_current_span("error_test_span") as span:
            try:
                # Simulate an operation that fails
                raise ValueError("Test error for telemetry")
            except ValueError as e:
                # Record the exception in the span
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
                # Verify span context is still valid after error
                context = span.get_span_context()
                assert context.trace_id != 0
                assert context.span_id != 0
        
        # Exception should not prevent span completion
        assert True
    
    def test_multiple_tracers_same_provider(self, otel_integration_setup):
        """Test that multiple tracers from the same provider work correctly."""
        tracer_provider = otel_integration_setup['tracer_provider']
        
        # Create multiple tracers (note: version parameter not supported in this SDK version)
        tracer1 = tracer_provider.get_tracer("component1")
        tracer2 = tracer_provider.get_tracer("component2")
        tracer3 = tracer_provider.get_tracer("component3")
        
        # All should be functional
        with tracer1.start_as_current_span("span1") as span1:
            context1 = span1.get_span_context()
            
            with tracer2.start_as_current_span("span2") as span2:
                context2 = span2.get_span_context()
                
                with tracer3.start_as_current_span("span3") as span3:
                    context3 = span3.get_span_context()
                    
                    # All spans should be in the same trace
                    assert context1.trace_id == context2.trace_id == context3.trace_id
                    
                    # But different spans
                    assert context1.span_id != context2.span_id != context3.span_id
    
    def test_resource_attributes(self, otel_integration_setup):
        """Test that resource attributes are properly configured."""
        tracer_provider = otel_integration_setup['tracer_provider']
        
        # Get the resource from the provider
        resource = tracer_provider.resource
        
        # Verify required service attributes
        assert "service.name" in resource.attributes
        assert resource.attributes["service.name"] == "test-service"
        
        # May have additional default attributes from OpenTelemetry
        # Just verify the basic structure is correct
        assert len(resource.attributes) > 0
    
    def test_concurrent_span_operations(self, otel_integration_setup):
        """Test that concurrent span operations work correctly."""
        import threading
        import time
        
        tracer = otel_integration_setup['tracer']
        results = []
        
        def create_span_with_delay(span_name, delay):
            """Create a span with some processing time."""
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("thread.name", threading.current_thread().name)
                time.sleep(delay)
                context = span.get_span_context()
                results.append({
                    'span_name': span_name,
                    'trace_id': context.trace_id,
                    'span_id': context.span_id,
                    'thread': threading.current_thread().name
                })
        
        # Create multiple threads with spans
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=create_span_with_delay,
                args=(f"concurrent_span_{i}", 0.01),
                name=f"TestThread{i}"
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all spans were created
        assert len(results) == 3
        
        # All spans should have valid IDs
        for result in results:
            assert result['trace_id'] != 0
            assert result['span_id'] != 0
        
        # Each span should be unique
        span_ids = [result['span_id'] for result in results]
        assert len(set(span_ids)) == 3  # All unique 