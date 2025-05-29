"""
OpenTelemetry telemetry system for MCP Journal.

Provides tracing, metrics, and logging integration for observability
of MCP operations and journal management.
"""

import uuid
from typing import Optional, Dict, Any
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, SERVICE_INSTANCE_ID, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

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