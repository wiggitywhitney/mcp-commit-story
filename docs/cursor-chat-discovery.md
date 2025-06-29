# Cursor Chat Database Architecture

## Overview

**MCP Commit Story** generates rich development journals by extracting comprehensive context from your Cursor chat history. This document explains Cursor's chat storage architecture and provides implementation guidance for chat data extraction.

## Cursor Chat Architecture

Cursor 1.1.6 stores chat conversations in the **Composer system** - a rich conversational interface that maintains complete chat history with full context, file attachments, and chronological message threading.

### Database Locations

**Cross-Platform Paths:**
```bash
# macOS
~/Library/Application Support/Cursor/User/workspaceStorage/{hash}/state.vscdb
~/Library/Application Support/Cursor/User/globalStorage/state.vscdb

# Windows  
%APPDATA%\Cursor\User\workspaceStorage\{hash}\state.vscdb
%APPDATA%\Cursor\User\globalStorage\state.vscdb

# Linux
~/.config/Cursor/User/workspaceStorage/{hash}/state.vscdb
~/.config/Cursor/User/globalStorage/state.vscdb

# WSL2
/mnt/c/Users/{USERNAME}/AppData/Roaming/Cursor/User/workspaceStorage/{hash}/state.vscdb
/mnt/c/Users/{USERNAME}/AppData/Roaming/Cursor/User/globalStorage/state.vscdb
```

### Storage Architecture

**Two-Database System:**
1. **Workspace Database** (`workspaceStorage/{hash}/state.vscdb`): Contains session metadata and workspace mapping
2. **Global Database** (`globalStorage/state.vscdb`): Contains actual conversation content

**Workspace Detection:**
```json
// workspaceStorage/{hash}/workspace.json
{
  "folder": "file:///Users/username/Repos/project-name"
}
```

## Database Schema

### Workspace Database (`state.vscdb`)
```sql
CREATE TABLE ItemTable (
    [key] TEXT PRIMARY KEY,
    value BLOB
);

-- Key: 'composer.composerData' - Session metadata
-- Key: 'workspace' - Workspace path mapping
```

### Global Database (`state.vscdb`)
```sql
CREATE TABLE cursorDiskKV (
    [key] TEXT PRIMARY KEY,
    value BLOB
);

-- Key Pattern: 'composerData:{composerId}' - Session headers
-- Key Pattern: 'bubbleId:{composerId}:{bubbleId}' - Individual messages
```

## Data Structure

### Session Metadata
```json
{
  "allComposers": [
    {
      "composerId": "0c74276c-5af6-4ca3-b49f-353481619b2d",
      "name": "Implement user authentication",
      "createdAt": 1751171755435,
      "lastUpdatedAt": 1751178902944,
      "type": "head"
    }
  ],
  "selectedComposerId": "current-session-id",
  "selectedChatId": "current-chat-id"
}
```

### Session Conversation
```json
{
  "composerId": "0c74276c-5af6-4ca3-b49f-353481619b2d",
  "name": "Implement user authentication",
  "fullConversationHeadersOnly": [
    {
      "bubbleId": "message-id-1",
      "type": 1  // 1 = user, 2 = assistant
    }
  ],
  "context": {
    "fileSelections": [...],
    "folderSelections": [...],
    "selectedDocs": [...]
  }
}
```

### Individual Messages
```json
{
  "text": "How do I implement JWT authentication?",
  "richText": "{\"root\":{\"children\":[...]}}",
  "timestamp": 1751046149314,
  "context": {
    "fileSelections": [
      {
        "fileName": "auth.py",
        "content": "selected code..."
      }
    ],
    "folderSelections": [...],
    "selectedDocs": [...]
  }
}
```

## Implementation Guide

### Complete Chat Extraction

```python
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional

def extract_cursor_conversations(target_workspace: Optional[str] = None) -> Dict:
    """Extract complete Cursor chat history for a workspace."""
    
    # 1. Find workspace databases
    workspace_dirs = find_workspace_databases(target_workspace)
    
    # 2. Extract session metadata
    sessions = []
    for workspace_dir in workspace_dirs:
        db_path = workspace_dir / "state.vscdb"
        sessions.extend(extract_session_metadata(db_path))
    
    # 3. Extract conversations from global database
    global_db = get_global_database_path()
    conversations = extract_conversations(global_db, sessions)
    
    return {
        'workspace': target_workspace,
        'sessions': conversations,
        'total_sessions': len(conversations),
        'total_messages': sum(len(c['messages']) for c in conversations)
    }

def find_workspace_databases(target_workspace: str) -> List[Path]:
    """Find all database directories for a workspace."""
    storage_path = get_cursor_storage_path()
    matching_dirs = []
    
    for hash_dir in storage_path.iterdir():
        if not hash_dir.is_dir():
            continue
            
        workspace_file = hash_dir / "workspace.json"
        if workspace_file.exists():
            workspace_data = json.loads(workspace_file.read_text())
            if target_workspace in workspace_data.get("folder", ""):
                matching_dirs.append(hash_dir)
    
    return matching_dirs

def extract_session_metadata(db_path: Path) -> List[Dict]:
    """Extract composer session metadata from workspace database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT value FROM ItemTable WHERE [key] = 'composer.composerData'"
    )
    
    result = cursor.fetchone()
    if not result:
        return []
        
    composer_data = json.loads(result[0])
    return composer_data.get("allComposers", [])

def extract_conversations(global_db_path: Path, sessions: List[Dict]) -> List[Dict]:
    """Extract full conversations from global database."""
    conn = sqlite3.connect(global_db_path)
    conversations = []
    
    for session in sessions:
        composer_id = session["composerId"]
        
        # Get conversation headers
        headers_key = f"composerData:{composer_id}"
        cursor = conn.execute(
            "SELECT value FROM cursorDiskKV WHERE [key] = ?", (headers_key,)
        )
        
        headers_result = cursor.fetchone()
        if not headers_result:
            continue
            
        headers = json.loads(headers_result[0])
        
        # Extract individual messages
        messages = []
        for header in headers.get("fullConversationHeadersOnly", []):
            bubble_key = f"bubbleId:{composer_id}:{header['bubbleId']}"
            message_cursor = conn.execute(
                "SELECT value FROM cursorDiskKV WHERE [key] = ?", (bubble_key,)
            )
            
            message_result = message_cursor.fetchone()
            if message_result:
                message_data = json.loads(message_result[0])
                message_data['type'] = header['type']  # 1=user, 2=assistant
                messages.append(message_data)
        
        conversations.append({
            'composerId': composer_id,
            'name': session['name'],
            'createdAt': session['createdAt'],
            'lastUpdatedAt': session['lastUpdatedAt'],
            'messages': messages,
            'context': headers.get('context', {})
        })
    
    return conversations
```

### Workspace Detection

```python
def get_cursor_storage_path() -> Path:
    """Get platform-specific Cursor storage path."""
    import platform
    
    system = platform.system()
    home = Path.home()
    
    if system == "Darwin":  # macOS
        return home / "Library/Application Support/Cursor/User/workspaceStorage"
    elif system == "Windows":
        return home / "AppData/Roaming/Cursor/User/workspaceStorage"
    else:  # Linux
        return home / ".config/Cursor/User/workspaceStorage"

def get_global_database_path() -> Path:
    """Get global database path."""
    storage_base = get_cursor_storage_path().parent
    return storage_base / "globalStorage/state.vscdb"
```

### Time-Based Filtering

```python
def filter_recent_conversations(conversations: List[Dict], hours: int = 48) -> List[Dict]:
    """Filter conversations to recent activity."""
    import time
    
    cutoff_time = (time.time() - (hours * 3600)) * 1000  # Convert to milliseconds
    recent_conversations = []
    
    for conversation in conversations:
        # Filter messages within time window
        recent_messages = [
            msg for msg in conversation['messages']
            if msg.get('timestamp', 0) >= cutoff_time
        ]
        
        if recent_messages:
            conversation_copy = conversation.copy()
            conversation_copy['messages'] = recent_messages
            recent_conversations.append(conversation_copy)
    
    return recent_conversations
```

## Time Window Filtering

The system uses precise commit-based time windows to collect only relevant chat history:

- **Normal commits**: Previous commit timestamp → current commit timestamp
- **First commits**: 24-hour lookback window
- **Merge commits**: Skipped entirely (no journal entries generated)
- **Error fallback**: 24-hour window when git operations fail

This ensures each journal entry contains exactly the conversations that led to that commit.

## Key Features

### Chronological Message Structure
- **Pre-sorted**: Messages are stored chronologically within each session
- **Timestamps**: All messages include precise local system timestamps
- **Git Correlation**: Timestamps correlate directly with git commit times (same timezone)

### Rich Context
- **File Attachments**: Code files and selections included with messages
- **Folder Context**: Entire folder selections preserved
- **Documentation References**: Links to relevant documentation
- **Rich Formatting**: Syntax highlighting and formatted text preserved

### Session Organization
- **Named Sessions**: Human-readable session names like "Implement authentication"
- **Session Metadata**: Creation and update timestamps
- **Conversation Threading**: Complete conversation flow preserved

## Integration with MCP Commit Story

### Git Hook Integration
```python
# Extract conversation around commit time
def get_commit_context_conversation(commit_hash: str) -> Dict:
    commit_timestamp = get_commit_timestamp(commit_hash)
    
    conversations = extract_cursor_conversations()
    
    # Find conversations around commit time (30 min before, 5 min after)
    context_conversations = []
    for conversation in conversations:
        relevant_messages = [
            msg for msg in conversation['messages']
            if (commit_timestamp - 1800000) <= msg.get('timestamp', 0) <= (commit_timestamp + 300000)
        ]
        
        if relevant_messages:
            context_conversations.append({
                **conversation,
                'messages': relevant_messages
            })
    
    return {
        'commit': commit_hash,
        'conversations': context_conversations
    }
```

### Journal Generation Enhancement
- **Direct Quotes**: Extract verbatim conversation quotes with full context
- **Problem-Solving Narrative**: Complete development reasoning preserved  
- **File Context**: Show which files were discussed during implementation
- **Decision Rationale**: Capture why specific approaches were chosen

## Community Validation

The [cursor-chat-browser](https://github.com/thomas-pedersen/cursor-chat-browser) project (415 stars, 69 forks) demonstrates this approach in production with:
- Cross-platform workspace detection
- Complete conversation extraction
- Rich context preservation
- Export capabilities (Markdown, HTML, PDF)

## Workspace Detection

The system automatically finds the correct Cursor workspace for your repository by:
1. Matching git remote URLs (survives repo moves)
2. Matching folder paths
3. Checking folder name similarity
4. Falling back to most recent workspace if needed

Confidence threshold: 0.8 (matches below this use fallback)

### Troubleshooting
If the wrong workspace is detected, check logs for "Using fallback workspace" - this usually means the repository path or git remotes have changed since the workspace was created.

## Benefits

- **Zero Dependencies**: Uses Python's built-in sqlite3 module
- **Real-time Access**: Direct database reading as conversations happen
- **Complete Context**: Full development session history with file attachments
- **Performance**: Fast SQLite queries for immediate results
- **Cross-platform**: Proven approach across all major platforms 