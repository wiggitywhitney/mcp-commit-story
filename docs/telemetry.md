# Telemetry System Documentation

This document describes the comprehensive telemetry system implemented for MCP Commit Story, providing observability through OpenTelemetry traces, metrics, and structured logging.

## Overview

The telemetry system provides three key observability pillars:
- **Tracing**: Request flow and operation tracking
- **Metrics**: Quantitative measurements and KPIs  
- **Structured Logging**: JSON-formatted logs with trace correlation

## Features

- **Distributed Tracing**: Track operations across the entire MCP server lifecycle
- **Metrics Collection**: Monitor performance, success rates, and system health
- **Structured Logging**: JSON-formatted logs with automatic trace correlation
- **Multi-Exporter Support**: Console, OTLP, and custom exporters
- **Graceful Degradation**: Server continues operation even if telemetry fails
- **Hot Configuration Reload**: Update telemetry settings without restart

## MCP Server Integration

### Configuration

The telemetry system integrates seamlessly with the MCP server through the enhanced configuration schema:

```yaml
# .mcp-commit-storyrc.yaml
telemetry:
  enabled: true
  service_name: 'mcp-commit-story'
  service_version: '1.0.0'
  deployment_environment: 'development'
  exporters:
    console:
      enabled: true
    otlp:
      enabled: false
      endpoint: 'http://localhost:4317'
  auto_instrumentation:
    enabled: true
    preset: 'minimal'
```

### Integration Points

The telemetry system integrates at multiple points in the MCP server lifecycle:

1. **Server Startup**: Telemetry initializes during `create_mcp_server()`
2. **Tool Calls**: All MCP tools are automatically traced via decorators
3. **Error Handling**: Metrics and traces capture both success and failure scenarios
4. **Configuration Reload**: Telemetry respects hot configuration changes

### Tool Call Tracing

All MCP tools are automatically instrumented with tracing:

```python
@server.tool()
@trace_mcp_operation("journal_new_entry")
async def journal_new_entry(request: JournalNewEntryRequest) -> JournalNewEntryResponse:
    \"\"\"Create a new journal entry with AI-generated content.\"\"\"
    return await handle_journal_new_entry(request)
```

This provides:
- **Span Creation**: Each tool call creates a dedicated span
- **Automatic Attributes**: Tool name, request metadata, success/failure status
- **Error Capture**: Exceptions are automatically recorded in spans
- **Duration Tracking**: Precise timing for performance analysis

### Metrics Collection

The system automatically collects comprehensive metrics:

#### Tool Call Metrics
- `mcp_tool_calls_total{tool_name, status}` - Total tool call count
- `mcp_tool_call_duration_seconds{tool_name}` - Tool call duration histogram
- `mcp_operation_duration_seconds{operation_name, success}` - Operation timing

#### Server Metrics  
- `mcp_server_startup_duration_seconds` - Server initialization time
- `mcp_active_operations_total` - Currently active operations
- `mcp_config_reload_total{status}` - Configuration reload events

#### Application-Specific Metrics
- `mcp_git_operations_total{operation_type}` - Git-specific operations
- `mcp_file_operations_total{operation_type}` - File I/O operations  
- `mcp_context_collection_duration_seconds` - Context gathering performance

### Structured Logging Integration

All logs are automatically enhanced with trace correlation:

```json
{
  "timestamp": "2025-05-31T12:00:00.000Z",
  "level": "INFO",
  "message": "Processing journal entry request",
  "otelSpanID": "abc123def456",
  "otelTraceID": "789xyz012uvw",
  "tool_name": "journal_new_entry",
  "user_id": "user123"
}
```

### Error Handling and Graceful Degradation

The integration is designed to never block MCP server operation:

```python
# Telemetry failures are logged but don't prevent server startup
try:
    telemetry_initialized = setup_telemetry(config.as_dict())
    if telemetry_initialized:
        logging.info("Telemetry system initialized successfully")
    else:
        logging.info("Telemetry disabled via configuration")
except Exception as e:
    logging.warning(f"Telemetry setup failed, continuing without telemetry: {e}")
    telemetry_initialized = False
```

### Performance Characteristics

The telemetry integration maintains excellent performance:

- **< 5ms overhead per tool call** - Minimal impact on operation latency
- **< 1MB memory overhead** - Efficient resource utilization
- **< 10% CPU overhead** - Negligible processing impact
- **~1MB daily data volume** - Reasonable storage requirements for moderate usage

### Health Checks

The system provides built-in health monitoring:

```python
# Check telemetry system health
if hasattr(server, 'telemetry_initialized') and server.telemetry_initialized:
    # Telemetry is active and healthy
    tracer = get_tracer(__name__)
    metrics = get_mcp_metrics()
```

### Troubleshooting

#### Common Issues

**Telemetry Not Initializing**
```bash
# Check configuration
cat .mcp-commit-storyrc.yaml | grep -A 10 telemetry

# Verify logs for initialization errors
tail -f logs/mcp-server.log | grep telemetry
```

**Missing Traces**
- Verify `telemetry.enabled: true` in configuration
- Check that `@trace_mcp_operation` decorators are applied
- Ensure OpenTelemetry exporters are configured correctly

**High Overhead**
- Reduce sampling rate in configuration
- Switch to `preset: 'minimal'` for auto-instrumentation
- Disable console exporter in production

#### Debug Mode

Enable detailed telemetry logging:

```yaml
telemetry:
  enabled: true
  debug: true  # Enables verbose telemetry logging
  exporters:
    console:
      enabled: true
      verbose: true
```

### Production Deployment

For production environments:

```yaml
telemetry:
  enabled: true
  service_name: 'mcp-commit-story'
  service_version: '1.2.0'
  deployment_environment: 'production'
  exporters:
    console:
      enabled: false  # Disable console output
    otlp:
      enabled: true
      endpoint: 'https://your-otlp-collector:4317'
      headers:
        authorization: 'Bearer your-token'
  auto_instrumentation:
    enabled: true
    preset: 'minimal'  # Reduced overhead
```

## Architecture

### Component Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Server    │───▶│  Telemetry Core  │───▶│   Exporters     │
│                 │    │                  │    │                 │
│ • Tool Handlers │    │ • TracerProvider │    │ • Console       │
│ • Error Handler │    │ • MeterProvider  │    │ • OTLP          │
│ • Config Reload │    │ • Structured Log │    │ • Custom        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Data Flow

1. **Tool Call Initiated** → Span created with `@trace_mcp_operation`
2. **Operation Executed** → Metrics recorded via `handle_mcp_error`
3. **Logs Generated** → Enhanced with trace correlation
4. **Results Exported** → Sent to configured exporters (console, OTLP, etc.)

## API Reference

### Core Functions

- `setup_telemetry(config: dict) -> bool` - Initialize telemetry system
- `get_tracer(name: str) -> Tracer` - Get OpenTelemetry tracer
- `get_mcp_metrics() -> MCPMetrics` - Get metrics collector
- `trace_mcp_operation(operation_name: str)` - Decorator for tracing
- `setup_structured_logging(config: dict)` - Configure JSON logging

### Configuration Schema

See the [Configuration Reference](config.md) for complete schema documentation.

## Examples

### Basic Usage

```python
from mcp_commit_story.server import create_mcp_server
from mcp_commit_story.telemetry import get_tracer, get_mcp_metrics

# Create server with telemetry
server = create_mcp_server()

# Use telemetry in custom operations
tracer = get_tracer(__name__)
metrics = get_mcp_metrics()

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("operation.type", "custom")
    metrics.record_operation_duration("custom_operation", 0.123)
```

### Custom Metrics

```python
from mcp_commit_story.telemetry import get_mcp_metrics

metrics = get_mcp_metrics()

# Record custom metrics
metrics.record_tool_call("custom_tool", success=True, user_id="user123")
metrics.record_operation_duration("data_processing", 2.5, success=True)
```

## Related Documentation

- [Configuration Guide](config.md) - Complete configuration reference
- [Multi-Exporter Setup](multi-exporter.md) - Advanced exporter configuration
- [Structured Logging](structured-logging.md) - JSON logging with trace correlation

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