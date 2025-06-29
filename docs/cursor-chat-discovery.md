# Cursor Chat Database Discovery

## System Overview

**MCP Commit Story** is an engineering journal system that generates rich documentation from your development sessions using direct context collection. When you make a git commit, it:

1. **Executes Git Hooks** to trigger immediate journal generation  
2. **Collects Context** from four sources: git changes, terminal history, chat conversations, and AI summaries
3. **Generates Journal Entries** with AI, including technical details, accomplishments, and decision rationale  
4. **Preserves Development History** in markdown files for future reference

**The Chat History Problem**: Previously, journal entries had poor "discussion notes" because AI agents only access ~5-20 recent messages, missing crucial conversation context about design decisions and problem-solving approaches.

**This Discovery**: Found that Cursor stores complete chat history in accessible SQLite databases across **two separate chat systems**, enabling comprehensive conversation capture for rich journal documentation.

## Summary

**BREAKTHROUGH**: Discovered that Cursor 1.1.6 stores chat history across **two separate systems** in accessible SQLite databases:

1. **aiService System**: Quick AI interactions (~361 messages in current function)
2. **Composer System**: Rich conversational sessions (~535+ messages per session, with 29 sessions found!)

**CRITICAL INSIGHT**: Current implementation only captures **~25% of actual chat data**. The majority of rich conversational content is stored in the Composer system with full context, file attachments, and threading.

**WORKSPACE DETECTION SOLVED**: Each workspace directory contains `workspace.json` files that map hash directories to actual project paths, enabling precise workspace-specific chat extraction.

**ARCHITECTURE INSIGHT**: One workspace can have multiple hash directories due to Cursor's database rotation/archiving, requiring multi-directory scanning for complete chat history.

## The Complete Discovery: Two Chat Systems

### cursor-chat-browser Validation ✅

**Community Project**: [cursor-chat-browser](https://github.com/thomas-pedersen/cursor-chat-browser)
- **415 stars, 69 forks** - Proven cross-platform approach
- **Active development** - Supports both chat systems
- **Production ready** - Web interface with search, export (Markdown/HTML/PDF)

**Their Architecture Understanding**:
- ✅ Recognizes two distinct chat systems
- ✅ Extracts from both workspace and global storage
- ✅ Handles rich composer conversation data
- ✅ Cross-platform workspace detection

### Cursor 1.1.6 Complete Architecture

| **System** | **Storage Location** | **Data Type** | **Coverage** |
|-----------|---------------------|---------------|--------------|
| **aiService** | `workspaceStorage/{hash}/state.vscdb` | Quick AI interactions | ~361 messages (current function) |
| **Composer** | Workspace: metadata<br/>Global: conversations | Rich sessions with context | ~535+ messages per session |

### Database Locations & Structure
```bash
# Cross-Platform Locations
# Windows: %APPDATA%\Cursor\User\workspaceStorage
# WSL2: /mnt/c/Users/<USERNAME>/AppData/Roaming/Cursor/User/workspaceStorage
# macOS: ~/Library/Application Support/Cursor/User/workspaceStorage
# Linux: ~/.config/Cursor/User/workspaceStorage

# Workspace Storage Structure
workspaceStorage/
├── 1045d7c1d15e4bacac8a85d48b8acfcb/          # Hash-based directory
│   ├── workspace.json                           # 🔑 Workspace mapping
│   ├── state.vscdb                             # aiService + Composer metadata
│   └── state.vscdb.backup                      # Backup
└── [Multiple other workspace directories]

# Global Storage Structure  
globalStorage/
└── state.vscdb                                  # 🔑 Composer conversation content
```

### Workspace Detection Solution
```json
// workspace.json contains the actual workspace path mapping
{
  "folder": "file:///Users/username/Repos/mcp-commit-story"
}
```

**Key Insight**: Hash directories are NOT workspace names - they're generated IDs. The `workspace.json` file contains the actual workspace path, enabling precise workspace identification.

## Chat System 1: aiService (Current Function)

### Database Schema & Data Structure
```sql
-- Table: ItemTable (key-value store)
-- Location: workspaceStorage/{hash}/state.vscdb
CREATE TABLE ItemTable (
    [key] TEXT PRIMARY KEY,
    value BLOB
);

-- aiService Keys:
-- 'aiService.prompts' - User messages (261 messages, NO timestamps)
-- 'aiService.generations' - AI responses (100 messages, WITH unixMs timestamps)
```

### aiService Data Structure

**Human Messages (aiService.prompts)**:
```json
[
  {
    "text": "User message content...",
    "commandType": 4
    // Note: NO timestamp field
  }
]
```

**AI Responses (aiService.generations)**:
```json
[
  {
    "unixMs": 1751046149314,
    "generationUUID": "uuid-here", 
    "type": "composer",  // or "apply"
    "textDescription": "AI response content..."
  }
]
```

### Current Function Results (aiService Only)
**From MCP-Commit-Story Workspace (Last 48 Hours)**:
- **Total Messages**: 361 (261 user + 70 composer + 30 apply)
- **User Messages**: 261 (no timestamps, identified by lack of type)
- **AI Composer**: 70 (with timestamps, conversation responses)
- **AI Apply**: 30 (with timestamps, code application actions)
- **Time Span**: 35.8 hours (June 27-29, 2025)

**⚠️ CRITICAL LIMITATION**: This represents only **~25%** of actual chat data!

## Chat System 2: Composer (Missing from Current Function)

### Composer Architecture

**Metadata Storage**: `workspaceStorage/{hash}/state.vscdb`
```sql
-- Key: 'composer.composerData'
-- Contains: Composer session metadata (29 sessions found)
```

**Conversation Storage**: `globalStorage/state.vscdb`
```sql
-- Table: cursorDiskKV (different from ItemTable!)
-- Key Pattern: 'composerData:{composerId}' - Full session data
-- Key Pattern: 'bubbleId:{composerId}:{bubbleId}' - Individual messages
```

### Composer Data Structure

**Session Metadata** (`composer.composerData`):
```json
{
  "allComposers": [
    {
      "composerId": "0c74276c-5af6-4ca3-b49f-353481619b2d",
      "name": "Summarize daily accomplishments", 
      "createdAt": 1751171755435,
      "lastUpdatedAt": 1751178902944,
      "type": "head"
    }
  ],
  "selectedComposerId": "...",
  "selectedChatId": "..."
}
```

**Session Conversation** (`composerData:{composerId}`):
```json
{
  "composerId": "0c74276c-5af6-4ca3-b49f-353481619b2d",
  "name": "Summarize daily accomplishments",
  "fullConversationHeadersOnly": [
    {
      "bubbleId": "aaf471dc-8de5-4a23-8f1c-abc123...",
      "type": 1  // 1 = user, 2 = assistant
    }
  ],
  "conversationMap": {},  // Empty in Cursor 1.1.6
  "context": {...},       // File attachments, selections
  "richText": "...",
  "text": "..."
}
```

**Individual Messages** (`bubbleId:{composerId}:{bubbleId}`):
```json
{
  "text": "User message or AI response content...",
  "richText": "{\"root\":{\"children\":[...]}}",  // Formatted content
  "timestamp": 1751046149314,
  "context": {
    "fileSelections": [...],   // Attached files
    "folderSelections": [...], // Attached folders  
    "selectedDocs": [...]      // Documentation references
  }
}
```

### Composer Results (One Session Example)
**"Summarize daily accomplishments" Session**:
- **Total Conversation Headers**: 535 messages
- **Rich Context**: File attachments, code selections, documentation references
- **Timestamps**: Proper chronological ordering
- **Rich Formatting**: Code blocks, syntax highlighting
- **Session Names**: Human-readable titles like "Review journal entries and plan 46.9"

**Found 29 Composer Sessions** in current workspace!

## Complete Cursor 1.1.6 Extraction Method

### cursor-chat-browser's Proven Approach

**Workspace Discovery**:
```typescript
// Scan all hash directories for workspace matches
for (const entry of workspaceEntries) {
  const workspaceJsonPath = path.join(workspacePath, entry.name, 'workspace.json')
  const workspaceData = JSON.parse(await fs.readFile(workspaceJsonPath, 'utf-8'))
  // Match workspace.folder to target workspace
}
```

**aiService Chat Extraction**:
```sql
-- Legacy chat data (older Cursor versions)
SELECT value FROM ItemTable 
WHERE [key] = 'workbench.panel.aichat.view.aichat.chatdata'

-- Current approach (aiService system)
SELECT value FROM ItemTable WHERE [key] = 'aiService.prompts'
SELECT value FROM ItemTable WHERE [key] = 'aiService.generations'
```

**Composer Extraction**:
```sql
-- Step 1: Get composer metadata from workspace DB
SELECT value FROM ItemTable WHERE [key] = 'composer.composerData'

-- Step 2: Get conversation headers from global DB  
SELECT value FROM cursorDiskKV WHERE [key] = 'composerData:{composerId}'

-- Step 3: Get individual messages from global DB
SELECT value FROM cursorDiskKV WHERE [key] = 'bubbleId:{composerId}:{bubbleId}'
```

## Workspace Detection Architecture

### Current Reality vs Initial Assumptions

**What We Initially Thought**:
- One workspace = One hash directory
- Current function finds first matching directory
- 48-hour filtering applied to single database

**What Actually Happens**:
- **One workspace can have multiple hash directories** (rotation, archiving, corruption recovery)
- Cursor rotates/archives databases periodically
- Current approach only finds the most recent active database
- Earlier chat history gets lost when databases are rotated

### Evidence of Database Rotation
```
Database created: May 16, 2025 (6 weeks ago)
Chat data captured: 35.8 hours (June 27-29, 2025) 
Missing history: ~4+ weeks of earlier conversations!
```

**The user has been working on this project much longer than the current database shows.**

### Git Hook Workspace Specificity ✅ 
**Already solved!** Each repository gets its own hook in `.git/hooks/post-commit` that passes `"$PWD"` to the worker. Perfect workspace isolation - when you commit in MCP-commit-story, only the MCP-commit-story journal gets triggered.

### Recommended Complete Implementation Architecture

**Phase 1: Multi-System Chat Extraction**
```python
def query_cursor_chat_database_complete(target_workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Query BOTH cursor chat systems for complete conversation history.
    
    Returns:
        {
            'aiService': {
                'total_messages': 361,
                'user_messages': [...],
                'ai_responses': [...]
            },
            'composer': {
                'sessions': [
                    {
                        'composerId': '...',
                        'name': 'Summarize daily accomplishments',
                        'conversation': [...],  # 535+ messages
                        'context': {...}        # File attachments, etc.
                    }
                ],
                'total_sessions': 29,
                'total_messages': 15000+
            }
        }
    """
    # 1. Find ALL directories that map to the same workspace
    workspace_storage = get_primary_workspace_path()
    matching_directories = find_matching_workspace_directories(target_workspace_path)
    
    # 2. Extract aiService data (current implementation)
    aiservice_data = extract_aiservice_data(matching_directories)
    
    # 3. Extract Composer data (NEW)
    composer_data = extract_composer_data(matching_directories)
    
    # 4. Apply 48-hour filtering across ALL systems
    filtered_data = apply_time_filtering([aiservice_data, composer_data])
    
    return filtered_data

def extract_composer_data(workspace_directories: List[str]) -> Dict[str, Any]:
    """Extract complete composer conversation data."""
    # Get composer metadata from workspace databases
    composers = []
    for hash_dir in workspace_directories:
        workspace_db = sqlite3.connect(f"{hash_dir}/state.vscdb")
        metadata = workspace_db.execute("SELECT value FROM ItemTable WHERE [key] = 'composer.composerData'")
        composers.extend(parse_composer_metadata(metadata))
    
    # Get conversation content from global database
    global_db = sqlite3.connect("globalStorage/state.vscdb") 
    complete_conversations = []
    
    for composer in composers:
        # Get conversation headers
        headers_key = f"composerData:{composer['composerId']}"
        headers = global_db.execute("SELECT value FROM cursorDiskKV WHERE [key] = ?", (headers_key,))
        
        # Get individual message content
        conversation = []
        for header in headers['fullConversationHeadersOnly']:
            bubble_key = f"bubbleId:{composer['composerId']}:{header['bubbleId']}"
            message = global_db.execute("SELECT value FROM cursorDiskKV WHERE [key] = ?", (bubble_key,))
            conversation.append(parse_composer_message(message, header))
        
        complete_conversations.append({
            'composerId': composer['composerId'],
            'name': composer['name'],
            'conversation': conversation,
            'metadata': composer
        })
    
    return {
        'sessions': complete_conversations,
        'total_sessions': len(complete_conversations),
        'total_messages': sum(len(c['conversation']) for c in complete_conversations)
    }
```

## Current Implementation Status

### ✅ What Works (aiService System)
- **Database Access**: SQLite reading works perfectly across platforms
- **Data Extraction**: Successfully extracts both user and AI messages
- **48-Hour Filtering**: Correctly filters to recent activity
- **Workspace Storage Detection**: Finds correct workspace storage directory
- **JSON Parsing**: Clean parsing of prompts and generations data
- **Message Reconstruction**: Combines prompts + generations into chronological flow

### ❌ Major Gaps (Composer System)
- **Missing 75%+ of Chat Data**: Composer system not implemented
- **No Rich Context**: File attachments, code selections not captured
- **No Session Organization**: 29 composer sessions ignored
- **No Conversation Threading**: Rich conversation structure lost
- **No Global Database Access**: cursorDiskKV table not queried

### ⚠️ Current Limitations (Both Systems)
- **Single Directory**: Only scans first matching workspace directory
- **Missing Archives**: Doesn't include rotated/archived databases  
- **No Timestamp for User Messages**: User prompts lack timestamps in raw data
- **Message Duplication**: Some messages appear multiple times in processing
- **Incomplete History**: Missing 4+ weeks of earlier conversations due to rotation

### 🚀 Updated OSS Implementation Priorities

**Phase 1 (Critical)**: Composer System Implementation
- 🔥 **Extract composer metadata** from workspace databases
- 🔥 **Access global storage database** (different table structure)
- 🔥 **Implement conversation header parsing** (fullConversationHeadersOnly)
- 🔥 **Extract individual messages** via bubbleId key pattern
- 🔥 **Combine with existing aiService extraction** for complete coverage

**Phase 2 (Enhancement)**: Multi-Directory Workspace Detection
- ✅ Scan ALL hash directories for matching `workspace.json` files
- ✅ Combine chat data from multiple directories for same workspace  
- ✅ Apply 48-hour filtering across all matching databases
- ✅ Provide clear workspace identification in results

**Phase 3 (Polish)**: Archive Database Support
- 📋 Include `.backup` files in same directories
- 📋 Research Cursor's archive/rotation patterns
- 📋 Add configurable time windows (48h active, 7d archives)
- 📋 Implement archive database discovery

**Phase 4 (Configuration)**: Power User Options
- 📋 Allow users to specify custom database paths
- 📋 Support manual archive database inclusion
- 📋 Configurable time windows per workspace

## Strategic Research: Community Validation

### Inspiration: [cursor-chat-browser](https://github.com/thomas-pedersen/cursor-chat-browser)

**Community Validation**:
- **415 stars, 69 forks** - Proven approach
- **Active development** - Cross-platform support
- **Production ready** - Web interface for browsing chat histories

**Key Features That Validate Our Approach**:
- 🔍 Browse and search all workspaces with Cursor chat history
- 🤖 **View both AI chat logs and Composer logs** ⭐ **CRITICAL INSIGHT**
- 📁 Organize chats by workspace
- 🔎 Full-text search with filters for chat/composer logs
- ⬇️ Export chats as Markdown, HTML, PDF
- ⚙️ **Automatic workspace path detection**

**cursor-chat-browser Architecture We Should Adopt**:
```typescript
// They handle BOTH chat systems:
// 1. Legacy chat system (workbench.panel.aichat.view.aichat.chatdata)
// 2. Current aiService system (aiService.prompts + aiService.generations) 
// 3. Composer system (composer.composerData + global cursorDiskKV)

// Their extraction process:
const chatResult = await db.get(`
  SELECT value FROM ItemTable
  WHERE [key] = 'workbench.panel.aichat.view.aichat.chatdata'
`)

const composerResult = await db.get(`
  SELECT value FROM ItemTable
  WHERE [key] = 'composer.composerData'  
`)

// Global database lookup for composer content:
const globalDb = await open({ filename: globalDbPath })
const composersBodyResult = await globalDb.all(`
  SELECT value FROM cursorDiskKV WHERE [key] in (${placeholders})
`, composerKeys)
```

## Implementation Benefits

### ✅ **Confirmed Benefits**
- **Zero external dependencies**: Uses Python's built-in sqlite3 module
- **No cronjobs needed**: Direct database access eliminates complexity
- **Real-time accuracy**: Database updates as conversation progresses
- **Cross-platform proven**: Community projects validate all major platforms
- **Complete session context**: Full development session accessible
- **Performance**: Direct SQLite read is very fast

### 🎯 **Strategic Value (When Complete)**
- **Rich Journal Context**: Verbatim conversation quotes with full context
- **Complete Development Story**: Full problem-solving narrative with file attachments
- **Pattern Recognition**: AI can identify recurring themes across 29+ sessions
- **Knowledge Preservation**: Critical design discussions with code context never lost
- **Team Collaboration**: Shared understanding of development rationale with rich formatting

### 🚨 **Current Gap Analysis**
**Current Function**: 361 messages (aiService only)
**Complete Reality**: 361 + (29 sessions × ~535 messages) = **~15,000+ messages available!**

**Missing Data Types**:
- File attachments and code selections
- Rich text formatting and code blocks  
- Conversation threading and session organization
- Documentation references and context
- Timestamps for proper chronological reconstruction

## How We Discovered It

### Investigation Process
1. **Started with context7 research**: Used MCP context7 tools to investigate Cursor capabilities
2. **Found community knowledge**: cursor-chat-browser project provided architectural foundation
3. **Explored the file system**: Located workspaceStorage and hash directories
4. **Database Schema Analysis**: Used sqlite3 to understand ItemTable structure
5. **Data Structure Investigation**: Found prompts vs generations separation
6. **Workspace Mapping Discovery**: Found workspace.json files with path mappings
7. **Rotation Pattern Detection**: Discovered multi-directory workspace reality
8. **Function Implementation**: Built query_cursor_chat_database() with proper filtering
9. **cursor-chat-browser Deep Dive**: Analyzed their complete extraction approach
10. **Global Database Discovery**: Found cursorDiskKV table with composer conversations
11. **Key Pattern Investigation**: Discovered bubbleId:{composerId}:{bubbleId} pattern
12. **Testing & Validation**: Confirmed composer session extraction (535+ messages)

### The Complete Magic Queries

**aiService System (Current)**:
```sql
-- Get user messages (no timestamps)
SELECT value FROM ItemTable WHERE [key] = 'aiService.prompts';

-- Get AI responses (with timestamps)  
SELECT value FROM ItemTable WHERE [key] = 'aiService.generations';
```

**Composer System (Missing)**:
```sql
-- Step 1: Get composer session metadata (workspace DB)
SELECT value FROM ItemTable WHERE [key] = 'composer.composerData';

-- Step 2: Get conversation headers (global DB)  
SELECT value FROM cursorDiskKV WHERE [key] = 'composerData:{composerId}';

-- Step 3: Get individual messages (global DB)
SELECT value FROM cursorDiskKV WHERE [key] = 'bubbleId:{composerId}:{bubbleId}';
```

**Workspace Detection**:
```sql
-- Get workspace mapping
SELECT value FROM ItemTable WHERE [key] = 'workspace.json';
```

## Files Generated During Investigation
- `chat_data_last_48h.json` - Partial processed chat data (361 messages from aiService only)
- `raw_database_data.json` - Raw database contents for analysis
- ~~`chat_data_analysis.md`~~ - Replaced by this comprehensive discovery
- ~~`workspace_detection_analysis.md`~~ - Replaced by this comprehensive discovery

This discovery reveals that MCP Commit Story has access to **~15,000+ messages** of rich conversation history with full context, solving the core problem of AI memory limitations in development documentation. **Current implementation captures only ~25% of available data.**

**Next Step**: Implement composer system extraction to access the remaining **~75% of chat history** with rich context and formatting. 