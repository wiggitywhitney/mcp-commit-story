# Multi-Exporter Configuration System Documentation

This document describes the multi-exporter configuration system implemented in `src/mcp_commit_story/multi_exporter.py`. This module provides enhanced OpenTelemetry exporter configuration with environment variable precedence, partial success handling, and comprehensive validation.

## Table of Contents

1. [Overview](#overview)
2. [Configuration Management](#configuration-management)
3. [Supported Exporters](#supported-exporters)
4. [Environment Variable Precedence](#environment-variable-precedence)
5. [Validation System](#validation-system)
6. [Partial Success Handling](#partial-success-handling)
7. [Usage Examples](#usage-examples)

---

## Overview

The multi-exporter system provides flexible OpenTelemetry configuration supporting multiple export destinations simultaneously:

- **Console Exporter**: Development and debugging output
- **OTLP Exporter**: OpenTelemetry Protocol for observability platforms
- **Prometheus Exporter**: Metrics collection for monitoring systems

**Key Features**:
- **Multiple Exporters**: Configure multiple destinations simultaneously
- **Environment Precedence**: Smart environment variable handling
- **Partial Success**: Continue operation even if some exporters fail
- **Comprehensive Validation**: Prevent misconfigurations
- **Protocol Support**: Both gRPC and HTTP OTLP protocols

## Configuration Management

### ExporterConfigManager

The `ExporterConfigManager` class provides centralized configuration management:

```python
class ExporterConfigManager:
    def resolve_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Resolves configuration with environment variable precedence
    
    def validate_configuration(self, config: Dict[str, Any]) -> None:
        # Validates configuration with comprehensive rules
```

**Core Responsibilities**:
- **Configuration Resolution**: Merge defaults, config files, and environment variables
- **Validation**: Comprehensive rule-based validation
- **Environment Integration**: Smart environment variable handling
- **Error Prevention**: Catch configuration issues early

### Default Configuration

```python
DEFAULT_CONFIG = {
    "telemetry": {
        "enabled": True,
        "service_name": "mcp-commit-story",
        "exporters": {
            "console": {
                "enabled": True,
                "traces": True,
                "metrics": True
            },
            "otlp": {
                "enabled": False,
                "endpoint": "http://localhost:4317",
                "protocol": "grpc",
                "headers": {},
                "timeout": 30,
                "traces": True,
                "metrics": True
            },
            "prometheus": {
                "enabled": False,
                "port": 8888,
                "endpoint": "/metrics",
                "metrics": True,
                "traces": False
            }
        }
    }
}
```

**Default Behavior**:
- **Console Enabled**: Safe default for development
- **OTLP Disabled**: Requires explicit configuration
- **Prometheus Disabled**: Opt-in for production monitoring
- **Conservative Settings**: Sensible defaults that work everywhere

## Supported Exporters

### Console Exporter

**Purpose**: Development and debugging output to console/stdout.

**Configuration**:
```python
"console": {
    "enabled": True,
    "traces": True,    # Export trace data
    "metrics": True    # Export metrics data
}
```

**Use Cases**:
- **Development**: Local debugging and testing
- **CI/CD**: Build pipeline observability
- **Troubleshooting**: Quick diagnostic output

### OTLP Exporter

**Purpose**: Export to OpenTelemetry-compatible observability platforms.

**Configuration**:
```python
"otlp": {
    "enabled": True,
    "endpoint": "https://otlp.example.com:4317",
    "protocol": "grpc",  # or "http"
    "headers": {
        "authorization": "Bearer token123",
        "x-api-key": "api-key-value"
    },
    "timeout": 30,
    "traces": True,
    "metrics": True
}
```

**Supported Protocols**:
- **gRPC**: High-performance binary protocol
- **HTTP**: RESTful HTTP/JSON protocol
- **Auto-Selection**: Automatic exporter selection based on protocol

**Platform Support**:
- Jaeger
- Zipkin
- Honeycomb
- New Relic
- Datadog
- Custom OTLP receivers

### Prometheus Exporter

**Purpose**: Expose metrics for Prometheus scraping.

**Configuration**:
```python
"prometheus": {
    "enabled": True,
    "port": 8888,
    "endpoint": "/metrics",
    "metrics": True,     # Must be true for Prometheus
    "traces": False      # Prometheus doesn't support traces
}
```

**Features**:
- **HTTP Server**: Built-in metrics HTTP server
- **Standard Format**: Prometheus text exposition format
- **Scrape Target**: Discoverable metrics endpoint
- **Production Ready**: High-performance metrics collection

## Environment Variable Precedence

### Precedence Hierarchy

The configuration system resolves settings in order of precedence (highest to lowest):

1. **MCP-Specific Variables** (highest priority)
2. **Standard OpenTelemetry Variables**
3. **Configuration Files**
4. **Built-in Defaults** (lowest priority)

### Standard OpenTelemetry Variables

```python
standard_otel_vars = {
    'OTEL_EXPORTER_OTLP_ENDPOINT': ('telemetry.exporters.otlp.endpoint', str),
    'OTEL_EXPORTER_OTLP_HEADERS': ('telemetry.exporters.otlp.headers', header_parser),
    'OTEL_EXPORTER_OTLP_TIMEOUT': ('telemetry.exporters.otlp.timeout', int),
    'OTEL_SERVICE_NAME': ('telemetry.service_name', str),
}
```

### MCP-Specific Variables

```python
mcp_specific_vars = {
    'MCP_PROMETHEUS_PORT': ('telemetry.exporters.prometheus.port', int),
    'MCP_CONSOLE_ENABLED': ('telemetry.exporters.console.enabled', bool_parser),
    'MCP_OTLP_ENDPOINT': ('telemetry.exporters.otlp.endpoint', str),
    'MCP_OTLP_ENABLED': ('telemetry.exporters.otlp.enabled', bool_parser),
    'MCP_PROMETHEUS_ENABLED': ('telemetry.exporters.prometheus.enabled', bool_parser),
}
```

**Override Behavior**:
- **MCP variables override OTel variables**: `MCP_OTLP_ENDPOINT` overrides `OTEL_EXPORTER_OTLP_ENDPOINT`
- **Type Conversion**: Automatic type conversion with error handling
- **Validation**: Invalid values logged but don't crash the system

### Environment Variable Examples

```bash
# Standard OpenTelemetry
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io:443"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=your-api-key"
export OTEL_SERVICE_NAME="my-journal-service"

# MCP-specific (higher priority)
export MCP_OTLP_ENABLED="true"
export MCP_PROMETHEUS_ENABLED="true"
export MCP_PROMETHEUS_PORT="9090"
export MCP_CONSOLE_ENABLED="false"
```

## Validation System

### Comprehensive Validation Rules

The `validate_configuration()` method enforces configuration correctness:

**Prometheus Validation**:
```python
# Port range validation (1-65535)
if 'port' in prometheus_config:
    port = prometheus_config['port']
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValidationError("Port must be between 1 and 65535")

# Endpoint must start with '/'
if 'endpoint' in prometheus_config:
    endpoint = prometheus_config['endpoint']
    if not isinstance(endpoint, str) or not endpoint.startswith('/'):
        raise ValidationError("Endpoint must start with '/'")
```

**OTLP Validation**:
```python
# Protocol must be 'grpc' or 'http'
if 'protocol' in otlp_config:
    protocol = otlp_config['protocol']
    if protocol not in ['grpc', 'http']:
        raise ValidationError("Protocol must be 'grpc' or 'http'")

# Timeout must be positive integer
if 'timeout' in otlp_config:
    timeout = otlp_config['timeout']
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValidationError("Timeout must be a positive integer")
```

### Validation Error Types

```python
class ValidationError(Exception):
    """Raised when configuration validation fails."""
    pass

class ExporterConfigurationError(Exception):
    """Raised when exporter configuration fails."""
    pass
```

**Error Handling**:
- **Early Validation**: Catch errors before exporter setup
- **Clear Messages**: Actionable error descriptions
- **Graceful Degradation**: Continue with valid exporters

## Partial Success Handling

### PartialSuccessResult

The `PartialSuccessResult` class tracks configuration outcomes:

```python
@dataclass
class PartialSuccessResult:
    status: str  # "success", "partial_success", "failure"
    successful_exporters: List[str] = field(default_factory=list)
    failed_exporters: Dict[str, Dict[str, str]] = field(default_factory=dict)
```

**Status Types**:
- **success**: All enabled exporters configured successfully
- **partial_success**: Some exporters failed, but at least one succeeded
- **failure**: All exporters failed or telemetry disabled

### Exporter Setup Functions

Each exporter has a dedicated setup function that handles failures gracefully:

```python
def setup_console_exporter(config: Dict[str, Any]) -> List[...]:
    """Set up console exporter for traces and metrics."""
    processors = []
    console_config = config['telemetry']['exporters']['console']
    
    if console_config.get('traces', True):
        span_exporter = ConsoleSpanExporter()
        processors.append(BatchSpanProcessor(span_exporter))
        logger.info("Console trace exporter configured")
    
    if console_config.get('metrics', True):
        metric_exporter = ConsoleMetricExporter()
        processors.append(PeriodicExportingMetricReader(metric_exporter))
        logger.info("Console metric exporter configured")
    
    return processors
```

### Failure Recovery

The `configure_exporters()` function implements comprehensive failure handling:

```python
def configure_exporters(config: Dict[str, Any]) -> PartialSuccessResult:
    result = PartialSuccessResult(status="success")
    all_processors = []
    
    # Try each exporter independently
    for exporter_name, setup_func in exporters.items():
        try:
            if is_enabled(config, exporter_name):
                processors = setup_func(config)
                all_processors.extend(processors)
                result.successful_exporters.append(exporter_name)
        except Exception as e:
            result.failed_exporters[exporter_name] = {
                "error": str(e),
                "category": categorize_error(e)
            }
    
    # Determine final status
    if result.failed_exporters:
        if result.successful_exporters:
            result.status = "partial_success"
        else:
            result.status = "failure"
    
    return result
```

**Benefits**:
- **Fault Isolation**: One exporter failure doesn't affect others
- **Operational Continuity**: System continues with available exporters
- **Detailed Reporting**: Clear indication of what worked and what failed
- **Debugging Support**: Error categorization for troubleshooting

## Usage Examples

### Basic Configuration

```python
from mcp_commit_story.multi_exporter import ExporterConfigManager, configure_exporters

# Basic configuration with defaults
config = {
    "telemetry": {
        "enabled": True,
        "exporters": {
            "console": {"enabled": True},
            "otlp": {"enabled": False},
            "prometheus": {"enabled": False}
        }
    }
}

manager = ExporterConfigManager()
resolved_config = manager.resolve_configuration(config)
manager.validate_configuration(resolved_config)

result = configure_exporters(resolved_config)
print(f"Status: {result.status}")
print(f"Successful: {result.successful_exporters}")
```

### Production Configuration

```python
# Production configuration with multiple exporters
config = {
    "telemetry": {
        "enabled": True,
        "service_name": "journal-production",
        "exporters": {
            "console": {
                "enabled": False  # Disable console in production
            },
            "otlp": {
                "enabled": True,
                "endpoint": "https://api.honeycomb.io:443",
                "protocol": "grpc",
                "headers": {
                    "x-honeycomb-team": "your-api-key"
                },
                "timeout": 10
            },
            "prometheus": {
                "enabled": True,
                "port": 8888,
                "endpoint": "/metrics"
            }
        }
    }
}

result = configure_exporters(config)
if result.status == "success":
    logger.info("All exporters configured successfully")
elif result.status == "partial_success":
    logger.warning(f"Some exporters failed: {result.failed_exporters}")
else:
    logger.error("All exporters failed")
```

### Environment Variable Override

```python
import os

# Set environment variables (can be done in docker, k8s, etc.)
os.environ['MCP_OTLP_ENABLED'] = 'true'
os.environ['MCP_OTLP_ENDPOINT'] = 'https://custom-otlp.example.com:4317'
os.environ['MCP_PROMETHEUS_ENABLED'] = 'true'
os.environ['MCP_PROMETHEUS_PORT'] = '9090'

# Environment variables will override config file settings
manager = ExporterConfigManager()
resolved_config = manager.resolve_configuration(base_config)

# Check what was actually resolved
otlp_config = resolved_config['telemetry']['exporters']['otlp']
print(f"OTLP endpoint: {otlp_config['endpoint']}")  # Shows environment value
print(f"OTLP enabled: {otlp_config['enabled']}")    # Shows environment value
```

### Error Handling

```python
from mcp_commit_story.multi_exporter import ValidationError, ExporterConfigurationError

try:
    # Invalid configuration
    bad_config = {
        "telemetry": {
            "exporters": {
                "prometheus": {
                    "enabled": True,
                    "port": 99999,  # Invalid port
                    "endpoint": "metrics"  # Missing leading slash
                }
            }
        }
    }
    
    manager = ExporterConfigManager()
    manager.validate_configuration(bad_config)
    
except ValidationError as e:
    print(f"Configuration error: {e}")
    # Handle validation error - fix config or use defaults

try:
    result = configure_exporters(config)
    if result.status == "failure":
        # Handle complete failure
        logger.error("No exporters could be configured")
    elif result.status == "partial_success":
        # Handle partial failure
        logger.warning(f"Some exporters failed: {result.failed_exporters}")
        
except ExporterConfigurationError as e:
    print(f"Exporter setup error: {e}")
    # Handle setup errors
```

## Integration Points

### Telemetry System Integration

The multi-exporter system integrates with the main telemetry system:

```python
from mcp_commit_story.telemetry import setup_telemetry
from mcp_commit_story.multi_exporter import configure_exporters

def setup_comprehensive_telemetry(config):
    # Configure exporters first
    exporter_result = configure_exporters(config)
    
    if exporter_result.status != "failure":
        # Setup telemetry with configured exporters
        setup_telemetry(config)
        return True
    else:
        logger.error("Cannot setup telemetry: no exporters available")
        return False
```

### Configuration System Integration

- **Config Loading**: Integrates with main configuration system
- **Hot Reloading**: Supports dynamic configuration updates
- **Environment Variables**: Respects standard OTel and MCP-specific variables

### MCP Server Integration

- **Server Startup**: Configured during MCP server initialization
- **Request Tracing**: All MCP operations automatically instrumented
- **Health Monitoring**: Exporter health affects overall system health

## See Also

- **[Telemetry](telemetry.md)** - Complete telemetry and monitoring system
- **[Structured Logging](structured-logging.md)** - Logging integration with telemetry
- **[Server Setup](server_setup.md)** - MCP server configuration and deployment
- **[Implementation Guide](implementation-guide.md)** - Development patterns and practices 