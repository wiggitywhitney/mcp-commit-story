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

1. **`journal/add-reflection`** - Add user reflection to today's journal entry  
2. **`journal/capture-context`** - Capture AI context and save to journal

Each operation is instrumented with appropriate traces to monitor performance and error rates.

---

## Operation Details




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
- Uses consistent "AI Context Capture" section headers

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
### 2:30 PM — AI Context Capture

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

#### Journal Entry Generation
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

#### File Operations
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