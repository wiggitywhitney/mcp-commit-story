"""
OpenTelemetry telemetry system for MCP Journal.

Provides tracing, metrics, and logging integration for observability
of MCP operations and journal management.
"""

import uuid
import asyncio
import functools
from typing import Optional, Dict, Any, Callable
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, SERVICE_INSTANCE_ID, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.trace import Status, StatusCode

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


# Global state
_telemetry_initialized = False
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None


def setup_telemetry(config: Dict[str, Any]) -> bool:
    """
    Initialize OpenTelemetry based on configuration.
    
    Args:
        config: Configuration dictionary containing telemetry settings
        
    Returns:
        True if telemetry was enabled and initialized, False if disabled
    """
    global _telemetry_initialized, _tracer_provider, _meter_provider
    
    # Shutdown existing providers if any
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
    
    if _meter_provider:
        _meter_provider.shutdown()
        _meter_provider = None
    
    # Get telemetry config, default to enabled
    telemetry_config = config.get("telemetry", {"enabled": True})
    
    # Check if telemetry is disabled
    if not telemetry_config.get("enabled", True):
        _telemetry_initialized = False
        # Set NoOp providers when disabled
        trace.set_tracer_provider(trace.NoOpTracerProvider())
        metrics.set_meter_provider(metrics.NoOpMeterProvider())
        return False
    
    # Extract service information with proper defaults
    service_name = telemetry_config.get("service_name", "mcp-journal")
    service_version = telemetry_config.get("service_version", "1.0.0")
    deployment_environment = telemetry_config.get("deployment_environment", "development")
    
    # Create resource with service attributes
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        SERVICE_INSTANCE_ID: str(uuid.uuid4()),
        "deployment.environment": deployment_environment,
    })
    
    # Setup TracerProvider
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)
    
    # Setup MeterProvider  
    _meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(_meter_provider)
    
    # TODO: Add exporters based on configuration
    # For now, using console exporter for basic setup
    
    _telemetry_initialized = True
    return True


def get_tracer(name: str = "mcp_journal") -> trace.Tracer:
    """
    Get a tracer for the specified component name.
    
    Args:
        name: Component name for the tracer
        
    Returns:
        OpenTelemetry tracer instance
    """
    if not _telemetry_initialized:
        # Return NoOp tracer when telemetry is disabled
        return trace.NoOpTracer()
    
    return trace.get_tracer(name)


def get_meter(name: str = "mcp_journal") -> metrics.Meter:
    """
    Get a meter for the specified component name.
    
    Args:
        name: Component name for the meter
        
    Returns:
        OpenTelemetry meter instance
    """
    if not _telemetry_initialized:
        # Return NoOp meter when telemetry is disabled
        return metrics.NoOpMeter(name)
    
    return metrics.get_meter(name)


def shutdown_telemetry() -> None:
    """
    Shutdown telemetry providers and clean up resources.
    """
    global _telemetry_initialized, _tracer_provider, _meter_provider
    
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
    
    if _meter_provider:
        _meter_provider.shutdown()
        _meter_provider = None
    
    # Only reset to NoOp if we're actually shutting down
    trace.set_tracer_provider(trace.NoOpTracerProvider())
    metrics.set_meter_provider(metrics.NoOpMeterProvider())
    
    _telemetry_initialized = False 


def trace_mcp_operation(
    operation_name: str,
    *,
    attributes: Optional[Dict[str, Any]] = None,
    operation_type: str = "mcp_operation",
    tracer_name: str = "mcp_journal"
) -> Callable:
    """
    Decorator for tracing MCP operations with OpenTelemetry.
    
    Args:
        operation_name: Name of the MCP operation for the span
        attributes: Optional custom attributes to add to the span
        operation_type: Type of MCP operation (default: "mcp_operation")
        tracer_name: Name of the tracer to use (default: "mcp_journal")
        
    Returns:
        Decorated function with tracing instrumentation
        
    Example:
        @trace_mcp_operation("journal_entry_creation")
        def create_journal_entry():
            pass
            
        @trace_mcp_operation("tool_call", attributes={"tool.name": "journal/create"})
        async def handle_tool_call():
            pass
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_tracer(tracer_name)
                
                with tracer.start_as_current_span(operation_name) as span:
                    # Set standard MCP operation attributes
                    span.set_attribute("mcp.operation.name", operation_name)
                    span.set_attribute("mcp.operation.type", operation_type)
                    span.set_attribute("mcp.function.name", func.__name__)
                    span.set_attribute("mcp.function.module", func.__module__)
                    span.set_attribute("mcp.function.async", True)
                    
                    # Add custom attributes if provided
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        span.set_attribute("mcp.result.status", "success")
                        return result
                    except Exception as e:
                        # Record exception details in span
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        
                        # Add error attributes
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        span.set_attribute("mcp.result.status", "error")
                        
                        # Always propagate - never fail silently
                        raise
                        
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_tracer(tracer_name)
                
                with tracer.start_as_current_span(operation_name) as span:
                    # Set standard MCP operation attributes
                    span.set_attribute("mcp.operation.name", operation_name)
                    span.set_attribute("mcp.operation.type", operation_type)
                    span.set_attribute("mcp.function.name", func.__name__)
                    span.set_attribute("mcp.function.module", func.__module__)
                    span.set_attribute("mcp.function.async", False)
                    
                    # Add custom attributes if provided
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        span.set_attribute("mcp.result.status", "success")
                        return result
                    except Exception as e:
                        # Record exception details in span
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        
                        # Add error attributes
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        span.set_attribute("mcp.result.status", "error")
                        
                        # Always propagate - never fail silently
                        raise
                        
            return sync_wrapper
    return decorator 