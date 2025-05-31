"""
OpenTelemetry telemetry system for MCP Commit Story.

This module provides comprehensive observability through OpenTelemetry,
including tracing, metrics, and structured logging with trace correlation.
"""

import uuid
import asyncio
import functools
import logging
import re
import os
from typing import Optional, Dict, Any, Callable, List, Union
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, SERVICE_INSTANCE_ID, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.trace import Status, StatusCode

# Import structured logging functionality
from .structured_logging import setup_structured_logging

# Optional exporters - gracefully handle if not available
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False

try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# Global state tracking
_telemetry_initialized = False
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None
_mcp_metrics: Optional["MCPMetrics"] = None

logger = logging.getLogger(__name__)


def setup_telemetry(config: Dict[str, Any]) -> bool:
    """
    Initialize OpenTelemetry based on configuration.
    
    Args:
        config: Configuration dictionary containing telemetry settings
        
    Returns:
        bool: True if telemetry was enabled and configured, False if disabled
    """
    global _telemetry_initialized, _tracer_provider, _meter_provider, _mcp_metrics
    
    # Check if telemetry is enabled
    telemetry_config = config.get("telemetry", {})
    enabled = telemetry_config.get("enabled", True)
    
    if not enabled:
        logger.info("Telemetry disabled via configuration")
        return False
    
    try:
        # Shutdown existing telemetry first to ensure clean state
        if _telemetry_initialized:
            logger.debug("Telemetry already initialized, reinitializing with fresh providers")
            shutdown_telemetry()
        
        # Setup service resource
        service_name = telemetry_config.get("service_name", "mcp-commit-story")
        service_version = telemetry_config.get("service_version", "1.0.0")
        deployment_env = telemetry_config.get("deployment_environment", "development")
        
        resource = Resource.create({
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": deployment_env,
        })
        
        # Create fresh TracerProvider
        _tracer_provider = TracerProvider(resource=resource)
        
        # Try to set the tracer provider, handling the case where it's already set
        try:
            trace.set_tracer_provider(_tracer_provider)
        except RuntimeError as e:
            if "not allowed" in str(e):
                # In test environments, we may need to work around the global state
                logger.warning("Could not override global TracerProvider, using existing one")
                # Still keep our reference for span processors, etc.
            else:
                raise
        
        # Create fresh MeterProvider
        _meter_provider = MeterProvider(resource=resource)
        
        # Try to set the meter provider, handling the case where it's already set  
        try:
            metrics.set_meter_provider(_meter_provider)
        except RuntimeError as e:
            if "not allowed" in str(e):
                logger.warning("Could not override global MeterProvider, using existing one")
            else:
                raise
        
        # Setup auto-instrumentation if configured
        if telemetry_config.get("auto_instrumentation", {}).get("enabled", True):
            enable_auto_instrumentation(config)
        
        # Setup structured logging with telemetry integration
        structured_logging_enabled = setup_structured_logging(config)
        if structured_logging_enabled:
            logger.info("Structured logging with trace correlation enabled")
        
        # Initialize MCP metrics instance
        _mcp_metrics = MCPMetrics()
        
        _telemetry_initialized = True
        logger.info(f"Telemetry system initialized for service: {service_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {e}")
        return False


def enable_auto_instrumentation(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enable OpenTelemetry auto-instrumentation for approved libraries.
    
    Args:
        config: Configuration dictionary with auto-instrumentation settings
        
    Returns:
        Dict containing enabled instrumentors and status information
    """
    # Check if auto-instrumentation is enabled
    auto_config = config.get("telemetry", {}).get("auto_instrumentation", {})
    enabled = auto_config.get("enabled", True)
    
    if not enabled:
        return {
            "status": "disabled",
            "enabled_instrumentors": [],
            "failed_instrumentors": [],
            "logging_trace_correlation": False
        }
    
    # Determine instrumentors to enable
    preset = auto_config.get("preset")
    instrumentors_config = auto_config.get("instrumentors", {})
    
    # Validate instrumentors_config is a dict
    if not isinstance(instrumentors_config, dict):
        logger.warning(f"Invalid instrumentors configuration format: {type(instrumentors_config)}. Using empty config.")
        instrumentors_config = {}
        # When config is invalid, don't apply any preset, use empty config
        final_config = {}
    else:
        # If no preset is specified but instrumentors are provided, treat as custom
        if preset is None and instrumentors_config:
            preset = "custom"
        elif preset is None:
            preset = "minimal"
        
        # Define preset configurations
        preset_configs = {
            "minimal": {
                "requests": True,
                "logging": True,
                "aiohttp": False,
                "asyncio": False
            },
            "comprehensive": {
                "requests": True,
                "aiohttp": True,
                "asyncio": True,
                "logging": True
            },
            "custom": instrumentors_config  # Use user-provided config
        }
        
        # Get the final instrumentor configuration
        if preset == "custom":
            final_config = instrumentors_config
        else:
            final_config = preset_configs.get(preset, preset_configs["minimal"])
    
    # Track results
    enabled_instrumentors = []
    failed_instrumentors = []
    logging_trace_correlation = False
    
    # Enable approved instrumentors
    instrumentor_map = {
        "requests": _enable_requests_instrumentation,
        "aiohttp": _enable_aiohttp_instrumentation, 
        "asyncio": _enable_asyncio_instrumentation,
        "logging": _enable_logging_instrumentation
    }
    
    for instrumentor_name, is_enabled in final_config.items():
        if not is_enabled:
            continue
            
        if instrumentor_name in instrumentor_map:
            try:
                success = instrumentor_map[instrumentor_name]()
                if success:
                    enabled_instrumentors.append(instrumentor_name)
                    if instrumentor_name == "logging":
                        logging_trace_correlation = True
                else:
                    failed_instrumentors.append(instrumentor_name)
            except Exception as e:
                logger.warning(f"Failed to enable {instrumentor_name} instrumentation: {e}")
                failed_instrumentors.append(instrumentor_name)
        else:
            # Handle unsupported instrumentors (like sqlalchemy) gracefully
            logger.warning(f"Instrumentor '{instrumentor_name}' is not supported")
            failed_instrumentors.append(instrumentor_name)
    
    return {
        "status": "enabled",
        "enabled_instrumentors": enabled_instrumentors,
        "failed_instrumentors": failed_instrumentors,
        "logging_trace_correlation": logging_trace_correlation,
        "preset": preset
    }


def _enable_requests_instrumentation() -> bool:
    """Enable requests library instrumentation."""
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()
        return True
    except ImportError:
        logger.warning("requests instrumentation package not available")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument requests: {e}")
        return False


def _enable_aiohttp_instrumentation() -> bool:
    """Enable aiohttp client instrumentation."""
    try:
        from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
        AioHttpClientInstrumentor().instrument()
        return True
    except ImportError:
        logger.warning("aiohttp instrumentation package not available")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument aiohttp: {e}")
        return False


def _enable_asyncio_instrumentation() -> bool:
    """Enable asyncio instrumentation."""
    try:
        from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
        AsyncioInstrumentor().instrument()
        return True
    except ImportError:
        logger.warning("asyncio instrumentation package not available")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument asyncio: {e}")
        return False


def _enable_logging_instrumentation() -> bool:
    """Enable logging instrumentation for trace correlation."""
    try:
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        LoggingInstrumentor().instrument()
        
        # Additional integration with structured logging
        logger.info("OpenTelemetry logging instrumentation enabled")
        logger.debug("Logs will now include trace correlation when spans are active")
        return True
    except ImportError:
        logger.warning("OpenTelemetry logging instrumentation package not available")
        return False
    except Exception as e:
        logger.error(f"Failed to instrument logging: {e}")
        return False


def get_tracer(name: str = "mcp_commit_story") -> trace.Tracer:
    """
    Get a tracer for the specified name.
    
    Args:
        name: Name for the tracer
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str = "mcp_commit_story") -> metrics.Meter:
    """
    Get a meter for the specified name.
    
    Args:
        name: Name for the meter
        
    Returns:
        Meter instance
    """
    return metrics.get_meter(name)


def trace_mcp_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to trace MCP operations with OpenTelemetry using enhanced sensitive data filtering.
    Supports both sync and async functions.
    
    Args:
        operation_name: Name of the operation for the span
        attributes: Additional attributes to add to the span (will be sanitized)
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(operation_name) as span:
                    try:
                        # Add sanitized default attributes
                        span.set_attribute("mcp.tool_name", sanitize_for_telemetry(func.__name__))
                        span.set_attribute("mcp.operation_type", sanitize_for_telemetry(operation_name))
                        
                        # Add sanitized custom attributes
                        if attributes:
                            for key, value in attributes.items():
                                span.set_attribute(key, sanitize_for_telemetry(value))
                        
                        # Execute the async function
                        result = await func(*args, **kwargs)
                        
                        # Mark span as successful
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        # Record error with sanitized message
                        span.set_status(Status(StatusCode.ERROR, sanitize_for_telemetry(str(e))))
                        span.set_attribute("error.type", sanitize_for_telemetry(type(e).__name__))
                        span.set_attribute("error.message", sanitize_for_telemetry(str(e)))
                        raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                tracer = trace.get_tracer(__name__)
                with tracer.start_as_current_span(operation_name) as span:
                    try:
                        # Add sanitized default attributes
                        span.set_attribute("mcp.tool_name", sanitize_for_telemetry(func.__name__))
                        span.set_attribute("mcp.operation_type", sanitize_for_telemetry(operation_name))
                        
                        # Add sanitized custom attributes
                        if attributes:
                            for key, value in attributes.items():
                                span.set_attribute(key, sanitize_for_telemetry(value))
                        
                        # Execute the function
                        result = func(*args, **kwargs)
                        
                        # Mark span as successful
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        # Record error with sanitized message
                        span.set_status(Status(StatusCode.ERROR, sanitize_for_telemetry(str(e))))
                        span.set_attribute("error.type", sanitize_for_telemetry(type(e).__name__))
                        span.set_attribute("error.message", sanitize_for_telemetry(str(e)))
                        raise
            return wrapper
    return decorator


def shutdown_telemetry():
    """Shutdown telemetry and clean up resources."""
    global _telemetry_initialized, _tracer_provider, _meter_provider, _mcp_metrics
    
    if not _telemetry_initialized:
        return
    
    try:
        # Shutdown TracerProvider
        if _tracer_provider:
            try:
                _tracer_provider.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down TracerProvider: {e}")
            finally:
                _tracer_provider = None
        
        # Shutdown MeterProvider
        if _meter_provider:
            try:
                _meter_provider.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down MeterProvider: {e}")
            finally:
                _meter_provider = None
        
        # Clear metrics instance
        _mcp_metrics = None
        
    except Exception as e:
        logger.error(f"Error during telemetry shutdown: {e}")
    finally:
        _telemetry_initialized = False
        logger.info("Telemetry system shutdown complete")


class MCPMetrics:
    """
    MCP-specific metrics collection for OpenTelemetry.
    
    Provides counters, histograms, and gauges for tracking MCP operations,
    tool calls, and system state with semantic attributes.
    """
    
    def __init__(self):
        """Initialize MCP metrics with OpenTelemetry meter."""
        self.meter = get_meter("mcp_metrics")
        
        # Initialize metric instruments
        self._setup_counters()
        self._setup_histograms()
        self._setup_gauges()
        
        # Internal state for testing/inspection
        self._counter_values = {}
        self._histogram_data = {}
        self._gauge_values = {}
    
    def _setup_counters(self):
        """Set up counter metrics for MCP operations."""
        self.tool_calls_counter = self.meter.create_counter(
            name="mcp.tool_calls_total",
            description="Total number of MCP tool calls",
            unit="1"
        )
        
        self.operations_counter = self.meter.create_counter(
            name="mcp.operations_total", 
            description="Total number of MCP operations",
            unit="1"
        )
        
        self.errors_counter = self.meter.create_counter(
            name="mcp.errors_total",
            description="Total number of MCP errors",
            unit="1"
        )
    
    def _setup_histograms(self):
        """Set up histogram metrics for duration tracking."""
        # Standard duration buckets optimized for MCP operations (sub-second to several seconds)
        duration_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
        
        self.operation_duration_histogram = self.meter.create_histogram(
            name="mcp.operation_duration_seconds",
            description="Duration of MCP operations in seconds",
            unit="s"
        )
        
        self.tool_call_duration_histogram = self.meter.create_histogram(
            name="mcp.tool_call_duration_seconds", 
            description="Duration of MCP tool calls in seconds",
            unit="s"
        )
    
    def _setup_gauges(self):
        """Set up gauge metrics for state tracking."""
        self.active_operations_gauge = self.meter.create_gauge(
            name="mcp.active_operations",
            description="Number of currently active MCP operations",
            unit="1"
        )
        
        self.queue_size_gauge = self.meter.create_gauge(
            name="mcp.queue_size",
            description="Number of operations in the MCP queue",
            unit="1"
        )
        
        self.memory_usage_gauge = self.meter.create_gauge(
            name="mcp.memory_usage_bytes",
            description="Memory usage in bytes",
            unit="By"
        )
    
    def record_tool_call(self, tool_name: str, success: bool, **attributes):
        """
        Record a tool call metric with semantic attributes.
        
        Args:
            tool_name: Name of the MCP tool being called
            success: Whether the tool call succeeded
            **attributes: Additional semantic attributes like client_type, error_type, etc.
        """
        # Build semantic attributes
        attrs = {
            "tool_name": tool_name,
            "success": str(success).lower(),
            **attributes
        }
        
        # Record counter
        self.tool_calls_counter.add(1, attrs)
        
        # Track internal state for testing
        self._update_counter_values("tool_calls_total", tool_name, "success" if success else "failure")
    
    def record_operation_duration(self, operation: str, duration: float, **attributes):
        """
        Record operation duration metric.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            **attributes: Additional semantic attributes like model, operation_type, client_type, etc.
        """
        # Build semantic attributes
        attrs = {
            "operation": operation,
            **attributes
        }
        
        # Record histogram
        self.operation_duration_histogram.record(duration, attrs)
        
        # Track internal state for testing
        self._update_histogram_data("operation_duration_seconds", operation, duration)
    
    def set_active_operations(self, count: int, **attributes):
        """Set the number of active operations."""
        self.active_operations_gauge.set(count, attributes)
        self._gauge_values["active_operations"] = count
    
    def set_queue_size(self, size: int, **attributes):
        """Set the queue size."""
        self.queue_size_gauge.set(size, attributes)
        self._gauge_values["queue_size"] = size
    
    def set_memory_usage_mb(self, mb: float, **attributes):
        """Set memory usage in megabytes."""
        bytes_value = mb * 1024 * 1024
        self.memory_usage_gauge.set(bytes_value, attributes)
        self._gauge_values["memory_usage_mb"] = mb
    
    def get_metric_data(self):
        """Get metric data for testing/inspection."""
        return {
            "tool_calls_total": self._counter_values.get("tool_calls_total", {}),
            "operation_duration_seconds": self._histogram_data.get("operation_duration_seconds", {}),
            "active_operations": self._gauge_values.get("active_operations"),
            "queue_size": self._gauge_values.get("queue_size"),
            "memory_usage_mb": self._gauge_values.get("memory_usage_mb")
        }
    
    def get_counter_values(self):
        """Get counter values for testing."""
        return {"tool_calls_total": self._counter_values.get("tool_calls_total", {})}
    
    def get_histogram_data(self):
        """Get histogram data for testing."""
        return self._histogram_data
    
    def get_gauge_values(self):
        """Get gauge values for testing."""
        return self._gauge_values
    
    def get_metric_names(self):
        """Get all metric names."""
        return [
            "mcp.tool_calls_total",
            "mcp.operation_duration_seconds",
            "mcp.active_operations", 
            "mcp.queue_size",
            "mcp.memory_usage_bytes"
        ]
    
    def get_metric_attributes(self, metric_name: str):
        """Get expected attributes for a metric."""
        # Base attributes for different metrics
        base_attributes = {
            "mcp.tool_calls_total": ["tool_name", "success", "tool_type", "operation_type", "client_type", "error_type", "file_type"],
            "mcp.operation_duration_seconds": ["operation", "model", "operation_type", "client_type"]
        }
        return base_attributes.get(metric_name, [])
    
    def _update_counter_values(self, metric_name: str, key: str, result: str):
        """Update internal counter values for testing."""
        if metric_name not in self._counter_values:
            self._counter_values[metric_name] = {}
        if key not in self._counter_values[metric_name]:
            self._counter_values[metric_name][key] = {"success": 0, "failure": 0}
        self._counter_values[metric_name][key][result] += 1
    
    def _update_histogram_data(self, metric_name: str, key: str, value: float):
        """Update internal histogram data for testing."""
        if metric_name not in self._histogram_data:
            self._histogram_data[metric_name] = {}
        if key not in self._histogram_data[metric_name]:
            self._histogram_data[metric_name][key] = {"count": 0, "sum": 0.0}
        self._histogram_data[metric_name][key]["count"] += 1
        self._histogram_data[metric_name][key]["sum"] += value


def get_mcp_metrics() -> Optional["MCPMetrics"]:
    """
    Get the global MCP metrics instance.
    
    Returns:
        MCPMetrics instance if telemetry is initialized, None otherwise
    """
    return _mcp_metrics 


def sanitize_for_telemetry(value: Any, debug_mode: bool = False) -> str:
    """
    Sanitize potentially sensitive values for telemetry spans with enhanced filtering patterns.
    
    Args:
        value: The value to sanitize
        debug_mode: If True, applies less aggressive sanitization for development/debugging
    
    Handles:
    - Git information (commit hashes, branch names)
    - URLs (query parameters, auth tokens)
    - Connection strings
    - File content metadata
    - Personal information
    - Authentication data
    """
    if value is None:
        return ""
    
    str_value = str(value)
    
    # In debug mode, apply minimal sanitization - only truly sensitive data
    if debug_mode:
        # Only sanitize the most critical sensitive data in debug mode
        # API keys and tokens (common patterns)
        str_value = re.sub(r'\b[A-Za-z0-9]{32,}\b', lambda m: m.group(0)[:8] + '***' if len(m.group(0)) > 16 else m.group(0), str_value)
        
        # JSON Web Tokens
        str_value = re.sub(r'\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b', 'jwt.***', str_value)
        
        # Bearer tokens in headers
        str_value = re.sub(r'(Bearer\s+)[A-Za-z0-9\-._~+/]+=*', r'\1***', str_value, flags=re.IGNORECASE)
        
        # Database passwords in connection strings
        str_value = re.sub(r'(password|pwd|secret)=([^;,\s]+)', r'\1=***', str_value, flags=re.IGNORECASE)
        
        # Limit length to prevent span overflow
        if len(str_value) > 2000:  # More generous limit in debug mode
            str_value = str_value[:1997] + "..."
        
        return str_value
    
    # Production mode: Full aggressive sanitization
    # Git information patterns
    # Full commit hashes (preserve first 8 chars for debugging)
    str_value = re.sub(r'\b([a-f0-9]{8})[a-f0-9]{32,}\b', r'\1...', str_value)
    
    # Git branch names containing personal/sensitive info
    str_value = re.sub(r'(branch|ref)s?[:/].*?/(feature|bugfix|hotfix)/[^/\s]+', r'\1/\2/***', str_value)
    
    # URL patterns
    # Query parameters (keep first param name for debugging)
    str_value = re.sub(r'(\?[^=&\s]+=[^&\s]*)', r'\1&***', str_value)
    
    # Auth tokens in URLs
    str_value = re.sub(r'(token|auth|key|secret)=[^&\s]+', r'\1=***', str_value, flags=re.IGNORECASE)
    
    # Bearer tokens in headers
    str_value = re.sub(r'(Bearer\s+)[A-Za-z0-9\-._~+/]+=*', r'\1***', str_value, flags=re.IGNORECASE)
    
    # Connection strings
    # Database connection strings
    str_value = re.sub(r'(password|pwd|secret)=([^;,\s]+)', r'\1=***', str_value, flags=re.IGNORECASE)
    str_value = re.sub(r'(mongodb|postgres|mysql)://[^@]*@', r'\1://***:***@', str_value)
    
    # API endpoints with credentials
    str_value = re.sub(r'(https?://)[^@/]+:[^@/]+@', r'\1***:***@', str_value)
    
    # File content metadata
    # File sizes (keep for debugging, but truncate large numbers)
    str_value = re.sub(r'\b(\d{4,})\d{4,}\b', r'\1***', str_value)
    
    # File paths (keep directory structure but obscure specific file names)
    str_value = re.sub(r'(/[^/\s]+){3,}(/[^/\s]+\.[a-zA-Z0-9]+)', r'/***\2', str_value)
    
    # Personal information patterns
    # Email addresses (keep domain for debugging)
    str_value = re.sub(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', r'***@\1', str_value)
    
    # IP addresses (keep first octet)
    str_value = re.sub(r'\b(\d{1,3})\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', r'\1.***.***.***', str_value)
    
    # Phone numbers (basic pattern)
    str_value = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '***-***-****', str_value)
    
    # Authentication data
    # API keys (common patterns)
    str_value = re.sub(r'\b[A-Za-z0-9]{20,}\b', lambda m: m.group(0)[:8] + '***' if len(m.group(0)) > 16 else m.group(0), str_value)
    
    # JSON Web Tokens
    str_value = re.sub(r'\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b', 'jwt.***', str_value)
    
    # Session IDs and UUIDs
    str_value = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', 'uuid-***', str_value, flags=re.IGNORECASE)
    
    # Environment variable patterns
    str_value = re.sub(r'(export\s+)?[A-Z_]+(KEY|SECRET|TOKEN|PASSWORD|AUTH)=[^\s]+', r'\1***=***', str_value)
    
    # Limit length to prevent span overflow
    if len(str_value) > 1000:
        str_value = str_value[:997] + "..."
    
    return str_value 