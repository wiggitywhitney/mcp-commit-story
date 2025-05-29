# MCP API Specification

This document defines the Model Context Protocol (MCP) server operations, data formats, and integration patterns for the mcp-commit-story journal system.

## Table of Contents

1. [MCP Server Configuration](#mcp-server-configuration)
2. [MCP Operations](#mcp-operations)
3. [Operation Details](#operation-details)
4. [Data Formats](#data-formats)
5. [Error Handling](#error-handling)
6. [Context Data Structures](#context-data-structures)

---

## MCP Server Configuration

The MCP server must be launchable as a standalone process and expose the required journal operations. The server should be discoverable by compatible clients via standard configuration.

### Server Launch
- The method for launching the MCP server is not prescribed by this specification
- May be started via CLI command, Python entry point, or any appropriate mechanism
- Server must remain running and accessible to clients for the duration of its use

### Client/Editor Integration
Clients (such as editors or agents) should be able to connect using a configuration block:

```json
{
  "mcpServers": {
    "mcp-commit-story": {
      "command": "<launch command>",
      "args": ["<arg1>", "<arg2>", ...],
      "env": {
        "ANTHROPIC_API_KEY": "<optional>"
      }
    }
  }
}
```

### Separation of Concerns
- MCP server configuration (launch/discovery) is separate from journal system configuration
- Journal system configuration managed via `.mcp-commit-storyrc.yaml`

---

## MCP Operations

The server exposes these operations for journal management:

1. **`journal/new-entry`** - Create a new journal entry from current git state
2. **`journal/summarize`** - Generate weekly/monthly summaries  
3. **`journal/blogify`** - Convert journal entry(s) to blog post format
4. **`journal/backfill`** - Check for missed commits and create entries
5. **`journal/install-hook`** - Install git post-commit hook
6. **`journal/add-reflection`** - Add a manual reflection to today's journal
7. **`journal/init`** - Initialize journal in current repository

Each operation is instrumented with appropriate traces to monitor performance and error rates.

---

## Operation Details

### journal/new-entry
**Purpose**: Create a journal entry for the current commit

**Behavior**:
- Check for missed commits and backfill if needed
- Generate entry for current commit
- Return path to updated file

**Parameters**: None (uses current git state)

**Returns**:
```json
{
  "success": true,
  "file_path": "journal/daily/2025-01-15.md",
  "entries_created": 1,
  "backfilled": 0
}
```

### journal/summarize
**Purpose**: Generate summaries for specified time periods

**Parameters**:
- `period`: One of "day", "week", "month", "year"
- `date`: Specific date (optional, defaults to most recent)
- `range`: Arbitrary range in format "YYYY-MM-DD:YYYY-MM-DD" (optional)

**Behavior**:
- Daily summaries for quick recaps of previous day's work
- Weekly summaries for sprint retrospectives and short-term trends
- Monthly summaries for broader patterns and accomplishments
- Yearly summaries for major milestones and career progression
- Prioritize manually added reflections in summaries
- Prioritize substantial/complex work over routine changes

**Returns**:
```json
{
  "success": true,
  "file_path": "journal/summaries/weekly/2025-01-week3.md",
  "period": "week",
  "date_range": "2025-01-13 to 2025-01-19"
}
```

### journal/init
**Purpose**: Initialize journal in current repository

**Behavior**:
- Create initial journal directory structure
- Generate default configuration file
- Install git post-commit hook (with user confirmation)
- Return initialization status and created paths

**Returns**:
```json
{
  "success": true,
  "config_created": true,
  "hook_installed": true,
  "directories_created": ["journal/daily", "journal/summaries"]
}
```

### journal/add-reflection
**Purpose**: Add manual reflection to today's journal

**Parameters**:
- `text`: Reflection content (supports markdown)

**Behavior**:
- Append to today's journal file with timestamp
- Support markdown formatting in reflection
- Return path to updated file

**Returns**:
```json
{
  "success": true,
  "file_path": "journal/daily/2025-01-15.md",
  "reflection_added": true
}
```

### journal/blogify
**Purpose**: Transform journal entries into cohesive narrative content

**Parameters**:
- `files`: Array of journal file paths (single or multiple)

**Behavior**:
- Creates natural, readable blog post from technical entries
- Removes structural elements (headers, timestamps, metadata)
- Preserves key decisions and insights

**Returns**:
```json
{
  "success": true,
  "content": "<markdown blog post content>",
  "source_files": ["journal/daily/2025-01-15.md"]
}
```

### journal/backfill
**Purpose**: Check for missed commits and create entries

**Behavior**:
- Detection: Check commits since last journal entry in any file
- Order: Add missed entries in chronological order
- Context: Skip terminal/chat history for backfilled entries
- Annotation: Mark entries as backfilled with timestamp

**Returns**:
```json
{
  "success": true,
  "entries_created": 3,
  "date_range": "2025-01-10 to 2025-01-12"
}
```

### journal/install-hook
**Purpose**: Install git post-commit hook

**Behavior**:
- Check for existing hooks and handle conflicts
- Create hook with recursion prevention logic
- Back up existing hooks before modification

**Returns**:
```json
{
  "success": true,
  "hook_installed": true,
  "backup_created": ".git/hooks/post-commit.backup.20250115-143022"
}
```

---

## Data Formats

### Success Response Format
All successful operations return structured data with:
- `success: true`
- `file_path`: Path to created/modified file (when applicable)
- Operation-specific metadata

### Error Response Format
Failed operations return:
```json
{
  "success": false,
  "error": "Brief error description",
  "details": "Additional context (optional)"
}
```

### Journal Entry Content
- All operations return pre-formatted markdown strings
- Structured according to canonical journal entry format
- Include metadata for file paths and operation status

---

## Error Handling

### Hard Failures (Return Error Status)
These errors return error status and stop execution:
- Git repository not found
- Journal directory doesn't exist and can't be created
- Invalid MCP connection
- Corrupted git repository

### Soft Failures (Silent Skip)
These errors are handled gracefully without user notification:
- Terminal history not accessible
- Chat history unavailable or API errors  
- AI session command collection fails
- Previous commit not found for backfill
- Network timeouts when fetching optional data

### Graceful Degradation
- Always generate a journal entry regardless of available data sources
- Include what works, silently omit what doesn't
- No error messages clutter the journal output
- User never sees broken features - they just don't get that section

---

## Context Data Structures

All context collection functions return explicit Python TypedDicts for type safety and clear interfaces.

### JournalContext
```python
class JournalContext(TypedDict):
    commit_hash: str
    commit_message: str
    timestamp: datetime
    files_changed: List[str]
    insertions: int
    deletions: int
    chat_history: Optional[List[ChatMessage]]
    terminal_commands: Optional[List[str]]
    mood_indicators: Optional[str]
```

### ChatMessage
```python
class ChatMessage(TypedDict):
    speaker: str  # "Human" or "Agent"
    text: str
    timestamp: Optional[datetime]
```

### SummaryContext
```python
class SummaryContext(TypedDict):
    period: str  # "day", "week", "month", "year"
    start_date: datetime
    end_date: datetime
    journal_entries: List[str]
    major_accomplishments: List[str]
    patterns: List[str]
```

These structures ensure consistent data handling across all MCP operations and provide clear contracts for client integration. 