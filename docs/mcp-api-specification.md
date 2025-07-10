# MCP API Specification

This document defines the Model Context Protocol (MCP) server operations, data formats, and integration patterns for the mcp-commit-story journal system.

## Table of Contents

1. [MCP Server Configuration](#mcp-server-configuration)
2. [MCP Operations](#mcp-operations)
3. [Operation Details](#operation-details)
4. [Data Formats](#data-formats)
5. [Error Handling](#error-handling)
6. [Context Data Structures](#context-data-structures)
7. [Type System](#type-system)

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
        "OPENAI_API_KEY": "<your-openai-api-key>"
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

1. **`journal/new-entry`** - Create a new journal entry from git, chat, and terminal context ✅ **IMPLEMENTED**
2. **`journal/add-reflection`** - Add a manual reflection to a specific date's journal
3. **`journal/capture-context`** - Capture AI-generated project knowledge for future context ✅ **IMPLEMENTED**
4. **`journal/init`** - Initialize journal in current repository  
5. **`journal/install-hook`** - Install git post-commit hook

Each operation is instrumented with appropriate traces to monitor performance and error rates.

---

## Operation Details

### journal/new-entry ✅ **FULLY IMPLEMENTED**
**Purpose**: Create a journal entry for the current commit

**Implementation Status**: Complete with comprehensive TypedDict integration, full test coverage, and proper error handling.

**Parameters**:
- `git: Dict[str, Any]` (required) - Git context information including commit hash, message, files changed, etc.
- `chat: Optional[Any]` (optional) - Chat history context from development session
- `terminal: Optional[Any]` (optional) - Terminal command history context

**Implementation Details**:
- Integrates with `generate_journal_entry()` from subtask 9.1 for context collection and entry generation
- Uses `save_journal_entry()` from subtask 9.2 for file operations and persistence  
- Implements comprehensive TypedDict validation for all workflow data structures
- Includes journal-only commit detection to prevent recursion
- Provides structured error responses with telemetry integration
- Supports automatic directory creation following on-demand patterns

**Returns**:
```json
{
  "status": "success", 
  "file_path": "journal/daily/2025-01-15.md",
  "error": null
}
```

**Skipped Commits Response**:
```json
{
  "status": "skipped",
  "file_path": "",
  "error": null
}
```

**Error Response**:
```json
{
  "status": "error",
  "file_path": "",
  "error": "Detailed error message"
}
```

**Example Request**:
```json
{
  "git": {
    "commit_hash": "abc123",
    "commit_message": "Implement user authentication",
    "files_changed": ["src/auth.py", "tests/test_auth.py"],
    "insertions": 45,
    "deletions": 12
  },
  "chat": {
    "messages": [
      {"speaker": "Human", "text": "Let's implement JWT authentication"},
      {"speaker": "Agent", "text": "I'll help you set up JWT tokens..."}
    ]
  },
  "terminal": {
    "commands": ["npm test", "git add .", "git commit -m 'Implement user authentication'"]
  }
}
```

### journal/init
**Purpose**: Initialize journal in current repository

**Parameters**:
- `repo_path: str` (optional) - Path to the git repository (defaults to current directory)
- `config_path: str` (optional) - Path for the config file (defaults to .mcp-commit-storyrc.yaml in repo root)
- `journal_path: str` (optional) - Path for the journal directory (defaults to journal/ in repo root)

**Behavior**:
- Create initial journal directory structure
- Generate default configuration file
- Install git post-commit hook (with user confirmation)
- Return initialization status and created paths

**Returns**:
```json
{
  "status": "success",
  "paths": {
    "config": "/path/to/.mcp-commit-storyrc.yaml",
    "journal": "/path/to/journal"
  },
  "message": "Journal initialized successfully"
}
```

**Example Request**:
```json
{
  "repo_path": "/path/to/my-project",
  "config_path": "/path/to/my-project/.mcp-commit-storyrc.yaml",
  "journal_path": "/path/to/my-project/journal"
}
```

### journal/add-reflection
**Purpose**: Add manual reflection to a specific date's journal

**Parameters**:
- `reflection: str` (required) - Reflection content (supports markdown)
- `date: str` (required) - ISO date string (YYYY-MM-DD)

**Behavior**:
- Append to the specified date's journal file with timestamp
- Support markdown formatting in reflection
- Return path to updated file

**Returns**:
```json
{
  "status": "success",
  "file_path": "journal/daily/2025-01-15.md",
  "error": null
}
```

**Example Request**:
```json
{
  "reflection": "Today I learned about JWT token validation and how to properly handle refresh tokens. The key insight was understanding the difference between access and refresh token lifespans.",
  "date": "2025-01-15"
}
```

### journal/install-hook
**Purpose**: Install git post-commit hook

**Parameters**:
- `repo_path: str` (optional) - Path to git repository (defaults to current directory)

**Behavior**:
- Check for existing hooks and handle conflicts
- Create hook with recursion prevention logic
- Back up existing hooks before modification

**Returns**:
```json
{
  "status": "success",
  "message": "Post-commit hook installed successfully.",
  "backup_path": "/path/to/.git/hooks/post-commit.backup.20250115-143022",
  "hook_path": "/path/to/.git/hooks/post-commit"
}
```

**Example Request**:
```json
{
  "repo_path": "/path/to/my-project"
}
```

### journal/capture-context ✅ **FULLY IMPLEMENTED**
**Purpose**: Capture AI-generated project knowledge and store it in the daily journal

**Implementation Status**: Complete with telemetry integration, context collection support, and proper file operations.

**Parameters**:
- `text: Optional[str]` (optional) - AI knowledge to capture (if null, captures full AI context dump)

**Implementation Details**:
- Integrates with existing journal file structure and timestamp formatting
- Includes captured knowledge in future journal generation as context
- Implements proper telemetry tracking and error handling
- Supports automatic creation of daily journal files
- Uses consistent "AI Knowledge Capture" section headers

**Behavior**:
- Append AI knowledge to today's journal file with timestamp
- Create daily journal file if it doesn't exist
- Support markdown formatting in captured text
- Include captured knowledge in future journal context collection

**Returns**:
```json
{
  "status": "success",
  "file_path": "journal/daily/2025-01-15-journal.md",
  "error": null
}
```

**Error Response**:
```json
{
  "status": "error",
  "file_path": "",
  "error": "Detailed error message"
}
```

**Example Request**:
```json
{
  "text": "Key insight about React state management: Use useCallback for expensive computations in list items to prevent unnecessary re-renders. This pattern reduces rendering time by 60% in our product catalog."
}
```

**Example Journal Output**:
```markdown
### 2:30 PM — AI Knowledge Capture

Key insight about React state management: Use useCallback for expensive 
computations in list items to prevent unnecessary re-renders. This pattern 
reduces rendering time by 60% in our product catalog.
```

---

## Data Formats

### Success Response Format
All successful operations return structured data with:
- `status: "success"`
- Operation-specific data (e.g., `file_path`, `paths`, `message`)
- `error: null` (for operations that include error field)

### Error Response Format
Failed operations return:
```json
{
  "status": "error",
  "error": "Brief error description"
}
```

**Note**: Some operations may use custom status values (e.g., `"bad-request"`) for specific error types.

### Journal Entry Content
- All operations return pre-formatted markdown strings when applicable
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
    period: str  # "day", "week", "month", "quarter", "year"
    start_date: datetime
    end_date: datetime
    journal_entries: List[str]
    major_accomplishments: List[str]
    patterns: List[str]
```

---

## Type System

The journal workflow operations utilize comprehensive TypedDict definitions to ensure type safety and clear API contracts across all functions.

### Core Workflow Types

#### Journal Entry Generation (Subtask 9.1)
```python
class GenerateJournalEntryInput(TypedDict):
    """Input parameters for generate_journal_entry function."""
    commit: Any  # git.Commit object
    config: Dict[str, Any]  # Config object or dict representation
    debug: bool

class GenerateJournalEntryResult(TypedDict):
    """Result from generate_journal_entry function."""
    entry: Optional[Any]  # JournalEntry object or None if skipped
    skipped: bool
    skip_reason: Optional[str]  # Only present if skipped=True
```

#### File Operations (Subtask 9.2)
```python
class SaveJournalEntryInput(TypedDict):
    """Input parameters for save_journal_entry function."""
    entry: Any  # JournalEntry object
    config: Dict[str, Any]  # Config object or dict representation

class SaveJournalEntryResult(TypedDict):
    """Result from save_journal_entry function."""
    file_path: str  # Absolute path to saved journal file
    success: bool
    created_new_file: bool  # Whether a new file was created vs appended
```

#### Context Collection
```python
class CollectedJournalContext(TypedDict):
    """Fully assembled context data for journal generation."""
    git_context: GitContext
    chat_context: Optional[ChatHistory]
    terminal_context: Optional[TerminalContext]
    config: Dict[str, Any]
    collection_timestamp: str  # ISO timestamp when context was collected

class ContextCollectionResult(TypedDict):
    """Result from context collection operations."""
    context: CollectedJournalContext
    collection_success: bool
    failed_sources: List[str]  # Sources that failed to collect
    warnings: List[str]  # Non-fatal issues during collection
```

### Type Safety Benefits
- **Clear API Contracts**: Each function's inputs and outputs are explicitly typed
- **IDE Support**: Full IntelliSense and autocomplete support
- **Runtime Validation**: TypedDict structures can be validated at runtime
- **Documentation**: Self-documenting code with clear data structure expectations
- **Error Prevention**: Catch type mismatches during development

### Import Usage
```python
# Import from package root
from mcp_commit_story import GenerateJournalEntryInput, SaveJournalEntryResult

# Or import from specific modules
from mcp_commit_story.journal_workflow_types import CollectedJournalContext
from mcp_commit_story.context_types import GitContext, ChatHistory
```

The type system is fully tested with 17 comprehensive test cases covering structure validation, compatibility, and integration scenarios.