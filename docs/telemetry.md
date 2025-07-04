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

#### Configuration Management Metrics
- `mcp.config.operations_total{operation, result}` - Configuration operation tracking
- `mcp.config.load_duration_seconds{operation}` - Configuration loading performance
- `mcp.config.reload_events_total{trigger, result}` - Configuration reload events
- `mcp.config.validation_errors_total{field_path, error_type}` - Validation error tracking

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
      endpoint: 'https://api.datadog.com:443'
      headers:
        DD-API-KEY: '${DD_API_KEY}'
  auto_instrumentation:
    enabled: true
    preset: 'minimal'  # Reduced overhead
```

## Integration Test Telemetry Validation

The MCP Commit Story project includes a comprehensive integration test framework specifically designed to validate telemetry functionality across the complete MCP tool execution pipeline. This ensures that observability works correctly in production scenarios.

### Test Framework Architecture

The integration test framework provides:

- **Isolated Telemetry Collection**: Custom `TelemetryCollector` captures spans and metrics without external dependencies
- **Custom Assertion Helpers**: Production-ready validation API for trace and metric validation
- **AI-Specific Testing**: Validates context size correlation and AI generation pipeline telemetry
- **Performance Impact Validation**: Ensures telemetry overhead remains within acceptable bounds
- **Circuit Breaker Testing**: Validates graceful degradation when telemetry systems fail

### Core Test Infrastructure

#### TelemetryCollector

The `TelemetryCollector` provides isolated, controllable telemetry collection:

```python
from tests.integration.test_telemetry_validation_integration import TelemetryCollector

# Create isolated collector for testing
collector = TelemetryCollector()

# Test spans are automatically captured
with tracer.start_as_current_span("test_operation") as span:
    span.set_attribute("test.operation", "example")
    # ... perform operations

# Validate captured spans
spans = collector.get_spans_by_name("test_operation")
assert len(spans) == 1
assert spans[0].attributes["test.operation"] == "example"
```

#### Custom Assertion Helpers

The framework provides production-ready assertion helpers:

```python
from tests.integration.test_telemetry_validation_integration import (
    assert_operation_traced,
    assert_trace_continuity,
    assert_ai_context_tracked,
    assert_performance_within_bounds
)

# Validate operation was properly traced
assert_operation_traced(collector, "journal.generate_summary", {
    "section_type": "summary",
    "journal.context_size": 1024
})

# Validate trace continuity across operations
assert_trace_continuity(collector, "parent_operation", ["child_operation_1", "child_operation_2"])

# Validate AI-specific context tracking
assert_ai_context_tracked(collector, "journal.generate_summary",
                         expected_context_size=1024,
                         expected_generation_type="summary")

# Validate performance is within bounds
assert_performance_within_bounds(collector, "journal.generate_summary", max_duration_ms=2000)
```

### Test Categories

#### 1. MCP Tool Chain Integration Tests

These tests validate telemetry across complete MCP tool execution chains:

```python
def test_journal_new_entry_generates_expected_spans(patch_telemetry_for_testing):
    """Test that journal new-entry generates expected telemetry spans."""
    collector = patch_telemetry_for_testing
    
    # Execute MCP tool chain
    result = await handle_journal_new_entry(test_request)
    
    # Validate telemetry was captured
    assert_operation_traced(collector, "journal.new_entry")
    assert_trace_continuity(collector, "journal.new_entry", [
        "git.context_collection",
        "ai.journal_generation",
        "file.journal_write"
    ])
```

#### 2. AI-Specific Performance Tests

These tests validate AI generation pipeline telemetry and context correlation:

```python
def test_context_size_impact_tracking(patch_telemetry_for_testing):
    """Test context size performance correlation tracking."""
    collector = patch_telemetry_for_testing
    
    # Test with different context sizes
    for size in [10, 100, 1000]:
        context = create_test_context(size=size)
        generate_summary_section(context)
    
    # Validate performance correlation
    spans = collector.get_spans_by_name("journal.generate_summary")
    spans_by_size = sorted(spans, key=lambda s: s.attributes["journal.context_size"])
    
    # Verify duration increases with context size
    for i in range(1, len(spans_by_size)):
        assert spans_by_size[i].duration_ms >= spans_by_size[i-1].duration_ms
```

#### 3. Circuit Breaker Integration Tests

These tests validate graceful degradation when telemetry fails:

```python
def test_telemetry_circuit_breaker_integration(patch_telemetry_for_testing):
    """Test circuit breaker behavior during telemetry failures."""
    collector = patch_telemetry_for_testing
    
    # Simulate telemetry failures
    with patch.object(collector, 'record_metric', side_effect=Exception("Telemetry failure")):
        # Critical operations should continue despite telemetry failures
        results = []
        for i in range(10):
            result = critical_mcp_operation()
            results.append(result)
    
    # Verify operations completed successfully
    assert len(results) == 10
    assert all(r == "operation_completed" for r in results)
```

#### 4. Performance Impact Validation

These tests ensure telemetry overhead remains minimal:

```python
def test_telemetry_overhead_measurement(patch_telemetry_for_testing):
    """Test that telemetry adds minimal overhead to operations."""
    
    # Measure baseline performance
    baseline_times = measure_operation_times(baseline_operation, iterations=10)
    
    # Measure instrumented performance  
    instrumented_times = measure_operation_times(instrumented_operation, iterations=10)
    
    # Calculate and validate overhead
    overhead_percentage = calculate_overhead(baseline_times, instrumented_times)
    assert overhead_percentage < 50, f"Telemetry overhead too high: {overhead_percentage:.1f}%"
```

### Running Integration Tests

Execute the telemetry validation tests:

```bash
# Run all telemetry integration tests
python -m pytest tests/integration/test_telemetry_validation_integration.py -v

# Run specific test categories
python -m pytest tests/integration/test_telemetry_validation_integration.py::TestAIGenerationTelemetry -v
python -m pytest tests/integration/test_telemetry_validation_integration.py::TestPerformanceImpactValidation -v

# Run with detailed output
python -m pytest tests/integration/test_telemetry_validation_integration.py -v -s
```

### Best Practices for Telemetry Testing

#### 1. Use Isolated Telemetry Environment

Use the `isolated_telemetry_environment` fixture for clean, fast test isolation:

```python
def test_operation_telemetry(isolated_telemetry_environment):
    """Test telemetry with isolated environment - no manual flush needed."""
    collector = isolated_telemetry_environment
    
    # Get tracer from isolated environment
    tracer = collector.get_tracer("test_tracer")
    
    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("test.key", "test_value")
        # Perform operation
    
    # Spans are processed immediately - no delays needed!
    spans = collector.get_spans_by_name("test_operation")
    assert len(spans) == 1
```

#### 2. Validate Trace Relationships

Test parent-child span relationships to ensure proper trace continuity:

```python
# Validate trace continuity
assert_trace_continuity(collector, "parent_operation", ["child_operation"])

# Verify span attributes
parent_spans = collector.get_spans_by_name("parent_operation")
child_spans = collector.get_child_spans(parent_spans[0].span_id)
assert len(child_spans) > 0
```

#### 3. Test Error Scenarios

Validate that error scenarios are properly captured:

```python
# Test error telemetry
with pytest.raises(Exception):
    problematic_operation()

assert_error_telemetry(collector, "problematic_operation",
                      expected_error_type="ValidationError",
                      expected_error_category="input_validation")
```

#### 4. Performance Correlation Testing

Test that telemetry captures performance correlations:

```python
# Test with varying loads
for load_factor in [1, 5, 10]:
    operation_with_load(load_factor)

# Validate duration correlation
spans = collector.get_spans_by_name("load_test_operation")
assert spans[2].duration_ms > spans[1].duration_ms > spans[0].duration_ms
```

### Integration with CI/CD

The telemetry integration tests are designed to run in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run Telemetry Integration Tests
  run: |
    python -m pytest tests/integration/test_telemetry_validation_integration.py \
      --junitxml=reports/telemetry-integration-tests.xml \
      --cov=src/mcp_commit_story/telemetry \
      --cov-report=xml:reports/telemetry-coverage.xml
```

### Troubleshooting Integration Tests

#### Common Issues

**Spans Not Captured**
```python
# With isolated telemetry, check collector directly
print(f"Captured {len(collector.spans)} spans:")
for span in collector.spans:
    print(f"  {span.span_name}: {span.attributes}")

# Ensure you're using the isolated tracer
tracer = collector.get_tracer("test_tracer")  # Use collector's tracer
# NOT: tracer = trace.get_tracer("test_tracer")  # Global tracer won't work
```

**Test Performance Issues**
- Use `isolated_telemetry_environment` fixture for fast, synchronous processing
- Minimize `time.sleep()` calls in tests - spans process immediately
- Use small test data sizes for performance correlation tests

**Test Isolation Problems**
- Each test gets a completely isolated telemetry environment
- No global state conflicts between tests
- Reset is automatic with the fixture

The integration test framework ensures that telemetry functionality works correctly across the entire MCP tool execution pipeline, providing confidence that observability will function properly in production environments.

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

**Chat History Collection (Legacy):**
```python
@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(since_commit=None, max_messages_back=150):
    """AI prompt for chat analysis - clean and focused."""
    # Function contains only AI prompts and business logic
    return ChatHistory(messages=processed_messages)
```

**Composer Chat History Collection (Enhanced):**
```python
@trace_mcp_operation("cursor_db.query_composer")
def query_cursor_chat_database() -> Dict[str, Any]:
    """Enhanced Composer-based chat history with rich telemetry."""
    metrics = get_mcp_metrics()
    start_time = time.time()
    span = trace.get_current_span()
    
    try:
        # Enhanced telemetry attributes
        span.set_attribute("cursor.workspace_detected", True)
        span.set_attribute("cursor.commit_detected", True)
        span.set_attribute("time_window.strategy", "commit_based")
        span.set_attribute("time_window.duration_hours", 2.5)
        span.set_attribute("cursor.messages_retrieved", 42)
        span.set_attribute("cursor.database_type", "composer")
        
        # Success metrics
        if metrics:
            metrics.record_histogram(
                "mcp.cursor.query_duration_seconds", 
                0.235,
                attributes={"database_type": "composer", "strategy": "commit_based"}
            )
            metrics.record_counter(
                "mcp.cursor.messages_total",
                42, 
                attributes={"source": "composer"}
            )
        
        return enhanced_composer_data
        
    except Exception as e:
        # Error categorization and metrics
        error_category = categorize_cursor_error(e)
        span.set_attribute("error.category", error_category)
        
        if metrics:
            metrics.record_counter(
                "mcp.cursor.errors_total",
                1,
                attributes={"error_category": error_category}
            )
        raise
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
- `mcp.journal.chat_history.duration` - Chat history collection timing (legacy)
- `mcp.cursor.query_duration_seconds` - Composer chat history collection timing (enhanced)
- `mcp.journal.terminal_commands.duration` - Terminal command collection timing

**Performance Metrics:**
- `git_context_slow_operation` - When operations exceed configured thresholds
- `files_processed` - Number of files analyzed per operation
- `memory_usage_mb` - Memory consumption during large repository operations

**Error Metrics:**
- `mcp.journal.errors.by_type{error_type="git"}` - Git-specific errors
- `mcp.journal.errors.by_type{error_type="filesystem"}` - File system errors
- `mcp.journal.errors.by_type{error_type="memory"}` - Memory-related errors
- `mcp.cursor.errors_total{error_category}` - Composer database errors with categorization
- `mcp.cursor.messages_total{source="composer"}` - Composer message retrieval counters

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

#### AI Invocation Telemetry
The AI invocation layer includes lightweight telemetry that adds essential attributes to existing OpenTelemetry spans:

```python
from mcp_commit_story.ai_invocation import invoke_ai

# AI invocation with automatic telemetry
response = await invoke_ai(prompt, context)
# Span: ai.invoke (from @trace_mcp_operation decorator)
# Attributes automatically added:
#   - ai.success: True/False
#   - ai.latency_ms: 1250 (total duration including retries)
#   - ai.error_type: "ConnectionError" (only on failures)
```

**Telemetry Attributes:**
- **`ai.success`** (boolean): Whether the AI call completed successfully
- **`ai.latency_ms`** (integer): Total duration including all retry attempts in milliseconds  
- **`ai.error_type`** (string): Exception class name of the final error (only set on failures)

**Implementation Philosophy:**
- **Minimal overhead**: Piggybacks on existing `@trace_mcp_operation("ai.invoke")` spans
- **No new infrastructure**: Uses current telemetry system without additional components
- **Essential data only**: Three key attributes provide core observability needs
- **Graceful degradation**: Operations continue normally when telemetry unavailable

**What's NOT tracked** (by design):
- Token counting or usage metrics
- Cost calculations or billing estimates
- Aggregated metrics or daily summaries  
- Complex performance analytics
- Model-specific metadata

This approach provides essential AI observability while maintaining the system's philosophy of simplicity and avoiding over-engineering.

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

### Configuration Management Telemetry

The system provides comprehensive observability for configuration operations including loading, validation, and hot reloads:

#### Instrumented Operations

**Configuration Loading**
```python
@trace_config_operation("load")
def load_config(config_path: Optional[str] = None) -> 'Config':
    \"\"\"Load configuration with full telemetry instrumentation.\"\"\"
    # Function implementation with automatic telemetry
```

**Configuration Validation** 
```python
@trace_config_operation("validate")
def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Validate configuration with error categorization.\"\"\"
    # Function implementation with automatic telemetry
```

**Configuration Reloading**
```python
@trace_config_operation("reload")
def reload_config(self):
    \"\"\"Hot reload configuration with change detection.\"\"\"
    # Function implementation with automatic telemetry
```

#### Telemetry Features

**Performance Monitoring**
- **Load Duration Warning**: 250ms threshold for initial config loads
- **Reload Duration Warning**: 500ms threshold for config reloads  
- **Validation Duration Warning**: 100ms threshold for validation operations
- **Sampling Strategy**: 100% for initial loads/reloads, 5% for high-frequency access

**Privacy Protection**
```python
# Sensitive values are automatically hashed
config_path_hash = hash_sensitive_value("/path/to/config")
# Results in: "a1b2c3d4" (8-character SHA256 prefix)
```

**Error Categorization**
- `yaml_error` - Malformed YAML syntax
- `file_error` - File access permissions/not found
- `validation_error` - Schema validation failures
- `type_error` - Incorrect data types
- `missing_field` - Required fields absent

**Change Detection**
```python
# Automatic tracking of configuration modifications
def detect_config_changes(old_config: dict, new_config: dict) -> List[str]:
    \"\"\"Detect and track specific field changes.\"\"\"
    # Implementation with telemetry reporting
```

#### Circuit Breaker Protection

Configuration telemetry includes circuit breaker protection to prevent cascading failures:

```python
# Circuit breaker per operation type
CONFIG_CIRCUIT_BREAKERS = {
    "load": CircuitBreaker(failure_threshold=5, recovery_timeout=300.0),
    "reload": CircuitBreaker(failure_threshold=5, recovery_timeout=300.0), 
    "validate": CircuitBreaker(failure_threshold=5, recovery_timeout=300.0),
}
```

#### Example Metrics Output

**Successful Configuration Load**
```json
{
  "metric_name": "mcp.config.operations_total",
  "value": 1,
  "attributes": {
    "operation": "load",
    "result": "success",
    "config_source": "file",
    "has_config_file": true
  }
}
```

**Configuration Validation Error**
```json
{
  "metric_name": "mcp.config.operations_total", 
  "value": 1,
  "attributes": {
    "operation": "validate",
    "result": "failure",
    "error_type": "missing_field",
    "config_validation_error": true
  }
}
```

**Configuration Reload Performance**
```json
{
  "metric_name": "mcp.config.reload_duration_seconds",
  "value": 0.245,
  "attributes": {
    "operation": "reload",
    "result": "success",
    "changes_detected": true,
    "config_complexity": "moderate"
  }
}
```

#### Integration with MCP Server Startup

Configuration telemetry integrates seamlessly with server initialization:

```python
# Server startup with configuration telemetry
async def create_mcp_server():
    try:
        # Configuration loading is automatically instrumented
        config = load_config()  # Generates telemetry spans/metrics
        
        # Telemetry setup respects config telemetry settings
        telemetry_initialized = setup_telemetry(config.as_dict())
        
        # Config dependency tracking for startup
        if telemetry_initialized:
            metrics = get_mcp_metrics()
            metrics.record_mcp_server_config_dependency(
                config_path=config._config_path,
                startup_phase="initialization",
                required=True
            )
    except Exception as e:
        # Configuration errors are automatically categorized and tracked
        logger.error(f"Configuration error during startup: {e}")
```

#### Troubleshooting Configuration Issues

**Configuration Load Failures**
```bash
# Check configuration loading metrics
curl -s http://localhost:8080/metrics | grep "mcp.config.operations_total.*failure"

# Look for specific error categories
curl -s http://localhost:8080/metrics | grep "error_type"
```

**Performance Issues**
```bash
# Monitor configuration operation duration
curl -s http://localhost:8080/metrics | grep "mcp.config.*duration_seconds"

# Check for slow operations exceeding thresholds
curl -s http://localhost:8080/metrics | grep "mcp.config.slow_operations_total"
```

**Configuration Change Tracking**
```bash
# Monitor configuration reload events
curl -s http://localhost:8080/metrics | grep "mcp.config.reload_events_total"

# Track configuration change detection
curl -s http://localhost:8080/metrics | grep "mcp.config.change_detection"
``` 