# Telemetry and Observability

This document describes the telemetry and observability capabilities of the MCP Commit Story system, built on OpenTelemetry standards.

## Overview

The MCP Commit Story implements comprehensive observability through OpenTelemetry, providing:

- **Distributed Tracing**: Track requests through the AI → MCP → tool call pipeline
- **Metrics Collection**: Monitor operation performance, success rates, and system health
- **Structured Logging**: Correlate logs with traces for debugging
- **Auto-Instrumentation**: Automatic tracing of HTTP requests, async operations, and more
- **Multi-Exporter Support**: Send telemetry to console, OTLP, Prometheus, and other backends

## Configuration

### Basic Setup

Telemetry is configured in the main configuration file:

```yaml
telemetry:
  enabled: true                    # Master switch (default: true)
  service_name: "mcp-commit-story" # Service identifier
  service_version: "1.0.0"         # Version for tracking
  deployment_environment: "production"  # Environment tag
  
  auto_instrumentation:            # Automatic library instrumentation
    enabled: true                  # Enable auto-instrumentation (default: true)
    preset: "minimal"              # Preset: minimal, comprehensive, or custom
    instrumentors:                 # Individual instrumentor control
      requests: true               # HTTP requests library
      aiohttp: true                # Async HTTP client
      asyncio: true                # Async operations
      logging: true                # Log-trace correlation
      
  exporters:
    console:
      enabled: true                # Console output for development
    otlp:
      enabled: false               # OTLP for production backends
      endpoint: "http://localhost:4317"
    prometheus:
      enabled: false               # Prometheus metrics
      port: 8000
```

### Auto-Instrumentation

The system provides automatic instrumentation for common libraries, eliminating the need for manual tracing in most cases.

#### Approved Instrumentors

- **requests**: Traces HTTP requests made with the `requests` library
- **aiohttp**: Traces async HTTP requests with `aiohttp` client
- **asyncio**: Traces async operations and coroutines
- **logging**: Automatically correlates log messages with active traces

#### Preset Configurations

**Minimal Preset** (default):
```yaml
auto_instrumentation:
  preset: "minimal"
  # Enables: requests, logging
```

**Comprehensive Preset**:
```yaml
auto_instrumentation:
  preset: "comprehensive"
  # Enables: requests, aiohttp, asyncio, logging
```

**Custom Preset**:
```yaml
auto_instrumentation:
  preset: "custom"
  instrumentors:
    requests: true
    aiohttp: false    # Selective enabling
    asyncio: true
    logging: true
```

#### Graceful Fallback

Auto-instrumentation gracefully handles missing libraries:
- If a target library (e.g., `aiohttp`) isn't installed, instrumentation is skipped
- Failed instrumentors are tracked but don't break the system
- Logs warning messages for debugging

#### Integration

Auto-instrumentation is automatically enabled during telemetry setup:

```python
from mcp_commit_story.telemetry import setup_telemetry

config = {
    "telemetry": {
        "enabled": True,
        "auto_instrumentation": {
            "enabled": True,
            "preset": "comprehensive"
        }
    }
}

# This automatically enables auto-instrumentation
setup_telemetry(config)
```

### Environment Variables

Sensitive configuration can be provided via environment variables:

- `OTEL_EXPORTER_OTLP_ENDPOINT`: Override OTLP endpoint
- `OTEL_SERVICE_NAME`: Override service name
- `OTEL_RESOURCE_ATTRIBUTES`: Additional resource attributes

## Telemetry Data

### Traces

The system generates traces for:

- **MCP Operations**: Tool calls from AI agents
- **Journal Operations**: Entry creation, reflection addition
- **Git Operations**: Context collection, file scanning
- **Configuration**: Loading and validation

Example trace hierarchy:
```
ai_request
├── mcp_tool_call
│   ├── journal_entry_creation
│   │   ├── git_commit_analysis
│   │   ├── context_collection
│   │   └── file_write_operation
│   └── response_formatting
└── ai_response
```

### Metrics

Key metrics collected:

- **Operation Counters**: Success/failure rates by operation type
- **Duration Histograms**: Performance distribution for operations
- **System Gauges**: Active spans, memory usage, file counts

Example metrics:
- `mcp_journal_operations_total{operation="create_entry", status="success"}`
- `mcp_journal_operation_duration_seconds{operation="git_analysis"}`
- `mcp_journal_active_spans_total`

### Logs

Structured logs with trace correlation:

```json
{
  "timestamp": "2025-01-28T10:30:00Z",
  "level": "INFO",
  "message": "Journal entry created",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "operation": "create_entry",
  "commit_id": "sha123..."
}
```

## Usage Patterns

### Development

For local development, enable console exporter:

```yaml
telemetry:
  enabled: true
  exporters:
    console:
      enabled: true
```

### Production

For production deployments, use OTLP with your observability backend:

```yaml
telemetry:
  enabled: true
  service_name: "mcp-journal-prod"
  deployment_environment: "production"
  exporters:
    otlp:
      enabled: true
      endpoint: "https://your-backend.com:4317"
    prometheus:
      enabled: true
      port: 8000
```

### Debugging

To troubleshoot specific operations:

1. Enable debug logging and console tracing
2. Look for trace IDs in error logs
3. Search for the trace ID across all telemetry data
4. Analyze the trace timeline and span attributes

## Integration with MCP Server

The telemetry system integrates with the MCP server lifecycle:

1. **Initialization**: Telemetry setup during server startup
2. **Request Handling**: Automatic tracing of MCP operations
3. **Shutdown**: Graceful telemetry provider cleanup

### Custom Instrumentation

For custom operations, use the provided decorators:

```python
from mcp_journal.telemetry import get_tracer

tracer = get_tracer("my_component")

@trace_operation("custom_operation")
def my_function():
    with tracer.start_as_current_span("detailed_work") as span:
        span.set_attribute("custom.attribute", "value")
        # Your logic here
```

### MCP Operation Decorator

For tracing MCP-specific operations, use the `trace_mcp_operation` decorator:

```python
from mcp_commit_story.telemetry import trace_mcp_operation

# Basic usage
@trace_mcp_operation("journal_entry_creation")
def create_journal_entry():
    # Your function implementation
    pass

# With custom attributes
@trace_mcp_operation("tool_call", attributes={"tool.name": "journal/create"})
async def handle_tool_call():
    # Your async function implementation
    pass

# Full customization
@trace_mcp_operation(
    "complex_operation",
    operation_type="mcp_tool", 
    attributes={"priority": "high"}
)
def complex_operation():
    pass
```

#### Decorator API

**Parameters:**
- `operation_name` (required): Name of the MCP operation for the span
- `attributes` (optional): Dictionary of custom attributes to add to the span
- `operation_type` (optional): Type of MCP operation (default: "mcp_operation")
- `tracer_name` (optional): Name of the tracer to use (default: "mcp_journal")

#### Semantic Attributes

The decorator automatically sets these span attributes following OpenTelemetry semantic conventions:

**Standard MCP Attributes:**
- `mcp.operation.name`: The operation name provided to the decorator
- `mcp.operation.type`: The type of MCP operation (e.g., "mcp_operation", "mcp_tool")
- `mcp.function.name`: The actual Python function name
- `mcp.function.module`: The module containing the function
- `mcp.function.async`: Boolean indicating if the function is async

**Result Attributes:**
- `mcp.result.status`: "success" or "error" based on execution outcome

**Error Attributes (when exceptions occur):**
- `error.type`: The exception class name (e.g., "FileNotFoundError")
- `error.message`: The exception message

#### Features

**Automatic Function Detection:**
- Detects async vs sync functions using `asyncio.iscoroutinefunction()`
- Applies appropriate wrapper automatically
- Preserves original function metadata with `functools.wraps()`

**Error Handling:**
- Records exceptions in spans with full details
- Sets span status to ERROR with descriptive messages
- Always propagates exceptions (never suppresses them)
- Follows observability principle: don't change application behavior

**Context Propagation:**
- Integrates with OpenTelemetry distributed tracing
- Child operations automatically link to parent spans
- Enables end-to-end request tracking across components

## Best Practices

### Performance

- Telemetry adds minimal overhead when enabled
- Use sampling for high-volume operations
- Disable telemetry in performance-critical scenarios

### Security

- Sensitive data is automatically filtered from spans
- Configuration values are masked in telemetry
- Use secure endpoints for production exporters

### Monitoring

Set up alerts on:
- High error rates in MCP operations
- Increased operation latency
- Telemetry system health metrics

## Troubleshooting

### Common Issues

**Telemetry not appearing:**
- Check `telemetry.enabled` configuration
- Verify exporter endpoints are reachable
- Check for provider initialization errors

**High overhead:**
- Reduce sampling rate
- Disable auto-instrumentation for unused libraries
- Use efficient exporters (avoid console in production)

**Missing context:**
- Ensure proper span propagation
- Check trace correlation configuration
- Verify parent-child span relationships

### Logs to Monitor

Key log messages for telemetry health:
- "Telemetry initialized successfully"
- "Exporter connection failed"
- "Span export errors"
- "Provider shutdown completed"

## Future Enhancements

Planned telemetry improvements:

- Custom metric dashboards
- Anomaly detection on operation patterns
- Integration with APM tools
- Automated performance regression detection
- Cross-service trace correlation 