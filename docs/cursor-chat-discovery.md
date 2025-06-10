# Cursor Chat Database Discovery

## Summary

**BREAKTHROUGH**: Discovered that Cursor stores complete chat history in accessible SQLite databases, providing full conversation context for journal generation without AI memory limitations.

## The Problem We Solved

- AI agents only have access to ~5-20 recent messages (not the "laughable 150" we thought)
- Journal entries had poor discussion notes due to limited chat context
- We were considering complex cronjob/file-saving solutions
- Needed verbatim conversation quotes for rich journal entries

## The Discovery

### What We Found
- **Complete chat history**: 271+ messages stored in SQLite database
- **Perfect JSON structure**: `text` and `commandType` fields
- **Real-time updates**: Database updates as conversation progresses
- **Full session context**: Entire development session accessible

### Where It's Stored
```bash
# macOS Location
~/Library/Application Support/Cursor/User/workspaceStorage/

# Structure
workspaceStorage/
├── [md5-hash-1]/
│   ├── state.vscdb          # The SQLite database with chat data
│   ├── state.vscdb.backup
│   └── workspace.json
├── [md5-hash-2]/
└── ...
```

### Database Schema
```sql
-- Table: ItemTable
CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);

-- Key chat data locations:
-- 'aiService.prompts' - Contains the complete chat history as JSON array
-- 'workbench.panel.aichat.view.aichat.chatdata' - May contain additional chat data
```

## How We Discovered It

### Investigation Steps
1. **Started with context7 research**: Used MCP context7 tools to investigate Cursor capabilities
2. **Found community knowledge**: Someone shared the exact workspaceStorage location and query
3. **Explored the file system**:
   ```bash
   cd ~/Library/Application\ Support/Cursor/User/workspaceStorage
   ls -la  # Found md5 hash directories
   ```
4. **Installed datasette** for SQLite analysis:
   ```bash
   pip install datasette
   ```
5. **Queried the database**:
   ```bash
   sqlite3 [hash]/state.vscdb ".tables"  # Found ItemTable
   sqlite3 [hash]/state.vscdb ".schema ItemTable"  # Found key/value structure
   ```
6. **Found the chat data**:
   ```sql
   SELECT rowid, [key], length(value) 
   FROM ItemTable 
   WHERE [key] IN ('aiService.prompts', 'workbench.panel.aichat.view.aichat.chatdata');
   ```

### The Magic Query
```sql
SELECT value FROM ItemTable WHERE [key] = 'aiService.prompts';
```
Returns JSON array with complete chat history:
```json
[
  {
    "text": "User message text here...",
    "commandType": 4
  },
  ...
]
```

## Implementation for Journal System

### New Architecture (No Cronjobs Needed!)
```python
def collect_cursor_chat_history(since_commit=None) -> ChatHistory:
    """
    Collect complete chat history directly from Cursor's SQLite database.
    No AI interruption, no cronjobs, no file management needed.
    """
    # 1. Find current workspace
    workspace_storage = Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    current_workspace = find_current_workspace_hash()  # Most recently modified
    
    # 2. Query SQLite database
    db_path = workspace_storage / current_workspace / "state.vscdb"
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT value FROM ItemTable WHERE [key] = 'aiService.prompts'")
    chat_json = cursor.fetchone()[0]
    
    # 3. Parse and return
    chat_data = json.loads(chat_json)
    return ChatHistory(messages=[msg["text"] for msg in chat_data])
```

### Integration Points
- **Git hook trigger**: Hook calls journal generation
- **Journal generation**: Calls `collect_cursor_chat_history()` directly
- **No file management**: Read directly from Cursor's live database
- **Full context**: Complete conversation available for discussion notes

## Technical Details

### Finding Current Workspace
```python
def find_current_workspace_hash() -> str:
    """Find the most recently active workspace by modification time."""
    workspace_storage = Path.home() / "Library/Application Support/Cursor/User/workspaceStorage"
    most_recent = None
    latest_time = 0
    
    for workspace_dir in workspace_storage.iterdir():
        if workspace_dir.is_dir() and len(workspace_dir.name) == 32:  # MD5 hash length
            state_file = workspace_dir / "state.vscdb"
            if state_file.exists():
                mtime = state_file.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    most_recent = workspace_dir.name
    
    return most_recent
```

### Error Handling
```python
def collect_cursor_chat_with_fallback() -> ChatHistory:
    """Graceful degradation if Cursor database isn't accessible."""
    try:
        return collect_cursor_chat_history()
    except Exception as e:
        logger.warning(f"Cursor chat collection failed: {e}")
        # Fallback to synthesized summary or empty chat
        return ChatHistory(messages=[])
```

## What This Changes

### ✅ Problems Solved
- **No more chat memory limitations**: Full conversation available
- **No more cronjobs needed**: Direct database access
- **No more file management**: Read from live Cursor database
- **Rich discussion notes**: Complete verbatim conversations
- **Real-time accuracy**: Database updates as we chat

### 🎯 New Capabilities
- **Complete session context**: Journal entries can reference entire development session
- **Verbatim quotes**: Exact conversation snippets for discussion notes
- **Decision tracking**: Full decision-making process captured
- **Cursor-enhanced**: Leverages Cursor's unique data storage

### 🔧 Implementation Changes Needed
1. **Update `context_collection.py`**: Replace chat collection with direct SQLite query
2. **Remove cronjob plans**: No longer needed
3. **Update journal generation**: Use full chat context for discussion notes
4. **Add error handling**: Graceful degradation if database unavailable

## Next Steps

1. **Implement the SQLite reader function**
2. **Update context collection to use it**
3. **Test with real journal generation**
4. **Update documentation to reflect new architecture**
5. **Celebrate having solved the chat limitation problem!** 🎉

## Notes
- This approach is Cursor-specific (perfect for "Cursor-enhanced" system)
- Database format could change with Cursor updates (monitor for breaking changes)
- Performance is excellent (direct SQLite read is very fast)
- No user interruption or background processes needed 