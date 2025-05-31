# Telemetry System Documentation

This document describes the comprehensive telemetry system implemented for MCP Commit Story, providing observability through OpenTelemetry traces, metrics, and structured logging.

## Overview

The telemetry system provides three key observability pillars:
- **Tracing**: Request flow and operation tracking
- **Metrics**: Quantitative measurements and KPIs  
- **Structured Logging**: JSON-formatted logs with trace correlation

## Architecture

The system is built on OpenTelemetry standards with vendor-neutral export capabilities:
- **Traces**: BatchSpanProcessor with configurable exporters
- **Metrics**: PeriodicExportingMetricReader with multiple export formats
- **Structured Logging**: Custom OTelFormatter with automatic trace correlation

## Structured Logging with Trace Correlation

### Features

- **JSON Format**: All logs output as structured JSON for parsing and analysis
- **Automatic Trace Correlation**: Active span IDs automatically injected into logs
- **Sensitive Data Redaction**: Automatic sanitization of passwords, tokens, API keys
- **Performance Optimization**: Lazy evaluation for expensive log data
- **Metrics Integration**: Optional log-based metrics collection

### Log Format

Standard JSON structure includes:
```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "message": "Operation completed successfully",
  "logger": "mcp_commit_story.module",
  "pathname": "/path/to/file.py",
  "lineno": 42,
  "trace_id": "1234567890abcdef1234567890abcdef",
  "span_id": "abcdef1234567890",
  "operation_id": "abc123",
  "user_id": "12345"
}
```

When spans are active, `trace_id` and `span_id` are automatically added for correlation.

### Sensitive Data Protection

The system automatically redacts sensitive information from logs:
- Password fields: `password`, `user_password`, `db_password`
- Tokens: `token`, `api_token`, `access_token`, `refresh_token`
- Keys: `api_key`, `private_key`, `secret_key`
- Authentication: `auth`, `authorization`, `credentials`
- Sessions: `session_id`, `cookie`

Nested structures are recursively sanitized, replacing sensitive values with `[REDACTED]`.

### Performance Optimization

For expensive computations:
```python
from mcp_commit_story.structured_logging import LazyLogData, log_performance_optimized

# Lazy evaluation - only computed if logging enabled
expensive_data = LazyLogData(lambda: serialize_complex_object(data))

# Recommended pattern - check level before expensive operations
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Complex details", extra={"data": expensive_computation()})

# Or use performance-optimized helper
log_performance_optimized(
    logger, 
    logging.DEBUG, 
    "Operation details", 
    {"complex_data": expensive_data}
)
```

### Integration Usage

```python
from mcp_commit_story.telemetry import setup_telemetry
from mcp_commit_story.structured_logging import get_correlated_logger

# Setup during initialization
config = {
    "telemetry": {
        "enabled": True,
        "service_name": "my-service",
        "logging": {
            "level": "INFO",
            "format": "json",
            "correlation": True,
            "metrics": True
        }
    }
}

setup_telemetry(config)

# Use throughout application
logger = get_correlated_logger(__name__)
logger.info("User action", extra={
    "user_id": "12345",
    "action": "file_upload",
    "file_size": 1024
})
```

### Configuration

Configure logging via telemetry config:
```python
{
    "telemetry": {
        "logging": {
            "level": "INFO",          # Log level 
            "format": "json",         # Always JSON (only supported format)
            "correlation": True,      # Enable trace correlation
            "metrics": False,         # Enable log-based metrics
            "handlers": ["console"]   # Output destinations
        }
    }
}
```

When telemetry is disabled, correlation is automatically disabled but structured logging continues to work.

## Multi-Exporter Configuration

### Supported Exporters

1. **Console Exporter** (Default)
   - Always available for development and debugging
   - Human-readable trace and metric output

2. **OTLP Exporter** (Production)
   - gRPC protocol: `otlp-grpc`
   - HTTP protocol: `otlp-http`
   - Compatible with observability platforms

3. **Prometheus Exporter** (Metrics)
   - Native Prometheus format metrics
   - HTTP endpoint for scraping

### Environment Variable Precedence

Configuration follows a hierarchical precedence system:

1. **MCP-specific variables** (highest priority)
2. **Standard OpenTelemetry variables** (medium priority)  
3. **Default values** (lowest priority)

#### MCP-Specific Variables
```bash
# Service identification
MCP_SERVICE_NAME="mcp-commit-story"
MCP_SERVICE_VERSION="1.0.0"
MCP_DEPLOYMENT_ENVIRONMENT="production"

# Exporter selection (comma-separated list)
MCP_TELEMETRY_EXPORTERS="console,otlp-grpc,prometheus"

# OTLP configuration
MCP_OTLP_ENDPOINT="https://api.honeycomb.io:443"
MCP_OTLP_HEADERS="x-honeycomb-team=your-api-key"
MCP_OTLP_INSECURE="false"

# Prometheus configuration  
MCP_PROMETHEUS_PORT="8000"
MCP_PROMETHEUS_ENDPOINT="/metrics"
```

#### Standard OpenTelemetry Variables
```bash
# Service identification
OTEL_SERVICE_NAME="mcp-commit-story"
OTEL_SERVICE_VERSION="1.0.0"

# OTLP configuration
OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
OTEL_EXPORTER_OTLP_HEADERS="authorization=Bearer token"
OTEL_EXPORTER_OTLP_INSECURE="true"
```

### Exporter Configuration Examples

#### Console Only (Development)
```bash
MCP_TELEMETRY_EXPORTERS="console"
```

#### OTLP gRPC (Production)  
```bash
MCP_TELEMETRY_EXPORTERS="otlp-grpc"
MCP_OTLP_ENDPOINT="https://api.honeycomb.io:443"
MCP_OTLP_HEADERS="x-honeycomb-team=your-api-key"
```

#### Multiple Exporters (Comprehensive)
```bash
MCP_TELEMETRY_EXPORTERS="console,otlp-grpc,prometheus"
MCP_OTLP_ENDPOINT="https://api.honeycomb.io:443"
MCP_OTLP_HEADERS="x-honeycomb-team=your-api-key"
MCP_PROMETHEUS_PORT="8000"
```

### Validation and Error Handling

#### Validation Rules
- **Exporters**: Must be from supported list: `console`, `otlp-grpc`, `otlp-http`, `prometheus`
- **OTLP Endpoint**: Must be valid URL format when OTLP exporters enabled
- **Prometheus Port**: Must be valid integer between 1024-65535
- **Headers**: Must be in format `key1=value1,key2=value2`

#### Partial Success Handling
The system implements graceful degradation:
- Invalid exporters are skipped with warning logs
- Failed exporter initialization doesn't prevent system startup
- At least one successful exporter required for telemetry to be marked as enabled
- Detailed validation errors logged for troubleshooting

#### Error Messages
```
Invalid exporter 'jaeger': supported exporters are console, otlp-grpc, otlp-http, prometheus
Missing required OTLP endpoint for exporter: otlp-grpc
Invalid Prometheus port '99999': must be between 1024 and 65535
Failed to initialize exporter 'otlp-grpc': connection refused
```

## Metrics Collection

The system provides comprehensive MCP-specific metrics:

### Counters
- `mcp.tool_calls_total`: Total tool calls with success/failure labels
- `mcp.operations_total`: Total operations by type
- `mcp.errors_total`: Error counts by category

### Histograms  
- `mcp.operation_duration_seconds`: Operation latency distribution
- `mcp.tool_call_duration_seconds`: Tool call performance

### Gauges
- `mcp.active_operations`: Current concurrent operations
- `mcp.queue_size`: Request queue depth
- `mcp.memory_usage_mb`: Current memory consumption

## Best Practices

### Logging
1. **Use semantic attributes**: Add structured context with `extra` parameter
2. **Check log levels**: Use `logger.isEnabledFor()` for expensive operations
3. **Avoid sensitive data**: System auto-redacts but be mindful of field names
4. **Correlation context**: Logs within spans automatically get trace correlation

### Tracing
1. **Meaningful span names**: Use descriptive operation names
2. **Semantic attributes**: Add context like `user_id`, `operation_type`
3. **Error handling**: Spans automatically record exceptions
4. **Nested operations**: Child spans inherit trace context

### Metrics
1. **Consistent labeling**: Use standard attributes across metrics
2. **Appropriate types**: Counters for totals, histograms for latency
3. **Resource efficiency**: Avoid high-cardinality labels

## Security Considerations

- **API Keys**: Never log authentication credentials
- **Sensitive Fields**: Auto-redaction covers common patterns but review field names
- **Network Security**: Use TLS for OTLP exports in production
- **Access Control**: Secure metrics endpoints appropriately

## Troubleshooting

### Common Issues

1. **Missing Trace Correlation**
   - Verify telemetry is enabled and spans are active
   - Check logging instrumentation is enabled

2. **Exporter Failures**
   - Check network connectivity for OTLP endpoints
   - Verify authentication credentials
   - Review validation error messages

3. **Performance Impact**
   - Use lazy evaluation for expensive log data
   - Adjust export intervals for high-volume scenarios
   - Monitor exporter queue depths

### Debug Configuration
```python
config = {
    "telemetry": {
        "enabled": True,
        "logging": {
            "level": "DEBUG",
            "correlation": True
        }
    }
}
```

### Monitoring Commands
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# View recent traces (if using console exporter)
tail -f /var/log/application.log | grep trace_id
``` 