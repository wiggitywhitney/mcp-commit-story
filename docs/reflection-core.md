# Reflection Core Module Documentation

This document describes the reflection core functionality implemented in `src/mcp_commit_story/reflection_core.py`. This module provides the infrastructure for adding manual reflections to journal entries with comprehensive telemetry, validation, and error handling.

## Table of Contents

1. [Overview](#overview)
2. [Core Functions](#core-functions)
3. [Validation System](#validation-system)
4. [Telemetry Integration](#telemetry-integration)
5. [Error Handling](#error-handling)
6. [Usage Examples](#usage-examples)

---

## Overview

The reflection core module enables users to add manual reflections to their journal entries, providing a way to capture thoughts, insights, and retrospective analysis outside of the automated commit-driven journal generation.

**Key Features**:
- **Manual Reflection Addition**: Add timestamped reflections to any date's journal
- **Comprehensive Validation**: Date format validation and future date prevention
- **Telemetry Integration**: Full OpenTelemetry tracing and metrics
- **On-Demand Directory Creation**: Follows established file system patterns
- **Error Categorization**: Structured error handling for monitoring
- **UTF-8 Support**: Proper text encoding for international characters

## Core Functions

### format_reflection()

```python
def format_reflection(reflection_text: str) -> str
```

**Purpose**: Formats reflection text with timestamp and proper Markdown structure.

**Format**:
```markdown
## Reflection (YYYY-MM-DD HH:MM:SS)

[reflection_text]
```

**Features**:
- **Automatic Timestamping**: Current timestamp in ISO format
- **Markdown Headers**: Proper H2 heading with timestamp
- **Double Newlines**: Consistent section separation as established in codebase
- **Text Preservation**: Maintains user formatting and line breaks

**Example**:
```python
formatted = format_reflection("Today I learned about JWT token validation")
# Returns: "\n\n## Reflection (2025-01-15 14:30:00)\n\nToday I learned about JWT token validation"
```

### add_reflection_to_journal()

```python
@trace_mcp_operation("reflection.add_to_journal")
def add_reflection_to_journal(journal_path: Union[str, Path], reflection_text: str) -> bool
```

**Purpose**: Adds a formatted reflection to a journal file with comprehensive telemetry.

**Key Features**:
- **On-Demand Directory Creation**: Uses `ensure_journal_directory()` utility
- **Telemetry Instrumented**: Full OpenTelemetry tracing with span attributes
- **UTF-8 Encoding**: Proper text encoding for file operations
- **Error Handling**: Comprehensive exception handling with categorization
- **Performance Monitoring**: Duration tracking and threshold warnings

**Span Attributes**:
- `file.path`: Journal filename (privacy-conscious)
- `file.extension`: File extension (.md)
- `reflection.content_length`: Reflection text length

**Returns**: `True` on success, raises exceptions on failure.

### add_manual_reflection()

```python
@trace_mcp_operation("reflection.add_manual")
def add_manual_reflection(reflection_text: str, date: str) -> Dict[str, Any]
```

**Purpose**: Main entry point for adding manual reflections with configuration loading.

**Features**:
- **Date Validation**: Comprehensive date format and range validation
- **Configuration Loading**: Automatic config loading for journal paths
- **File Path Generation**: Uses standard journal file path patterns
- **Comprehensive Response**: Structured return with status and metadata

**Parameters**:
- `reflection_text`: The reflection content (supports Markdown)
- `date`: ISO date string (YYYY-MM-DD format)

**Returns**:
```python
{
    "status": "success" | "error",
    "file_path": "journal/daily/YYYY-MM-DD-journal.md",  # on success
    "error": "Error description"  # on failure
}
```

## Validation System

### Date Validation

The `_validate_reflection_date()` function provides comprehensive date validation:

**Format Validation**:
```python
if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
    raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
```

**Date Parsing**:
```python
try:
    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
except ValueError as e:
    raise ValueError(f"Invalid date: {date_str}. {str(e)}")
```

**Future Date Prevention**:
```python
if parsed_date > date.today():
    raise ValueError(f"Future date not allowed: {date_str}")
```

**Validation Rules**:
- **Format**: Must be YYYY-MM-DD (e.g., "2025-01-15")
- **Valid Date**: Must be a real calendar date
- **Time Constraint**: Cannot be in the future
- **Range**: Must be today or any past date

### Error Categorization

The `_categorize_reflection_error()` function provides structured error classification:

```python
def _categorize_reflection_error(error: Exception) -> str:
    if isinstance(error, PermissionError):
        return "permission_error"
    elif isinstance(error, OSError):
        return "file_system_error"
    elif isinstance(error, UnicodeError):
        return "encoding_error"
    elif isinstance(error, ValueError):
        if "date" in str(error).lower():
            return "invalid_date_format"
        return "validation_error"
    else:
        return "unknown_error"
```

**Error Categories**:
- `permission_error`: File system permissions
- `file_system_error`: General file operations
- `encoding_error`: Text encoding issues
- `invalid_date_format`: Date validation failures
- `validation_error`: General validation issues
- `unknown_error`: Unexpected errors

## Telemetry Integration

### Operation Tracing

All reflection operations are instrumented with OpenTelemetry tracing:

```python
@trace_mcp_operation("reflection.add_to_journal", attributes={
    "operation_type": "file_write", 
    "content_type": "reflection",
    "file_type": "markdown"
})
```

**Trace Attributes**:
- `operation_type`: Type of operation (file_write, manual_input)
- `content_type`: Content type (reflection)
- `file_type`: File format (markdown)
- `file.path`: Journal filename
- `reflection.content_length`: Content size

### Metrics Recording

The `_record_reflection_metrics()` function provides comprehensive metrics:

**Performance Monitoring**:
```python
PERFORMANCE_THRESHOLD = 0.1  # 100ms
if duration > PERFORMANCE_THRESHOLD:
    logging.warning(f"Reflection operation '{operation}' took {duration:.3f}s")
```

**Operation Counters**:
```python
metrics.record_counter('mcp.reflection.operations_total', **counter_attrs)
```

**Duration Tracking**:
```python
metrics.record_operation_duration(
    'mcp.reflection.duration_seconds',
    duration,
    operation=operation,
    operation_type='manual_input'
)
```

**Metric Attributes**:
- `operation`: Specific operation name
- `operation_type`: manual_input, file_write
- `content_type`: reflection
- `status`: success, error
- `error_category`: Specific error type (if failed)
- `content_length`: Reflection size

## Error Handling

### Exception Strategy

The reflection system uses structured exception handling:

**Validation Errors**:
```python
try:
    _validate_reflection_date(date)
except ValueError as e:
    return {"status": "error", "error": str(e)}
```

**File Operation Errors**:
```python
except Exception as e:
    error_category = _categorize_reflection_error(e)
    _record_reflection_metrics("add_to_journal", duration, False, error_category=error_category)
    raise
```

**Error Recovery**:
- **Graceful Degradation**: Clear error messages for user feedback
- **Telemetry Preservation**: Errors are recorded for monitoring
- **Status Reporting**: Structured response format for API integration

### Common Error Scenarios

**Permission Errors**:
```
PermissionError: [Errno 13] Permission denied: 'journal/daily/2025-01-15-journal.md'
```

**File System Errors**:
```
OSError: [Errno 28] No space left on device
```

**Date Validation Errors**:
```
ValueError: Invalid date format: 2025-1-15. Expected YYYY-MM-DD
ValueError: Future date not allowed: 2025-12-31
```

**Encoding Errors**:
```
UnicodeError: 'utf-8' codec can't decode byte 0xff in position 0
```

## Usage Examples

### Basic Reflection Addition

```python
from mcp_commit_story.reflection_core import add_manual_reflection

result = add_manual_reflection(
    reflection_text="Today I learned about JWT token validation and refresh patterns.",
    date="2025-01-15"
)

if result["status"] == "success":
    print(f"Reflection added to {result['file_path']}")
else:
    print(f"Error: {result['error']}")
```

### Direct File Operations

```python
from mcp_commit_story.reflection_core import add_reflection_to_journal, format_reflection

# Format a reflection
formatted = format_reflection("Great debugging session today!")

# Add to specific file
try:
    success = add_reflection_to_journal("journal/daily/2025-01-15-journal.md", formatted)
    print("Reflection added successfully")
except Exception as e:
    print(f"Failed to add reflection: {e}")
```

### Configuration-Aware Addition

```python
from mcp_commit_story.reflection_core import add_manual_reflection

# The function automatically loads configuration and determines journal paths
result = add_manual_reflection(
    reflection_text="""
    ## Key Insights
    - JWT access tokens should be short-lived (15-30 minutes)
    - Refresh tokens can be longer-lived but should rotate
    - Always validate token signatures and expiration
    
    ## Next Steps
    - Implement refresh token rotation
    - Add rate limiting to auth endpoints
    """,
    date="2025-01-15"
)
```

### Error Handling Example

```python
from mcp_commit_story.reflection_core import add_manual_reflection

# Handle various error scenarios
try:
    result = add_manual_reflection("My reflection", "2025-13-01")  # Invalid date
    if result["status"] == "error":
        print(f"Validation error: {result['error']}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Check for future dates
result = add_manual_reflection("Future thoughts", "2026-01-01")
# Returns: {"status": "error", "error": "Future date not allowed: 2026-01-01"}
```

## Integration Points

### MCP Server Integration

The reflection core is used by MCP operations:
- `journal/add-reflection`: Primary entry point via MCP
- Structured responses compatible with MCP protocol
- Comprehensive telemetry for MCP operation monitoring

### File System Integration

- **On-Demand Directories**: Uses `ensure_journal_directory()` utility
- **Standard Paths**: Uses `get_journal_file_path()` for consistent naming
- **UTF-8 Encoding**: Proper text encoding for international support

### Configuration System

- **Config Loading**: Automatic configuration loading via `load_config()`
- **Journal Paths**: Respects configured journal directory structure
- **Default Handling**: Graceful fallback to default configurations

## See Also

- **[Journal Core](journal-core.md)** - Main journal entry generation system
- **[Context Collection](context-collection.md)** - Automated context gathering
- **[MCP API Specification](mcp-api-specification.md)** - MCP operation definitions
- **[Telemetry](telemetry.md)** - Comprehensive monitoring and tracing 