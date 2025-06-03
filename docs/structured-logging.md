# Structured Logging System Documentation

This document describes the structured logging system implemented in `src/mcp_commit_story/structured_logging.py`. This module provides JSON-formatted logging with OpenTelemetry trace correlation, automatic sensitive data redaction, and comprehensive metrics collection.

## Table of Contents

1. [Overview](#overview)
2. [Core Components](#core-components)
3. [Trace Correlation](#trace-correlation)
4. [Sensitive Data Protection](#sensitive-data-protection)
5. [Metrics Collection](#metrics-collection)
6. [Configuration](#configuration)
7. [Performance Optimization](#performance-optimization)
8. [Usage Examples](#usage-examples)

---

## Overview

The structured logging system provides enterprise-grade logging capabilities with:

- **JSON-Formatted Output**: Structured, machine-readable log entries
- **OpenTelemetry Integration**: Automatic trace and span ID injection
- **Sensitive Data Redaction**: Automatic protection of secrets and credentials
- **Metrics Collection**: Log-based operational metrics
- **Performance Optimization**: Lazy evaluation and efficient processing
- **Security-First Design**: Privacy-conscious data handling

## Core Components

### OTelFormatter

The `OTelFormatter` class provides JSON-formatted logging with trace correlation:

```python
class OTelFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Creates structured JSON logs with trace correlation
```

**Key Features**:
- **JSON Structure**: Consistent, parseable log format
- **Trace Correlation**: Automatic trace/span ID injection when available
- **Metadata Enrichment**: File path, line numbers, logger names
- **Exception Handling**: Structured exception information
- **Sensitive Data Protection**: Automatic redaction via `sanitize_log_data()`

**Log Format**:
```json
{
  "timestamp": "2025-01-15T14:30:00.123456Z",
  "level": "INFO",
  "message": "Journal entry created successfully",
  "logger": "mcp_commit_story.journal",
  "pathname": "/path/to/file.py",
  "lineno": 42,
  "trace_id": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
  "span_id": "9a8b7c6d5e4f3a2b",
  "operation": "journal_creation",
  "duration": 0.123
}
```

### LogMetricsHandler

The `LogMetricsHandler` class collects operational metrics from log entries:

```python
class LogMetricsHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Processes log records and updates metrics
```

**Metrics Collected**:
- **Log Entry Counts**: By level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Total Log Volume**: Overall logging activity
- **Error Rates**: Percentage of logs at ERROR+ levels
- **Trend Analysis**: Log patterns over time

## Trace Correlation

### Automatic Trace Injection

The formatter automatically detects active OpenTelemetry spans and injects correlation IDs:

```python
current_span = get_current_span()
if current_span and hasattr(current_span, 'get_span_context'):
    span_context = current_span.get_span_context()
    if (span_context and span_context.trace_id != 0 and span_context.span_id != 0):
        log_data["trace_id"] = format(span_context.trace_id, '032x')
        log_data["span_id"] = format(span_context.span_id, '016x')
```

**Benefits**:
- **Request Correlation**: Link log entries to specific operations
- **Distributed Tracing**: Connect logs across service boundaries
- **Debugging**: Easily find all logs related to a specific request
- **Performance Analysis**: Correlate logs with trace timing data

**Trace ID Format**:
- **trace_id**: 32-character hexadecimal string
- **span_id**: 16-character hexadecimal string
- **Validation**: Only valid (non-zero) IDs are included

### Span Context Safety

The system handles span context extraction safely:

```python
try:
    span_context = current_span.get_span_context()
    # Process span context...
except Exception:
    # Continue without trace correlation if extraction fails
    pass
```

This ensures logging continues to work even if OpenTelemetry is misconfigured or unavailable.

## Sensitive Data Protection

### Automatic Redaction

The `sanitize_log_data()` function automatically redacts sensitive information:

```python
SENSITIVE_FIELDS: Set[str] = {
    "password", "token", "api_key", "secret", "auth", "authorization", 
    "credentials", "key", "private_key", "access_token", "refresh_token",
    "client_secret", "webhook_secret", "session_id", "cookie"
}
```

**Redaction Strategy**:
- **Field Name Matching**: Checks field names against sensitive patterns
- **Case Insensitive**: Matches regardless of capitalization
- **Recursive Processing**: Handles nested dictionaries and lists
- **Value Replacement**: Replaces sensitive values with `[REDACTED]`
- **Structure Preservation**: Maintains original data structure

**Example**:
```python
original = {
    "user": "john",
    "api_key": "secret123",
    "data": {
        "password": "mysecret",
        "email": "john@example.com"
    }
}

sanitized = sanitize_log_data(original)
# Result:
{
    "user": "john",
    "api_key": "[REDACTED]",
    "data": {
        "password": "[REDACTED]",
        "email": "john@example.com"
    }
}
```

### Privacy-Conscious Design

**File Path Handling**:
- Only filename logged, not full paths
- Sensitive directories automatically filtered
- User information never included in logs

**Content Size Limits**:
- Large content automatically truncated
- Hash values for content identification
- Memory usage protection

## Metrics Collection

### LogMetricsHandler

The metrics handler provides comprehensive logging analytics:

```python
handler = LogMetricsHandler()
metrics = handler.get_metrics()
# Returns:
{
    "log_entries_total": {"INFO": 150, "ERROR": 5, "WARNING": 12},
    "total_logs": 167,
    "error_logs": 5
}
```

**Metrics Available**:
- **log_entries_total**: Count by log level
- **total_logs**: Overall log count
- **error_logs**: Error and critical count
- **error_rate**: Calculated error percentage

### Error Rate Calculation

```python
def get_error_rate(self) -> float:
    if self._total_logs == 0:
        return 0.0
    return self._error_logs / self._total_logs
```

**Use Cases**:
- **Health Monitoring**: Track application health via error rates
- **Alert Generation**: Trigger alerts on high error rates
- **Trend Analysis**: Monitor logging patterns over time
- **Capacity Planning**: Understand logging volume requirements

### Metrics Reset

```python
def reset_metrics(self) -> None:
    self._log_counts.clear()
    self._total_logs = 0
    self._error_logs = 0
```

Enables periodic metrics collection without memory accumulation.

## Configuration

### get_correlated_logger()

Creates loggers with trace correlation and structured formatting:

```python
def get_correlated_logger(name: str, level: Optional[str] = None, 
                         enable_metrics: bool = False) -> logging.Logger:
```

**Parameters**:
- `name`: Logger name (typically `__name__`)
- `level`: Log level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
- `enable_metrics`: Whether to enable metrics collection

**Features**:
- **Automatic Formatter**: OTelFormatter attached automatically
- **Metrics Integration**: Optional LogMetricsHandler attachment
- **Level Configuration**: Configurable log levels
- **Handler Management**: Proper handler setup and cleanup

### configure_structured_logging()

Configures logging from configuration dictionary:

```python
def configure_structured_logging(config: Dict[str, Any]) -> bool:
```

**Configuration Options**:
```python
config = {
    "logging": {
        "level": "INFO",
        "format": "structured",  # Enables JSON formatting
        "enable_metrics": True,
        "enable_trace_correlation": True
    }
}
```

### setup_structured_logging()

Main setup function for structured logging system:

```python
def setup_structured_logging(telemetry_config: Dict[str, Any]) -> bool:
```

**Integration Points**:
- **Telemetry Config**: Coordinates with OpenTelemetry setup
- **Environment Variables**: Respects LOG_LEVEL and other env vars
- **Default Handling**: Graceful fallback to standard logging

## Performance Optimization

### Lazy Log Data

The `LazyLogData` class provides performance optimization for expensive log operations:

```python
class LazyLogData:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._evaluated = False
        self._result = None
    
    def __str__(self) -> str:
        if not self._evaluated:
            self._result = self.func(*self.args, **self.kwargs)
            self._evaluated = True
        return str(self._result)
```

**Benefits**:
- **Deferred Evaluation**: Expensive operations only run if log level requires it
- **Memory Efficiency**: Avoids creating large strings for filtered logs
- **Performance**: Significant speedup when debug logging is disabled

**Usage**:
```python
# Expensive operation only runs if DEBUG level is enabled
logger.debug("Processing data: %s", LazyLogData(expensive_data_formatter, large_dataset))
```

### Performance-Optimized Logging

The `log_performance_optimized()` function provides efficient logging:

```python
def log_performance_optimized(logger: logging.Logger, level: int, message: str, 
                            lazy_data: Optional[Dict[str, Any]] = None) -> None:
```

**Features**:
- **Level Checking**: Early return if log level not enabled
- **Lazy Evaluation**: Optional lazy data evaluation
- **Minimal Overhead**: Optimized for high-frequency logging
- **Structured Data**: Support for structured log data

## Usage Examples

### Basic Structured Logging

```python
from mcp_commit_story.structured_logging import get_correlated_logger

logger = get_correlated_logger(__name__)
logger.info("Journal entry created", extra={
    "operation": "create_entry",
    "file_path": "journal/daily/2025-01-15.md",
    "entry_size": 1024
})
```

### Sensitive Data Handling

```python
from mcp_commit_story.structured_logging import sanitize_log_data

# Automatically redact sensitive information
user_data = {
    "username": "john",
    "api_key": "secret123",
    "email": "john@example.com"
}

logger.info("User operation completed", extra={"user_data": user_data})
# api_key is automatically redacted in logs
```

### Metrics Collection

```python
from mcp_commit_story.structured_logging import get_correlated_logger, get_log_metrics

# Enable metrics collection
logger = get_correlated_logger(__name__, enable_metrics=True)

# Log some events
logger.info("Operation successful")
logger.error("Operation failed")

# Get metrics
metrics = get_log_metrics()
print(f"Error rate: {get_log_error_rate():.2%}")
```

### Performance Optimization

```python
from mcp_commit_story.structured_logging import LazyLogData, log_performance_optimized

def expensive_formatter(data):
    # This only runs if DEBUG level is enabled
    return json.dumps(data, indent=2)

# Using LazyLogData
logger.debug("Debug data: %s", LazyLogData(expensive_formatter, large_data))

# Using performance-optimized logging
log_performance_optimized(
    logger, 
    logging.INFO, 
    "Operation completed",
    lazy_data={"details": LazyLogData(expensive_formatter, operation_data)}
)
```

### Configuration Setup

```python
from mcp_commit_story.structured_logging import setup_structured_logging

# Configure structured logging with telemetry
config = {
    "telemetry": {
        "logging": {
            "level": "INFO",
            "enable_metrics": True,
            "enable_trace_correlation": True
        }
    }
}

success = setup_structured_logging(config)
if success:
    logger = get_correlated_logger(__name__)
    logger.info("Structured logging configured successfully")
```

## Integration Points

### OpenTelemetry Integration

- **Trace Correlation**: Automatic trace/span ID injection
- **Span Attributes**: Log data becomes span attributes when relevant
- **Unified Observability**: Logs, traces, and metrics in one system

### MCP Server Integration

- **Operation Logging**: All MCP operations logged with structured data
- **Error Tracking**: Structured error information for debugging
- **Performance Monitoring**: Request/response timing and data sizes

### Configuration System

- **Config-Driven**: Logging behavior controlled by configuration
- **Environment Variables**: Standard logging environment variable support
- **Hot Reloading**: Configuration changes applied without restart

## See Also

- **[Telemetry](telemetry.md)** - Complete telemetry and monitoring system
- **[MCP API Specification](mcp-api-specification.md)** - How logging integrates with MCP operations
- **[Implementation Guide](implementation-guide.md)** - Development patterns and practices
- **[Server Setup](server_setup.md)** - MCP server configuration and deployment 