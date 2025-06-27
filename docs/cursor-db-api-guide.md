# Cursor DB API Guide

## Overview

The `cursor_db` package provides programmatic access to Cursor's chat history stored in SQLite databases. This enables automated journal generation, development workflow analysis, and conversation archival with complete conversation context.

### Value Proposition

- **Complete Conversation Access**: Extract full chat history without AI memory limitations
- **Multi-Workspace Support**: Handle database rotation and multiple workspace configurations  
- **Performance Optimized**: 80-90% faster processing with 48-hour intelligent filtering
- **Cross-Platform Compatible**: Works on macOS, Windows, and Linux
- **Zero Dependencies**: Uses Python's built-in sqlite3 module
- **Production Ready**: Comprehensive error handling and telemetry integration

## Quick Start

### Basic Usage

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database

# Get complete chat history for current workspace
result = query_cursor_chat_database()

if result['workspace_info']['total_messages'] > 0:
    print(f"Found {result['workspace_info']['total_messages']} messages")
    print(f"Workspace: {result['workspace_info']['workspace_path']}")
    
    # Process messages
    for message in result['chat_history']:
        print(f"{message['role']}: {message['content'][:100]}...")
else:
    print("No chat history found")
```

### Error Handling

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.cursor_db.exceptions import CursorDatabaseError

try:
    result = query_cursor_chat_database()
    # Process result...
except CursorDatabaseError as e:
    print(f"Database error: {e}")
    # Fallback handling...
```

## API Reference

### Core Functions

#### `query_cursor_chat_database() -> Dict`

Main entry point for extracting complete chat history with workspace metadata.

**Returns:**
```python
{
    "workspace_info": {
        "workspace_path": str,      # Detected workspace directory
        "database_path": str,       # SQLite database location  
        "last_updated": str,        # Database modification time
        "total_messages": int       # Total message count
    },
    "chat_history": [              # List of conversation messages
        {
            "role": "user" | "assistant",
            "content": str,         # Message text
            "timestamp": int | None, # Unix timestamp (None for user prompts)
            "type": str | None      # Message type ("composer", etc.)
        }
    ]
}
```

**Error Handling:**
- Returns empty structure with error indicators if workspace/database not found
- Graceful degradation for permission errors or corrupted databases
- All errors logged with telemetry tracking

**Performance:**
- Threshold: 500ms for typical workspaces
- 80-90% faster processing with 48-hour intelligent filtering
- Sub-10ms filtering overhead for database selection

#### `discover_all_cursor_databases(workspace_path: str) -> List[str]`

Discover all Cursor databases for a workspace to handle database rotation.

**Parameters:**
- `workspace_path`: Absolute path to workspace directory

**Returns:**
- List of absolute paths to state.vscdb files

**Usage:**
```python
from mcp_commit_story.cursor_db import discover_all_cursor_databases

workspace = "/path/to/project"
databases = discover_all_cursor_databases(workspace)
print(f"Found {len(databases)} databases")
```

#### `extract_from_multiple_databases(database_paths: List[str]) -> List[Dict]`

Extract chat data from multiple databases with skip-and-continue error handling.

**Parameters:**
- `database_paths`: List of absolute paths to database files

**Returns:**
```python
[
    {
        "database_path": str,
        "prompts": List[Dict],      # User prompts from extract_prompts_data
        "generations": List[Dict]   # AI responses from extract_generations_data
    }
]
```

**Error Handling:**
- Skips corrupted/inaccessible databases
- Returns partial results from successful extractions
- Logs warnings for failed databases

#### `get_recent_databases(database_paths: List[str]) -> List[str]`

Filter databases by 48-hour modification window for performance optimization.

**Parameters:**
- `database_paths`: List of database paths to filter

**Returns:**
- List of database paths modified within last 48 hours

**Performance Impact:**
- 80-90% reduction in database processing for mature projects
- Balances performance vs. completeness for typical development cycles

### Lower-Level Functions

#### `execute_cursor_query(db_path: str, query: str, parameters: Tuple = None) -> List[Tuple]`

Execute parameterized SQL queries against Cursor databases.

**Parameters:**
- `db_path`: Absolute path to SQLite database
- `query`: SQL query string
- `parameters`: Optional tuple of query parameters

**Returns:**
- List of tuples containing query results

**Safety:**
- Parameterized queries prevent SQL injection
- 5-second connection timeout
- Automatic connection cleanup

#### `extract_prompts_data(db_path: str) -> List[Dict]`

Extract user prompts from ItemTable with JSON parsing.

**Returns:**
```python
[
    {
        "text": str,           # User message content
        "commandType": int,    # Message type identifier
        # Additional prompt metadata...
    }
]
```

#### `extract_generations_data(db_path: str) -> List[Dict]`

Extract AI responses from ItemTable with JSON parsing.

**Returns:**
```python
[
    {
        "textDescription": str,    # AI response content
        "type": str,              # Response type ("composer", etc.)
        "unixMs": int,            # Unix timestamp in milliseconds
        "generationUUID": str,    # Unique response identifier
        # Additional generation metadata...
    }
]
```

#### `reconstruct_chat_history(prompts: List[Dict], generations: List[Dict]) -> Dict`

Combine prompts and generations into standardized message format.

**Returns:**
```python
{
    "messages": [
        {
            "role": "user" | "assistant",
            "content": str,
            "timestamp": int | None,
            "type": str | None
        }
    ],
    "metadata": {
        "prompt_count": int,       # Original prompt count
        "generation_count": int    # Original generation count
    }
}
```

**Note:** No chronological pairing attempted due to missing user prompt timestamps.

## Performance Optimization

### 48-Hour Intelligent Filtering

The cursor_db package includes automatic performance optimization through 48-hour database filtering:

**How It Works:**
- Automatically filters databases by modification time before processing
- Only processes databases modified within the last 48 hours
- Transparent optimization - no API changes required

**Performance Impact:**
```python
# Before optimization (processing all databases)
# 10 databases × 100ms each = 1000ms total

# After optimization (48-hour filtering)  
# 2 recent databases × 100ms each = 200ms total
# 80% performance improvement!
```

**Configuration:**
- Fixed 48-hour window (balances performance vs. completeness)
- Automatically applied by `discover_all_cursor_databases()`
- No configuration options - optimized for typical development cycles

**Edge Cases:**
- Empty result if no databases modified recently
- Graceful fallback for clock changes or permission errors
- Debug logging shows filtered vs. processed database counts

**Monitoring:**
```python
# Telemetry attributes tracked:
# - databases_discovered: total found
# - databases_filtered: recent only  
# - filter_duration_ms: optimization overhead
# - time_window_hours: filtering window (48)
```

## Common Workflows

### 1. Journal Generation Workflow

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database

def generate_journal_entry():
    """Extract chat history for journal generation."""
    result = query_cursor_chat_database()
    
    if result['workspace_info']['total_messages'] == 0:
        return "No chat history available"
    
    # Filter recent messages for journal context
    recent_messages = [
        msg for msg in result['chat_history'] 
        if msg.get('timestamp') and 
           msg['timestamp'] > (time.time() * 1000) - (24 * 60 * 60 * 1000)  # Last 24h
    ]
    
    # Format for AI journal generation
    conversation_context = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in recent_messages[-20:]  # Last 20 messages
    ])
    
    return conversation_context
```

### 2. Development Session Analysis

```python
from mcp_commit_story.cursor_db import discover_all_cursor_databases, extract_from_multiple_databases

def analyze_session_patterns(workspace_path):
    """Analyze development patterns across multiple sessions."""
    databases = discover_all_cursor_databases(workspace_path)
    extractions = extract_from_multiple_databases(databases)
    
    session_stats = {
        "total_sessions": len(extractions),
        "total_prompts": sum(len(e['prompts']) for e in extractions),
        "total_generations": sum(len(e['generations']) for e in extractions),
        "active_databases": len([e for e in extractions if e['prompts'] or e['generations']])
    }
    
    return session_stats
```

### 3. Conversation Archival

```python
import json
from datetime import datetime
from mcp_commit_story.cursor_db import query_cursor_chat_database

def archive_conversations(output_file):
    """Archive complete conversation history to JSON."""
    result = query_cursor_chat_database()
    
    archive_data = {
        "exported_at": datetime.now().isoformat(),
        "workspace_info": result['workspace_info'],
        "message_count": len(result['chat_history']),
        "conversations": result['chat_history']
    }
    
    with open(output_file, 'w') as f:
        json.dump(archive_data, f, indent=2)
    
    print(f"Archived {archive_data['message_count']} messages to {output_file}")
```

### 4. Development Context Collection

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database

def collect_development_context(hours_back=8):
    """Collect recent development context for team handoffs."""
    result = query_cursor_chat_database()
    
    cutoff_time = (time.time() - hours_back * 3600) * 1000  # Convert to ms
    
    recent_context = []
    for message in result['chat_history']:
        if message.get('timestamp') and message['timestamp'] > cutoff_time:
            recent_context.append({
                "time": datetime.fromtimestamp(message['timestamp'] / 1000),
                "role": message['role'],
                "content": message['content'][:200] + "..." if len(message['content']) > 200 else message['content']
            })
    
    return recent_context
```

### 5. Multi-Workspace Processing

```python
from mcp_commit_story.cursor_db import discover_all_cursor_databases
import os

def process_all_workspaces(base_directory):
    """Process all workspace projects in a directory."""
    results = {}
    
    for project in os.listdir(base_directory):
        project_path = os.path.join(base_directory, project)
        if os.path.isdir(project_path):
            try:
                databases = discover_all_cursor_databases(project_path)
                if databases:
                    results[project] = {
                        "database_count": len(databases),
                        "databases": databases
                    }
            except Exception as e:
                results[project] = {"error": str(e)}
    
    return results
```

## Troubleshooting Guide

### Common Issues

#### "No databases found"

**Symptoms:**
- `discover_all_cursor_databases()` returns empty list
- `query_cursor_chat_database()` returns zero messages

**Solutions:**
1. **Verify Cursor installation and usage:**
   ```bash
   # Check if Cursor has been used for chat in this workspace
   ls ~/Library/Application\ Support/Cursor/User/workspaceStorage/
   ```

2. **Check workspace path detection:**
   ```python
   from mcp_commit_story.platform import get_cursor_storage_path
   storage_path = get_cursor_storage_path()
   print(f"Cursor storage: {storage_path}")
   ```

3. **Manual database search:**
   ```bash
   find ~/Library/Application\ Support/Cursor -name "state.vscdb" -type f
   ```

#### "Permission denied" errors

**Symptoms:**
- `CursorDatabaseError` with permission-related messages
- Partial results from multi-database extraction

**Solutions:**
1. **Check file permissions:**
   ```bash
   ls -la ~/Library/Application\ Support/Cursor/User/workspaceStorage/*/state.vscdb
   ```

2. **Ensure Cursor is not running:**
   - Close Cursor completely before database access
   - SQLite may lock databases during active use

3. **Use read-only access:**
   ```python
   # Database access is already read-only, but ensure proper cleanup
   from mcp_commit_story.cursor_db import execute_cursor_query
   # Use context managers for guaranteed cleanup
   ```

#### "Malformed JSON data" warnings

**Symptoms:**
- Messages missing from extraction
- Warnings in logs about JSON parsing

**Solutions:**
1. **Check database integrity:**
   ```bash
   sqlite3 path/to/state.vscdb "PRAGMA integrity_check;"
   ```

2. **Handle partial data gracefully:**
   ```python
   # The package already handles malformed data gracefully
   # Check logs for specific parsing errors
   import logging
   logging.getLogger('mcp_commit_story.cursor_db').setLevel(logging.DEBUG)
   ```

#### "Empty chat history" despite having conversations

**Symptoms:**
- `total_messages` is 0 but you know there are conversations
- Recent conversations not appearing

**Solutions:**
1. **Check database age with 48-hour filtering:**
   ```python
   from mcp_commit_story.cursor_db import discover_all_cursor_databases
   
   # Get all databases (bypassing 48-hour filter temporarily)
   all_dbs = discover_all_cursor_databases(workspace_path)
   # Check modification times manually
   import os
   for db in all_dbs:
       mtime = os.path.getmtime(db)
       print(f"{db}: {datetime.fromtimestamp(mtime)}")
   ```

2. **Verify correct workspace detection:**
   ```python
   # Check if detecting correct workspace
   from mcp_commit_story.cursor_db import query_cursor_chat_database
   result = query_cursor_chat_database()
   print(f"Detected workspace: {result['workspace_info']['workspace_path']}")
   ```

#### Performance issues with large histories

**Symptoms:**
- Slow query response times
- Memory usage spikes
- Timeouts

**Solutions:**
1. **Monitor 48-hour filtering effectiveness:**
   ```python
   # Check if optimization is working
   from mcp_commit_story.cursor_db import discover_all_cursor_databases, get_recent_databases
   
   all_dbs = discover_all_cursor_databases(workspace_path)
   recent_dbs = get_recent_databases(all_dbs)
   print(f"Filtering: {len(all_dbs)} → {len(recent_dbs)} databases")
   ```

2. **Process databases incrementally:**
   ```python
   from mcp_commit_story.cursor_db import extract_from_multiple_databases
   
   # Process in smaller batches
   batch_size = 5
   for i in range(0, len(databases), batch_size):
       batch = databases[i:i+batch_size]
       results = extract_from_multiple_databases(batch)
       # Process batch results...
   ```

### Platform-Specific Notes

#### macOS
- Storage location: `~/Library/Application Support/Cursor/User/workspaceStorage/`
- May require Terminal full disk access for some directories
- Cursor must be closed for database access

#### Windows
- Storage location: `%APPDATA%\Cursor\User\workspaceStorage`
- Check Windows Defender exclusions if access is slow
- Use `\\` or raw strings for Windows paths

#### Linux
- Storage location: `~/.config/Cursor/User/workspaceStorage`
- Check file permissions and ownership
- Some distributions may use different config paths

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging

# Enable debug logging for cursor_db package
logging.getLogger('mcp_commit_story.cursor_db').setLevel(logging.DEBUG)
logging.getLogger('mcp_commit_story.cursor_db').addHandler(logging.StreamHandler())

# Enable telemetry debug output
logging.getLogger('mcp_commit_story.telemetry').setLevel(logging.DEBUG)
```

## Integration Examples

### Git Hook Integration

```python
#!/usr/bin/env python3
"""Post-commit hook to extract chat context."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_commit_story.cursor_db import query_cursor_chat_database

def main():
    """Extract chat context for journal generation."""
    try:
        result = query_cursor_chat_database()
        
        if result['workspace_info']['total_messages'] > 0:
            print(f"✅ Found {result['workspace_info']['total_messages']} chat messages")
            
            # Save context for journal generation
            context_file = ".mcp-commit-story/chat-context.json"
            with open(context_file, 'w') as f:
                json.dump(result, f)
            
            print(f"💾 Chat context saved to {context_file}")
        else:
            print("ℹ️  No chat history found")
            
    except Exception as e:
        print(f"❌ Error extracting chat context: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### MCP Server Integration

```python
from mcp.server import Server
from mcp_commit_story.cursor_db import query_cursor_chat_database

app = Server("cursor-chat-extractor")

@app.call_tool()
async def extract_chat_history(workspace_path: str = None):
    """MCP tool to extract Cursor chat history."""
    try:
        result = query_cursor_chat_database()
        
        return {
            "success": True,
            "data": result,
            "message": f"Extracted {result['workspace_info']['total_messages']} messages"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to extract chat history"
        }
```

### CI/CD Integration

```python
"""CI/CD script to archive development conversations."""

import os
import json
from datetime import datetime
from mcp_commit_story.cursor_db import query_cursor_chat_database

def archive_for_ci():
    """Archive conversations for CI/CD artifacts."""
    if not os.getenv('CI'):
        print("Not in CI environment")
        return
    
    try:
        result = query_cursor_chat_database()
        
        if result['workspace_info']['total_messages'] > 0:
            # Create CI artifact
            artifact = {
                "build_id": os.getenv('BUILD_ID'),
                "timestamp": datetime.now().isoformat(),
                "chat_summary": {
                    "total_messages": result['workspace_info']['total_messages'],
                    "workspace": result['workspace_info']['workspace_path']
                },
                "recent_messages": result['chat_history'][-10:]  # Last 10 messages
            }
            
            with open('chat-archive.json', 'w') as f:
                json.dump(artifact, f, indent=2)
            
            print("Chat history archived for CI")
    except Exception as e:
        print(f"CI chat archival failed: {e}")

if __name__ == "__main__":
    archive_for_ci()
```

## Advanced Usage

### Custom Filtering

```python
from mcp_commit_story.cursor_db import extract_from_multiple_databases, discover_all_cursor_databases
import time

def extract_with_custom_timeframe(workspace_path, hours_back=24):
    """Extract with custom time filtering."""
    databases = discover_all_cursor_databases(workspace_path)
    
    # Custom time filtering
    cutoff_time = time.time() - (hours_back * 3600)
    recent_databases = [
        db for db in databases 
        if os.path.getmtime(db) > cutoff_time
    ]
    
    return extract_from_multiple_databases(recent_databases)
```

### Memory-Efficient Processing

```python
def process_large_history_efficiently(workspace_path):
    """Process large chat histories with memory efficiency."""
    databases = discover_all_cursor_databases(workspace_path)
    
    # Process one database at a time
    for db_path in databases:
        # Process single database
        result = extract_from_multiple_databases([db_path])
        
        # Process immediately and discard
        for extraction in result:
            yield process_single_extraction(extraction)
            
        # Memory cleanup happens automatically
```

## Performance Benchmarks

### Typical Performance Characteristics

- **Single database extraction**: 50-100ms
- **Multi-database discovery**: 20-50ms  
- **48-hour filtering**: 5-10ms overhead
- **Large history (1000+ messages)**: 200-500ms
- **Cross-platform workspace detection**: 10-30ms

### Optimization Tips

1. **Use 48-hour filtering**: Automatically enabled, provides 80-90% improvement
2. **Process incrementally**: For very large histories, process databases individually
3. **Cache results**: Implement application-level caching for repeated access
4. **Monitor telemetry**: Use built-in performance tracking to identify bottlenecks

## API Versioning

The cursor_db package follows semantic versioning:

- **Major versions**: Breaking API changes
- **Minor versions**: New features, backward compatible
- **Patch versions**: Bug fixes

### Current Version: 0.18.0

**Stability:**
- Core functions are stable and production-ready
- Database schema handling is battle-tested
- Performance optimizations are mature

**Compatibility:**
- Supports Cursor versions 0.39+
- Cross-platform support for macOS, Windows, Linux
- Python 3.8+ required

---

*For additional support, see the [Cursor Database Implementation Guide](cursor-database-implementation.md) or check the project's GitHub issues.* 