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

## Implementation

The ComposerChatProvider class provides the interface for retrieving chat history:

- Connects to both workspace and global databases
- Accepts pre-calculated time windows (milliseconds)
- Returns chronologically sorted messages with session names
- No caching or connection pooling (per-request connections)
- Comprehensive error handling and telemetry

See `src/mcp_commit_story/composer_chat_provider.py` for implementation details.

## Database Persistence Lag Analysis

### Critical Discovery: In-Memory Buffering Problem

**Active conversations are buffered in memory before being persisted to the database.** This creates a fundamental gap where the most crucial development context - conversations happening RIGHT before a commit - are missed by real-time extraction systems.

#### Real-World Validation Data

**Test Case: Commit 55de441 (July 1st, 19:54:26)**
- **Latest Persisted Session**: July 1st, 18:34:02  
- **Persistence Gap**: 1.3 hours between latest conversation and commit
- **Missing Context**: 711 messages including critical "context7" workspace fix conversation
- **Result**: Journal generation without this gap would have ZERO relevant context

#### Timing Analysis

```bash
# Latest conversation session
Session: July 1st 18:34:02 (persisted)
├── 711 messages about workspace context issues
├── Direct problem-solving for the exact bug fixed
└── Implementation decisions that led to the commit

# Actual commit
Commit: July 1st 19:54:26 (1.3 hours later)
```

**Key Finding**: The conversations that directly led to the workspace fix commit were unavailable for 1.3 hours after they occurred, proving that lag-based processing is not just an optimization but **essential for system functionality**.

#### Technical Root Cause: Timestamp Extraction Bug

**Problem**: ComposerChatProvider was looking for individual `message.timestamp` fields that don't exist in real Cursor database schema.

```python
# BROKEN: Individual messages have NO timestamps
message_timestamp = message_data.get('timestamp', 0)  # Always defaulted to 0
```

**Solution**: Use session-level `createdAt` timestamps for all messages in that session.

```python
# FIXED: Use session timestamp for all messages
session_timestamp = message_headers.get('createdAt', 0)
# All messages in session inherit this timestamp
```

#### Database Schema Reality vs. Assumptions

**Session Metadata (HAS timestamps)**:
```json
{
  "composerId": "session-id",
  "name": "Fix workspace detection",
  "createdAt": 1751171755435,  // ✅ Session timestamp exists
  "lastUpdatedAt": 1751178902944
}
```

**Individual Messages (NO timestamps)**:
```json
{
  "text": "The workspace detection is broken",
  "context": {"fileSelections": [...]},
  "bubbleId": "msg-1",
  "_v": 2,
  "type": 1
  // ❌ NO "timestamp" field!
}
```

#### Cursor Database Flush Behavior

**Evidence from user reports**:
- Cursor users report periodic freezes every 30-60 seconds
- These correspond to database flush operations
- Chat history lag correlates with performance issues
- Unreliable persistence patterns observed in production

**Research Finding**: Cursor buffers active conversations in memory, periodically flushing to SQLite databases. The flush timing is unpredictable and can create significant delays.

#### Lag-Based Journal Generation Requirements

**Minimum Lag Requirements**:
- **Development commits**: 4-24 hour lag for complete context
- **Time window expansion**: 30 minutes before → 2-4 hours before commit
- **Persistence validation**: Check latest session timestamps vs. commit times

**Implementation Strategy**:
```python
def should_process_commit(commit_timestamp: int, latest_session_timestamp: int) -> bool:
    """Determine if enough lag exists for reliable extraction."""
    lag_hours = (commit_timestamp - latest_session_timestamp) / (1000 * 60 * 60)
    return lag_hours >= 4  # Minimum 4-hour lag for safety

def get_expanded_time_window(commit_timestamp: int) -> tuple:
    """Expand time window to account for persistence lag."""
    four_hours_ms = 4 * 60 * 60 * 1000
    thirty_minutes_ms = 30 * 60 * 1000
    
    return (
        commit_timestamp - four_hours_ms,  # Look back 4 hours instead of 30 minutes
        commit_timestamp + thirty_minutes_ms
    )
```

#### Production Implications

**For Real-Time Systems**:
- ❌ **Immediate extraction fails**: Active conversations unavailable
- ❌ **Critical context missing**: Most relevant discussions not persisted
- ❌ **Timing-based filtering broken**: Messages filtered out due to timestamp=0 bug

**For Lag-Based Systems**:
- ✅ **Complete context available**: All relevant conversations persisted
- ✅ **Accurate timestamps**: Session-level timestamps work correctly  
- ✅ **Reliable extraction**: Conversations that led to commits are captured

#### cursor-chat-browser Validation

The popular [cursor-chat-browser](https://github.com/thomas-pedersen/cursor-chat-browser) project confirms this behavior:
- **Same data access pattern**: Uses identical database queries
- **Same limitation**: Cannot access active/buffered conversations
- **No special handling**: No attempt to solve the buffering problem
- **Production evidence**: 415 stars, 69 forks, same persistence gaps

#### Test-Driven Discovery

**Bug Detection**: Added `test_real_cursor_data_structure_timestamps` using realistic Cursor data (no individual message timestamps).

**Before Fix**:
```python
# Test failed - returned 0 messages instead of 2
# All timestamps defaulted to 0, filtered out by time window
```

**After Fix**:
```python
# Test passes - uses session createdAt for all messages
assert result[0]['timestamp'] == session_timestamp
assert result[1]['timestamp'] == session_timestamp  # Same session
```

#### Recommended Architecture

**Journal Generation Pipeline**:
1. **Commit Detection**: Git hooks trigger after commits
2. **Lag Validation**: Check if sufficient time has passed (4+ hours)  
3. **Queue Processing**: Add to delayed processing queue if too recent
4. **Context Extraction**: Use expanded time windows (4 hours before commit)
5. **Session-Level Timestamps**: Group messages by session timestamps

**Configuration**:
```python
MINIMUM_LAG_HOURS = 4
CONTEXT_WINDOW_HOURS = 4  # Instead of 0.5 hours
PROCESSING_DELAY_HOURS = 24  # Daily batch processing
```

This discovery fundamentally changes how chat-based development tools should be architected, proving that **lag-based processing is mandatory** for capturing complete development context.

## Time Window Filtering 