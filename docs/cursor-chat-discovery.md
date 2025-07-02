# Cursor Chat Database Architecture

## Overview

**MCP Commit Story** generates rich development journals by extracting comprehensive context from your Cursor chat history. This document explains Cursor's chat storage architecture and provides implementation guidance for chat data extraction.

## Cursor Chat Architecture

Cursor stores chat conversations in the **Composer system** - a rich conversational interface that maintains complete chat history with full context, file attachments, and chronological message threading.

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

**Important Notes:**
- Database files use `.vscdb` extension (SQLite format), not `.vsdb`
- Each database has a corresponding `.vscdb.backup` file for transaction safety
- Workspace hash directories can be identified via `workspace.json` files
- No evidence of `.vsdb` files or short-term chat storage in separate databases

### Storage Architecture

**Two-Database System:**
1. **Workspace Database** (`workspaceStorage/{hash}/state.vscdb`): Contains workspace mapping and session references
2. **Global Database** (`globalStorage/state.vscdb`): Contains all conversation content, session metadata, and message data

**Workspace Detection:**
```json
// workspaceStorage/{hash}/workspace.json
{
  "folder": "file:///Users/username/Repos/project-name"
}
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

Cursor stores different message types in distinct fields within bubble records:

**User Messages** (type 1):
```json
{
  "text": "How do I implement JWT authentication?",
  "richText": "{\"root\":{\"children\":[...]}}",
  "type": 1,
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

**AI Responses** (type 2):
```json
{
  "thinking": {
    "text": "I'll help you implement JWT authentication. First, let me analyze your current setup...",
    "signature": "..."
  },
  "type": 2,
  "tokenCount": {"inputTokens": 1500, "outputTokens": 800},
  "context": {...}
}
```

**Tool Executions**:
```json
{
  "toolFormerData": {
    "name": "read_file",
    "params": "{\"target_file\": \"auth.py\"}",
    "result": "{\"contents\": \"...\"}",
    "status": "completed",
    "toolCallId": "toolu_vrtx_01...",
    "rawArgs": "..."
  },
  "type": 2,
  "capabilityType": 15,
  "tokenCount": {"inputTokens": 0, "outputTokens": 0},
  "context": {...}
}
```

## Database Schema

### Workspace Database (`state.vscdb`)
```sql
CREATE TABLE ItemTable (
    [key] TEXT PRIMARY KEY,
    value BLOB
);

CREATE TABLE cursorDiskKV (
    [key] TEXT PRIMARY KEY,
    value BLOB
);

-- ItemTable Keys:
-- 'composer.composerData' - Session references and workspace-specific composer state
-- 'workspace' - Workspace path mapping
-- 'workbench.backgroundComposer.workspacePersistentData' - Background composer configuration

-- cursorDiskKV: Typically empty in workspace databases (all conversation data in global database)
```

### Global Database (`state.vscdb`)
```sql
CREATE TABLE cursorDiskKV (
    [key] TEXT PRIMARY KEY,
    value BLOB
);

-- Key Patterns:
-- 'composerData:{composerId}' - Session headers and metadata (75 sessions typical)
-- 'bubbleId:{composerId}:{bubbleId}' - Individual messages with multi-field content (37,000+ messages typical)
-- 'checkpointId:{composerId}:{checkpointId}' - Code editing checkpoints (12,000+ entries)
-- 'messageRequestContext:{composerId}:{bubbleId}' - Message context metadata (3,000+ entries)
-- 'codeBlockDiff:{diffId}' - Code change tracking (4,000+ entries)
```

## Database Persistence and Timing

### Message Content Distribution

Analysis of active sessions reveals Cursor uses a **multi-field message storage system** with high data completeness:

**Content Field Distribution** (example from 311-message session):
- **User messages**: 153 entries with content in `text` field
- **AI responses**: 35 entries with content in `thinking.text` field  
- **Tool executions**: 121 entries with data in `toolFormerData` field
- **Empty/metadata**: 2 entries (UI elements, ~0.6%)
- **Overall completion rate**: 99.4% when extracting from all relevant fields

### Persistence Stages

Analysis reveals a multi-stage persistence process:

1. **Message Placeholder Creation** - Bubble IDs created immediately
2. **Session Metadata Updates** - Headers updated with message count
3. **Content Population** - Content fields populated asynchronously  
4. **Index Synchronization** - Database and session headers aligned

This can result in messages existing in the database with empty content fields while awaiting content population.

### Persistence Behavior Patterns

**Active Sessions:**
- High completion rates (99%+) when extracting from appropriate content fields
- Immediate availability of `text`, `thinking.text`, and `toolFormerData` content
- Real-time persistence for current conversations

**Historical Sessions:**
- Variable persistence timing for older conversations
- Content population delays can affect time-based queries
- Inconsistencies between database bubble count and session header references

**Real-world evidence of persistence gaps:**
- Content extraction timing can lag conversation activity by 30-60 minutes
- Historical queries may encounter empty content fields for recent conversations
- Session metadata updates faster than individual message content population

### Persistence Triggers

Content persistence appears triggered by:

1. **Time-based intervals** (30-60 minute intervals observed)
2. **Memory pressure** (conversation buffer capacity)
3. **Application lifecycle events** (shutdown, restart, workspace changes)
4. **Session transitions** (switching between chat sessions)

No user-controllable flush mechanism exists.

### Schema Notes

**Individual Message Structure:**
- Messages use a **multi-field content system**: `text` (user), `thinking.text` (AI), `toolFormerData` (tools)
- Messages do not contain individual timestamp fields
- Timestamps are stored at session level in `createdAt` and `lastUpdatedAt` fields
- All messages within a session inherit the session's timestamp for time-based filtering
- Message types: 1=user, 2=assistant, with content in appropriate fields

**Content Extraction Strategy:**
- Check `text` field for user messages
- Check `thinking.text` field for AI responses  
- Check `toolFormerData` field for tool execution details
- Multi-field extraction achieves 99%+ completion rates on active sessions

**Backup Files:**
- Each `.vscdb` file has corresponding `.vscdb.backup` file
- Suggests transaction-safe updates with rollback capability

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
        
        # Extract individual messages using multi-field approach
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
                
                # Extract content from appropriate field based on message type
                content = ""
                if message_data.get('text'):  # User messages
                    content = message_data['text']
                elif message_data.get('thinking', {}).get('text'):  # AI responses
                    content = message_data['thinking']['text']
                elif message_data.get('toolFormerData'):  # Tool executions
                    tool_data = message_data['toolFormerData']
                    content = f"Tool: {tool_data.get('name', 'unknown')} - {tool_data.get('status', 'unknown')}"
                
                message_data['extracted_content'] = content
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
        # Use session timestamp for filtering (messages inherit session timing)
        session_timestamp = conversation.get('lastUpdatedAt', conversation.get('createdAt', 0))
        
        if session_timestamp >= cutoff_time:
            recent_conversations.append(conversation)
    
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
  - **Timestamps**: Session metadata includes creation and update timestamps
  - **Git Correlation**: Session timestamps correlate with git commit times (same timezone)

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
        session_timestamp = conversation.get('lastUpdatedAt', conversation.get('createdAt', 0))
        
        if (commit_timestamp - 1800000) <= session_timestamp <= (commit_timestamp + 300000):
            context_conversations.append(conversation)
    
    return {
        'commit': commit_hash,
        'conversations': context_conversations
    }
```

## Key Findings Summary

### Multi-Field Content System

Cursor's message storage uses a **distributed content approach** rather than single-field storage:

- **User messages**: Content in `text` field
- **AI responses**: Content in `thinking.text` field  
- **Tool executions**: Data in `toolFormerData` field
- **Metadata messages**: UI elements with minimal content

This system achieves **99.4% content completion** when extracting from all relevant fields, significantly higher than single-field extraction approaches.

### Persistence Behavior Implications

**For Active Sessions:**
- Near-complete data availability (99%+)
- Real-time content persistence across all message types
- Suitable for current conversation analysis

**For Historical Data:**
- Variable persistence timing still affects older conversations
- Time-based queries may encounter content gaps
- Session-level timestamps provide reliable filtering reference

### Implementation Impact

The multi-field discovery changes the extraction strategy from:
- ❌ Single-field approach: "Check `text` field only" (20-30% completion)
- ✅ Multi-field approach: "Check appropriate field per message type" (99%+ completion)

This resolves data completeness issues for active conversations while persistence timing remains relevant for historical data extraction.

## Implementation Considerations

### Content Extraction Timing

Chat extraction systems should account for different completion rates based on session age:

- **Active sessions** achieve 99%+ completion rates with multi-field extraction
- **Historical sessions** may have variable persistence timing affecting time-based queries
- **Session timestamps** provide reliable timing reference for all messages within a session
- **Multi-field extraction** significantly improves data completeness over single-field approaches

### Journal Generation Enhancement

- **Direct Quotes**: Extract verbatim conversation quotes with full context
- **Problem-Solving Narrative**: Complete development reasoning preserved  
- **File Context**: Show which files were discussed during implementation
- **Decision Rationale**: Capture why specific approaches were chosen

## Community Validation

The [cursor-chat-browser](https://github.com/thomas-pedersen/cursor-chat-browser) and [cursor-chat-export](https://github.com/somogyijanos/cursor-chat-export) projects successfully extract Cursor's chat data using similar database access patterns. Their success likely stems from implementing the **multi-field content extraction approach** described above, accessing `text`, `thinking.text`, and `toolFormerData` fields appropriately rather than relying on single-field extraction methods.

---

## Development History and Failed Approaches

*This section documents our research journey and failed attempts to prevent repeating the same mistakes.*

### Initial Single-Field Extraction Approach (FAILED)

**What we tried:** Extracting conversation content by checking only the `text` field in bubble records.

**Results:** 
- Achieved only 20-30% completion rates
- Most AI responses appeared as "empty" messages
- Tool executions completely missing from extracted conversations

**Why it failed:** Cursor uses a **distributed multi-field system** where different message types are stored in different fields:
- User messages: `text` field
- AI responses: `thinking.text` field  
- Tool executions: `toolFormerData` field

**Lesson learned:** Single-field extraction fundamentally misunderstands Cursor's storage architecture.

### Pre-Assembled Conversation Search (FAILED)

**What we tried:** Searching for "tab" structures or complete pre-assembled conversation units based on Browser Claude's suggestion.

**Investigation results:**
- Searched `ItemTable` and `cursorDiskKV` for keys containing "tab", "conversation", "complete", "full"
- Examined large `composerData` entries (1MB+) for complete conversation text
- Found no pre-assembled conversation units

**Why it failed:** Cursor doesn't store complete conversations as single units. Large `composerData` entries contain:
- File content caching (`originalModelLines`: 407KB+ per file)
- Code block metadata (31 files worth)
- Conversation headers (1,359 bubble references)
- **But no complete conversation text**

**Lesson learned:** cursor-chat-export and similar tools succeed through **reconstruction**, not by accessing pre-assembled data.

### Persistence Gap Theory (PARTIALLY CORRECT)

**What we theorized:** Cursor has systematic persistence delays where message content lags behind conversation activity by hours.

**Evidence found:**
- 1.3-hour gap between conversation activity and content availability
- Empty `text` fields in recent conversations
- Database bubble counts exceeding session header references

**Why partially wrong:** The "persistence gaps" were largely artifacts of **single-field extraction**. When checking all relevant fields (`text`, `thinking.text`, `toolFormerData`), completion rates reached 99.4% even for active sessions.

**What's still correct:** 
- **Historical sessions** may still experience variable persistence timing
- **Multi-stage persistence process** still occurs (placeholders → content population)
- **Time-based queries** for journal generation may encounter gaps in older data

**Lesson learned:** Persistence timing is less of an issue than extraction methodology. The multi-field approach resolves most "missing content" problems.

### Implementation Errors

**Timestamp Logic Error:**
- **Issue:** Used undefined `session_timestamp` variable in filtering examples
- **Fix:** Use `conversation.get('lastUpdatedAt', conversation.get('createdAt', 0))`

**Schema Misunderstanding:**
- **Issue:** Incorrectly stated workspace databases contain session metadata
- **Fix:** Session metadata stored in global database; workspace databases contain references only

**Tool Execution Overlooked:**
- **Issue:** Failed to account for tool executions as significant portion of conversation content
- **Fix:** Tool calls represent ~39% of messages in active sessions (121/311 in our test case)

### Key Success Factors

**What actually works:**
1. **Multi-field extraction** from `text`, `thinking.text`, and `toolFormerData` fields
2. **Session-level timestamps** for time-based filtering (not individual message timestamps)
3. **Bubble-by-bubble reconstruction** with proper field handling

**Critical insight:** cursor-chat-export succeeds not because they access different data, but because they **correctly implement the multi-field extraction approach** we initially missed.

### Implications for Journal Generation

**For active conversations:** 99%+ completion rates achievable with proper multi-field extraction.

**For historical data:** Persistence timing may still affect journal generation quality. Time-based queries should account for potential gaps in older sessions.

**Recommended approach:** Implement multi-field extraction first, then evaluate whether historical persistence timing requires additional lag periods for journal generation. 