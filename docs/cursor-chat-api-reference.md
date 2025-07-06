# Cursor Chat API Reference

## Overview

The `cursor_db` package provides programmatic access to Cursor's chat history stored in SQLite databases. This enables automated journal generation, development workflow analysis, and conversation archival with complete conversation context.

### Key Features

- **Complete Conversation Access**: Extract full chat history without memory limitations
- **Multi-Workspace Support**: Handle database rotation and multiple workspace configurations  
- **Performance Optimized**: Commit-based time windows provide precise context without artificial limits
- **Cross-Platform Compatible**: Works on macOS, Windows, and Linux
- **Zero Dependencies**: Uses Python's built-in sqlite3 module
- **Production Ready**: Comprehensive error handling and monitoring

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

Main entry point for extracting complete chat history using Cursor's Composer system with commit-based time windows.

**Features:**
- **Commit-based filtering**: Uses git commit boundaries for precise temporal context
- **Enhanced metadata**: Messages include timestamps and session names from Composer
- **Precise context**: Natural conversation boundaries based on development activity
- **Rich monitoring**: Comprehensive observability and error categorization

**Returns:**
```python
{
    "workspace_info": {
        "workspace_database_path": str | None,    # Workspace SQLite database path
        "global_database_path": str | None,       # Global Cursor database path  
        "total_messages": int,                   # Total message count
        "time_window_start": int | None,         # Time window start (Unix ms)
        "time_window_end": int | None,           # Time window end (Unix ms)
        "time_window_strategy": str,             # Strategy used ("commit_based", "24_hour_fallback", etc.)
        "commit_hash": str | None,               # Current git commit hash
        "last_updated": str                      # ISO timestamp of operation
    },
    "chat_history": [                           # List of conversation messages
        {
            "speaker": str,                      # "user" or "assistant"
            "text": str,                        # Message content
            "timestamp": int | None,            # Unix timestamp in milliseconds
            "sessionName": str | None           # Cursor session identifier
        }
    ]
}
```

**Error Handling:**
- Returns empty structure with error indicators if workspace/database not found
- Graceful degradation for permission errors or corrupted databases
- All errors logged with monitoring

**Performance:**
- Optimized for typical workspaces (< 500ms)
- Commit-based time windows provide precise context boundaries
- Monitoring tracks query duration and message counts
- Graceful degradation with 24-hour fallback for git errors

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

### Exception Handling

#### Exception Hierarchy

```python
# Base exception
CursorDatabaseError
    ├── CursorDatabaseNotFoundError      # Database files not found
    ├── CursorDatabaseAccessError        # Permission/file access issues
    ├── CursorDatabaseSchemaError        # Database structure issues
    └── CursorDatabaseQueryError         # SQL query execution issues
```

#### Error Context

All exceptions include:
- **Error message**: Human-readable description
- **Database path**: Which database caused the error
- **Error context**: Additional troubleshooting information
- **Suggested actions**: Recommendations for resolution

```python
try:
    result = query_cursor_chat_database()
except CursorDatabaseNotFoundError as e:
    print(f"Database not found: {e}")
    print(f"Suggested actions: {e.suggested_actions}")
except CursorDatabaseAccessError as e:
    print(f"Access denied: {e}")
    print(f"Database path: {e.database_path}")
```

## Common Use Cases

### 1. Journal Generation

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database
from datetime import datetime

def generate_journal_entry():
    """Generate a journal entry with chat context."""
    result = query_cursor_chat_database()
    
    if result['workspace_info']['total_messages'] == 0:
        return "No chat history found for this session."
    
    # Format chat history for journal
    journal_entry = f"""
# Development Journal - {datetime.now().strftime('%Y-%m-%d')}

## Chat Context
Found {result['workspace_info']['total_messages']} messages in workspace.

## Recent Conversations
"""
    
    for message in result['chat_history'][-10:]:  # Last 10 messages
        journal_entry += f"**{message['speaker']}**: {message['text'][:200]}...\n\n"
    
    return journal_entry
```

### 2. Conversation Analysis

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database
from collections import Counter

def analyze_conversation_patterns():
    """Analyze conversation patterns and topics."""
    result = query_cursor_chat_database()
    
    if result['workspace_info']['total_messages'] == 0:
        return "No data to analyze."
    
    # Analyze message distribution
    speakers = [msg['speaker'] for msg in result['chat_history']]
    speaker_counts = Counter(speakers)
    
    # Analyze common topics (simple keyword analysis)
    all_text = ' '.join(msg['text'] for msg in result['chat_history'])
    common_words = Counter(all_text.lower().split()).most_common(10)
    
    return {
        'total_messages': len(result['chat_history']),
        'speaker_distribution': dict(speaker_counts),
        'common_topics': common_words,
        'time_span': {
            'start': result['workspace_info']['time_window_start'],
            'end': result['workspace_info']['time_window_end']
        }
    }
```

### 3. Context Extraction

```python
from mcp_commit_story.cursor_db import query_cursor_chat_database
import json

def extract_context_for_commit(commit_hash: str):
    """Extract relevant chat context for a specific commit."""
    result = query_cursor_chat_database()
    
    if result['workspace_info']['total_messages'] == 0:
        return None
    
    # Filter messages by relevance to commit
    relevant_messages = []
    for message in result['chat_history']:
        if any(keyword in message['text'].lower() 
               for keyword in ['fix', 'bug', 'error', 'implement', 'add']):
            relevant_messages.append(message)
    
    context = {
        'commit_hash': commit_hash,
        'total_messages': result['workspace_info']['total_messages'],
        'relevant_messages': relevant_messages,
        'workspace_path': result['workspace_info']['workspace_path']
    }
    
    return context
```

## Troubleshooting

### Common Issues

#### "No databases found"

**Symptoms:**
- `CursorDatabaseNotFoundError` with no valid databases message
- Empty results from `discover_all_cursor_databases()`

**Solutions:**
1. **Verify Cursor usage**: Ensure Cursor has been run recently in a workspace
2. **Check database locations**: Verify expected paths exist
3. **Use environment override**: Set `CURSOR_WORKSPACE_PATH` for custom locations
4. **Check permissions**: Ensure read access to Cursor's data directories

#### "Empty chat history" despite having conversations

**Symptoms:**
- `total_messages` is 0 but you know there are conversations
- Recent conversations not appearing

**Solutions:**
1. **Check database age**: Verify databases are within 48-hour window
2. **Verify workspace detection**: Ensure correct workspace is being detected
3. **Check git repository**: Commit-based filtering requires git repository

#### Performance issues with large histories

**Symptoms:**
- Slow query response times
- Memory usage spikes
- Timeouts

**Solutions:**
1. **Monitor filtering effectiveness**: Check if 48-hour optimization is working
2. **Process incrementally**: Handle large datasets in smaller batches
3. **Use specific time windows**: Limit queries to relevant time periods

### Platform-Specific Notes

#### macOS
- Storage location: `~/Library/Application Support/Cursor/User/workspaceStorage/`
- May require Terminal full disk access for some directories
- Close Cursor for database access

#### Windows
- Storage location: `%APPDATA%\Cursor\User\workspaceStorage`
- Use `\\\\` or raw strings for Windows paths
- Check Windows Defender exclusions if access is slow

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
```

## Integration Examples

### Git Hook Integration

```python
#!/usr/bin/env python3
"""Post-commit hook to extract chat context."""

import sys
import os
import json
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
            os.makedirs(os.path.dirname(context_file), exist_ok=True)
            
            with open(context_file, 'w') as f:
                json.dump(result, f, indent=2)
            
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

### Custom Application Integration

```python
"""Custom application using cursor_db for development insights."""

import json
from datetime import datetime, timedelta
from mcp_commit_story.cursor_db import query_cursor_chat_database

class DevelopmentInsights:
    def __init__(self):
        self.chat_data = None
        self.load_chat_data()
    
    def load_chat_data(self):
        """Load chat data from Cursor."""
        try:
            result = query_cursor_chat_database()
            self.chat_data = result
            print(f"Loaded {result['workspace_info']['total_messages']} messages")
        except Exception as e:
            print(f"Failed to load chat data: {e}")
            self.chat_data = None
    
    def get_recent_activity(self, hours: int = 24):
        """Get chat activity from last N hours."""
        if not self.chat_data:
            return []
        
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        
        recent = []
        for message in self.chat_data['chat_history']:
            if message.get('timestamp') and message['timestamp'] > cutoff_ms:
                recent.append(message)
        
        return recent
    
    def export_summary(self, output_file: str):
        """Export chat summary to file."""
        if not self.chat_data:
            return
        
        summary = {
            'generated_at': datetime.now().isoformat(),
            'workspace_info': self.chat_data['workspace_info'],
            'message_count': len(self.chat_data['chat_history']),
            'recent_activity': self.get_recent_activity(24)
        }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Summary exported to {output_file}")

# Usage
insights = DevelopmentInsights()
recent_messages = insights.get_recent_activity(6)  # Last 6 hours
insights.export_summary("development_summary.json")
```

## Performance Considerations

### Optimization Strategies

- **48-hour filtering**: Automatically filters databases by modification time
- **Commit-based windows**: Provides precise temporal context without processing entire history
- **Batch processing**: Handle large datasets in manageable chunks
- **Connection pooling**: Reuse database connections when possible

### Monitoring

The API includes comprehensive monitoring capabilities:

- **Query duration tracking**: Monitor performance against thresholds
- **Error categorization**: Track different types of failures
- **Resource usage**: Monitor memory and CPU usage during operations
- **Cache effectiveness**: Track hit/miss ratios for optimizations

```python
# Example monitoring integration
import logging
from mcp_commit_story.cursor_db import query_cursor_chat_database

# Enable monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitored_chat_extraction():
    """Extract chat data with monitoring."""
    start_time = time.time()
    
    try:
        result = query_cursor_chat_database()
        duration = time.time() - start_time
        
        logger.info(f"Chat extraction completed in {duration:.2f}s")
        logger.info(f"Extracted {result['workspace_info']['total_messages']} messages")
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Chat extraction failed after {duration:.2f}s: {e}")
        raise
```

## Security Considerations

- **Read-only access**: The API only reads from Cursor databases, never modifies them
- **Sensitive data protection**: Error messages automatically redact sensitive information
- **File permissions**: Respects system file permissions and fails gracefully when access is denied
- **No network access**: All operations are local file system access only
- **Safe SQL queries**: Uses parameterized queries to prevent SQL injection

## Supported Cursor Versions

The API is compatible with:
- Cursor Stable (all versions)
- Cursor Insiders (all versions)
- Portable Cursor installations
- Custom Cursor installations with standard workspace structure

## Advanced Topics

### Custom Database Paths

```python
import os
from mcp_commit_story.cursor_db import query_cursor_chat_database

# Override default database discovery
os.environ['CURSOR_WORKSPACE_PATH'] = '/custom/path/to/cursor/workspaces'

result = query_cursor_chat_database()
```

### Handling Multiple Workspaces

```python
from mcp_commit_story.cursor_db import discover_all_cursor_databases, extract_from_multiple_databases

# Process multiple workspaces
workspace_dirs = ['/path/to/workspace1', '/path/to/workspace2']

all_databases = []
for workspace in workspace_dirs:
    databases = discover_all_cursor_databases(workspace)
    all_databases.extend(databases)

# Extract from all databases
results = extract_from_multiple_databases(all_databases)
```

### Custom Time Windows

```python
from datetime import datetime, timedelta
from mcp_commit_story.cursor_db import query_cursor_chat_database

# Custom time filtering (if needed for specific use cases)
result = query_cursor_chat_database()

# Filter messages by custom time window
start_time = datetime.now() - timedelta(hours=12)
start_ms = int(start_time.timestamp() * 1000)

recent_messages = [
    msg for msg in result['chat_history']
    if msg.get('timestamp') and msg['timestamp'] > start_ms
]
``` 