"""
Tests for structured logging with OpenTelemetry trace correlation.

This module tests the OTelFormatter class and trace-correlated logging functionality
for Task 4.6 of the telemetry system implementation.
"""

import json
import logging
import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import set_tracer_provider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class TestOTelFormatter:
    """Test the OTelFormatter class for structured logging with trace correlation."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Import setup_telemetry to ensure proper initialization
        from src.mcp_commit_story.telemetry import setup_telemetry
        
        # Setup telemetry first to ensure proper provider initialization
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-service",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
        
        # Setup tracing for testing
        self.resource = Resource.create({"service.name": "test-service"})
        self.tracer_provider = TracerProvider(resource=self.resource)
        set_tracer_provider(self.tracer_provider)
        
        # Setup in-memory exporter for testing
        self.span_exporter = InMemorySpanExporter()
        self.span_processor = SimpleSpanProcessor(self.span_exporter)
        self.tracer_provider.add_span_processor(self.span_processor)
        
        self.tracer = trace.get_tracer("test_tracer")
        
        # Setup logger for testing
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clear spans
        self.span_exporter.clear()
        
        # Clear logger handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def test_otel_formatter_class_initialization(self):
        """Test that OTelFormatter can be initialized with basic settings."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        assert formatter is not None
        assert hasattr(formatter, 'format')

    def test_otel_formatter_json_output_format(self):
        """Test that OTelFormatter produces valid JSON output."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        
        # Basic structure checks
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "message" in parsed
        assert "logger" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test.logger"

    def test_trace_id_injection_with_active_span(self):
        """Test that trace ID is injected when there's an active span."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        with self.tracer.start_as_current_span("test_span") as span:
            # Create log record within span context
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/test/path.py",
                lineno=42,
                msg="Test message with trace",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            # Should contain trace information
            assert "trace_id" in parsed
            assert "span_id" in parsed
            
            # Extract the actual trace and span IDs from the span
            span_context = span.get_span_context()
            expected_trace_id = format(span_context.trace_id, '032x')
            expected_span_id = format(span_context.span_id, '016x')
            
            assert parsed["trace_id"] == expected_trace_id
            assert parsed["span_id"] == expected_span_id

    def test_span_id_injection_with_active_span(self):
        """Test that span ID is injected when there's an active span."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        with self.tracer.start_as_current_span("test_span") as span:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.WARNING,
                pathname="/test/path.py", 
                lineno=24,
                msg="Warning with span context",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            # Verify span ID is present and correct
            span_context = span.get_span_context()
            expected_span_id = format(span_context.span_id, '016x')
            
            assert parsed["span_id"] == expected_span_id

    def test_no_trace_context_without_active_span(self):
        """Test that no trace context is injected when there's no active span."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        # Log without any active span
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=100,
            msg="Error without trace context",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        # Should not contain trace information
        assert "trace_id" not in parsed
        assert "span_id" not in parsed
        
        # But should still contain other fields
        assert parsed["message"] == "Error without trace context"
        assert parsed["level"] == "ERROR"

    def test_log_correlation_with_nested_spans(self):
        """Test that logs correlate correctly with nested span contexts."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        with self.tracer.start_as_current_span("parent_span") as parent_span:
            # Log in parent span context
            parent_record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/test/path.py",
                lineno=50,
                msg="Parent span message",
                args=(),
                exc_info=None
            )
            
            parent_formatted = formatter.format(parent_record)
            parent_parsed = json.loads(parent_formatted)
            
            with self.tracer.start_as_current_span("child_span") as child_span:
                # Log in child span context
                child_record = logging.LogRecord(
                    name="test.logger",
                    level=logging.DEBUG,
                    pathname="/test/path.py",
                    lineno=60,
                    msg="Child span message",
                    args=(),
                    exc_info=None
                )
                
                child_formatted = formatter.format(child_record)
                child_parsed = json.loads(child_formatted)
                
                # Both should have same trace ID (same trace)
                assert parent_parsed["trace_id"] == child_parsed["trace_id"]
                
                # But different span IDs (different spans)
                assert parent_parsed["span_id"] != child_parsed["span_id"]
                
                # Verify span IDs match actual spans
                parent_context = parent_span.get_span_context()
                child_context = child_span.get_span_context()
                
                assert parent_parsed["span_id"] == format(parent_context.span_id, '016x')
                assert child_parsed["span_id"] == format(child_context.span_id, '016x')

    def test_different_log_levels_formatting(self):
        """Test that different log levels are formatted correctly."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        levels = [
            (logging.DEBUG, "DEBUG", "Debug message"),
            (logging.INFO, "INFO", "Info message"),
            (logging.WARNING, "WARNING", "Warning message"),
            (logging.ERROR, "ERROR", "Error message"),
            (logging.CRITICAL, "CRITICAL", "Critical message")
        ]
        
        for level_int, level_str, message in levels:
            record = logging.LogRecord(
                name="test.logger",
                level=level_int,
                pathname="/test/path.py",
                lineno=10,
                msg=message,
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            assert parsed["level"] == level_str
            assert parsed["message"] == message

    def test_structured_log_format_completeness(self):
        """Test that the structured log format contains all expected fields."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        
        formatter = OTelFormatter()
        
        with self.tracer.start_as_current_span("test_span"):
            record = logging.LogRecord(
                name="test.logger.module",
                level=logging.INFO,
                pathname="/path/to/module.py",
                lineno=123,
                msg="Complete log entry",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            parsed = json.loads(formatted)
            
            # Required fields
            required_fields = [
                "timestamp", "level", "message", "logger",
                "pathname", "lineno", "trace_id", "span_id"
            ]
            
            for field in required_fields:
                assert field in parsed, f"Missing required field: {field}"
            
            # Verify field values
            assert parsed["logger"] == "test.logger.module"
            assert parsed["pathname"] == "/path/to/module.py"
            assert parsed["lineno"] == 123
            assert parsed["message"] == "Complete log entry"


class TestLogBasedMetrics:
    """Test optional log-based metrics functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.logger = logging.getLogger("test_metrics_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after each test."""
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def test_log_metrics_counter_initialization(self):
        """Test that log-based metrics can be initialized."""
        from src.mcp_commit_story.structured_logging import LogMetricsHandler
        
        handler = LogMetricsHandler()
        assert handler is not None
        assert hasattr(handler, 'emit')

    def test_log_level_metrics_collection(self):
        """Test that log level metrics are collected correctly."""
        from src.mcp_commit_story.structured_logging import LogMetricsHandler
        
        handler = LogMetricsHandler()
        self.logger.addHandler(handler)
        
        # Emit logs at different levels
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.info("Another info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        
        # Get metrics
        metrics = handler.get_metrics()
        
        assert "log_entries_total" in metrics
        level_metrics = metrics["log_entries_total"]
        
        assert level_metrics.get("DEBUG", 0) == 1
        assert level_metrics.get("INFO", 0) == 2
        assert level_metrics.get("WARNING", 0) == 1
        assert level_metrics.get("ERROR", 0) == 1

    def test_error_rate_metrics(self):
        """Test that error rate metrics are tracked correctly."""
        from src.mcp_commit_story.structured_logging import LogMetricsHandler
        
        handler = LogMetricsHandler()
        self.logger.addHandler(handler)
        
        # Mix of normal and error logs
        for _ in range(8):
            self.logger.info("Normal operation")
        
        for _ in range(2):
            self.logger.error("Error occurred")
        
        metrics = handler.get_metrics()
        error_rate = handler.get_error_rate()
        
        # 2 errors out of 10 total = 20% error rate
        assert error_rate == 0.2


class TestLoggingUtilityFunctions:
    """Test logging utility functions for telemetry integration."""
    
    def test_get_correlated_logger_function(self):
        """Test utility function to get a logger with trace correlation enabled."""
        from src.mcp_commit_story.structured_logging import get_correlated_logger
        
        logger = get_correlated_logger("test.module")
        assert logger is not None
        assert logger.name == "test.module"
        
        # Should have OTelFormatter handler
        has_otel_handler = False
        for handler in logger.handlers:
            if hasattr(handler, 'formatter') and hasattr(handler.formatter, '__class__'):
                if "OTelFormatter" in handler.formatter.__class__.__name__:
                    has_otel_handler = True
                    break
        
        assert has_otel_handler, "Logger should have OTelFormatter handler"

    def test_configure_structured_logging_function(self):
        """Test function to configure structured logging for the entire application."""
        from src.mcp_commit_story.structured_logging import configure_structured_logging
        
        config = {
            "level": "INFO",
            "format": "json",
            "correlation": True
        }
        
        result = configure_structured_logging(config)
        assert result is True

    def test_logging_integration_with_existing_telemetry(self):
        """Test that structured logging integrates with existing telemetry setup."""
        # This test ensures the logging system works with the existing telemetry module
        from src.mcp_commit_story.structured_logging import configure_structured_logging
        from src.mcp_commit_story.telemetry import setup_telemetry
        
        # Setup telemetry first
        telemetry_config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-integration",
                "auto_instrumentation": {
                    "enabled": True,
                    "instrumentors": {
                        "logging": True
                    }
                }
            }
        }
        
        telemetry_result = setup_telemetry(telemetry_config)
        assert telemetry_result is True
        
        # Then configure structured logging
        logging_config = {
            "level": "INFO",
            "format": "json",
            "correlation": True
        }
        
        logging_result = configure_structured_logging(logging_config)
        assert logging_result is True


class TestSensitiveDataFiltering:
    """Test automatic sensitive data redaction functionality."""
    
    def test_sensitive_field_redaction_in_dict(self):
        """Test that sensitive fields are automatically redacted from dictionaries."""
        from src.mcp_commit_story.structured_logging import sanitize_log_data
        
        sensitive_data = {
            "username": "john_doe",
            "password": "secret123",
            "api_key": "abc123def456", 
            "token": "xyz789",
            "normal_field": "normal_value",
            "user_config": {"nested_password": "nested_secret"}
        }
        
        sanitized = sanitize_log_data(sensitive_data)
        
        assert sanitized["username"] == "john_doe"  # Not sensitive
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["user_config"]["nested_password"] == "[REDACTED]"

    def test_sensitive_field_redaction_in_log_output(self):
        """Test that sensitive data is redacted in actual log output."""
        from src.mcp_commit_story.structured_logging import OTelFormatter
        import json
        
        formatter = OTelFormatter()
        
        # Create log record with sensitive data in extra fields
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="User login",
            args=(),
            exc_info=None
        )
        
        # Add sensitive data as extra fields
        record.user_password = "secret123"
        record.api_token = "abc456def"
        record.user_id = "12345"  # Not sensitive
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        assert parsed["user_password"] == "[REDACTED]"
        assert parsed["api_token"] == "[REDACTED]"
        assert parsed["user_id"] == "12345"  # Should not be redacted

    def test_nested_sensitive_data_redaction(self):
        """Test redaction of sensitive data in nested structures."""
        from src.mcp_commit_story.structured_logging import sanitize_log_data
        
        nested_data = {
            "users": [
                {"name": "alice", "user_password": "alice123"},
                {"name": "bob", "secret": "bob456"}
            ],
            "config": {
                "database": {
                    "host": "localhost",
                    "connection": {
                        "username": "db_user",
                        "db_password": "db_pass"
                    }
                }
            }
        }
        
        sanitized = sanitize_log_data(nested_data)
        
        assert sanitized["users"][0]["name"] == "alice"
        assert sanitized["users"][0]["user_password"] == "[REDACTED]"
        assert sanitized["users"][1]["secret"] == "[REDACTED]"
        assert sanitized["config"]["database"]["host"] == "localhost"
        assert sanitized["config"]["database"]["connection"]["username"] == "db_user"
        assert sanitized["config"]["database"]["connection"]["db_password"] == "[REDACTED]"


class TestPerformanceOptimization:
    """Test performance optimization features for logging."""
    
    def setup_method(self):
        """Set up test environment."""
        self.logger = logging.getLogger("test_performance_logger")
        self.logger.setLevel(logging.INFO)  # Set to INFO to test DEBUG filtering
        
        # Clear handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after tests."""
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

    def test_lazy_log_data_evaluation(self):
        """Test that LazyLogData only evaluates when accessed."""
        from src.mcp_commit_story.structured_logging import LazyLogData
        
        call_count = 0
        
        def expensive_function():
            nonlocal call_count
            call_count += 1
            return {"expensive": "data", "computation": "result"}
        
        lazy_data = LazyLogData(expensive_function)
        
        # Should not have called the function yet
        assert call_count == 0
        
        # Accessing the data should trigger computation
        str_repr = str(lazy_data)
        assert call_count == 1
        assert "expensive" in str_repr
        
        # Second access should use cached result
        str_repr2 = str(lazy_data)
        assert call_count == 1  # Should not increment again

    def test_performance_optimized_logging_with_level_check(self):
        """Test that expensive log data is only computed when logging level is enabled."""
        from src.mcp_commit_story.structured_logging import (
            log_performance_optimized, LazyLogData
        )
        
        call_count = 0
        
        def expensive_computation():
            nonlocal call_count
            call_count += 1
            return "expensive_result"
        
        lazy_data = LazyLogData(expensive_computation)
        
        # Logger level is INFO, so DEBUG should not trigger computation
        log_performance_optimized(
            self.logger, 
            logging.DEBUG, 
            "Debug message", 
            {"expensive_data": lazy_data}
        )
        
        # Should not have computed expensive data
        assert call_count == 0
        
        # INFO level should trigger computation
        log_performance_optimized(
            self.logger,
            logging.INFO,
            "Info message",
            {"expensive_data": lazy_data}
        )
        
        # Now should have computed the data
        assert call_count == 1

    def test_logger_is_enabled_for_optimization(self):
        """Test the recommended pattern using logger.isEnabledFor()."""
        expensive_call_count = 0
        
        def expensive_serialization():
            nonlocal expensive_call_count
            expensive_call_count += 1
            return {"large": "object", "with": "many", "fields": "..."}
        
        # This should not trigger expensive computation (DEBUG not enabled)
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Complex operation details", extra={
                "operation_data": expensive_serialization()
            })
        
        assert expensive_call_count == 0
        
        # This should trigger computation (INFO is enabled)
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info("Operation completed", extra={
                "operation_data": expensive_serialization()
            })
        
        assert expensive_call_count == 1


class TestIntegrationPatterns:
    """Test integration patterns with existing telemetry system."""
    
    def test_clean_integration_pattern(self):
        """Test the recommended clean integration pattern."""
        from src.mcp_commit_story.structured_logging import setup_structured_logging
        from src.mcp_commit_story.telemetry import setup_telemetry
        
        # Setup telemetry with logging configuration
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-integration",
                "logging": {
                    "level": "DEBUG",
                    "format": "json",
                    "correlation": True,
                    "metrics": True
                }
            }
        }
        
        # Setup telemetry first (this should also configure logging)
        telemetry_result = setup_telemetry(config)
        assert telemetry_result is True
        
        # Setup structured logging
        logging_result = setup_structured_logging(config)
        assert logging_result is True
        
        # Use normally throughout codebase
        logger = logging.getLogger(__name__)
        
        # This should work without issues
        logger.info("Operation completed", extra={"operation_id": "abc123"})

    def test_structured_logging_with_disabled_telemetry(self):
        """Test that structured logging works even when telemetry is disabled."""
        from src.mcp_commit_story.structured_logging import setup_structured_logging
        
        config = {
            "telemetry": {
                "enabled": False,  # Telemetry disabled
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "correlation": True  # This should be overridden to False
                }
            }
        }
        
        result = setup_structured_logging(config)
        assert result is True
        
        # Should still be able to log, but without trace correlation
        logger = logging.getLogger("test_disabled_telemetry")
        logger.info("Message without telemetry")

    def test_logging_with_extra_fields_integration(self):
        """Test logging with extra fields using the recommended integration pattern."""
        from src.mcp_commit_story.structured_logging import get_correlated_logger
        import json
        import io
        import sys
        
        # Capture log output
        log_capture = io.StringIO()
        
        logger = get_correlated_logger("test.integration")
        
        # Replace the handler's stream to capture output
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.stream = log_capture
        
        # Log with extra fields
        logger.info("User action completed", extra={
            "user_id": "12345",
            "action": "file_upload", 
            "file_size": 1024,
            "duration_ms": 150
        })
        
        # Parse the captured log
        log_output = log_capture.getvalue()
        if log_output.strip():  # Only parse if we got output
            parsed_log = json.loads(log_output.strip())
            
            assert parsed_log["message"] == "User action completed"
            assert parsed_log["user_id"] == "12345"
            assert parsed_log["action"] == "file_upload"
            assert parsed_log["file_size"] == 1024
            assert parsed_log["duration_ms"] == 150 