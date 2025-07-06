# Cursor Chat Integration Setup Guide

This guide explains how to set up and configure access to Cursor's chat database for automated journal generation.

## Overview

The chat integration system reads Cursor's conversation history from SQLite databases to generate rich journal entries. The system automatically discovers and connects to recent Cursor workspace databases across different platforms.

## Platform-Specific Database Locations

### macOS
- **Default Path**: `~/Library/Application Support/Cursor/User/workspaceStorage/[workspace-hash]/state.vscdb`
- **Environment Override**: Set `CURSOR_WORKSPACE_PATH` to specify a custom directory

### Windows
- **Default Path**: `%APPDATA%\Cursor\User\workspaceStorage\[workspace-hash]\state.vscdb`
- **Environment Override**: Set `CURSOR_WORKSPACE_PATH` to specify a custom directory

### Linux
- **Default Path**: `~/.config/Cursor/User/workspaceStorage/[workspace-hash]/state.vscdb`
- **Environment Override**: Set `CURSOR_WORKSPACE_PATH` to specify a custom directory

### WSL (Windows Subsystem for Linux)
- **Automatic Detection**: The system detects WSL and searches Windows paths from within the Linux environment
- **Fallback**: Falls back to Linux paths if Windows paths are not accessible

## Database Discovery Process

The system automatically discovers recent Cursor databases using the following process:

1. **Platform Detection**: Identifies the current operating system and WSL status
2. **Path Resolution**: Determines appropriate search directories based on platform
3. **Database Search**: Looks for `state.vscdb` files in workspace storage directories
4. **Recency Filter**: Only considers databases modified within the last 48 hours
5. **Validation**: Verifies each database is readable and contains valid SQLite data
6. **Selection**: Returns the most recently modified valid database

### Example Commands

Test database discovery:
```bash
# Check if databases can be found
python -c "from mcp_commit_story.cursor_db.connection import get_cursor_chat_database; print(get_cursor_chat_database())"

# List all recent workspace databases
python -c "from mcp_commit_story.cursor_db.connection import query_multiple_databases; print([db[0] for db in query_multiple_databases('SELECT name FROM sqlite_master LIMIT 1')])"
```

Expected output when databases are found:
```
/Users/username/Library/Application Support/Cursor/User/workspaceStorage/abc123def456/state.vscdb
```

## Error Handling and Troubleshooting

The system provides comprehensive error handling with context-rich error messages and troubleshooting guidance.

### Common Error Types

#### Database Not Found Errors
**Symptoms**: `CursorDatabaseNotFoundError` with messages about no valid databases found

**Common Causes**:
- Cursor hasn't been run recently in any workspace (48+ hours)
- No workspaces contain chat history
- Database files are in unexpected locations
- Incorrect environment variable configuration

**Troubleshooting Steps**:
1. **Verify Cursor Usage**: Ensure Cursor has been run recently in a workspace with chat activity
2. **Check Workspace Activity**: Open a workspace in Cursor and have some chat interactions
3. **Verify Paths**: Check that the expected database locations exist:
   ```bash
   # macOS
   ls -la ~/Library/Application\ Support/Cursor/User/workspaceStorage/*/state.vscdb
   
   # Linux
   ls -la ~/.config/Cursor/User/workspaceStorage/*/state.vscdb
   
   # Windows (PowerShell)
   Get-ChildItem "$env:APPDATA\Cursor\User\workspaceStorage\*\state.vscdb"
   ```
4. **Environment Override**: Set `CURSOR_WORKSPACE_PATH` if databases are in non-standard locations
5. **File Permissions**: Ensure the process has read access to Cursor's data directories

#### Database Access Errors
**Symptoms**: `CursorDatabaseAccessError` with permission or file access messages

**Common Causes**:
- Insufficient file permissions
- Database locked by another process
- Cursor currently running and using the database
- File system permissions issues

**Troubleshooting Steps**:
1. **Check Permissions**: Verify read access to database files
2. **Close Cursor**: Ensure Cursor is not actively using the database
3. **Process Check**: Look for other processes accessing the database files
4. **User Permissions**: Ensure the current user has access to Cursor's data directory

#### Database Schema Errors
**Symptoms**: `CursorDatabaseSchemaError` with messages about missing tables or columns

**Common Causes**:
- Database from different Cursor version
- Corrupted or incomplete database
- Database doesn't contain chat data

**Troubleshooting Steps**:
1. **Version Check**: Ensure Cursor is up to date
2. **Database Integrity**: Try a different workspace database
3. **Recreate Data**: Open Cursor and have new chat interactions to create fresh data
4. **Manual Inspection**: Use SQLite tools to examine database structure:
   ```bash
   sqlite3 path/to/state.vscdb ".schema"
   ```

#### Query Errors
**Symptoms**: `CursorDatabaseQueryError` with SQL syntax or parameter errors

**Common Causes**:
- Invalid SQL syntax in queries
- Parameter count mismatch
- Database corruption

**Troubleshooting Steps**:
1. **Syntax Check**: Verify SQL query syntax is valid SQLite
2. **Parameter Count**: Ensure parameter count matches placeholders (?)
3. **Database Test**: Try simple queries first:
   ```bash
   sqlite3 path/to/state.vscdb "SELECT COUNT(*) FROM sqlite_master;"
   ```

### Environment Variable Configuration

Set `CURSOR_WORKSPACE_PATH` to override default search locations:

```bash
# Point to specific directory containing workspace folders
export CURSOR_WORKSPACE_PATH="/custom/path/to/cursor/workspaces"

# Point to specific database file
export CURSOR_WORKSPACE_PATH="/path/to/specific/state.vscdb"
```

### Logging and Debugging

Enable debug logging to see detailed discovery process:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from mcp_commit_story.cursor_db.connection import get_cursor_chat_database
db_path = get_cursor_chat_database()
```

### Advanced Troubleshooting

#### Manual Database Inspection
```bash
# Check database file validity
sqlite3 path/to/state.vscdb "PRAGMA integrity_check;"

# List available tables
sqlite3 path/to/state.vscdb ".tables"

# Check for chat-related tables
sqlite3 path/to/state.vscdb "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%chat%';"
```

#### Platform-Specific Issues

**WSL Users**: If auto-detection fails, manually set the Windows path:
```bash
export CURSOR_WORKSPACE_PATH="/mnt/c/Users/username/AppData/Roaming/Cursor/User/workspaceStorage"
```

**macOS Users**: If databases aren't found, check for permission issues with Application Support:
```bash
ls -la ~/Library/Application\ Support/Cursor/
```

**Linux Users**: Verify XDG config directory setup:
```bash
echo $XDG_CONFIG_HOME
ls -la ~/.config/Cursor/
```

## Performance Considerations

- **No Caching**: Database connections are created fresh each time for data consistency
- **48-Hour Filter**: Only recent databases are considered to improve discovery speed
- **Auto-Discovery**: Platform detection and path search add minimal overhead
- **Connection Pooling**: Not implemented - SQLite connections are lightweight

For high-frequency usage, consider caching the discovered database path in your application rather than running discovery repeatedly.

## System Monitoring

The platform detection system includes comprehensive monitoring capabilities for tracking performance, errors, and system behavior.

### Monitoring Features

**Performance Monitoring**:
- Function-level performance thresholds (50ms - 1000ms depending on operation complexity)
- Duration tracking with threshold breach detection
- Memory usage monitoring for large workspace enumeration operations
- Performance overhead constraint validation (under 5% impact)

**Error Categorization**:
- **Platform Detection**: `platform_detection.detection_failure`
- **Path Operations**: `path_operations.path_not_found`, `path_operations.invalid_path_format`, `path_operations.permission_denied`
- **Workspace Validation**: `workspace_validation.workspace_corrupted`, `workspace_validation.database_missing`, `workspace_validation.no_valid_workspaces`

**Cache Performance**:
- Cache hit/miss ratios for path validation
- Cache effectiveness monitoring

**Workspace Metrics**:
- Database presence and count tracking
- Valid database validation metrics
- Workspace enumeration efficiency

### Monitoring Configuration Examples

**Enable Monitoring**:
```python
import logging
from mcp_commit_story.telemetry import configure_telemetry

# Enable telemetry with OpenTelemetry
configure_telemetry(
    service_name="cursor-platform-detection",
    endpoint="http://localhost:4317"  # OTLP endpoint
)

# Enable debug logging to see telemetry data
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("mcp_commit_story.cursor_db.platform").setLevel(logging.DEBUG)
```

**Monitor Platform Detection Performance**:
```python
from mcp_commit_story.cursor_db.platform import detect_platform, get_cursor_workspace_paths
from mcp_commit_story.telemetry import get_mcp_metrics

# Platform operations are automatically instrumented
platform = detect_platform()  # Monitored: duration, errors, platform type
paths = get_cursor_workspace_paths()  # Monitored: workspace count, memory usage

# Access metrics programmatically
metrics = get_mcp_metrics()
print(f"Platform detection calls: {metrics.get('platform_detection_calls', 0)}")
```

**Performance Threshold Configuration**:
```python
# Default thresholds (in milliseconds):
TELEMETRY_THRESHOLDS = {
    "detect_platform": 50,           # Platform identification
    "get_cursor_workspace_paths": 100,  # Workspace path enumeration  
    "validate_workspace_path": 200,     # Individual path validation
    "find_valid_workspace_paths": 1000, # Full workspace discovery
    "get_primary_workspace_path": 200   # Primary workspace selection
}
```

### Monitoring Integration

**OpenTelemetry Integration**:
The platform detection module exports traces and metrics in OpenTelemetry format, compatible with:
- Jaeger for distributed tracing
- Prometheus for metrics collection
- Grafana for dashboards and alerts
- DataDog, New Relic, and other APM tools

**Custom Metrics Dashboard**:
Key metrics to monitor:
- `platform_detection_duration_ms`: Platform identification time
- `workspace_discovery_duration_ms`: Workspace enumeration time
- `workspace_count`: Number of workspaces discovered
- `valid_workspace_count`: Number of valid workspaces found
- `cache_hit_ratio`: Path validation cache effectiveness
- `memory_usage_mb`: Memory consumption during operations
- `error_rate_by_category`: Error frequency by type

**Alerting Recommendations**:
- Alert on detection duration > 1000ms (indicates performance issues)
- Alert on error_rate > 5% (indicates systematic problems)
- Alert on valid_workspace_count = 0 (indicates no accessible workspaces)
- Alert on memory_usage_mb > 100MB (indicates memory leak potential)

### Troubleshooting with Monitoring

**Performance Issues**:
```python
# Check performance metrics
from mcp_commit_story.telemetry import get_tracer

tracer = get_tracer()
with tracer.start_as_current_span("debug_platform_detection") as span:
    # Your platform detection code here
    span.set_attribute("debug.enabled", True)
```

**Error Investigation**:
Monitoring provides detailed error context:
- Platform type and version information
- File system access patterns
- Memory usage during failures
- Performance degradation indicators

**Production Monitoring**:
In production environments, monitor these key indicators:
- Workspace discovery success rate > 95%
- Average detection time < 200ms
- Cache hit ratio > 80%
- Memory growth patterns stable

## Testing and Validation

The chat integration system includes comprehensive testing capabilities to verify end-to-end functionality across platforms and scenarios.

### Running Tests

```bash
# Run all chat integration tests
python -m pytest tests/integration/test_cursor_db_integration.py -v

# Run specific test categories
python -m pytest tests/integration/test_cursor_db_integration.py::TestCursorDbIntegration::test_end_to_end_chat_data_extraction_workflow -v
python -m pytest tests/integration/test_cursor_db_integration.py::TestCursorDbPerformance -v
```

### Test Coverage Areas

**End-to-End Workflows**:
- Complete database discovery → validation → query workflows
- Cross-platform platform detection and path resolution
- Multiple database discovery and selection logic
- Context manager resource cleanup and lifecycle

**Performance Benchmarks**:
- Query execution time < 100ms
- Database connection time < 50ms  
- Batch query execution < 200ms
- Large workspace discovery < 1000ms
- Concurrent access simulation < 500ms

**Error Handling**:
- Platform detection failures
- Database not found scenarios
- Access permission issues
- Schema validation errors

**Integration Points**:
- Platform detection → workspace path resolution
- Database discovery → validation → connection
- SQL querying → result processing
- Error propagation through complete call stack

### Testing Framework

The tests use a comprehensive testing framework that:

- Creates realistic SQLite databases with chat data structure
- Simulates cross-platform environment scenarios
- Mocks file system operations without requiring real Cursor installation
- Provides performance benchmarking with controlled database sizes
- Tests error conditions and edge cases safely

This allows thorough testing of integration workflows without dependencies on actual Cursor installations or workspace databases.

## Security Considerations

- **Read-Only Access**: The system only reads from Cursor databases, never modifies them
- **Sensitive Data**: Error messages automatically redact sensitive information like passwords and API keys
- **File Permissions**: Respects system file permissions and fails gracefully when access is denied
- **No Network Access**: All operations are local file system access only

## Supported Cursor Versions

The system is compatible with:
- Cursor Stable (all versions)
- Cursor Insiders (all versions)
- Portable Cursor installations
- Custom Cursor installations with standard workspace structure

## Advanced Configuration

### Multiple Workspace Support
If you work with multiple Cursor workspaces, the system will automatically discover all available workspace storage directories and process them in priority order.

### Network Drive Support
The system supports Cursor installations on network drives, though performance may be reduced. Ensure proper network permissions and stable connectivity.

### Performance Optimization
For large workspace directories (>1000 workspace folders), consider:
- Using the environment variable override to specify exact paths
- Implementing custom filtering in your application configuration
- Monitoring system performance during database scanning operations 