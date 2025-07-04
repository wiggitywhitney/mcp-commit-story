# Cursor Chat Database Architecture

## Overview

**MCP Commit Story** generates rich development journals by extracting comprehensive context from your Cursor chat history. This document explains Cursor's chat storage architecture and provides implementation guidance for chat data extraction.

## Quick Start Summary

**For implementers:** Cursor stores conversations in SQLite databases with a multi-field message system. To extract complete conversations:

1. **Find the global database** at `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` (macOS)
2. **Extract session metadata** from `composerData:{sessionId}` keys
3. **Get messages in chronological order** using session's `fullConversationHeadersOnly` array  
4. **Check multiple content fields**: `text` (user), `thinking.text` (AI), `toolFormerData` (tools)
5. **Use session timestamps** for time-based filtering (individual messages lack timestamps)

**Success rate:** 99%+ message extraction when using multi-field approach.

## Understanding Bubble Records

### What is a Bubble Record?

A **bubble record** is Cursor's fundamental unit for storing individual messages in chat conversations. Each message (whether from you or the AI) gets its own bubble record with a unique identifier.

**Think of it like this:**
- Each chat message = 1 bubble record  
- Each bubble record = 1 row in the database
- Bubble records contain the actual message content + metadata

**Database Key Pattern:**
```
bubbleId:{sessionId}:{bubbleId}
```

**Example:**
```
bubbleId:95d1fba7-8182-47e9-b02e-51331624eca3:msg_123456
```

### Message Types: User vs AI

Cursor uses a **type** field to distinguish between different kinds of messages:

| Type | Source | Description | Content Location |
|------|---------|-------------|------------------|
| **1** | **User** | Your questions and requests | `text` field |
| **2** | **AI** | Assistant responses and tool executions | `text`, `thinking.text`, or `toolFormerData` fields |

### Field Mapping: Where Content Lives

**🔑 Critical Insight:** Different message types store content in different fields. You MUST check the right field for each type.

```
Type 1 (User Messages):
├── text: "How do I implement authentication?"
├── context: {fileSelections, folderSelections}
└── type: 1

Type 2 (AI Messages):
├── Case A: Direct Response
│   ├── text: "I'll help you implement authentication..."
│   └── type: 2
├── Case B: AI Thinking
│   ├── thinking.text: "Let me analyze your setup..."
│   └── type: 2
└── Case C: Tool Execution
    ├── toolFormerData: {name: "read_file", result: "..."}
    └── type: 2
```

### Bubble Record Structure

```
┌─────────────────────────────────────┐
│          BUBBLE RECORD              │
├─────────────────────────────────────┤
│ type: 1 (user) or 2 (AI)           │
│ bubbleId: unique identifier         │
│                                     │
│ ┌─────────────────────────────┐    │
│ │    CONTENT (varies by type) │    │
│ ├─────────────────────────────┤    │
│ │ User (type 1):              │    │
│ │   text: "user's question"   │    │
│ ├─────────────────────────────┤    │
│ │ AI (type 2) can have:       │    │
│ │   text: "AI response"       │    │
│ │   thinking: {text: "..."}   │    │
│ │   toolFormerData: {...}     │    │
│ └─────────────────────────────┘    │
│                                     │
│ context: {                          │
│   fileSelections: [...]             │
│   folderSelections: [...]           │
│ }                                   │
└─────────────────────────────────────┘
```

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

## Practical Extraction Guide

### Multi-Field Message Extraction

**Critical:** Cursor stores different message types in different fields. You MUST check all relevant fields:

```python
def extract_message_content(bubble_data):
    """Extract content from all possible fields based on message type"""
    
    # User messages - check 'text' field
    if bubble_data.get('type') == 1:
        return bubble_data.get('text', '')
    
    # AI messages - check multiple fields
    elif bubble_data.get('type') == 2:
        # AI thinking/reasoning
        if 'thinking' in bubble_data:
            return bubble_data['thinking'].get('text', '')
        
        # AI direct responses
        elif 'text' in bubble_data:
            return bubble_data['text']
        
        # Tool executions
        elif 'toolFormerData' in bubble_data:
            tool_data = bubble_data['toolFormerData']
            return f"TOOL: {tool_data.get('name')} - {tool_data.get('result', '')}"
    
    return ""  # Empty or metadata message
```

### Session Discovery and Extraction

```python
def extract_session_conversations(session_id, db_path):
    """Extract complete conversation in chronological order"""
    
    # 1. Get session metadata with message order
    session_data = execute_cursor_query(
        db_path,
        "SELECT value FROM cursorDiskKV WHERE [key] = ?",
        (f'composerData:{session_id}',)
    )
    
    session = json.loads(session_data[0][0])
    headers = session.get('fullConversationHeadersOnly', [])
    
    # 2. Extract messages in chronological order
    messages = []
    for header in headers:  # This provides correct chronological order
        bubble_id = header['bubbleId']
        
        # Get individual message content
        bubble_data = execute_cursor_query(
            db_path,
            "SELECT value FROM cursorDiskKV WHERE [key] = ?",
            (f'bubbleId:{session_id}:{bubble_id}',)
        )
        
        if bubble_data and bubble_data[0][0]:
            message = json.loads(bubble_data[0][0])
            content = extract_message_content(message)
            
            messages.append({
                'content': content,
                'type': message.get('type'),
                'timestamp': session.get('lastUpdatedAt'),  # Session-level timing
                'bubble_id': bubble_id
            })
    
    return messages
```

### Time Window Integration

```python
def extract_commit_conversations(commit_hash, before_minutes=30):
    """Extract conversations relevant to a git commit"""
    
    commit_time = get_git_commit_timestamp(commit_hash)
    start_time = commit_time - (before_minutes * 60 * 1000)  # Convert to milliseconds
    
    # Find sessions overlapping the time window
    overlapping_sessions = []
    all_sessions = get_all_sessions(global_db_path)
    
    for session in all_sessions:
        session_start = session.get('createdAt', 0)
        session_end = session.get('lastUpdatedAt', session_start)
        
        # Check if session overlaps with commit time window
        if session_start <= commit_time and session_end >= start_time:
            messages = extract_session_conversations(session['composerId'], global_db_path)
            overlapping_sessions.append({
                'session': session,
                'messages': messages,
                'relevance_score': calculate_relevance(messages, commit_hash)  # Optional AI filtering
            })
    
    return overlapping_sessions
```

### Key Success Factors

1. **Multi-field extraction** - Check `text`, `thinking.text`, and `toolFormerData` fields
2. **Chronological ordering** - Use session metadata `fullConversationHeadersOnly`, NOT database key order
3. **Session-level timestamps** - Individual messages inherit session timing
4. **Correct session discovery** - Ensure you're querying the right session ID

## Schema Details

**Individual Message Structure:**
- Messages use a **multi-field content system**: `text` (user), `thinking.text` (AI), `toolFormerData` (tools)
- Messages do not contain individual timestamp fields - timestamps are session-level only
- Message types: 1=user, 2=assistant
- Backup files (`.vscdb.backup`) exist for transaction safety

**Persistence Notes:**
- Recent conversations (< 2 hours) are fully accessible in real-time
- Historical sessions may have variable persistence timing
- Multi-field extraction achieves 99%+ completion rates

## References

The [cursor-chat-browser](https://github.com/thomas-pedersen/cursor-chat-browser) and [cursor-chat-export](https://github.com/somogyijanos/cursor-chat-export) projects successfully extract Cursor's chat data using similar multi-field database access patterns.

---

## Development History and Failed Approaches

*This section documents our research journey and failed attempts to prevent repeating the same mistakes.*

**Example Session Timing:**
- **Session duration:** 5.1 hours (18:34 to 23:40)
- **Message density:** 269.9 messages/hour
- **Commit correlation:** Sessions span multiple commits; AI filtering needed for relevance

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

### Multi-Field Extraction Validation Test (COMPLETE SUCCESS)

**July 2, 2025: Complete Validation Achieved**

**What we tested:** Multi-field extraction on recent commit b71e3e1 session `95d1fba7-8182-47e9-b02e-51331624eca3`.

**Complete success:**
- ✅ **69 user messages** (type 1) extracted successfully via `text` field
- ✅ **1,236 AI messages** (type 2) extracted via `thinking.text` and `text` fields
- ✅ **Tool executions** extracted via `toolFormerData` field
- ✅ **No persistence lag** for recent data (all 1,377 messages fully accessible)
- ✅ **Perfect chronological ordering** using session metadata `fullConversationHeadersOnly`
- ✅ **End-to-end conversation flow** validated from user input through AI execution

**Critical Discovery - Chronological Ordering:**
Database key ordering (`ORDER BY [key]`) produces alphabetical UUID sorting, not chronological order. Session metadata provides correct temporal sequence.

**Time Window Integration:**
- Session-level timestamps compatible with git commit time windows
- Sessions can span 5+ hours across multiple commits
- AI filtering needed to scope session content to commit-relevant portions

**Key insight:** Complete conversation extraction validated. Technical foundation proven for production implementation.

**Status:** ✅ **FULLY VALIDATED** - All message types accessible, chronological ordering solved, time window strategy confirmed. 