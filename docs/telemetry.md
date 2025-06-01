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

### Git Operation Instrumentation

The system provides comprehensive instrumentation for Git operations and context collection with a clean decorator pattern that separates telemetry from business logic.

#### Enhanced Git Operation Decorator

```python
from mcp_commit_story.telemetry import trace_git_operation

@trace_git_operation("git_context",
                    performance_thresholds={"duration": 2.0},
                    error_categories=["git", "filesystem", "memory"])
def collect_git_context(commit_hash=None, repo=None, journal_path=None):
    """Clean function focused solely on Git context collection logic."""
    # Pure implementation - no telemetry noise
    return git_context_data
```

#### Automatic Features

The `@trace_git_operation` decorator automatically provides:

- **Performance Monitoring**: Tracks operation duration and compares against configurable thresholds
- **Memory Tracking**: Uses context managers to monitor memory usage during operations  
- **Error Categorization**: Categorizes exceptions into configured categories (git, filesystem, memory, etc.)
- **Timeout Protection**: Applies configurable timeouts with graceful degradation
- **Smart File Sampling**: For large repositories, applies sampling strategies to prevent performance degradation
- **Circuit Breaker Pattern**: Disables telemetry temporarily after repeated failures

#### Context Collection Examples

**Chat History Collection:**
```python
@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(since_commit=None, max_messages_back=150):
    """AI prompt for chat analysis - clean and focused."""
    # Function contains only AI prompts and business logic
    return ChatHistory(messages=processed_messages)
```

**Terminal Commands Collection:**
```python
@trace_git_operation("terminal_commands",
                    performance_thresholds={"duration": 1.0}, 
                    error_categories=["api", "network", "parsing"])
def collect_ai_terminal_commands(since_commit=None, max_messages_back=150):
    """AI prompt for terminal command analysis."""
    # Clean implementation focused on command extraction logic
    return TerminalContext(commands=extracted_commands)
```

#### Generated Metrics

Git operation instrumentation automatically generates:

**Duration Metrics:**
- `mcp.journal.git_context.duration` - Git context collection timing
- `mcp.journal.chat_history.duration` - Chat history collection timing  
- `mcp.journal.terminal_commands.duration` - Terminal command collection timing

**Performance Metrics:**
- `git_context_slow_operation` - When operations exceed configured thresholds
- `files_processed` - Number of files analyzed per operation
- `memory_usage_mb` - Memory consumption during large repository operations

**Error Metrics:**
- `mcp.journal.errors.by_type{error_type="git"}` - Git-specific errors
- `mcp.journal.errors.by_type{error_type="filesystem"}` - File system errors
- `mcp.journal.errors.by_type{error_type="memory"}` - Memory-related errors

#### Performance Optimizations

The instrumentation includes built-in performance optimizations:

```python
# Large repository handling
if total_file_count > PERFORMANCE_THRESHOLDS["detailed_analysis_file_count_limit"]:
    # Automatically truncates analysis for commits with >100 files
    changed_files = all_changed_files[:10]
    
# Smart file sampling  
sampled_files = smart_file_sampling(all_changed_files)
# Prioritizes source code files (.py, .js, .ts) and large files
# Samples 20% of other file types for repos with >50 files

# Memory tracking
with memory_tracking_context("git_context_collection") as memory_snapshot:
    # Only records metrics if memory increase exceeds 50MB threshold
```

#### Error Handling Examples

**Repository Access Errors:**
```python
# Automatic categorization and metrics recording
try:
    context = collect_git_context("invalid_commit_hash")
except git.BadName as e:
    # Automatically categorized as "git" error
    # Metrics: git_context_operation{success=false, error_type="git"}
    # Span status: ERROR with sanitized error message
```

**Timeout Protection:**
```python
# Configurable timeouts with graceful degradation
@trace_git_operation("git_context", timeout_seconds=5.0)
def collect_git_context(commit_hash=None):
    # If operation takes >5 seconds, TimeoutError is raised
    # Metrics: git_context_operation{success=false, error_type="timeout"}
```

#### Memory Usage Monitoring

```python
# Strategic memory sampling at operation boundaries
def memory_tracking_context(operation_name: str, baseline_threshold_mb: float = 50.0):
    """Only records metrics when memory increase exceeds threshold."""
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    yield
    final_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    if (final_memory - initial_memory) > baseline_threshold_mb:
        # Record memory usage metrics
        metrics.set_memory_usage_mb(final_memory, operation=operation_name)
```

#### Configuration Options

Git operation instrumentation can be configured through telemetry settings:

```yaml
telemetry:
  enabled: true
  git_operations:
    performance_thresholds:
      collect_git_context_slow_seconds: 2.0
      journal_generation_slow_seconds: 10.0
      file_processing_slow_per_10_files_seconds: 1.0
    sampling:
      large_repo_file_count: 50
      detailed_analysis_file_count_limit: 100
      file_sampling_percentage: 0.2
    memory_tracking:
      threshold_mb: 50.0
    timeouts:
      git_operation_timeout_seconds: 5.0
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

## Journal Operations Instrumentation

The journal management system includes comprehensive OpenTelemetry instrumentation for observability into AI-driven content generation and file operations.

### Instrumented Operations

#### File Operations
All journal file operations are traced and measured:

```python
from mcp_commit_story.journal import append_to_journal_file, get_journal_file_path

# File path generation with telemetry
file_path = get_journal_file_path("daily", "2025-05-31")
# Span: journal.get_file_path
# Attributes: journal.entry_type, journal.date, file.name, directory.name

# File writing with metrics
append_to_journal_file(content, file_path)
# Span: journal.append_file  
# Metrics: journal.file_write_duration_seconds, journal.file_write_total
# Attributes: file.path, file.extension, journal.content_length, file.size_bytes
```

#### AI Generation Operations
All AI content generation functions are instrumented:

```python
from mcp_commit_story.journal import generate_summary_section

# AI generation with context tracking
summary = generate_summary_section(journal_context)
# Span: journal.generate_summary
# Metrics: journal.ai_generation_duration_seconds
# Attributes: journal.context_size, journal.entry_id, section_type="summary"
```

#### Reading Operations
Journal parsing and serialization operations:

```python
from mcp_commit_story.journal import JournalParser, JournalEntry

# Parse journal content
entry = JournalParser.parse(markdown_content)
# Span: journal.parse_entry
# Metrics: journal.parse_duration_seconds, journal.parse_operations_total
# Attributes: journal.content_length, journal.sections_parsed, journal.entry_id

# Serialize to markdown
markdown = entry.to_markdown()
# Span: journal.serialize_entry
# Metrics: journal.serialize_duration_seconds, journal.serialize_operations_total
# Attributes: journal.entry_id, journal.output_length
```

### Journal-Specific Metrics

#### Duration Histograms
- `journal.file_write_duration_seconds`: File write operation latency
- `journal.ai_generation_duration_seconds`: AI content generation time (labeled by section_type)
- `journal.directory_operation_duration_seconds`: Directory creation/validation time
- `journal.parse_duration_seconds`: Journal content parsing time
- `journal.serialize_duration_seconds`: Journal entry serialization time
- `journal.config_load_duration_seconds`: Configuration loading time
- `journal.path_generation_duration_seconds`: File path generation time

#### Operation Counters
- `journal.file_write_total`: File write operations (success/failure)
- `journal.generation_operations_total`: AI generation operations by section type
- `journal.directory_operations_total`: Directory operations (success/failure)
- `journal.parse_operations_total`: Journal parsing operations
- `journal.serialize_operations_total`: Journal serialization operations
- `journal.config_load_operations_total`: Configuration loading operations
- `journal.path_generation_operations_total`: Path generation operations

### Semantic Conventions

#### Standard Attributes
- `operation_type`: Type of operation (file_write, ai_generation, parse, etc.)
- `file_type`: File format (markdown, toml, etc.)
- `section_type`: Journal section being generated (summary, technical_synopsis, etc.)

#### Journal-Specific Attributes
- `journal.entry_id`: Commit hash or unique identifier for the journal entry
- `journal.entry_type`: Type of journal entry (daily, feature, etc.)
- `journal.date`: Date associated with the journal entry
- `journal.context_size`: Size of context provided to AI generation
- `journal.content_length`: Length of content being processed
- `journal.output_length`: Length of generated output
- `journal.sections_parsed`: Number of sections successfully parsed

#### Privacy-Conscious Attributes
- `file.name`: Filename only (not full path) for privacy
- `directory.name`: Directory name only (not full path)
- `config.file_path`: Basename only for configuration files

#### Error Classification
- `error.category`: Categorized error types:
  - `permission_denied_file`: File permission errors
  - `permission_denied_directory`: Directory permission errors
  - `file_not_found`: Missing file errors
  - `empty_content`: Empty or invalid content
  - `invalid_format`: Parsing format errors
  - `ai_generation_failed`: AI generation errors
  - `serialization_failed`: Serialization errors
  - `config_load_failed`: Configuration loading errors

### Sensitive Data Protection

The journal instrumentation includes comprehensive sensitive data filtering:

#### Automatic Sanitization
All span attributes are automatically sanitized using `sanitize_for_telemetry()`:

```python
# Git information (preserves first 8 chars for debugging)
"abc123def456..." → "abc123de..."

# URLs and query parameters  
"https://api.example.com?token=secret123&user=john" → "https://api.example.com?token=***&***"

# File paths (preserves structure, obscures specifics)
"/home/user/project/src/file.py" → "/****/file.py"

# Email addresses (preserves domain)
"user@example.com" → "***@example.com"

# API keys and tokens
"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." → "Bearer ***"
```

#### Protected Information Types
- Git commit hashes, branch names
- URLs with query parameters and auth tokens
- Database connection strings
- File content metadata and paths
- Personal information (emails, IPs, phone numbers)
- Authentication data (API keys, JWTs, UUIDs)
- Environment variables with sensitive names

### Performance Monitoring

#### Overhead Thresholds
The instrumentation is designed to meet strict performance criteria:
- **Individual operations**: ≤5% overhead
- **Batch operations**: ≤10% overhead
- **Concurrent operations**: Minimal contention

#### Performance Metrics
Monitor telemetry impact using these metrics:
```python
# Check operation overhead
baseline_time = measure_without_telemetry()
instrumented_time = measure_with_telemetry()
overhead_percent = ((instrumented_time - baseline_time) / baseline_time) * 100

# Should be ≤5% for individual operations, ≤10% for batch
assert overhead_percent <= 5.0  # Individual operations
assert overhead_percent <= 10.0  # Batch operations
```

### Usage Examples

#### Basic Journal Operation Monitoring
```python
from mcp_commit_story.telemetry import get_mcp_metrics
from mcp_commit_story.journal import append_to_journal_file

# Get metrics instance
metrics = get_mcp_metrics()

# Perform journal operation (automatically instrumented)
append_to_journal_file("Journal content", "/path/to/journal.md")

# Check metrics
metric_data = metrics.get_metric_data()
print(f"File writes: {metric_data['journal.file_write_total']}")
```

#### AI Generation Monitoring
```python
from mcp_commit_story.journal import generate_summary_section

# Generate content (automatically traced and measured)
journal_context = {"chat_history": {...}, "terminal_context": {...}}
summary = generate_summary_section(journal_context)

# Metrics automatically recorded:
# - journal.ai_generation_duration_seconds (histogram)
# - journal.generation_operations_total (counter)
# Span attributes include context_size, entry_id, section_type
```

#### Error Monitoring
```python
from opentelemetry import trace

# Errors are automatically captured in spans
try:
    append_to_journal_file(content, "/invalid/path")
except Exception as e:
    # Span automatically includes:
    # - error.category: "permission_denied_file"
    # - error.message: sanitized error message
    # - span status: ERROR
    pass
```

### Integration with Observability Platforms

#### Honeycomb Query Examples
```sql
-- AI generation performance by section type
SELECT AVG(duration_ms), section_type 
FROM spans 
WHERE name = "journal.generate_*" 
GROUP BY section_type

-- File operation error rates
SELECT COUNT(*) as errors, error.category
FROM spans 
WHERE name LIKE "journal.*" AND status = "ERROR"
GROUP BY error.category

-- Journal processing pipeline
SELECT trace_id, name, duration_ms
FROM spans 
WHERE trace_id IN (
  SELECT trace_id FROM spans WHERE name = "journal.append_file"
)
ORDER BY start_time
```

#### Grafana Dashboard Queries
```promql
# AI generation latency by section type
histogram_quantile(0.95, 
  rate(journal_ai_generation_duration_seconds_bucket[5m])
) by (section_type)

# File operation success rate
rate(journal_file_write_total{success="true"}[5m]) / 
rate(journal_file_write_total[5m])

# Journal processing throughput
rate(journal_generation_operations_total[5m])
```

### Best Practices for Journal Operations

#### Context Correlation
- Journal entries are correlated using `journal.entry_id` (typically commit hash)
- AI generation operations include `journal.context_size` for performance analysis
- File operations include size metrics for capacity planning

#### Error Handling
- All errors are categorized for easier analysis
- Sensitive information is automatically filtered from error messages
- Span status reflects operation success/failure

#### Performance Optimization
- Use `journal.context_size` to identify oversized AI contexts
- Monitor `journal.ai_generation_duration_seconds` for performance regressions
- Track file operation metrics for I/O bottleneck identification

#### Security Considerations
- File paths are sanitized to show only filenames
- Configuration data is filtered for sensitive values
- AI context content is not logged directly (only size metrics) 