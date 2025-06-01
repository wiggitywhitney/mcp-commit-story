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
import time
import psutil
import contextlib
from typing import Optional, Dict, Any, Callable, List, Union, Generator, Set
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, SERVICE_INSTANCE_ID, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.trace import Status, StatusCode
from dataclasses import dataclass
from collections import defaultdict

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

# Performance thresholds (approved specifications)
PERFORMANCE_THRESHOLDS = {
    "collect_git_context_slow_seconds": 2.0,
    "journal_generation_slow_seconds": 10.0, 
    "file_processing_slow_per_10_files_seconds": 1.0,
    "large_repo_file_count": 50,
    "detailed_analysis_file_count_limit": 100,
    "large_file_size_bytes": 1024 * 1024,  # 1MB
    "git_operation_timeout_seconds": 5.0,
    "memory_threshold_mb": 50.0,
    "file_sampling_percentage": 0.2  # 20% sampling for large repos
}

# File type priorities for smart sampling
SOURCE_CODE_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php'}
SIGNIFICANT_FILE_SIZE_BYTES = 100 * 1024  # 100KB

@dataclass
class MemorySnapshot:
    """Memory usage snapshot for tracking."""
    rss_mb: float
    vms_mb: float
    timestamp: float

class CircuitBreaker:
    """Circuit breaker for telemetry to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 300.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open
    
    def should_skip(self) -> bool:
        """Check if operations should be skipped due to circuit breaker state."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                return False
            return True
        return False
    
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def record_success(self):
        """Record a success and potentially close the circuit."""
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                logger.debug("Circuit breaker open - skipping telemetry operation")
                return None
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            logger.error(f"Telemetry operation failed: {e}")
            return None

# Global circuit breaker for telemetry operations
_telemetry_circuit_breaker = CircuitBreaker()

@contextlib.contextmanager
def memory_tracking_context(operation_name: str, baseline_threshold_mb: float = PERFORMANCE_THRESHOLDS["memory_threshold_mb"]) -> Generator[MemorySnapshot, None, None]:
    """
    Context manager for tracking memory usage during operations.
    
    Args:
        operation_name: Name of the operation for metrics
        baseline_threshold_mb: Only record metrics if memory increase exceeds this threshold
        
    Yields:
        MemorySnapshot: Initial memory snapshot
    """
    metrics = get_mcp_metrics()
    if not metrics:
        yield MemorySnapshot(rss_mb=0.0, vms_mb=0.0, timestamp=time.time())
        return
        
    process = psutil.Process()
    initial_memory = process.memory_info()
    initial_snapshot = MemorySnapshot(
        rss_mb=initial_memory.rss / (1024 * 1024),  # MB
        vms_mb=initial_memory.vms / (1024 * 1024),  # MB
        timestamp=time.time()
    )
    
    exception_occurred = False
    try:
        yield initial_snapshot
        
    except Exception as e:
        exception_occurred = True
        # Log but don't interfere with exception propagation
        logger.error(f"Memory tracking failed for {operation_name}: {e}")
        raise  # Re-raise the exception
        
    finally:
        # Always try to record memory metrics if possible
        if not exception_occurred:
            try:
                # Record final memory after operation
                final_memory = process.memory_info()
                final_rss_mb = final_memory.rss / (1024 * 1024)
                memory_increase = final_rss_mb - initial_snapshot.rss_mb
                
                # Record memory metrics
                def record_memory_metrics():
                    # Always record current memory usage
                    metrics.record_gauge(
                        "memory_usage_mb",
                        final_rss_mb,
                        attributes={"operation": operation_name, "type": "rss"}
                    )
                    
                    # Record memory increase if significant
                    if abs(memory_increase) > baseline_threshold_mb:
                        metrics.record_gauge(
                            "mcp.journal.memory.increase_mb",
                            memory_increase,
                            attributes={"operation": operation_name}
                        )
                        
                        if memory_increase > baseline_threshold_mb:
                            logger.info(f"Memory increase detected in {operation_name}: +{memory_increase:.1f}MB")
                
                record_memory_metrics()
                
            except Exception as mem_error:
                # Don't let memory tracking errors break the main operation
                logger.error(f"Failed to record memory metrics for {operation_name}: {mem_error}")

def smart_file_sampling(files: List[str], max_files: int = PERFORMANCE_THRESHOLDS["large_repo_file_count"]) -> List[str]:
    """
    Apply smart sampling strategy for large repositories.
    
    Args:
        files: List of file paths
        max_files: Threshold for applying sampling
        
    Returns:
        List of sampled files following approved strategy
    """
    if len(files) <= max_files:
        return files
    
    # Categorize files
    source_files = []
    large_files = []
    other_files = []
    
    for file_path in files:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Always include source code files
        if file_ext in SOURCE_CODE_EXTENSIONS:
            source_files.append(file_path)
        # Always include large files (likely significant)
        elif any(keyword in file_path.lower() for keyword in ['large', 'big']) or len(file_path) > 100:
            # Heuristic for potentially large files - would need actual size in real implementation
            large_files.append(file_path)
        else:
            other_files.append(file_path)
    
    # Sample other files at specified percentage
    sample_size = int(len(other_files) * PERFORMANCE_THRESHOLDS["file_sampling_percentage"])
    sampled_others = other_files[:sample_size]  # Simple sampling - could use random
    
    result = source_files + large_files + sampled_others
    logger.debug(f"Smart sampling: {len(files)} -> {len(result)} files (source: {len(source_files)}, large: {len(large_files)}, sampled: {len(sampled_others)})")
    
    return result

def trace_git_operation(
    operation_type: str, 
    timeout_seconds: float = PERFORMANCE_THRESHOLDS["git_operation_timeout_seconds"],
    performance_thresholds: Optional[Dict[str, float]] = None,
    error_categories: Optional[List[str]] = None
):
    """
    Enhanced decorator for tracing Git operations with comprehensive telemetry.
    
    Args:
        operation_type: Type of Git operation (diff, log, status, context_collection, etc.)
        timeout_seconds: Timeout for the operation
        performance_thresholds: Dict of performance thresholds like {"duration": 2.0}
        error_categories: List of error categories to track like ["api", "network", "parsing", "git", "filesystem"]
    """
    # Set defaults
    if performance_thresholds is None:
        performance_thresholds = {"duration": 2.0}
    if error_categories is None:
        error_categories = ["git", "filesystem", "network", "api", "memory"]
    
    def decorator(func):
        # Mark function as instrumented for tests
        func._telemetry_instrumented = True
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if _telemetry_circuit_breaker.should_skip():
                # Circuit breaker: skip telemetry, just call function
                return func(*args, **kwargs)
                
            metrics = get_mcp_metrics()
            start_time = time.time()
            operation_name = f"{operation_type}_operation"
            
            try:
                with memory_tracking_context(f"{operation_type}_collection") as memory_snapshot:
                    # Execute the function with timeout
                    try:
                        result = func(*args, **kwargs)
                        success = True
                        error_type = None
                        
                    except Exception as e:
                        success = False
                        error_type = _categorize_error(e, error_categories)
                        
                        # Record error metrics
                        if metrics:
                            def record_error():
                                metrics.record_counter(
                                    f"mcp.journal.{operation_type}.errors",
                                    1,
                                    attributes={"error_type": error_type, "operation": operation_type}
                                )
                            record_error()
                        
                        # Re-raise the original exception (this was missing!)
                        raise
                    
                    # Record success metrics
                    duration = time.time() - start_time
                    if metrics:
                        def record_metrics():
                            # Record basic operation metrics
                            metrics.record_tool_call(
                                operation_name,
                                success,
                                operation=operation_type,
                                duration=duration
                            )
                            
                            # Record duration histogram
                            metrics.record_histogram(
                                f"mcp.journal.{operation_type}.duration",
                                duration,
                                attributes={"operation": operation_type, "success": str(success)}
                            )
                            
                            # Record operation counters
                            counter_name = f"{operation_type}_collection" if "collection" in operation_type else f"{operation_type}_operation"
                            metrics.record_counter(
                                f"mcp.journal.{counter_name}",
                                1,
                                attributes={"success": str(success), "operation": operation_type}
                            )
                            
                            # Context-specific metrics
                            if operation_type == "git_context":
                                metrics.record_counter(
                                    "context_collection_success",
                                    1,
                                    attributes={"operation": "git_context"}
                                )
                                metrics.record_histogram(
                                    "context_scan_duration", 
                                    duration,
                                    attributes={"operation": "git_context"}
                                )
                                # Record files processed metric
                                if hasattr(result, 'changed_files') and isinstance(result.get('changed_files'), list):
                                    metrics.record_counter(
                                        "files_processed",
                                        len(result['changed_files']),
                                        attributes={"operation": "git_context"}
                                    )
                            
                            elif operation_type == "chat_history":
                                metrics.record_counter(
                                    "chat_history_collection",
                                    1,
                                    attributes={"operation": "chat_history"}
                                )
                                
                            elif operation_type == "terminal_commands":
                                metrics.record_counter(
                                    "terminal_commands_collection",
                                    1,
                                    attributes={"operation": "terminal_commands"}
                                )
                            
                            # Performance threshold warnings
                            duration_threshold = performance_thresholds.get("duration", 2.0)
                            if duration > duration_threshold:
                                logger.warning(f"{operation_type} operation exceeded threshold: {duration:.2f}s > {duration_threshold}s")
                        
                        record_metrics()
                        _telemetry_circuit_breaker.record_success()
                    
                    return result
                    
            except TimeoutError as e:
                # Handle timeout specifically
                duration = time.time() - start_time
                logger.warning(f"Git {operation_type} operation timed out after {duration:.2f}s")
                if metrics:
                    def record_timeout():
                        metrics.record_counter(
                            f"mcp.journal.{operation_type}.timeouts",
                            1,
                            attributes={"operation": operation_type}
                        )
                    record_timeout()
                raise
                
            except Exception as e:
                duration = time.time() - start_time
                error_type = _categorize_error(e, error_categories)
                
                # Record error metrics
                if metrics:
                    def record_error():
                        metrics.record_counter(
                            f"mcp.journal.{operation_type}.errors",
                            1,
                            attributes={"error_type": error_type, "operation": operation_type}
                        )
                    
                    record_error()
                
                _telemetry_circuit_breaker.record_failure()
                logger.error(f"Git {operation_type} operation failed after {duration:.2f}s: {e}")
                
                # Re-raise the original exception
                raise
        
        return wrapper
    return decorator


def _categorize_error(exception: Exception, error_categories: List[str]) -> str:
    """
    Categorize an exception based on configured error categories.
    
    Args:
        exception: The exception to categorize
        error_categories: List of valid error categories
        
    Returns:
        Error category string
    """
    error_str = str(type(exception).__name__).lower()
    exception_msg = str(exception).lower()
    
    # Map exceptions to categories based on configured categories
    category_mapping = {
        "git": ["invalidgitrepository", "badname", "gitcommand", "gitdb"],
        "filesystem": ["oserror", "ioerror", "filenotfound", "permissionerror"],
        "memory": ["memoryerror"],
        "timeout": ["timeouterror"],
        "network": ["connectionerror", "networkerror", "httperror", "urlerror"],
        "api": ["apierror", "httperror", "authenticationerror"],
        "parsing": ["json", "yaml", "xml", "parse", "syntax"]
    }
    
    # Check each configured category
    for category in error_categories:
        if category in category_mapping:
            category_patterns = category_mapping[category]
            if any(pattern in error_str or pattern in exception_msg for pattern in category_patterns):
                return category
    
    return "unknown"


def _extract_function_context(func: Callable, args: tuple, kwargs: dict) -> dict:
    """
    Extract relevant context from function arguments for telemetry.
    
    Args:
        func: The function being called
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Dict of sanitized context attributes
    """
    context = {}
    
    # Extract common patterns
    if 'max_messages_back' in kwargs:
        context['messages_limit'] = kwargs['max_messages_back']
    elif len(args) >= 2 and isinstance(args[1], int):
        context['messages_limit'] = args[1]
    
    if 'commit_hash' in kwargs:
        commit_hash = kwargs['commit_hash']
        if commit_hash:
            context['commit_hash_prefix'] = str(commit_hash)[:8]
    elif args and isinstance(args[0], str):
        commit_hash = args[0]
        if commit_hash:
            context['commit_hash_prefix'] = str(commit_hash)[:8]
    
    # Sanitize all values
    return {k: sanitize_for_telemetry(v) for k, v in context.items()}

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
    
    def record_counter(self, name: str, value: int = 1, attributes: Optional[Dict[str, str]] = None):
        """Record a counter metric."""
        if attributes is None:
            attributes = {}
        
        # Create counter if needed
        if not hasattr(self, f"_{name}_counter"):
            counter = self.meter.create_counter(
                name=name,
                description=f"Counter for {name}",
                unit="1"
            )
            setattr(self, f"_{name}_counter", counter)
        else:
            counter = getattr(self, f"_{name}_counter")
        
        counter.add(value, attributes)
        
        # Track for testing
        if name not in self._counter_values:
            self._counter_values[name] = {}
        key = str(attributes) if attributes else "default"
        self._counter_values[name][key] = self._counter_values[name].get(key, 0) + value
    
    def record_histogram(self, name: str, value: float, attributes: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        if attributes is None:
            attributes = {}
        
        # Create histogram if needed
        if not hasattr(self, f"_{name}_histogram"):
            histogram = self.meter.create_histogram(
                name=name,
                description=f"Histogram for {name}",
                unit="1"
            )
            setattr(self, f"_{name}_histogram", histogram)
        else:
            histogram = getattr(self, f"_{name}_histogram")
        
        histogram.record(value, attributes)
        
        # Track for testing
        if name not in self._histogram_data:
            self._histogram_data[name] = {}
        key = str(attributes) if attributes else "default"
        if key not in self._histogram_data[name]:
            self._histogram_data[name][key] = {"count": 0, "sum": 0.0}
        self._histogram_data[name][key]["count"] += 1
        self._histogram_data[name][key]["sum"] += value
    
    def record_gauge(self, name: str, value: float, attributes: Optional[Dict[str, str]] = None):
        """Record a gauge metric."""
        if attributes is None:
            attributes = {}
        
        # Create gauge if needed
        if not hasattr(self, f"_{name}_gauge"):
            gauge = self.meter.create_gauge(
                name=name,
                description=f"Gauge for {name}",
                unit="1"
            )
            setattr(self, f"_{name}_gauge", gauge)
        else:
            gauge = getattr(self, f"_{name}_gauge")
        
        gauge.set(value, attributes)
        
        # Track for testing
        self._gauge_values[name] = value
    
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