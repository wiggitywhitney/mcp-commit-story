"""
Structured logging with OpenTelemetry trace correlation for MCP Commit Story.

This module provides JSON-formatted logging with automatic trace/span ID injection,
log-based metrics, and integration with the existing telemetry system.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from opentelemetry import trace
from opentelemetry.trace import get_current_span


# Sensitive field names that should be automatically redacted
SENSITIVE_FIELDS: Set[str] = {
    "password", "token", "api_key", "secret", "auth", "authorization", 
    "credentials", "key", "private_key", "access_token", "refresh_token",
    "client_secret", "webhook_secret", "session_id", "cookie"
}


def sanitize_log_data(data: Any) -> Any:
    """
    Automatically redact sensitive information from log data.
    
    Args:
        data: The data to sanitize (dict, list, or primitive)
        
    Returns:
        Sanitized data with sensitive fields redacted
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                # If the key itself is sensitive, redact the value completely
                sanitized[key] = "[REDACTED]"
            else:
                # If the key is not sensitive, recursively sanitize the value
                sanitized[key] = sanitize_log_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_log_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_log_data(item) for item in data)
    else:
        return data


class OTelFormatter(logging.Formatter):
    """
    Custom JSON formatter that automatically injects OpenTelemetry trace and span IDs.
    
    Produces structured JSON logs with trace correlation when spans are active.
    Includes automatic sensitive data redaction for security.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the formatter."""
        super().__init__(*args, **kwargs)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON with optional trace correlation.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Start with basic log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "pathname": record.pathname,
            "lineno": record.lineno,
        }
        
        # Add trace correlation if span is active
        current_span = get_current_span()
        if current_span and hasattr(current_span, 'get_span_context'):
            try:
                span_context = current_span.get_span_context()
                # Check if we have valid trace and span IDs (non-zero)
                if (span_context and 
                    hasattr(span_context, 'trace_id') and 
                    hasattr(span_context, 'span_id') and
                    span_context.trace_id != 0 and 
                    span_context.span_id != 0):
                    log_data["trace_id"] = format(span_context.trace_id, '032x')
                    log_data["span_id"] = format(span_context.span_id, '016x')
            except Exception:
                # If we can't get span context for any reason, just continue without trace correlation
                pass
        
        # Add extra fields if present (from logger.info("msg", extra={...}))
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'message', 'exc_info', 'exc_text', 
                              'stack_info', 'getMessage']:
                    # Sanitize extra data for sensitive information
                    log_data[key] = sanitize_log_data(value)
        
        # Handle exception information
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Sanitize the final log data
        sanitized_data = sanitize_log_data(log_data)
        
        return json.dumps(sanitized_data, default=str)


class LogMetricsHandler(logging.Handler):
    """
    Optional logging handler that collects metrics from log entries.
    
    Tracks log entry counts by level and calculates error rates for
    operational monitoring.
    """
    
    def __init__(self):
        """Initialize the metrics handler."""
        super().__init__()
        self._log_counts: Dict[str, int] = {}
        self._total_logs = 0
        self._error_logs = 0
        
    def emit(self, record: logging.LogRecord) -> None:
        """
        Process a log record and update metrics.
        
        Args:
            record: The log record to process
        """
        level_name = record.levelname
        
        # Update counts
        self._log_counts[level_name] = self._log_counts.get(level_name, 0) + 1
        self._total_logs += 1
        
        # Track errors (ERROR and CRITICAL levels)
        if record.levelno >= logging.ERROR:
            self._error_logs += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current log metrics.
        
        Returns:
            Dictionary containing log metrics
        """
        return {
            "log_entries_total": self._log_counts.copy(),
            "total_logs": self._total_logs,
            "error_logs": self._error_logs
        }
    
    def get_error_rate(self) -> float:
        """
        Calculate current error rate.
        
        Returns:
            Error rate as a float between 0.0 and 1.0
        """
        if self._total_logs == 0:
            return 0.0
        return self._error_logs / self._total_logs
    
    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._log_counts.clear()
        self._total_logs = 0
        self._error_logs = 0


def get_correlated_logger(name: str, level: Optional[str] = None, 
                         enable_metrics: bool = False) -> logging.Logger:
    """
    Get a logger configured with trace correlation and structured formatting.
    
    Args:
        name: Logger name (typically __name__)
        level: Optional log level (defaults to INFO)
        enable_metrics: Whether to enable log-based metrics collection
        
    Returns:
        Configured logger with OTelFormatter
    """
    logger = logging.getLogger(name)
    
    # Set level if provided
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    
    # Check if already configured to avoid duplicate handlers
    has_otel_handler = any(
        hasattr(h, 'formatter') and isinstance(h.formatter, OTelFormatter)
        for h in logger.handlers
    )
    
    if not has_otel_handler:
        # Create handler with OTel formatter
        handler = logging.StreamHandler()
        handler.setFormatter(OTelFormatter())
        logger.addHandler(handler)
        
        # Add metrics handler if requested
        if enable_metrics:
            metrics_handler = LogMetricsHandler()
            logger.addHandler(metrics_handler)
    
    return logger


def configure_structured_logging(config: Dict[str, Any]) -> bool:
    """
    Configure structured logging for the entire application.
    
    Args:
        config: Configuration dictionary with logging settings
            {
                "level": "INFO",           # Log level
                "format": "json",          # Format (currently only json supported)
                "correlation": True,       # Enable trace correlation
                "metrics": False,          # Enable log-based metrics
                "handlers": ["console"]    # Output handlers
            }
    
    Returns:
        True if configuration was successful, False otherwise
    """
    try:
        # Get configuration values with defaults
        log_level = config.get("level", "INFO").upper()
        log_format = config.get("format", "json")
        enable_correlation = config.get("correlation", True)
        enable_metrics = config.get("metrics", False)
        handlers = config.get("handlers", ["console"])
        
        # Validate format
        if log_format != "json":
            logging.warning(f"Unsupported log format '{log_format}', using json")
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level))
        
        # Clear existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add configured handlers
        for handler_type in handlers:
            if handler_type == "console":
                handler = logging.StreamHandler()
                if enable_correlation:
                    handler.setFormatter(OTelFormatter())
                else:
                    # Fall back to standard formatter if correlation disabled
                    handler.setFormatter(logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    ))
                root_logger.addHandler(handler)
                
                # Add metrics handler if enabled
                if enable_metrics:
                    metrics_handler = LogMetricsHandler()
                    root_logger.addHandler(metrics_handler)
        
        logging.info("Structured logging configured successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to configure structured logging: {e}")
        return False


def setup_structured_logging(telemetry_config: Dict[str, Any]) -> bool:
    """
    Setup structured logging as part of telemetry initialization.
    
    Integrates with the existing telemetry system to provide unified
    configuration and initialization.
    
    Args:
        telemetry_config: Telemetry configuration containing logging settings
        
    Returns:
        True if setup was successful, False otherwise
    """
    try:
        # Extract logging configuration from telemetry config
        logging_config = telemetry_config.get("telemetry", {}).get("logging", {})
        
        # Set defaults based on telemetry settings
        if not logging_config:
            logging_config = {
                "level": "INFO",
                "format": "json",
                "correlation": True,
                "metrics": False,
                "handlers": ["console"]
            }
        
        # Enable correlation if telemetry is enabled
        telemetry_enabled = telemetry_config.get("telemetry", {}).get("enabled", True)
        if not telemetry_enabled:
            logging_config["correlation"] = False
        
        return configure_structured_logging(logging_config)
        
    except Exception as e:
        logging.error(f"Failed to setup structured logging: {e}")
        return False


# Performance optimization utility
class LazyLogData:
    """
    Lazy evaluation wrapper for expensive-to-serialize log data.
    
    Use this to defer serialization of complex objects until logging
    actually occurs at the configured level.
    """
    
    def __init__(self, func, *args, **kwargs):
        """
        Initialize lazy log data.
        
        Args:
            func: Function to call for data generation
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._computed = False
        self._result = None
    
    def __str__(self) -> str:
        """Compute and return string representation."""
        if not self._computed:
            self._result = self.func(*self.args, **self.kwargs)
            self._computed = True
        return str(self._result)
    
    def __repr__(self) -> str:
        """Return representation."""
        return f"LazyLogData({self.func.__name__})"


def log_performance_optimized(logger: logging.Logger, level: int, message: str, 
                            lazy_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Performance-optimized logging that only evaluates expensive data when needed.
    
    Args:
        logger: Logger instance
        level: Logging level (e.g., logging.DEBUG)
        message: Log message
        lazy_data: Optional dictionary of expensive-to-compute data
    """
    if logger.isEnabledFor(level):
        extra = {}
        if lazy_data:
            # Only compute expensive data if logging is enabled at this level
            for key, value in lazy_data.items():
                if isinstance(value, LazyLogData):
                    extra[key] = str(value)  # Triggers computation
                else:
                    extra[key] = value
        
        logger.log(level, message, extra=extra)


# Global metrics handler reference for easy access
_global_metrics_handler: Optional[LogMetricsHandler] = None


def get_log_metrics() -> Optional[Dict[str, Any]]:
    """
    Get current log metrics from the global metrics handler.
    
    Returns:
        Log metrics dictionary or None if metrics not enabled
    """
    global _global_metrics_handler
    if _global_metrics_handler:
        return _global_metrics_handler.get_metrics()
    return None


def get_log_error_rate() -> float:
    """
    Get current log error rate from the global metrics handler.
    
    Returns:
        Error rate as float, or 0.0 if metrics not enabled
    """
    global _global_metrics_handler
    if _global_metrics_handler:
        return _global_metrics_handler.get_error_rate()
    return 0.0 