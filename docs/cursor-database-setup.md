# Cursor Database Setup and Configuration

This guide explains how to set up and configure access to Cursor's chat database for automated journal generation.

## Overview

The MCP Commit Story project reads Cursor's chat history from SQLite databases to generate journal entries. The system automatically discovers and connects to recent Cursor workspace databases across different platforms.

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
- Implementing custom filtering in your MCP configuration
- Monitoring system performance during database scanning operations 