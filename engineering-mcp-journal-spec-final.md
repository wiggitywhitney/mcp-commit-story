# Commit Story MCP Server — Complete Developer Specification

## Table of Contents

1. [Overview](#overview)
2. [Goals](#goals)
3. [MCP Server Configuration and Integration](#mcp-server-configuration-and-integration)
4. [Technology Stack](#technology-stack)
   - [Core Technologies](#core-technologies)
   - [Project Structure](#project-structure)
   - [Development Methodology](#development-methodology)
   - [Dependencies](#dependencies)
5. [Implementation](#implementation)
   - [MCP Server Overview](#mcp-server-overview)
   - [Core Components](#core-components)
   - [File Structure](#file-structure)
   - [Configuration](#configuration)
   - [AI Tone/Style Configuration](#ai-tonestyle-configuration)
   - [On-Demand Directory Creation Pattern](#on-demand-directory-creation-pattern)
   - [Telemetry and Observability](#telemetry-and-observability)
6. [Journal Entry Behavior](#journal-entry-behavior)
   - [Triggering](#triggering)
   - [Chat History Collection Method](#chat-history-collection-method)
   - [Data Sources](#data-sources)
   - [History Collection Boundaries](#history-collection-boundaries)
   - [Anti-Hallucination Rules](#anti-hallucination-rules)
   - [Recursion Prevention](#recursion-prevention)
   - [Journal Entry Structure](#journal-entry-structure-canonical-format)
   - [Content Quality Guidelines](#content-quality-guidelines)
7. [MCP Server Implementation](#mcp-server-implementation)
   - [MCP Operations](#mcp-operations)
   - [Operation Details](#operation-details)
   - [Data Formats](#data-formats)
8. [CLI Interface (Setup Only)](#cli-interface-setup-only)
   - [Architectural Change](#architectural-change)
   - [Setup CLI Commands](#setup-cli-commands)
   - [MCP Operations (Primary Interface)](#mcp-operations-primary-interface)
   - [Usage Pattern](#usage-pattern)
   - [Global Options](#global-options)
9. [Data Handling Details](#data-handling-details)
   - [File Organization](#file-organization)
   - [Diff Processing](#diff-processing)
   - [Date/Time Handling](#datetime-handling)
10. [Error Handling](#error-handling)
    - [Hard Failures (Fail Fast)](#hard-failures-fail-fast)
    - [Soft Failures (Silent Skip)](#soft-failures-silent-skip)
    - [Error Messages](#error-messages)
    - [Debug Mode](#debug-mode)
    - [Graceful Degradation Philosophy](#graceful-degradation-philosophy)
11. [Git Integration](#git-integration)
    - [Hook Installation](#hook-installation)
    - [Backfill Mechanism](#backfill-mechanism)
    - [Commit Processing](#commit-processing)
    - [Post-Commit Hook Content Generation](#post-commit-hook-content-generation-engineering-spec)
    - [Post-Commit Hook Installation Core Logic](#post-commit-hook-installation-core-logic)
12. [Testing Plan](#testing-plan)
    - [Current Testing Status](#current-testing-status)
    - [Test Organization](#test-organization)
    - [Comprehensive Documentation Coverage](#comprehensive-documentation-coverage)
    - [Unit Tests](#unit-tests)
    - [Integration Tests](#integration-tests)
    - [Test Fixtures](#test-fixtures)
    - [Test Utilities](#test-utilities)
    - [Hook Execution Testing](#hook-execution-testing)
13. [Implementation Guidelines](#implementation-guidelines)
    - [Code Organization](#code-organization)
    - [Chat History Processing](#chat-history-processing)
    - [AI Terminal History Collection](#ai-terminal-history-collection)
    - [Implementation Pattern](#implementation-pattern)
    - [Dependencies](#dependencies-1)
    - [Performance Considerations](#performance-considerations)
    - [Security](#security)
14. [Future Enhancements (Out of Scope for MVP)](#future-enhancements-out-of-scope-for-mvp)
    - [Potential Features](#potential-features)
    - [Integration Opportunities](#integration-opportunities)
    - [Hyperlinked Commit Hashes](#hyperlinked-commit-hashes-in-journal-entries)
    - [Configurable AI Tone/Style](#configurable-ai-tonestyle-for-summaries)
    - [Tagging system for entries and content organization](#tagging-system-for-entries-and-content-organization)
15. [Final Notes](#final-notes)
    - [Success Criteria](#success-criteria)
    - [Development Workflow](#development-workflow)
    - [Initialization Workflow](#initialization-workflow)
    - [Context Data Structures](#context-data-structures)

---

## Overview
This document specifies a Model Context Protocol (MCP) server designed to capture and generate engineering journal entries within a code repository. The journal records commits, technical progress, decision-making context, and emotional tone, with the goal of producing content that can be analyzed for patterns and reused for storytelling (e.g., blog posts, conference talks).

## Goals
- Record accurate, structured engineering activity and emotional context
- Enable narrative storytelling across daily, weekly, and monthly timelines
- Identify patterns and trends in development work over time
- Keep entries truthful (anti-hallucination), useful, and minimally intrusive
- Integrate seamlessly with Git workflows and existing dev tools

## MCP Server Configuration and Integration

The MCP server must be launchable as a standalone process and expose the required journal operations (e.g., `journal/new-entry`, `journal/summarize`, etc.) as specified in this document. The server should be discoverable by compatible clients (such as AI-powered editors, agents, or other tools) via a standard configuration mechanism.

- **Server Launch:**
  - The method for launching the MCP server is not prescribed by this specification. It may be started via a CLI command, Python entry point, or any other mechanism appropriate to the environment.
  - The server must remain running and accessible to clients for the duration of its use.

- **Client/Editor Integration:**
  - Clients (such as editors or agents) should be able to connect to the MCP server using a configuration block similar to the following:

```json
{
  "mcpServers": {
    "mcp-commit-story": {
      "command": "<launch command>",
      "args": ["<arg1>", "<arg2>", ...],
      "env": {
        "ANTHROPIC_API_KEY": "<optional>"
      }
    }
  }
}
```
  - The actual command, arguments, and environment variables will depend on the deployment and are not specified here.
  - Environment variables such as API keys may be required if the underlying MCP SDK or AI provider requires them, but are not strictly necessary for local operation unless needed by dependencies.

- **Separation of Concerns:**
  - The MCP server configuration (how it is launched and discovered) is separate from the journal system's own configuration, which is managed via `.mcp-commit-storyrc.yaml` as described elsewhere in this specification.

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.9+
- **MCP Framework**: Official Anthropic MCP Python SDK
- **CLI Framework**: Click (for command parsing and user interface)
- **Configuration**: PyYAML (for .mcp-commit-storyrc.yaml files)
- **Git Integration**: GitPython library
- **File I/O**: Standard library (pathlib, datetime)
- **Testing**: pytest for unit/integration tests
- **Observability**: OpenTelemetry for distributed tracing, metrics collection, and structured logging with trace correlation

### Project Structure
```
mcp-commit-story/
├── src/
│   └── mcp_commit_story/
│       ├── __init__.py
│       ├── cli.py              # Click commands
│       ├── server.py           # MCP server implementation  
│       ├── journal.py          # Core journal functions and classes
│       ├── journal_workflow.py # Journal entry workflow orchestration
│       ├── git_utils.py        # Git operations
│       ├── telemetry.py        # OpenTelemetry setup and utilities
│       └── config.py           # Configuration handling
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── pyproject.toml       # Modern Python packaging
├── README.md
└── .mcp-commit-storyrc.yaml  # Default config
```

### Development Methodology
- **Test-Driven Development (TDD)** - Write tests first, then implementation
- Write failing tests → Implement minimal code → Refactor
- Maintain high test coverage (>90%)
- Test all MCP operations and CLI commands

### Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.9"
mcp = "^1.0.0"  # Official MCP Python SDK
click = "^8.0.0"
pyyaml = "^6.0"
gitpython = "^3.1.0"
python-dateutil = "^2.8.0"
opentelemetry-api = "^1.15.0"
opentelemetry-sdk = "^1.15.0"
opentelemetry-exporter-otlp = "^1.15.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-mock = "^3.10.0"
pytest-cov = "^4.0.0"  # Coverage reporting
pytest-watch = "^4.2.0"  # TDD friendly test runner
black = "^23.0.0"
flake8 = "^6.0.0"
mypy = "^1.0.0"
```

---

## Implementation

### MCP Server Overview
- Build standard MCP server using Anthropic's Python SDK
- Register tools for each journal operation (new-entry, summarize, etc.)
- Handle async operations for file I/O and git commands
- Return structured responses with success status and file paths
- Instrument key operations with OpenTelemetry for tracing and performance insights

### Core Components
```
src/mcp_commit_story/
├── __init__.py
├── cli.py              # Click commands
├── server.py           # MCP server implementation  
├── journal.py          # Core journal functions and classes
├── journal_workflow.py # Journal entry workflow orchestration
├── git_utils.py        # Git operations
├── telemetry.py        # OpenTelemetry setup and utilities
└── config.py           # Configuration handling
```

#### Module Architecture

The journal system follows a modular architecture with clear separation of concerns:

**journal.py** - Core journal functionality:
- `JournalEntry` class for structured representation
- `JournalParser` for parsing Markdown back to structured data
- Section generator functions for AI-powered content creation
- File operations for reading/writing journal files
- Utilities for configuration and telemetry

**journal_workflow.py** - Workflow orchestration:
- `generate_journal_entry()` - Main workflow function that orchestrates complete journal entry generation
- `save_journal_entry()` - Saves generated journal entries to daily files with proper header formatting
- `handle_journal_entry_creation()` - End-to-end workflow combining generation and saving for MCP tools
- `is_journal_only_commit()` - Detects commits that only modify journal files to prevent infinite loops
- Context collection integration to gather all necessary data
- Section generation coordination to call all AI generation functions
- Error handling and graceful degradation for robust operation
- Cross-platform timestamp formatting and file path handling

This separation follows the single responsibility principle and makes the codebase easier to maintain and test.

### File Structure
```
journal/
├── daily/
│   ├── 2025-05-14.md
│   ├── 2025-05-15.md
│   └── ...
├── summaries/
│   ├── daily/
│   │   ├── 2025-05-14-summary.md
│   │   └── ...
│   ├── weekly/
│   │   ├── 2025-05-week3.md
│   │   └── ...
│   ├── monthly/
│   │   ├── 2025-05.md
│   │   └── ...
│   └── yearly/
│       ├── 2025.md
│       └── ...
└── .mcp-commit-storyrc.yaml
```

### Configuration
Configurable via a `.mcp-commit-storyrc.yaml` file at repo root. Global defaults supported via `~/.mcp-commit-storyrc.yaml`.

#### Configuration Precedence
1. Local config (`.mcp-commit-storyrc.yaml` in repo root)
2. Global config (`~/.mcp-commit-storyrc.yaml`)
3. Built-in defaults

#### Configuration Validation
- Missing/invalid fields use defaults and continue with warnings
- Malformed YAML logs error but continues with defaults
- Invalid sections are ignored with warnings

#### Example Configuration:
```yaml
journal:
  path: journal/
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true

# Minimal telemetry configuration
telemetry:
  enabled: true                 # Toggle telemetry collection
  service_name: "mcp-commit-story"   # Service name for traces
```

### AI Tone/Style Configuration

The user can control the tone and style of AI-generated summaries in journal entries by setting the `ai_tone` field in `.mcp-commit-storyrc.yaml`.

**Supported values:**
- `neutral` (default): Objective, factual, and balanced. No strong personality.
- `concise`: Short, direct, and minimal. Focuses on brevity and essentials.
- `explanatory`: Clear, step-by-step, and focused on making things easy to understand.
- `technical`: Uses precise, domain-specific language. For advanced/engineering audiences.
- `reflective`: Thoughtful, introspective, and focused on lessons learned.
- `friendly`: Warm, encouraging, and positive—but still professional.

If an unsupported value is set, the system will fall back to `neutral` and log a warning.

#### Example Configuration:
```yaml
journal:
  path: journal/
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
```

#### Journal Entry Structure Note
- The **Summary** section of each journal entry will reflect the selected `ai_tone` style.

#### Technical Synopsis
{technical details about code changes}

- The Technical Synopsis section provides a code-focused analysis of what changed in the commit. It should include architectural patterns, specific classes/functions modified, technical approach taken, and any other relevant technical details. This section is self-contained and generated from the JournalContext.

### On-Demand Directory Creation Pattern

### Rationale
- Only create journal subdirectories (e.g., daily/, summaries/weekly/) when they are actually needed, not at initialization.
- Prevents empty folders, keeps the repo clean, and matches natural usage patterns.

### Implementation
- Use the utility function `ensure_journal_directory(file_path)` before any file write operation.
- This function creates all missing parent directories for the given file path, does nothing if they already exist, and raises PermissionError on failure.
- All journal file operations (append, save, etc.) must call this utility before writing.

#### Example:
```python
from mcp_commit_story.journal import ensure_journal_directory
file_path = Path("journal/daily/2025-05-28-journal.md")
ensure_journal_directory(file_path)
with open(file_path, "a") as f:
    f.write(entry)
```

### Deprecation of Upfront Directory Creation
- The old pattern of creating all subdirectories at init is fully removed.
- No code should use or reference `create_journal_directories`.

### Guidance
- See [docs/on-demand-directory-pattern.md](docs/on-demand-directory-pattern.md) for implementation details, anti-patterns, and integration tips.
- All future file-writing code must use this pattern.

### Telemetry and Observability

The system implements comprehensive observability using OpenTelemetry to provide insights into performance, reliability, and usage patterns across the entire AI → MCP → journal pipeline. **The telemetry system is fully integrated with the MCP server lifecycle, providing end-to-end observability from server startup through tool call completion.**

#### MCP Server Integration

**Early Integration Architecture:**
The telemetry system integrates at the earliest possible point in the MCP server lifecycle to ensure complete coverage:

```python
def create_mcp_server(config_path: str = None) -> FastMCP:
    """MCP server creation with integrated telemetry"""
    # 1. Load configuration first
    config = load_config(config_path)
    
    # 2. Early telemetry integration with graceful error handling
    telemetry_initialized = False
    try:
        telemetry_initialized = setup_telemetry(config.as_dict())
        if telemetry_initialized:
            logging.info("Telemetry system initialized successfully")
        else:
            logging.info("Telemetry disabled via configuration")
    except Exception as e:
        logging.warning(f"Telemetry setup failed, continuing without telemetry: {e}")
        telemetry_initialized = False
    
    # 3. Create server with telemetry context available
    server = FastMCP(app_name, version=version)
    server.telemetry_initialized = telemetry_initialized
    
    return server
```

**Tool Call Tracing Integration:**
All MCP tools are automatically instrumented with distributed tracing using a hybrid decorator approach:

```python
@server.tool()
@trace_mcp_operation("journal_new_entry")
async def journal_new_entry(request: JournalNewEntryRequest) -> JournalNewEntryResponse:
    """Create a new journal entry with AI-generated content."""
    return await handle_journal_new_entry(request)

@server.tool()
@trace_mcp_operation("journal_add_reflection")
async def journal_add_reflection(request: AddReflectionRequest) -> AddReflectionResponse:
    """Add a manual reflection to the journal."""
    return await handle_journal_add_reflection(request)
```

**Metrics Collection Integration:**
The `handle_mcp_error` decorator automatically collects comprehensive metrics for all tool operations:

```python
def handle_mcp_error(func):
    """Enhanced error handler with integrated metrics collection"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        operation_name = func.__name__
        start_time = time.time()
        
        # Get metrics instance if available
        metrics = get_mcp_metrics() if telemetry_available() else None
        
        try:
            result = await func(*args, **kwargs)
            
            # Record successful operation metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_tool_call(operation_name, True)
                metrics.record_operation_duration(operation_name, duration)
            
            return result
            
        except MCPError as e:
            # Preserve custom MCPError status while recording metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_tool_call(operation_name, False, error_type="mcp_error")
                metrics.record_operation_duration(operation_name, duration, success=False)
            
            return {"status": e.status, "error": e.message}
```

**Enhanced Configuration Schema:**
The MCP server integration includes an enhanced configuration schema supporting the complete telemetry feature set:

```yaml
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

**Performance Characteristics:**
The MCP server integration maintains excellent performance with minimal overhead:
- **< 5ms overhead per tool call** - Verified through comprehensive testing
- **< 1MB memory overhead** - Efficient resource utilization
- **< 10% CPU overhead** - Negligible processing impact
- **~1MB daily data volume** - Reasonable storage requirements

**Graceful Degradation:**
The integration is designed to never block MCP server operation:
- Telemetry failures are logged but don't prevent server startup
- Individual exporter failures don't affect other exporters
- Server continues normal operation even if all telemetry fails
- Health checks provide visibility into telemetry system status

**Hot Configuration Reload:**
Telemetry settings can be updated without restarting the MCP server:

```python
def reload_config():
    """Hot reload configuration including telemetry settings"""
    config.reload_config()
    # Telemetry system automatically respects new configuration
    logging.info("Config hot reloaded successfully.")

server.reload_config = reload_config
```

#### Architecture
- **OpenTelemetry Foundation**: TracerProvider and MeterProvider with configurable exporters
- **Multi-Exporter Support**: Console (development), OTLP (production), Prometheus (metrics)
- **Auto-Instrumentation**: Automatic tracing of HTTP requests, async operations, and logging
- **Trace Correlation**: Distributed tracing across MCP operations and journal generation
- **Structured Logging**: JSON logs with trace correlation for debugging
- **MCP Server Lifecycle Integration**: Complete observability from server startup through shutdown

#### Configuration
```yaml
telemetry:
  enabled: true
  service_name: "mcp-commit-story"
  service_version: "1.0.0"
  deployment_environment: "production"
  
  auto_instrumentation:
    enabled: true                  # Enable auto-instrumentation (default: true)
    preset: "minimal"              # Preset: minimal, comprehensive, or custom
    instrumentors:                 # Individual instrumentor control
      requests: true               # HTTP requests library
      aiohttp: true                # Async HTTP client
      asyncio: true                # Async operations
      logging: true                # Log-trace correlation
      
  exporters:
    console:
      enabled: true
      traces: true                 # Export traces to console
      metrics: true                # Export metrics to console
    otlp:
      enabled: false
      endpoint: "http://localhost:4317"
      protocol: "grpc"             # or "http"
      headers:
        authorization: "Bearer token123"
      timeout: 30                  # Connection timeout in seconds
      traces: true                 # Export traces via OTLP
      metrics: true                # Export metrics via OTLP
    prometheus:
      enabled: false
      port: 8888                   # Metrics endpoint port
      endpoint: "/metrics"         # Metrics endpoint path
      metrics: true                # Export metrics (only supported type)
      traces: false                # Prometheus doesn't support traces
```

#### Multi-Exporter Configuration System

The telemetry system implements an enhanced multi-exporter configuration system with environment variable precedence hierarchy, partial success error handling, and comprehensive validation rules.

**Core Implementation:**
```python
class ExporterConfigManager:
    """Manages multi-exporter configuration with enhanced features"""
    
    def resolve_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve configuration with environment variable precedence hierarchy"""
        
    def validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate configuration with comprehensive rules"""

def configure_exporters(config: Dict[str, Any]) -> PartialSuccessResult:
    """Configure all enabled exporters with partial success handling"""
```

**Environment Variable Precedence Hierarchy:**
1. **MCP-specific environment variables** (highest priority):
   - `MCP_PROMETHEUS_PORT`: Override Prometheus port
   - `MCP_CONSOLE_ENABLED`: Enable/disable console exporter ("true"/"false")
   - `MCP_OTLP_ENDPOINT`: Override OTLP endpoint URL
   - `MCP_OTLP_ENABLED`: Enable/disable OTLP exporter ("true"/"false") 
   - `MCP_PROMETHEUS_ENABLED`: Enable/disable Prometheus exporter ("true"/"false")

2. **Standard OpenTelemetry environment variables**:
   - `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint URL
   - `OTEL_EXPORTER_OTLP_HEADERS`: OTLP headers (comma-separated key=value pairs)
   - `OTEL_EXPORTER_OTLP_TIMEOUT`: OTLP timeout in seconds
   - `OTEL_SERVICE_NAME`: Service name

3. **Configuration file values**: Values specified in YAML/JSON config
4. **Built-in defaults**: System defaults (lowest priority)

**Enhanced Error Handling with Partial Success:**
```python
@dataclass
class PartialSuccessResult:
    """Result object for partial success scenarios"""
    status: str  # "success", "partial_success", "failure"
    successful_exporters: List[str] = field(default_factory=list)
    failed_exporters: Dict[str, Dict[str, str]] = field(default_factory=dict)
```

Example partial success response:
```python
{
    "status": "partial_success",
    "successful_exporters": ["console", "prometheus"],
    "failed_exporters": {
        "otlp": {
            "error": "Connection timeout",
            "details": "Failed to connect to http://localhost:4317 after 10 seconds"
        }
    }
}
```

**Comprehensive Validation Rules:**
- **Port range validation**: 1-65535 for all port configurations
- **Endpoint path validation**: Must start with "/" for Prometheus endpoints
- **Protocol validation**: OTLP protocol must be "grpc" or "http"
- **Timeout validation**: Must be positive integer
- **Headers validation**: Must be valid key-value pairs for OTLP

**Multi-Exporter Support:**

*Console Exporter:*
- Development-focused output to stdout/stderr
- Supports both traces and metrics
- No external dependencies

*OTLP Exporter:*
- Production-ready export to observability backends
- Support for both gRPC and HTTP protocols
- Compatible with Jaeger, DataDog, New Relic, Honeycomb, etc.
- Configurable authentication headers
- Supports both traces and metrics

*Prometheus Exporter:*
- Industry-standard metrics endpoint
- HTTP endpoint for scraping by Prometheus servers
- Metrics only (traces not supported by Prometheus)
- Configurable port and endpoint path

**Graceful Degradation Features:**
- No cascading failures: One failed exporter doesn't break others
- Detailed error reporting with specific failure context
- Comprehensive logging for debugging and monitoring
- Operational continuity: Application continues even if all exporters fail

**Production Configuration Example:**
```yaml
telemetry:
  exporters:
    console:
      enabled: false               # Disable console in production
    otlp:
      enabled: true
      endpoint: "https://api.honeycomb.io:443"
      protocol: "grpc"
      headers:
        "x-honeycomb-team": "${HONEYCOMB_API_KEY}"
      timeout: 30
      traces: true
      metrics: true
    prometheus:
      enabled: true
      port: 8888
      endpoint: "/metrics"
      metrics: true
```

**Environment Variable Override Example:**
```bash
# Override for specific deployment
export MCP_OTLP_ENDPOINT="https://custom-backend.com:4317"
export MCP_PROMETHEUS_PORT="9090"
export OTEL_EXPORTER_OTLP_HEADERS="authorization=Bearer custom-token"
```

#### Auto-Instrumentation Implementation

The system provides automatic instrumentation for common Python libraries, eliminating the need for manual tracing in most scenarios.

**Core Function:**
```python
def enable_auto_instrumentation(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enable OpenTelemetry auto-instrumentation for approved libraries.
    Automatically called during setup_telemetry() initialization.
    """
```

**Supported Instrumentors:**
- **requests**: Automatic HTTP request tracing with the `requests` library
- **aiohttp**: Async HTTP client tracing (graceful fallback if aiohttp not installed)
- **asyncio**: Automatic tracing of asyncio operations and coroutines
- **logging**: Automatic trace correlation in log messages

**Preset Configurations:**
- **minimal** (default): Enables `requests` and `logging` for basic observability
- **comprehensive**: Enables all approved instrumentors for maximum visibility
- **custom**: Respects individual instrumentor settings for granular control

**Graceful Fallback:**
- Missing target libraries (e.g., aiohttp not installed) are gracefully skipped
- Failed instrumentors are tracked but don't prevent system startup
- Warning messages logged for debugging purposes

**Integration:**
Auto-instrumentation is automatically enabled during telemetry setup:

```python
# Called automatically in setup_telemetry()
def setup_telemetry(config):
    # ... other setup ...
    if telemetry_config.get("auto_instrumentation", {}).get("enabled", True):
        enable_auto_instrumentation(config)
```

#### Structured Logging with Trace Correlation

The system implements comprehensive structured logging with automatic OpenTelemetry trace correlation, providing seamless integration between logs, traces, and metrics for enhanced observability.

**Core Implementation:**
```python
# src/mcp_commit_story/structured_logging.py
class OTelFormatter(logging.Formatter):
    """JSON formatter with automatic OpenTelemetry trace correlation"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with trace context"""

class LogMetricsHandler(logging.Handler):
    """Optional handler for collecting log-based metrics"""
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log-based metrics to OpenTelemetry"""

def setup_structured_logging(config: Dict[str, Any]) -> bool:
    """Configure structured logging with telemetry integration"""

def get_correlated_logger(name: str) -> logging.Logger:
    """Get logger configured for trace correlation"""
```

**Key Features:**

*JSON Format with Trace Correlation:*
- All logs output as structured JSON for parsing and analysis
- Automatic injection of `trace_id` and `span_id` when spans are active
- Standard OpenTelemetry trace format for seamless correlation
- Consistent timestamp formatting with microsecond precision

*Sensitive Data Protection:*
- Automatic redaction of passwords, tokens, API keys, and credentials
- Recursive sanitization of nested data structures
- Configurable sensitive field patterns
- Security-first approach for centralized logging systems

*Performance Optimization:*
- Lazy evaluation of expensive log data computations
- `LazyLogData` wrapper for deferred object serialization
- Level-aware logging helpers to avoid unnecessary processing
- Minimal overhead when logging is disabled

*Log-Based Metrics Integration:*
- Optional collection of operational metrics from log entries
- Error rate tracking by service and operation
- Log volume trends for capacity planning
- Integration with existing OpenTelemetry metrics pipeline

**Configuration:**
```yaml
telemetry:
  logging:
    level: "INFO"                 # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format: "json"                # Always JSON (only supported format)
    correlation: true             # Enable trace correlation (default: true)
    metrics: false                # Enable log-based metrics (default: false)
    handlers: ["console"]         # Output destinations
    sensitive_fields:             # Additional sensitive field patterns
      - "custom_secret"
      - "internal_token"
```

**Usage Patterns:**

*Basic Structured Logging:*
```python
from mcp_commit_story.structured_logging import get_correlated_logger

logger = get_correlated_logger(__name__)

# Automatic trace correlation when spans are active
logger.info("Operation completed", extra={
    "operation_id": "abc123",
    "user_id": "12345",
    "duration_ms": 150
})
```

*Performance-Optimized Logging:*
```python
from mcp_commit_story.structured_logging import LazyLogData, log_performance_optimized

# Lazy evaluation - only computed if logging enabled
expensive_data = LazyLogData(lambda: serialize_complex_object(data))

# Recommended pattern for expensive operations
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Complex operation details", extra={
        "operation_data": expensive_computation()
    })

# Or use performance-optimized helper
log_performance_optimized(
    logger, 
    logging.DEBUG, 
    "Operation details", 
    {"complex_data": expensive_data}
)
```

*Sensitive Data Handling:*
```python
from mcp_commit_story.structured_logging import sanitize_log_data

# Automatic sanitization
user_data = {
    "username": "john_doe",
    "password": "secret123",  # Will be redacted
    "api_key": "abc123",      # Will be redacted
    "profile": {"email": "john@example.com"}
}

sanitized = sanitize_log_data(user_data)
logger.info("User operation", extra={"user_data": sanitized})
```

**Log Format Example:**
```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "message": "Journal entry created successfully",
  "logger": "mcp_commit_story.journal",
  "pathname": "/src/mcp_commit_story/journal.py",
  "lineno": 42,
  "trace_id": "1234567890abcdef1234567890abcdef",
  "span_id": "abcdef1234567890",
  "operation_id": "create_entry_001",
  "commit_hash": "abc123def456",
  "files_changed": 3,
  "duration_ms": 150
}
```

**Integration with Telemetry System:**
- Automatically initialized during `setup_telemetry()` when enabled
- Seamless integration with existing OpenTelemetry instrumentation
- Works with or without active telemetry (graceful degradation)
- Consistent with multi-exporter configuration patterns

**Security Considerations:**
- Default sensitive field patterns cover common security risks
- Recursive sanitization prevents data leakage in nested structures
- Field name matching is case-insensitive and substring-based
- Custom sensitive patterns can be added via configuration

**Monitoring and Alerting:**
- Log-based metrics enable alerting on error rates and volume
- Trace correlation allows drilling down from metrics to specific requests
- JSON format enables rich querying in centralized logging systems
- Performance metrics help identify expensive operations

*Log-based Metrics:*
- Optional collection of metrics derived from log events
- Error rate metrics from ERROR/CRITICAL level logs
- Integration with OpenTelemetry metrics system
- Configurable log level thresholds for metric generation

**Configuration:**
```yaml
structured_logging:
  enabled: true
  format: "json"                  # or "text"
  level: "INFO"                   # Python logging level
  correlation:
    enabled: true                 # Enable trace correlation
    trace_id_field: "trace_id"    # Field name for trace ID
    span_id_field: "span_id"      # Field name for span ID
  sensitive_data_protection:
    enabled: true                 # Enable automatic redaction
    custom_patterns:              # Additional sensitive patterns
      - "custom_secret_\\w+"
  log_metrics:
    enabled: false                # Collect metrics from logs
    error_threshold: "ERROR"      # Minimum level for error metrics
```

**Example Output:**
```json
{
  "timestamp": "2024-12-07T19:30:45.123456Z",
  "level": "INFO",
  "logger": "mcp_commit_story.journal",
  "message": "Generated journal entry successfully",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "span_id": "b7ad6b7169203331",
  "module": "journal",
  "function": "generate_summary_section",
  "operation": "journal.generate_summary",
  "entry_type": "daily",
  "processing_time_ms": 1250.0,
  "context_size": 2048
}
```

#### Journal Operations Instrumentation

The journal management system includes comprehensive OpenTelemetry instrumentation providing complete observability into AI-driven content generation, file operations, and journal entry processing.

**Core Implementation Philosophy:**
- **Complete Coverage**: All journal operations are instrumented for end-to-end observability
- **TDD Approach**: 18 comprehensive tests validate telemetry behavior across all scenarios
- **Performance Focus**: Sub-5ms overhead for individual operations, sub-10% for batch operations
- **Privacy by Design**: Multi-layer sensitive data filtering with production and debug modes

**Instrumented Operations:**

*File Operations (Priority 1):*
```python
@trace_mcp_operation("journal.get_file_path", attributes={"operation_type": "file_path_generation"})
def get_journal_file_path(date: str, entry_type: str) -> str:
    """Generate journal file path with telemetry and sensitive data filtering."""

@trace_mcp_operation("journal.file_write", attributes={"operation_type": "file_write", "file_type": "markdown"})
def append_to_journal_file(content: str, file_path: Path) -> None:
    """Write journal content with duration metrics and file size tracking."""

@trace_mcp_operation("journal.directory_ensure", attributes={"operation_type": "directory_create"})
def ensure_journal_directory(file_path: Path) -> None:
    """Ensure directory exists with operation metrics and error tracking."""
```

*AI Generation Operations (Priority 2):*
```python
@trace_mcp_operation("journal.generate_summary", attributes={"operation_type": "ai_generation", "section_type": "summary"})
def generate_summary_section(journal_context: JournalContext) -> SummarySection:
    """Generate summary with AI generation telemetry and context size tracking."""

# All 8 generate_*_section functions instrumented:
# - generate_summary_section
# - generate_technical_synopsis_section  
# - generate_accomplishments_section
# - generate_frustrations_section
# - generate_tone_mood_section
# - generate_discussion_notes_section
# - generate_terminal_commands_section
# - generate_commit_metadata_section
```

*Reading Operations (Priority 3):*
```python
@trace_mcp_operation("journal.parse_entry", attributes={"operation_type": "file_read", "file_type": "markdown"})
def parse(md) -> JournalEntry:
    """Parse markdown content with content size and processing time metrics."""

@trace_mcp_operation("journal.serialize_entry", attributes={"operation_type": "serialization", "file_type": "markdown"})
def to_markdown(self) -> str:
    """Serialize journal entry with output size tracking."""

@trace_mcp_operation("journal.load_context", attributes={"operation_type": "config_read", "file_type": "toml"})
def load_journal_context(config_path: str) -> dict:
    """Load configuration with file size and parsing time metrics."""
```

**Metrics Collection:**

*Duration Histograms:*
- `journal.file_write_duration_seconds`: File write operation timing
- `journal.ai_generation_duration_seconds`: AI generation timing with section_type labels
- `journal.directory_operation_duration_seconds`: Directory creation timing
- `journal.file_read_duration_seconds`: Journal parsing and loading timing
- `journal.serialization_duration_seconds`: Entry serialization timing

*Success/Failure Counters:*
- `journal.file_operations_total`: File operation success/failure counts
- `journal.ai_generation_operations_total`: AI generation success/failure counts
- `journal.directory_operations_total`: Directory operation success/failure counts

*Content Size Tracking:*
- File size attributes: `file.size_bytes`, `journal.content_length`
- Context size attributes: `journal.context_size`, `journal.entry_count`
- Output size attributes: `journal.output_size`, `journal.section_count`

**Semantic Conventions:**

*Operation Classification:*
- `operation_type`: file_write, file_read, ai_generation, serialization, config_read, directory_create
- `section_type`: summary, technical_synopsis, accomplishments, frustrations, tone_mood, discussion_notes, terminal_commands, commit_metadata
- `file_type`: markdown, toml, json

*Privacy-Conscious Attributes:*
- `file.path`: Filename only (no full paths)
- `directory.path`: Directory name only (no full paths)  
- `journal.entry_type`: daily, weekly, monthly, quarterly, yearly
- `journal.entry_id`: Unique identifier for correlation

*Context Correlation:*
- `journal.entry_id`: Links operations to specific journal entries
- `journal.context_size`: Input context size for AI generation
- `ai.model_used`: Model identifier for AI generation operations
- `error.category`: Classification of errors for debugging

**Enhanced Sensitive Data Filtering (Priority 4):**

*Production Mode (Aggressive):*
- Git information: Full commit hashes → first 8 chars, branch names → sanitized patterns
- URLs: Query parameters → sanitized, auth tokens → removed
- Connection strings: Passwords/credentials → fully redacted
- Personal data: Email addresses → domain preserved, IP addresses → first octet only
- API keys: Common patterns → first 8 chars + "***"
- File paths: Deep paths → directory structure obscured
- Length limit: 1000 characters maximum

*Debug Mode (Less Aggressive):*
- More permissive pattern matching for development debugging
- Higher character limits (2000 vs 1000) for detailed context
- Preserves more information while protecting truly sensitive data
- Configurable via `sanitize_for_telemetry(value, debug_mode=True)`

**Async/Sync Decorator Support:**

The telemetry system automatically detects and handles both synchronous and asynchronous functions:

```python
def trace_mcp_operation(operation_name: str, attributes: Optional[Dict[str, Any]] = None):
    """Enhanced decorator supporting both sync and async functions"""
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Async telemetry implementation
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Sync telemetry implementation  
                return func(*args, **kwargs)
            return wrapper
    return decorator
```

**Testing Coverage:**

The journal telemetry system includes 21 comprehensive tests covering:
- File operation tracing and metrics (6 tests)
- AI context flow tracing for all generation functions (8 tests)
- Error scenario handling and recovery (3 tests)
- Sensitive data filtering patterns (2 tests)
- Performance impact assessment (2 tests)
- Async/sync decorator support (2 tests)

**Performance Characteristics:**
- **Individual Operations**: ≤5% overhead per operation
- **Batch Operations**: ≤10% total overhead for multiple operations
- **Memory Usage**: <1MB additional memory for telemetry data structures
- **Storage Impact**: ~500KB additional data per day for typical development activity

**Integration Points:**
- Automatic telemetry initialization during MCP server startup
- Seamless integration with existing error handling patterns
- Correlation with MCP tool call tracing for end-to-end observability
- Compatible with all configured exporters (console, OTLP, Prometheus)

#### Context Collection Telemetry

The context collection system includes comprehensive instrumentation for Git operations and context gathering with advanced performance optimizations, memory tracking, and smart file sampling for large repositories.

**Core Implementation Philosophy:**
- **Clean Decorator Pattern**: Complete separation of telemetry from business logic
- **Performance Optimization**: Built-in protections for large repositories and timeouts
- **Memory Awareness**: Strategic memory monitoring with configurable thresholds
- **Error Resilience**: Circuit breaker pattern and graceful degradation
- **Smart Sampling**: Intelligent file sampling to prevent performance degradation

**Enhanced Git Operation Decorator:**

```python
@trace_git_operation("git_context",
                    performance_thresholds={"duration": 2.0},
                    error_categories=["git", "filesystem", "memory"])
def collect_git_context(commit_hash=None, repo=None, journal_path=None):
    """Clean function focused solely on Git context collection logic."""
    # Pure implementation - no telemetry noise
    return git_context_data
```

**Instrumented Context Collection Functions:**

*Git Context Collection:*
```python
@trace_git_operation("git_context",
                    performance_thresholds={"duration": 2.0},
                    error_categories=["git", "filesystem", "memory"])
def collect_git_context(commit_hash=None, repo=None, journal_path=None):
    """Comprehensive Git context collection with performance optimization."""
    # Automatic features: memory tracking, timeout protection, smart file sampling
    # Large repo handling: >100 files triggers summary mode
    # Memory monitoring: Records metrics if usage exceeds 50MB threshold
```

*Chat History Collection:*
```python
@trace_git_operation("chat_history", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
def collect_chat_history(since_commit=None, max_messages_back=150):
    """AI-driven chat history analysis with telemetry tracking."""
    # Clean AI prompt implementation without telemetry noise
    # Automatic error categorization and duration tracking
```

*Terminal Commands Collection:*
```python
@trace_git_operation("terminal_commands",
                    performance_thresholds={"duration": 1.0}, 
                    error_categories=["api", "network", "parsing"])
def collect_ai_terminal_commands(since_commit=None, max_messages_back=150):
    """Terminal command extraction with context analysis."""
    # Focused on command extraction logic
    # Automatic performance monitoring and error handling
```

**Automatic Decorator Features:**

*Performance Monitoring:*
- Configurable duration thresholds per operation type
- Automatic slow operation detection and alerting
- Performance degradation protection for large repositories
- Timeout protection with graceful degradation (5-second default)

*Memory Tracking:*
- Strategic memory sampling at operation boundaries  
- Process-level RSS memory monitoring
- Configurable memory increase thresholds (50MB default)
- Peak memory tracking during operations

*Error Categorization:*
- Configurable error categories per operation (git, filesystem, memory, api, network, parsing)
- Automatic exception classification and metrics recording
- Circuit breaker pattern to disable telemetry after repeated failures
- Graceful degradation ensuring context collection continues

*Smart File Sampling:*
- Large repository detection (>50 files triggers sampling)
- Priority-based file selection (source code files prioritized)
- Configurable sampling percentage (20% default)
- Large file handling (>1MB files processed differently)
- Generated file exclusion (build artifacts, dependencies)

**Generated Metrics:**

*Context Collection Duration:*
- `mcp.journal.git_context.duration` - Git context collection timing
- `mcp.journal.chat_history.duration` - Chat history collection timing  
- `mcp.journal.terminal_commands.duration` - Terminal command collection timing

*Performance Optimization Metrics:*
- `mcp.journal.git_context.files_processed` - Number of files analyzed
- `mcp.journal.git_context.large_repo_detected` - Large repository handling triggered
- `mcp.journal.git_context.smart_sampling_applied` - File sampling applied
- `mcp.journal.memory_usage_mb` - Memory consumption tracking

*Error and Circuit Breaker Metrics:*
- `mcp.journal.errors.by_type{error_type="git"}` - Git-specific errors
- `mcp.journal.errors.by_type{error_type="filesystem"}` - File system errors
- `mcp.journal.errors.by_type{error_type="memory"}` - Memory-related errors
- `mcp.journal.circuit_breaker.triggered` - Circuit breaker activations
- `mcp.journal.timeout.exceeded` - Operation timeouts

**Performance Thresholds and Optimizations:**

*Configurable Performance Limits:*
```python
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
```

*Smart File Sampling Strategy:*
- **Always Include**: Changed source code files (.py, .js, .ts, .java)
- **Sample**: 20% of other file types randomly for repos with >50 files
- **Always Include**: Files >100KB (likely significant changes)
- **Always Exclude**: Generated files, build artifacts, dependencies
- **Truncate Analysis**: For commits with >100 files, use summary statistics only

*Memory Tracking Implementation:*
```python
@contextlib.contextmanager
def memory_tracking_context(operation_name: str, baseline_threshold_mb: float = 50.0):
    """Context manager for strategic memory monitoring."""
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    try:
        yield
    finally:
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        if (final_memory - initial_memory) > baseline_threshold_mb:
            # Record memory usage metrics only when significant
            metrics.set_memory_usage_mb(final_memory, operation=operation_name)
```

**Error Handling and Circuit Breaker:**

*Error Classification:*
- **git**: Repository access, commit resolution, branch operations
- **filesystem**: File access, permission errors, disk space issues  
- **memory**: Out of memory, allocation failures
- **api**: Network timeouts, API failures for AI operations
- **network**: Connection issues, DNS resolution failures
- **parsing**: Content parsing, format errors

*Circuit Breaker Implementation:*
```python
class TelemetryCircuitBreaker:
    """Disable telemetry temporarily after repeated failures."""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.is_open = False
```

**Testing Coverage:**

Comprehensive test suite with 15+ tests covering:
- Git operation timing and success/failure tracking (3 tests)
- Memory usage monitoring and threshold detection (3 tests)  
- Smart file sampling for large repositories (2 tests)
- Error categorization and circuit breaker patterns (3 tests)
- Performance optimization edge cases (2 tests)
- Context collection flow integration (3 tests)

**Configuration Options:**

Context collection telemetry can be configured through telemetry settings:

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
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout_seconds: 300
```

**Performance Characteristics:**
- **Individual Context Operations**: ≤3% overhead per operation
- **Large Repository Handling**: Automatic performance protection via sampling
- **Memory Overhead**: <2MB additional memory for tracking data structures  
- **Circuit Breaker Recovery**: Automatic re-enablement after timeout period

**Integration Benefits:**
- Clean separation of telemetry from AI prompt logic
- Automatic performance optimization for production environments
- Rich observability data for debugging and optimization
- Seamless integration with existing MCP server telemetry infrastructure

---

## Journal Entry Behavior

### Triggering
- **Default**: One journal entry per Git commit
- Entries written to daily Markdown files, named `YYYY-MM-DD.md`
- Timestamps included per entry (e.g., `4:02 PM — Commit abc123`)
- Files appended in chronological order

### Chat History Collection Method
- **Primary method**: AI scans backward through current conversation
- **How it works**: AI has access to its own chat history within the current session
- **Boundary**: Look back until finding previous commit reference OR 150-message safety limit
- **Usage**: Chat history may inform summary, accomplishments, frustrations, discussion notes, and tone/mood sections
- **No external file access required** - AI uses its own conversation context
- **Decision excerpts**: May include relevant conversation snippets in Discussion Notes section

### Data Sources
#### Required:
- Git commit message and metadata
- File diffs (simplified summaries with line counts)

#### Optional (if available):
- Chat history with dev agents (scanned in reverse until a reference to the previous git commit is found)
- **Discussion excerpts** from chat history showing decision-making context
- **AI session terminal commands** - commands executed by AI assistants during the work session

### History Collection Boundaries
- **Chat history**: From current commit backward until finding previous commit reference OR 150-message safety limit
- **AI session commands**: Request from AI assistant for commands executed during current work session
- **No filtering**: Include all commands/messages within boundaries

### Anti-Hallucination Rules
- Never infer *why* something was done unless evidence exists
- Mood/tone must be backed by language cues ("ugh", "finally", etc.)
- If data is unavailable (e.g., terminal history), omit that section

### Recursion Prevention
- **Initial filtering**: Examine all files in commit
  - If commit only modifies journal files → skip journal entry generation entirely
  - If commit modifies both code and journal files → proceed to create entry
- **Content generation**: When creating the entry
  - When generating file diffs and stats for the journal entry content, exclude journal files from this analysis
  - Only show changes for non-journal files
- This allows journal files to be git-tracked while preventing recursive entries
- No configuration needed - this behavior is built-in

### Journal Entry Structure (Canonical Format)

```markdown
### {timestamp} — Commit {commit_hash}

## Summary
{summary text}

## Technical Synopsis
{technical details about code changes}

## Accomplishments
- {accomplishment 1}
- {accomplishment 2}

## Frustrations or Roadblocks
- {frustration 1}
- {frustration 2}

## Tone/Mood
> {mood}
> {indicators}

## Discussion Notes (from chat)
> **Human:** {note text}
> **Agent:** {note text}
> {plain string note}

## Terminal Commands (AI Session)
Commands executed by AI during this work session:
```bash
{command 1}
{command 2}
```

## Commit Metadata
- **files_changed:** {number}
- **insertions:** {number}
- **deletions:** {number}
```

- All sections are omitted if empty.
- Terminal commands are always rendered as a bash code block with a descriptive line.
- Discussion notes are blockquotes; if a note is a dict with `speaker` and `text`, use `> **Speaker:** text`. Multiline notes are supported.
- Tone/Mood is only included if there is clear evidence (from commit messages, chat, or terminal commands) and is always for the human developer only. Render as two blockquote lines: mood and indicators. Omit if insufficient evidence.
- Never hallucinate or assume mood; always base on evidence.
- Markdown is the canonical format for all journal entries.

Mood inference rules: Only infer human developer's mood, must be evidence-based, omit if insufficient evidence, never hallucinate.
Discussion notes rules: Include all relevant notes, support multiline and speaker attribution, blockquote formatting.

### Content Quality Guidelines

#### Focus on Signal vs. Noise

- **Signal**: Unique decisions, technical challenges, emotional context, lessons learned, or anything that would help a future reader understand the story behind the work
- **Noise**: Routine process notes, standard workflow descriptions, or anything that is always true and already established in project documentation

Journal entries should prioritize signal over noise to maintain narrative value. For example:

- ❌ "Followed TDD methodology by writing tests first" (noise, as this is standard practice)
- ✅ "Test-first approach revealed an edge case in the API response handler" (signal, specific insight)
- ❌ "Used git to commit changes" (noise, obvious from context)
- ✅ "Split work into three focused commits to separate concerns" (signal, shows thought process)

#### Highlighting What's Unique

Each journal entry should capture what was distinctive about this particular development session:

- Technical challenges encountered and how they were addressed
- Design decisions made and their rationales
- Insights gained that weren't obvious at the start
- Emotional context that influenced the work approach

The Summary section should focus on these unique aspects rather than restating routine workflow steps.

---

## MCP Server Implementation

### MCP Operations
1. `journal/new-entry` - Create a new journal entry from current git state
2. `journal/summarize` - Generate weekly/monthly summaries  
3. `journal/blogify` - Convert journal entry(s) to blog post format
4. `journal/backfill` - Check for missed commits and create entries
5. `journal/install-hook` - Install git post-commit hook
6. `journal/add-reflection` - Add a manual reflection to today's journal
7. `journal/init` - Initialize journal in current repository

Each operation will be instrumented with appropriate traces to monitor performance and error rates.

### Operation Details

#### journal/new-entry
- Check for missed commits and backfill if needed
- Generate entry for current commit
- Return path to updated file

#### journal/summarize
- Options: `--week`, `--month`, `--range`, `--day`, `--year`
- Daily summaries for quick recaps of previous day's work
- Weekly summaries for sprint retrospectives and short-term trends
- Monthly summaries for broader patterns and accomplishments
- Yearly summaries for major milestones, skill development, and career progression
- Default to most recent period if no date specified
- Support specific dates (e.g., `--week 2025-01-13`, `--year 2025`)
- Support arbitrary ranges (e.g., `--range "2025-01-01:2025-01-31"`)
- Prioritize manually added reflections in summaries

Note: When generating summaries, the algorithm should prioritize and give more narrative weight to journal entries that reflect substantial or complex work, while de-emphasizing entries for small, routine, or trivial changes. This ensures that the most meaningful engineering efforts are highlighted in daily, weekly, and monthly summaries.

#### journal/init
- Create initial journal directory structure
- Generate default configuration file
- Install git post-commit hook (with user confirmation)
- Return initialization status and created paths

#### journal/add-reflection
- Accept reflection text as parameter
- Append to today's journal file with timestamp
- Support markdown formatting in reflection
- Return path to updated file

#### journal/blogify
- Transforms journal entries into cohesive narrative content
- Accepts single or multiple journal file paths as input
- Creates a natural, readable blog post from technical entries
- Removes structural elements (headers, timestamps, metadata)
- Preserves key decisions and insights

### Data Formats
- All operations return pre-formatted markdown strings
- Success operations return file path + status
- Hard failures return error status with message

---

## CLI Interface (Setup Only)

### Architectural Change

The system follows an **MCP-first architecture**. The CLI is now setup-only, with operational commands moved to the MCP server for AI-agent integration.

### Setup CLI Commands

Entry Point: `mcp-commit-story-setup`

```bash
mcp-commit-story-setup [command] [options]
```

### Supported Setup Commands
- `mcp-commit-story-setup journal-init` - Initialize journal in current repository
- `mcp-commit-story-setup install-hook` - Install git post-commit hook

### MCP Operations (Primary Interface)
Operational functionality via MCP server:
- `journal/new-entry` - Create journal entry for commit (with AI command collection)
- `journal/add-reflection` - Add manual reflection to journal
- `journal/init` - Programmatic journal initialization
- `journal/install-hook` - Programmatic hook installation

### Usage Pattern
```bash
# One-time setup (human)
mcp-commit-story-setup journal-init
mcp-commit-story-setup install-hook

# Ongoing operations (AI/automated)
# Git hook automatically triggers: journal/new-entry via MCP
# AI agents call: journal/add-reflection via MCP
```

### Global Options
- `--config <path>` - Override config file location
- `--dry-run` - Preview operations without writing files
- `--verbose` - Detailed output for debugging
- `--debug` - Show all errors and warnings, including soft failures

---

## Data Handling Details

### File Organization
- `journal.path` in config sets parent directory containing `daily/` and `summaries/`
- Paths always relative to git repository root
- Missing directories created automatically

### Diff Processing
- Examine all files in commit to determine if entry should be created
- When generating file diffs and stats for the journal entry content, exclude journal files from this analysis
- Capture simplified summaries with line counts (e.g., "modified 3 functions in auth.js")
- Binary files noted as "binary file changed"
- Large diffs truncated with note about truncation
- Focus only on code and documentation changes

### Date/Time Handling
- Week boundaries: Monday-Sunday
- Month boundaries: Calendar months (1st to last day)
- All timestamps in local timezone
- ISO format dates in filenames (YYYY-MM-DD)

---

## Error Handling

### Hard Failures (Fail Fast)
These errors return error status and stop execution:
- Git repository not found
- Journal directory doesn't exist and can't be created
- Invalid MCP connection
- Corrupted git repository

### Soft Failures (Silent Skip)
These errors are skipped silently without user notification:
- Terminal history not accessible (file permissions, format issues)
- Chat history unavailable or API errors  
- AI session command collection fails (unsupported AI tool, API changes)
- Previous commit not found for backfill
- Terminal commands unparseable
- AI assistant doesn't support command history
- Network timeouts when fetching optional data


### Error Messages
- Brief and actionable
- Include suggestions for resolution where possible
- Never expose internal implementation details

### Debug Mode
When using `--debug` flag, all soft failures are logged to stderr with details:
```bash
$ mcp-commit-story-setup journal-init --debug
[DEBUG] Failed to read terminal history: Permission denied for ~/.bash_history
[DEBUG] AI command collection failed: AssistantNotSupportedError
[DEBUG] Chat history scan stopped: Previous commit reference not found after 150 messages
Generated journal entry successfully (some sections omitted)
```

## Graceful Degradation Philosophy
* **Always generate a journal entry** regardless of available data sources
* **Include what works**, silently omit what doesn't
* **No error messages** clutter the journal output
* **User never sees broken features** - they just don't get that section
* **Future-proof**: automatically works when AI tools improve their APIs

### Error Messages
* Brief and actionable for hard failures only
* Include suggestions for resolution where possible
* Never expose internal implementation details
* **No error messages for soft failures in normal mode**
* Debug mode provides detailed error information

---

## Git Integration

### Hook Installation
- `mcp-commit-story-setup install-hook` command
- Checks for existing hooks and prompts for action
- Creates hook that implements recursion prevention logic
- Backs up existing hooks before modification

### Backfill Mechanism
- Detection: Check commits since last journal entry in any file
- Order: Add missed entries in chronological order
- Context: Skip terminal/chat history for backfilled entries
- Annotation: Mark entries as backfilled with timestamp

### Commit Processing
- Handle all commit types uniformly (regular, merge, rebase, cherry-pick)
- Process initial commit normally (no previous commit to reference)
- Skip commits that only modify journal files
- For mixed commits (code + journal files), exclude journal files from analysis

### Post-Commit Hook Content Generation (Engineering Spec)
- The post-commit hook is generated using the `generate_hook_content(command: str = "mcp-commit-story-setup install-hook")` function in [src/mcp_commit_story/git_utils.py](src/mcp_commit_story/git_utils.py).
- The hook script uses `#!/bin/sh` for portability and triggers MCP operations via the configured MCP server endpoint.
- All output is redirected to `/dev/null` and the command is followed by `|| true` to ensure the hook never blocks a commit, even if journal entry creation fails.
- The script is intentionally lightweight and non-intrusive, designed to never interfere with normal Git operations.
- The installation logic (see `install_post_commit_hook`) backs up any existing hook before replacing it and sets the new hook as executable.
- This approach guarantees:
  - **Portability** (works on all Unix-like systems)
  - **Non-blocking** (never prevents a commit)
  - **Simplicity** (easy to audit and modify)
  - **MCP Integration** (triggers automated journal entry via MCP server)
- All logic is covered by strict TDD and unit tests in `tests/unit/test_git_hook_installation.py` and `tests/unit/test_git_utils.py`.

**Example generated hook content:**
```sh
#!/bin/sh
# Trigger journal/new-entry via MCP server
# Exact implementation depends on MCP client configuration
echo "Triggering automated journal entry..." >/dev/null 2>&1 || true
```

#### Post-Commit Hook Installation Core Logic
- The function `install_post_commit_hook(repo_path)` in [src/mcp_commit_story/git_utils.py](src/mcp_commit_story/git_utils.py) installs or replaces the post-commit hook in `.git/hooks`.
- Existing hooks are always backed up with a timestamped filename before being replaced, with no user prompt or confirmation required.
- The new hook is written using the content from `generate_hook_content()`.
- The installed hook is set to be executable by user, group, and other (0o755), ensuring compatibility with all Git workflows.
- The process is fully automated and suitable for CI/CD pipelines and scripting.
- All logic is covered by unit tests in `tests/unit/test_git_utils.py` and `tests/unit/test_git_hook_installation.py`.

---

## Testing Plan

### Current Testing Status
The project currently has **532 tests** across **43 test files** with **80% test coverage**. The testing strategy emphasizes comprehensive coverage of MCP operations, telemetry integration, and core journal functionality following Test-Driven Development (TDD) principles.

### Test Organization
- **Unit tests**: `tests/unit/` (26 files) - Fast, isolated component tests
- **Integration tests**: `tests/integration/` (6 files) - Cross-component and end-to-end tests  
- **Core system tests**: Main `tests/` directory - Telemetry, journal, and structured logging
- **Test fixtures**: `tests/fixtures/` - Shared test data and utilities
- **Configuration**: `tests/conftest.py` - Pytest configuration and shared fixtures

### Comprehensive Documentation Coverage
The project includes comprehensive technical documentation covering all aspects of the system:

#### Core System Documentation
- **[Journal Core](docs/journal-core.md)** - Complete journal functionality, classes, and AI generation system
- **[Context Collection](docs/context-collection.md)** - Context gathering system and type definitions  
- **[Reflection Core](docs/reflection-core.md)** - Manual reflection addition with validation and telemetry
- **[Structured Logging](docs/structured-logging.md)** - JSON logging with trace correlation and data protection
- **[Multi-Exporter](docs/multi-exporter.md)** - OpenTelemetry exporter configuration system

#### API & Integration Documentation  
- **[MCP API Specification](docs/mcp-api-specification.md)** - Complete MCP operations reference
- **[Architecture](docs/architecture.md)** - System design and architectural decisions
- **[Implementation Guide](docs/implementation-guide.md)** - Development patterns and best practices

#### Development & Testing Documentation
- **[Testing Standards](docs/testing_standards.md)** - Complete testing strategy (532 tests, 80% coverage, TDD patterns)
- **[Telemetry](docs/telemetry.md)** - Comprehensive OpenTelemetry integration and monitoring

### Unit Tests
- Configuration parsing and validation
- Journal entry generation from mock data  
- MCP operation handlers
- Git utility functions
- CLI command parsing
- Date/time handling
- **Telemetry initialization and configuration**
- **Context collection and type validation**
- **Reflection system validation**
- **Structured logging with trace correlation**

### Integration Tests
- End-to-end git hook workflow
- File creation and appending
- Backfill detection and processing
- Summary generation across date ranges
- Blog post conversion
- **Telemetry validation across complete MCP tool execution chains**
- **Context collection performance optimization**
- **Multi-exporter configuration with partial success handling**

### Test Fixtures
- Sample git repositories with various states
- Mock terminal histories
- Sample chat histories
- Various configuration files
- **Mock telemetry exporters for verification**
- **Context collection test data**
- **Structured logging test scenarios**

### Test Utilities
```python
@pytest.fixture
def mock_git_repo():
    # Create temporary git repo with test commits
    pass

@pytest.fixture
def sample_journal_entries():
    # Load sample journal files
    pass

@pytest.fixture
def mock_terminal_history():
    # Provide test terminal command history
    pass

@pytest.fixture
def mock_telemetry_exporter():
    # Provide a test exporter that captures telemetry events
    pass

@pytest.fixture
def isolated_telemetry_environment():
    # Isolated telemetry testing environment
    pass

@pytest.fixture
def context_collection_fixtures():
    # Test data for context collection validation
    pass
```

### Advanced Testing Coverage

#### Telemetry Integration Tests
The system includes comprehensive telemetry integration tests implementing a 4-phase validation approach:

1. **Core Test Infrastructure** - Isolated telemetry collection and custom assertion helpers
2. **MCP Tool Chain Integration Tests** - Async trace propagation validation across MCP operations  
3. **AI-Specific Integration Tests** - Context size impact tracking with performance correlation
4. **Advanced Testing** - Performance impact validation and circuit breaker integration

#### Performance Testing
- **Telemetry overhead measurement**: Validates <5% overhead per operation
- **Context collection optimization**: Smart file sampling for large repositories
- **Memory usage tracking**: Monitors resource consumption patterns
- **Concurrent operation testing**: Validates system behavior under load

#### Reflection Integration Testing
The reflection system includes comprehensive integration tests implementing sophisticated mocking and validation patterns:

**Test Isolation Architecture:**
- **Temporary Directory Isolation**: Each test uses isolated temp directories to prevent interference
- **Server-Level Mocking**: Mock imports at the server module level for complete path coverage
- **Configuration Abstraction**: Mock configuration objects for controlled test environments

**Comprehensive Test Coverage:**
```python
# Test isolation with temporary directories
def create_isolated_temp_dir():
    """Create a fresh temporary directory for each test to ensure isolation."""
    return tempfile.mkdtemp()

# Server-level mocking for MCP handlers
def mock_add_manual_reflection(text, date):
    with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
        return add_manual_reflection(text, date)

# Comprehensive integration scenarios
test_scenarios = [
    {"text": "Unicode test: 🎉 café naïve résumé", "date": "2025-06-01"},
    {"text": "Large content: " + "analysis " * 200, "date": "2025-06-02"},
    {"text": "Concurrent reflection {i}", "date": "2025-06-03"}
]
```

**Validation Categories:**
- **End-to-End MCP Workflows**: Complete reflection addition via MCP server handlers
- **AI Agent Interaction Patterns**: Multi-reflection sessions simulating real agent workflows
- **Error Recovery and Resilience**: Permission errors, system failures, and recovery validation
- **Unicode and Special Characters**: International text, emoji, and markdown character handling
- **Large Content Processing**: Performance validation for multi-KB reflection content
- **Concurrent Operations**: Race condition detection and data integrity validation
- **Telemetry Integration**: Comprehensive instrumentation validation throughout reflection operations
- **Timestamp Accuracy**: Reflection timestamping and chronological ordering validation

**Key Testing Principles:**
1. **Complete Isolation**: Each test runs in completely isolated temp directories
2. **Real Integration**: Uses actual reflection core functions with mocked configuration
3. **Comprehensive Scenarios**: Tests all edge cases including failures and recovery
4. **Telemetry Validation**: Ensures all operations are properly instrumented
5. **Cleanup Guarantees**: Always cleans up temp directories in finally blocks

**Performance and Scale Testing:**
- **Concurrent reflection operations**: Validates no data loss or corruption under load
- **Large content handling**: Tests multi-KB reflections with <1 second processing time
- **Memory efficiency**: Validates minimal memory footprint during operations
- **File system resilience**: Tests recovery from permission errors and disk issues

#### Security and Privacy Testing
- **Sensitive data filtering**: Validates automatic redaction of credentials and personal information  
- **Trace correlation security**: Ensures no sensitive data leakage through telemetry
- **Configuration validation**: Tests security of multi-exporter configurations

### Hook Execution Testing (Subtask 14.6)

Integration tests for hook execution directly write a debug post-commit hook to `.git/hooks/post-commit` and verify that it is executed after a commit, when run directly, and with `sh post-commit`. This ensures the hook is actually executed in all scenarios, not just installed. See `tests/integration/test_git_hook_integration.py` for details.

### Test Execution
```bash
# Setup test environment (first time only)
./scripts/setup_test_env.sh

# Run all tests with coverage
./scripts/run_tests.sh

# Run specific test categories  
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/test_telemetry.py  # Telemetry-specific tests

# Run tests with detailed coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Continuous Integration
The project uses GitHub Actions for automated testing:
- **Multi-version testing**: Python 3.10 and 3.11
- **Coverage reporting**: Integrated with Codecov
- **Comprehensive test execution**: All 532 tests run on every commit
- **Performance validation**: Telemetry overhead and system performance monitoring

For complete testing documentation, see **[Testing Standards](docs/testing_standards.md)**.

---

### Implementation Guidelines

### Code Organization
- Each MCP operation maps to a dedicated handler function
- Separate concerns: git operations, file I/O, text processing
- Use type hints throughout for better IDE support
- Keep functions small and single-purpose
- Follow patterns documented in **[Implementation Guide](docs/implementation-guide.md)**

### Documentation and Standards
The project includes comprehensive documentation covering all implementation patterns and standards:

- **[Architecture Overview](docs/architecture.md)** - System design and component relationships
- **[Journal Core](docs/journal-core.md)** - Core journal functionality and AI generation patterns
- **[Context Collection](docs/context-collection.md)** - Data gathering patterns and type definitions
- **[Reflection Core](docs/reflection-core.md)** - Manual reflection implementation patterns
- **[Telemetry](docs/telemetry.md)** - Observability and monitoring implementation
- **[Structured Logging](docs/structured-logging.md)** - Logging patterns with trace correlation
- **[Multi-Exporter](docs/multi-exporter.md)** - OpenTelemetry configuration patterns
- **[Testing Standards](docs/testing_standards.md)** - Complete testing strategy and patterns

### Chat History Processing
- Use simple keyword matching for decision-related discussions
- Include context around matched keywords (e.g., previous/next sentences)
- No complex NLP or structured parsing required
- Fall back gracefully if chat history is unavailable
- Implementation details in **[Context Collection](docs/context-collection.md)**

### AI Terminal History Collection
- **Primary method**: Directly prompt the AI assistant for terminal session history
- **Example prompts**: 
  - "Can you give me a history of your terminal session?"
  - "What commands did you execute during this work session?"
- **No file parsing or API integration required** - works through conversation
- Format commands chronologically as executed
- Deduplicate only adjacent identical commands (e.g., "npm test x3")
- **Always attempt collection, but fail silently if unsupported**
- When successful, provides rich context about problem-solving process
- When unavailable, journal entry proceeds without terminal section
- Complete implementation patterns in **[Context Collection](docs/context-collection.md)**

### Telemetry and Observability Implementation
- **OpenTelemetry Integration**: Comprehensive tracing, metrics, and structured logging
- **Multi-Exporter Support**: Console, OTLP, and Prometheus exporters with partial success handling
- **Performance Optimization**: Built-in circuit breakers and smart sampling for large repositories
- **Privacy Protection**: Multi-layer sensitive data filtering with production and debug modes
- **Complete implementation guide**: **[Telemetry](docs/telemetry.md)**

### Implementation Pattern Example
```python
import logging
from mcp_commit_story.structured_logging import get_correlated_logger
from mcp_commit_story.telemetry import trace_mcp_operation

# Configure structured logging with trace correlation
logger = get_correlated_logger(__name__)

@trace_mcp_operation("journal.generate_entry", attributes={"operation_type": "ai_generation"})
def format_terminal_commands(commands):
    """Deduplicate adjacent identical commands with telemetry tracking"""
    if not commands:
        logger.info("No terminal commands provided", extra={"command_count": 0})
        return []
    
    formatted = []
    current_cmd = commands[0]
    count = 1
    
    for cmd in commands[1:]:
        if cmd == current_cmd:
            count += 1
        else:
            formatted.append(f"{current_cmd} x{count}" if count > 1 else current_cmd)
            current_cmd = cmd
            count = 1
    
    # Add final command
    formatted.append(f"{current_cmd} x{count}" if count > 1 else current_cmd)
    
    logger.info("Terminal commands processed", extra={
        "input_count": len(commands),
        "output_count": len(formatted),
        "deduplication_applied": len(commands) != len(formatted)
    })
    
    return formatted

def collect_ai_terminal_history(debug=False):
    """Collect terminal history with comprehensive error handling and telemetry"""
    try:
        commands = ai_session.get_terminal_commands()
        return format_terminal_commands(commands)
    except AttributeError as e:
        if debug:
            logger.error("AI assistant doesn't support terminal commands", 
                        extra={"error_type": "feature_not_supported"})
        return None
    except APIError as e:
        if debug:
            logger.error("API error getting terminal history", 
                        extra={"error_type": "api_error", "error_details": str(e)})
        return None
    except Exception as e:
        if debug:
            logger.error("Unexpected error collecting terminal history", 
                        extra={"error_type": "unexpected_error", "error_details": str(e)})
        return None

def generate_entry(debug=False):
    """Generate journal entry with structured logging and telemetry"""
    with trace_mcp_operation("journal.entry_generation"):
        terminal_commands = collect_ai_terminal_history(debug)
        if terminal_commands:
            logger.info("Including terminal commands section", 
                       extra={"command_count": len(terminal_commands)})
            add_terminal_section(terminal_commands)
        elif debug:
            logger.info("Terminal commands section omitted", 
                       extra={"reason": "data_unavailable"})
        # Continue with other sections...
```

### Dependencies
- Minimal external dependencies
- Prefer standard library where possible
- Use well-maintained packages for specialized tasks
- **Complete dependency documentation**: See `pyproject.toml` and **[Implementation Guide](docs/implementation-guide.md)**

### Performance Considerations
- Lazy loading for large files
- Stream processing for git logs
- Reasonable timeouts for external commands
- Efficient text processing for large diffs
- **Smart sampling for large repositories** (see **[Context Collection](docs/context-collection.md)**)
- **Telemetry overhead <5% per operation** (see **[Telemetry](docs/telemetry.md)**)

### Security
- Validate all file paths to prevent directory traversal
- Sanitize git data before processing
- No shell injection vulnerabilities in subprocess calls
- **Automatic sensitive data redaction** in logs and telemetry (see **[Structured Logging](docs/structured-logging.md)**)
- **Multi-layer privacy protection** (see **[Telemetry](docs/telemetry.md)**)

---

## Future Enhancements (Out of Scope for MVP)

### Potential Features
- **Global journal** across multiple repositories tracking a developer's complete activity
- **Human terminal history integration** for capturing non-AI commands and workflows
- Scheduled summarization via background agent
- Web interface for browsing/editing entries
- Tagging system for entries and content organization
- Plugin support for detecting test coverage, benchmarks
- Rich text formatting in terminal output
- Integration with project management tools

### Integration Opportunities
- IDE plugins for manual entry creation
- Slack/Discord bot for entry sharing
- GitHub Actions for automated summaries
- Export to various formats (PDF, HTML)

#### Hyperlinked Commit Hashes in Journal Entries
- In the "Behind the Commit" section, if a remote repository is detected, the commit hash must be hyperlinked to the commit page on the remote (e.g., GitHub, GitLab).
- The system should support at least GitHub and GitLab, and fall back to plain text if no supported remote is found.
- Example:
  - Commit hash: [`cda9ef2`](https://github.com/your-org/your-repo/commit/cda9ef2)

### Configurable AI Tone/Style for Summaries
- Allow the user to control the tone and style of AI-generated summaries in journal entries by setting the `ai_tone` field in `.mcp-commit-storyrc.yaml`.
- The value of `ai_tone` can be any free-form string, such as a tone, style, persona, or creative instruction. This value will be passed directly to the AI to guide summary generation.
- There is no fixed list of supported values. Users may specify anything, e.g., "concise and technical", "in the style of a pirate", "for a 10-year-old", "sarcastic", "neutral", etc.
- If omitted, the default is "neutral and factual".
- Results may vary depending on the AI's capabilities and the specificity of the instruction.

#### Example Configuration:
```yaml
journal:
  path: journal/
  ai_tone: "like a pirate, but concise"
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
```

#### Example Values for `ai_tone`:
- "concise and technical"
- "friendly and encouraging"
- "in the style of a pirate"
- "for a 10-year-old"
- "neutral"
- "explanatory, as if teaching a beginner"

---

## Final Notes

This tool is designed to be **developer-friendly**, **minimally intrusive**, and **genuinely useful**. It prioritizes narrative fidelity and long-term story value over exhaustive tracking or rigid formats. Every entry should help the future user say: "This is what I did, how it felt, and what I learned."

### Success Criteria
- Zero friction when working normally
- Valuable output for retrospectives
- Easy to customize and extend
- Reliable operation across different environments
- **Comprehensive observability** with minimal overhead (<5% per operation)
- **Complete documentation coverage** for developers and integrators
- **High test coverage** (current: 80%, target: 90%+)
- **Robust telemetry integration** with privacy protection

### Current Project Status
**Production-Ready Core Features:**
- ✅ **532 tests** across 43 files with **80% coverage** 
- ✅ **Comprehensive documentation** covering all system components
- ✅ **OpenTelemetry integration** with multi-exporter support
- ✅ **MCP server implementation** with complete API specification
- ✅ **Context collection system** with performance optimization
- ✅ **Structured logging** with trace correlation and sensitive data protection
- ✅ **Journal generation** with AI-powered content creation
- ✅ **Reflection system** for manual journal additions

**Documentation Coverage:**
- **[Complete Technical Documentation](docs/)** - Organized by category and use case
- **[Architecture Overview](docs/architecture.md)** - System design and decisions
- **[MCP API Specification](docs/mcp-api-specification.md)** - Complete integration reference
- **[Testing Standards](docs/testing_standards.md)** - TDD methodology and test patterns
- **[Implementation Guide](docs/implementation-guide.md)** - Development patterns and best practices

### Development Workflow
1. **Test-Driven Development (TDD)** - Write failing tests first, then implement
2. Implement MCP server operations with comprehensive telemetry
3. Add OpenTelemetry instrumentation for observability
4. Create comprehensive documentation for new features
5. Implement CLI setup commands (journal-init, install-hook)
6. Add configuration system with precedence hierarchy
7. Implement AI-powered context collection and content generation
8. Create structured logging with trace correlation
9. Add multi-exporter telemetry configuration
10. Implement comprehensive tests (maintain >90% coverage target)
11. Update documentation to reflect implementation
12. Package for distribution

**Note**: The development workflow now emphasizes **documentation-driven development** alongside TDD, ensuring every feature is properly documented as it's implemented.

### Initialization Workflow
1. User runs `mcp-commit-story-setup journal-init` in their repository
2. System checks if already initialized (look for `.mcp-commit-storyrc.yaml`)
3. Creates journal directory structure using **on-demand directory creation pattern**
4. Generates default configuration file with telemetry settings
5. Prompts to install git post-commit hook
6. Displays next steps and usage instructions with documentation references

**Note**: Initialization now includes telemetry configuration and references to comprehensive documentation for next steps.

### Context Data Structures

All context collection functions return explicit Python TypedDicts, defined in `src/mcp_commit_story/context_types.py`. Complete documentation available in **[Context Collection](docs/context-collection.md)**.

```python
from typing import TypedDict, Optional, List
from datetime import datetime

class JournalContext(TypedDict):
    commit_hash: str
    commit_message: str
    timestamp: datetime
    files_changed: List[str]
    insertions: int
    deletions: int
    chat_history: Optional[List['ChatMessage']]
    terminal_commands: Optional[List[str]]
    mood_indicators: Optional[str]

class ChatMessage(TypedDict):
    speaker: str  # "Human" or "Agent"
    text: str
    timestamp: Optional[datetime]

class SummaryContext(TypedDict):
    period: str  # "day", "week", "month", "year"
    start_date: datetime
    end_date: datetime
    journal_entries: List[str]
    major_accomplishments: List[str]
    patterns: List[str]
```

These structures ensure consistent data handling across all MCP operations and provide clear contracts for context collection and journal generation. Implementation details and usage patterns are documented in **[Context Collection](docs/context-collection.md)** and **[Journal Core](docs/journal-core.md)**.

