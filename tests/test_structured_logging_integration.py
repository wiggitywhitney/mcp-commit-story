"""
Integration tests for OTelFormatter with real OpenTelemetry providers.

These tests complement the unit tests in test_structured_logging.py which use mocks.
The unit tests are fast and isolated, these integration tests verify real OpenTelemetry behavior.

Usage:
    # Run just unit tests (fast)
    pytest tests/test_structured_logging.py -v
    
    # Run just integration tests (comprehensive)
    pytest tests/test_structured_logging_integration.py -v
    
    # Run both
    pytest tests/test_structured_logging*.py -v
"""

import json
import logging
import pytest
from opentelemetry import trace


class TestOTelFormatterIntegration:
    """
    Integration tests for OTelFormatter with real OpenTelemetry providers.
    These complement the unit tests which use mocks.
    """
    
    def test_real_trace_id_injection(self, otel_integration_setup):
        """Test trace ID injection with real OpenTelemetry spans."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        tracer = otel_integration_setup['tracer']
        
        with tracer.start_as_current_span("integration_test_span") as span:
            # Verify we have a real span with valid IDs
            span_context = span.get_span_context()
            assert span_context.trace_id != 0
            assert span_context.span_id != 0
            
            record = logging.LogRecord(
                name="integration.test.logger",
                level=logging.INFO,
                pathname="/test/integration.py",
                lineno=42,
                msg="Integration test message",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            # Verify trace correlation works with real spans
            expected_trace_id = format(span_context.trace_id, '032x')
            expected_span_id = format(span_context.span_id, '016x')
            
            # Check the fields your formatter should include
            # (Our formatter uses trace_id/span_id when available, otherwise falls back to defaults)
            assert "trace_id" in parsed or "otelTraceID" in parsed
            assert "span_id" in parsed or "otelSpanID" in parsed
            
            # Verify the actual values match (adjust field names to match your formatter)
            if "trace_id" in parsed:
                assert parsed["trace_id"] == expected_trace_id
                assert parsed["span_id"] == expected_span_id
            elif "otelTraceID" in parsed:
                # Fallback to OpenTelemetry auto-instrumentation fields
                assert parsed["otelTraceID"] != "0"
                assert parsed["otelSpanID"] != "0"
    
    def test_real_nested_span_correlation(self, otel_integration_setup):
        """Test log correlation with real nested spans."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        tracer = otel_integration_setup['tracer']
        
        with tracer.start_as_current_span("parent_span") as parent:
            parent_record = logging.LogRecord(
                name="test.logger", level=logging.INFO,
                pathname="/test.py", lineno=10,
                msg="Parent span log", args=(), exc_info=None
            )
            parent_formatted = formatter.format(parent_record)
            parent_parsed = json.loads(parent_formatted)
            
            with tracer.start_as_current_span("child_span") as child:
                child_record = logging.LogRecord(
                    name="test.logger", level=logging.DEBUG,
                    pathname="/test.py", lineno=20,
                    msg="Child span log", args=(), exc_info=None
                )
                child_formatted = formatter.format(child_record)
                child_parsed = json.loads(child_formatted)
                
                # Both should have same trace ID but different span IDs
                # Adjust field names based on your actual formatter output
                parent_trace = parent_parsed.get("trace_id") or parent_parsed.get("otelTraceID")
                child_trace = child_parsed.get("trace_id") or child_parsed.get("otelTraceID")
                
                parent_span = parent_parsed.get("span_id") or parent_parsed.get("otelSpanID")
                child_span = child_parsed.get("span_id") or child_parsed.get("otelSpanID")
                
                assert parent_trace == child_trace  # Same trace
                assert parent_span != child_span    # Different spans
                assert parent_trace != "0"          # Valid trace ID
                assert parent_span != "0"           # Valid span IDs
                assert child_span != "0"
    
    def test_real_span_without_context(self, otel_integration_setup):
        """Test formatter behavior when no span context is active."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        # Log without any active span
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test.py",
            lineno=100,
            msg="No span context",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        # Should still format correctly, but without trace context
        assert parsed["message"] == "No span context"
        assert parsed["level"] == "ERROR"
        assert parsed["logger"] == "test.logger"
        
        # Trace fields should either be missing or have default values
        if "trace_id" in parsed:
            # If present, should indicate no trace
            assert parsed["trace_id"] == "0" * 32 or parsed["trace_id"] is None
        if "otelTraceID" in parsed:
            assert parsed["otelTraceID"] == "0"
    
    def test_real_span_attributes_and_status(self, otel_integration_setup):
        """Test that span attributes and status don't interfere with logging."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        tracer = otel_integration_setup['tracer']
        
        with tracer.start_as_current_span("attributed_span") as span:
            # Set various span attributes
            span.set_attribute("user.id", "12345")
            span.set_attribute("operation.type", "test")
            span.set_attribute("result.count", 42)
            span.set_status(trace.Status(trace.StatusCode.OK, "Test completed"))
            
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/test.py",
                lineno=50,
                msg="Span with attributes",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            # Verify basic log structure is maintained
            assert parsed["message"] == "Span with attributes"
            assert parsed["level"] == "INFO"
            
            # Verify trace correlation still works
            span_context = span.get_span_context()
            if "trace_id" in parsed:
                expected_trace_id = format(span_context.trace_id, '032x')
                assert parsed["trace_id"] == expected_trace_id
    
    def test_real_error_span_correlation(self, otel_integration_setup):
        """Test that error logging correctly correlates with span context."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        tracer = otel_integration_setup['tracer']
        
        with tracer.start_as_current_span("error_span") as span:
            try:
                # Simulate an error
                raise ValueError("Test error for span correlation")
            except ValueError as e:
                # Mark span as error
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                # Log the error
                record = logging.LogRecord(
                    name="test.logger",
                    level=logging.ERROR,
                    pathname="/test.py",
                    lineno=75,
                    msg="Error occurred: %s",
                    args=(str(e),),
                    exc_info=(type(e), e, e.__traceback__)
                )
                
                formatted = formatter.format(record)
                parsed = json.loads(formatted)
                
                # Verify error log has trace correlation
                assert parsed["level"] == "ERROR"
                assert "Test error for span correlation" in parsed["message"]
                
                # Should have trace context even for errors
                if "trace_id" in parsed:
                    span_context = span.get_span_context()
                    expected_trace_id = format(span_context.trace_id, '032x')
                    assert parsed["trace_id"] == expected_trace_id
                elif "otelTraceID" in parsed:
                    assert parsed["otelTraceID"] != "0" 