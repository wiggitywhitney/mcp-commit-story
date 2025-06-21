# Cursor Database Setup Guide

This guide provides platform-specific instructions for setting up Cursor SQLite database integration with MCP Commit Story.

## Overview

MCP Commit Story automatically detects and reads Cursor's SQLite workspace databases (`state.vscdb` files) to extract chat history for journal generation. The system supports Windows, macOS, Linux, and WSL environments with automatic platform detection and focuses on recently active workspaces (modified within the last 48 hours).

## Platform-Specific Locations

### macOS
**Default Location:**
```
~/Library/Application Support/Cursor/User/workspaceStorage/
```

**Setup Requirements:**
- Cursor must be installed via the standard installer
- No additional configuration required
- System automatically detects the standard location

### Windows
**Default Locations:**
```
%APPDATA%\Cursor\User\workspaceStorage\
C:\Users\{username}\AppData\Roaming\Cursor\User\workspaceStorage\
```

**Setup Requirements:**
- Cursor installed in standard location
- Ensure APPDATA environment variable is set (default on Windows)
- No additional configuration required

### Linux
**Default Locations:**
```
~/.config/Cursor/User/workspaceStorage/
$XDG_CONFIG_HOME/Cursor/User/workspaceStorage/
```

**Setup Requirements:**
- Cursor installed via AppImage, Snap, or package manager
- Standard XDG configuration directory structure
- No additional configuration required

### WSL (Windows Subsystem for Linux)
**Default Locations:**
```
/mnt/c/Users/{username}/AppData/Roaming/Cursor/User/workspaceStorage/
/mnt/C/Users/{username}/AppData/Roaming/Cursor/User/workspaceStorage/
~/.config/Cursor/User/workspaceStorage/ (if Cursor installed in WSL)
```

**Setup Requirements:**
- Windows drives mounted under `/mnt/c/` (standard WSL configuration)
- Cursor installed on Windows host system
- Read permissions for Windows user directories

## Custom Configuration

### Environment Variable Override
Set a custom workspace path using the environment variable:

```bash
export CURSOR_WORKSPACE_PATH="/path/to/custom/workspace"
```

This takes priority over all platform-specific default locations.

### Manual Path Configuration
If automatic detection fails, you can override the workspace path programmatically:

```python
from mcp_commit_story.cursor_db.connection import get_cursor_chat_database

# Connect to specific database file
conn = get_cursor_chat_database(user_override_path="/path/to/specific/state.vscdb")
```

**Note**: The system expects `state.vscdb` files specifically, not general SQLite databases.

## Database Connection Troubleshooting

### Connection Issues

**No Valid Databases Found**
If you receive the error "No valid Cursor workspace databases found":

1. **Check Recent Activity**: The system only connects to `state.vscdb` files modified within the last 48 hours
   ```python
   from mcp_commit_story.cursor_db.connection import get_all_cursor_databases
   
   # List all discovered databases
   databases = get_all_cursor_databases()
   print(f"Found {len(databases)} recent databases")
   for db in databases:
       print(f"  {db}")
   ```
   
   **Example successful output:**
   ```
   Found 3 recent databases
     /Users/username/Library/Application Support/Cursor/User/workspaceStorage/abc123def456/state.vscdb
     /Users/username/Library/Application Support/Cursor/User/workspaceStorage/def789ghi012/state.vscdb
     /Users/username/Library/Application Support/Cursor/User/workspaceStorage/ghi345jkl678/state.vscdb
   ```

2. **Verify Database Files**: Ensure `state.vscdb` files exist in workspace directories and have been modified recently
   ```bash
   # Search for recent Cursor database files (macOS)
   find ~/Library/Application\ Support/Cursor/User/workspaceStorage/ -name "state.vscdb" -type f -mtime -2
   
   # Search for recent Cursor database files (Linux)
   find ~/.config/Cursor/User/workspaceStorage/ -name "state.vscdb" -type f -mtime -2
   ```
   
   **Example successful output:**
   ```
   /Users/username/Library/Application Support/Cursor/User/workspaceStorage/abc123def456/state.vscdb
   /Users/username/Library/Application Support/Cursor/User/workspaceStorage/def789ghi012/state.vscdb
   ```

3. **Use Explicit Path**: Override auto-discovery with a specific database path
   ```python
   from mcp_commit_story.cursor_db.connection import get_cursor_chat_database
   
   # Connect to specific database
   conn = get_cursor_chat_database(user_override_path="/path/to/state.vscdb")
   ```

**Database Connection Errors**
Common connection error patterns and solutions:

- **"Database file not found"**: Verify file path and permissions
- **"Permission denied"**: Ensure read access to the database file
- **"Database corrupted or invalid"**: File may be locked by Cursor or corrupted

**Query Execution Errors**
When executing queries against Cursor databases:

- **"Query execution failed: syntax error"**: Check SQL syntax
- **"Query execution failed: no such table"**: Database schema may be different than expected
- **SQL injection protection**: All queries use parameterized statements automatically

### Performance Considerations

**Connection Management**
- No connection caching implemented - each query creates a new connection
- Connections are automatically closed after each operation
- Use context managers for multiple operations:

```python
from mcp_commit_story.cursor_db.connection import cursor_chat_database_context

with cursor_chat_database_context() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages")
    results = cursor.fetchall()
    # Connection automatically closed
```

**Large Result Sets**
For queries returning large amounts of data:
- Results are returned as lists of tuples for maximum flexibility
- Consider using LIMIT clauses for large tables
- Monitor memory usage with very large datasets

### Testing Database Connectivity

**Basic Connection Test**
```python
from mcp_commit_story.cursor_db.connection import (
    get_cursor_chat_database,
    CursorDatabaseConnectionError
)

try:
    conn = get_cursor_chat_database()
    print("✅ Successfully connected to Cursor database")
    
    # Test basic query
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 5")
    tables = cursor.fetchall()
    print(f"Found {len(tables)} tables in database")
    
    conn.close()
except CursorDatabaseConnectionError as e:
    print(f"❌ Connection failed: {e}")
```

**Query All Databases**
```python
from mcp_commit_story.cursor_db.connection import query_all_cursor_databases

# Query across all discovered databases
results = query_all_cursor_databases(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
)

print(f"Queried {len(results)} databases:")
for db_path, query_results in results:
    table_count = query_results[0][0] if query_results else 0
    print(f"  {db_path}: {table_count} tables")
```

### Troubleshooting Commands

**Verify Database Discovery**
```python
from mcp_commit_story.cursor_db.connection import _discover_cursor_databases

# Check internal discovery process
databases = _discover_cursor_databases()
print(f"Discovery found {len(databases)} valid databases")
```

**Check Database Age Filter**
The system only considers `state.vscdb` files modified within 48 hours. To check file modification times:
```bash
# Check modification times (macOS/Linux)
find ~/Library/Application\ Support/Cursor/User/workspaceStorage/ -name "state.vscdb" -exec ls -la {} \;

# Check if files are within 48-hour window
find ~/Library/Application\ Support/Cursor/User/workspaceStorage/ -name "state.vscdb" -mtime -2
```

**Example output showing recent activity:**
```
-rw-r--r--  1 username  staff  2048000 Dec 21 14:30 .../abc123def456/state.vscdb
-rw-r--r--  1 username  staff  1536000 Dec 21 09:15 .../def789ghi012/state.vscdb
```

## Troubleshooting

### Common Issues

**Database Not Found**
```bash
# Check if Cursor is installed and has been used
ls -la ~/Library/Application\ Support/Cursor/User/workspaceStorage/  # macOS
ls -la ~/.config/Cursor/User/workspaceStorage/                       # Linux
dir %APPDATA%\Cursor\User\workspaceStorage\                         # Windows
```

**Permission Denied**
- Ensure the user running MCP Commit Story has read access to Cursor directories
- On WSL, verify Windows drive mount permissions
- Check file system permissions for the workspace directories

**Multiple Cursor Installations**
If you have multiple Cursor installations (stable, insiders, portable), the system will detect multiple workspace paths. The first valid path found will be used.

**WSL Detection Issues**
If WSL detection fails:
```bash
# Check WSL environment detection
cat /proc/version  # Should contain "Microsoft" or "WSL"
echo $WSL_DISTRO_NAME  # Should be set in WSL2
```

### Validation Commands

**Test Platform Detection:**
```python
from mcp_commit_story.cursor_db.platform import detect_platform, get_cursor_workspace_paths

# Check detected platform
platform = detect_platform()
print(f"Detected platform: {platform}")

# Check discovered workspace paths
paths = get_cursor_workspace_paths()
print(f"Found {len(paths)} potential workspace paths:")
for path in paths:
    print(f"  {path}")
```

**Validate Workspace Access:**
```python
from mcp_commit_story.cursor_db.platform import find_valid_workspace_paths

# Check accessible workspace paths
valid_paths = find_valid_workspace_paths()
print(f"Found {len(valid_paths)} accessible workspace paths:")
for path in valid_paths:
    print(f"  {path}")
```

## Security Considerations

- MCP Commit Story only reads from Cursor databases, never writes
- Chat history data is processed locally and not transmitted externally
- Sensitive information in chat history is sanitized before journal generation
- Database connections use read-only access patterns

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