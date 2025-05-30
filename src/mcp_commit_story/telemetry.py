"""
OpenTelemetry telemetry system for MCP Commit Story.

This module provides comprehensive observability through OpenTelemetry,
including tracing, metrics, and structured logging with trace correlation.
"""

import uuid
import asyncio
import functools
import logging
from typing import Optional, Dict, Any, Callable, List, Union
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

logger = logging.getLogger(__name__)


def setup_telemetry(config: Dict[str, Any]) -> bool:
    """
    Initialize OpenTelemetry based on configuration.
    
    Args:
        config: Configuration dictionary with telemetry settings
        
    Returns:
        bool: True if telemetry was enabled and initialized, False if disabled
    """
    global _telemetry_initialized, _tracer_provider, _meter_provider
    
    # Check if telemetry is enabled (default: True)
    telemetry_config = config.get("telemetry", {})
    enabled = telemetry_config.get("enabled", True)
    
    if not enabled:
        logger.info("Telemetry is disabled via configuration")
        return False
    
    # Create resource with service information
    service_name = telemetry_config.get("service_name", "mcp-commit-story")
    service_version = telemetry_config.get("service_version", "unknown")
    deployment_environment = telemetry_config.get("deployment_environment", "development")
    
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        SERVICE_INSTANCE_ID: str(uuid.uuid4()),
        "deployment.environment": deployment_environment,
    })
    
    # Initialize TracerProvider
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)
    
    # Initialize MeterProvider  
    _meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(_meter_provider)
    
    # Enable auto-instrumentation if configured
    auto_instrumentation_result = enable_auto_instrumentation(config)
    if auto_instrumentation_result.get('enabled_instrumentors'):
        logger.info(f"Auto-instrumentation enabled for: {auto_instrumentation_result['enabled_instrumentors']}")
    
    _telemetry_initialized = True
    logger.info(f"Telemetry initialized for service: {service_name}")
    
    return True


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
        return True
    except ImportError:
        logger.warning("logging instrumentation package not available")
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


def trace_mcp_operation(
    operation_name: str, 
    *, 
    attributes: Optional[Dict[str, Union[str, int, float, bool]]] = None
) -> Callable:
    """
    Decorator for tracing MCP operations with semantic attributes.
    
    Args:
        operation_name: Name of the operation for the span
        attributes: Optional custom attributes to add to the span
        
    Returns:
        Decorated function with tracing capabilities
    """
    def decorator(func: Callable) -> Callable:
        # Preserve function metadata
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.start_as_current_span(operation_name) as span:
                # Set semantic attributes for MCP operations
                span.set_attribute("mcp.operation.name", operation_name)
                span.set_attribute("mcp.operation.type", "sync")
                
                # Add custom attributes if provided
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    # Record the exception in the span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    # Re-raise the exception (record AND propagate)
                    raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            with tracer.start_as_current_span(operation_name) as span:
                # Set semantic attributes for MCP operations
                span.set_attribute("mcp.operation.name", operation_name)
                span.set_attribute("mcp.operation.type", "async")
                
                # Add custom attributes if provided
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    # Record the exception in the span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    # Re-raise the exception (record AND propagate)
                    raise
        
        # Auto-detect if function is async and return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def shutdown_telemetry() -> None:
    """
    Shutdown telemetry system and clean up resources.
    """
    global _telemetry_initialized, _tracer_provider, _meter_provider
    
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
    
    if _meter_provider:
        _meter_provider.shutdown() 
        _meter_provider = None
    
    _telemetry_initialized = False
    logger.info("Telemetry system shutdown complete") 