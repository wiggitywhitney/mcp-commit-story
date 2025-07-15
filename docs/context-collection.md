# Context Collection System Documentation

This document describes the context collection system implemented in `src/mcp_commit_story/context_collection.py` and the type definitions in `src/mcp_commit_story/context_types.py`. These modules provide the infrastructure for gathering and structuring development context for AI-powered journal entry generation.

## Table of Contents

1. [Overview](#overview)
2. [Context Types](#context-types)
3. [Collection Functions](#collection-functions)
4. [Git Context](#git-context)
5. [Chat History](#chat-history)
6. [Terminal Context](#terminal-context)
7. [Performance Optimization](#performance-optimization)
8. [Error Handling](#error-handling)

---

## Overview

The context collection system gathers rich development context from multiple sources:

- **Git Context**: Commit metadata, file changes, diff summaries, and repository state
- **Chat History**: Development conversations and AI interactions
- **Terminal Context**: Command history and execution details
- **Performance Telemetry**: Comprehensive monitoring and optimization

All context collection functions are instrumented with OpenTelemetry traces and follow the ephemeral data principle - context is only held in memory and persisted as part of generated journal entries.

## Context Types

### Core Type Definitions

The `context_types.py` module defines TypedDict structures for type safety and clear API contracts:

#### ChatMessage
```python
class ChatMessage(TypedDict):
    speaker: str      # "Human" or "Agent"
    text: str         # Message content
```

#### ChatHistory
```python
class ChatHistory(TypedDict):
    messages: List[ChatMessage]
```

#### TerminalCommand
```python
class TerminalCommand(TypedDict):
    command: str      # The command executed
    executed_by: str  # "user" or "ai"
```

#### TerminalContext
```python
class TerminalContext(TypedDict):
    commands: List[TerminalCommand]
```

#### GitMetadata
```python
class GitMetadata(TypedDict):
    hash: str         # Commit hash
    author: str       # Author name
    date: str         # ISO timestamp
    message: str      # Commit message
```

#### GitContext
```python
class GitContext(TypedDict):
    metadata: GitMetadata
    diff_summary: str
    changed_files: List[str]
    file_stats: dict
    commit_context: dict
```

#### JournalContext
```python
class JournalContext(TypedDict):
    chat: Optional[ChatHistory]
    terminal: Optional[TerminalContext]
    git: GitContext
```

### Section Types for AI Generation

The module also defines typed structures for AI-generated journal sections:

- `SummarySection`
- `TechnicalSynopsisSection`
- `AccomplishmentsSection`
- `FrustrationsSection`
- `ToneMoodSection`
- `DiscussionNotesSection`
- `TerminalCommandsSection`
- `CommitMetadataSection`

## Collection Functions

### collect_chat_history()

```python
@trace_git_operation("chat_history")
def collect_chat_history(since_commit=None, max_messages_back=150) -> ChatHistory
```

**Purpose**: Analyzes chat history to extract development-relevant conversations.

**AI Integration**: Uses specialized prompts to:
- Search backward from the last journal entry
- Extract technical discussions and debugging sessions
- Capture feature decisions and challenges overcome
- Record emotional context (frustration, breakthroughs, relief)
- Include external research and documentation reviews
- Focus on content explaining how commits came about

**Implementation**: Currently returns empty structure - designed for AI replacement with actual chat analysis.

### collect_ai_terminal_commands()

```python
@trace_git_operation("terminal_commands")
def collect_ai_terminal_commands(since_commit=None, max_messages_back=150) -> TerminalContext
```

**Purpose**: Collects relevant terminal commands from development session.

**AI Integration**: Uses specialized prompts to:
- Extract development workflow commands (git, tests, builds)
- Include both successful and failed attempts
- Capture command sequences that tell a story
- Record important outputs and error messages
- Focus on commands showing problem-solving attempts

**Implementation**: Currently returns empty structure - designed for AI replacement with actual terminal analysis.

### collect_git_context()

```python
@trace_git_operation("git_context")
def collect_git_context(commit_hash=None, repo=None, journal_path=None) -> GitContext
```

**Purpose**: Collects comprehensive git context for a commit.

**Key Features**:
- **Commit Analysis**: Metadata, author, timestamp, message
- **File Changes**: Smart sampling for large commits
- **Diff Summary**: Comprehensive change analysis
- **Performance Optimization**: Handles large commits gracefully
- **Recursion Prevention**: Filters out journal files to prevent loops

**Parameters**:
- `commit_hash`: Target commit (defaults to HEAD)
- `repo`: GitPython repo object (auto-detected if None)
- `journal_path`: Journal directory to exclude from analysis

## Git Context

### Commit Analysis

The `collect_git_context()` function provides detailed commit analysis:

1. **Metadata Collection**: Hash, author, date, message
2. **Diff Summary**: Using `get_commit_diff_summary()`
3. **File Changes**: Smart sampling with performance limits
4. **File Classification**: Source, config, docs, tests categorization
5. **Diff Collection**: Intelligent collection of actual code changes with adaptive size management

### Diff Collection Features

The git context collection includes comprehensive diff content using `get_commit_file_diffs()`:

**Adaptive Size Management**:
- **≤5 files**: 10KB per file (optimized for detailed analysis)
- **6-20 files**: 2.5KB per file (balanced detail vs performance)  
- **>20 files**: 1KB per file, max 50 files (performance-first with sampling)

**Intelligent Filtering**:
- Automatically excludes binary files (images, executables)
- Filters out generated files (`package-lock.json`, build artifacts)
- Focuses on meaningful code changes for journal context

**Error Handling**:
- Individual file errors don't break collection
- Size limit violations are clearly marked with truncation messages
- Critical failures return structured error information

**Integration Example**:
```python
# Diff collection is automatically integrated
git_context = collect_git_context(commit_hash)
file_diffs = git_context['file_diffs']  # Dict[str, str] mapping file paths to diffs

# Special handling for metadata keys
if "__truncated__" in file_diffs:
    # Some diffs were omitted due to size limits
if "__error__" in file_diffs:
    # Error occurred during collection
```

### Performance Optimization

**Large Commit Handling**:
- **File Count Limit**: Detailed analysis limited to avoid performance issues
- **Smart Sampling**: Representative file selection for medium-large commits
- **Performance Thresholds**: Configurable limits via `PERFORMANCE_THRESHOLDS`
- **Truncation Indicators**: Clear markers when analysis is limited

**Example Performance Mitigation**:
```python
if total_file_count > PERFORMANCE_THRESHOLDS["detailed_analysis_file_count_limit"]:
    # Skip detailed analysis for very large commits
    changed_files = all_changed_files[:10]
    diff_summary += "\n[Large commit: {total_file_count} files, analysis truncated]"
```

### Recursion Prevention

The system prevents infinite loops when journal operations trigger new commits:

```python
if journal_path:
    journal_rel = os.path.relpath(journal_path, repo.working_tree_dir)
    changed_files = [f for f in changed_files if not f.startswith(journal_rel)]
```

This ensures journal files are excluded from context analysis.

## Chat History

**Purpose**: Extract complete conversation history from Cursor's SQLite databases to provide rich context for journal entries.

**Current Implementation**: The system uses a **Composer-based chat integration** that directly accesses Cursor's workspace databases with intelligent time-window filtering.

### How It Works

1. **Database Discovery**: Automatically finds Cursor workspace databases across platforms:
   - macOS: `~/Library/Application Support/Cursor/User/workspaceStorage/[workspace-hash]/state.vscdb`
   - Windows: `%APPDATA%\Cursor\User\workspaceStorage\[workspace-hash]\state.vscdb`
   - Linux: `~/.config/Cursor/User/workspaceStorage/[workspace-hash]/state.vscdb`

2. **Time-Window Filtering**: Uses git commit timestamps to create intelligent boundaries:
   - Fetches conversations within a commit-based time window
   - Provides relevant context without overwhelming the system
   - Automatically handles database rotation and workspace switching

3. **Structured Data Extraction**: Extracts complete conversation data including:
   - **Full Message Content**: Complete chat history without memory limitations
   - **Conversation Metadata**: Timestamps, session names, and threading
   - **Context Preservation**: Maintains conversation flow and relationships
   - **File References**: Links to code files discussed in conversations

4. **AI-Powered Context Filtering**: Uses specialized AI processing functions (Pattern 2) to:
   - Identify conversation boundaries relevant to specific commits
   - Filter out unrelated discussions while preserving important context
   - Maintain conversation coherence and narrative flow

### Key Features

- **Complete History Access**: No artificial message limits or memory constraints
- **Cross-Platform Support**: Works consistently across macOS, Windows, and Linux
- **Performance Optimized**: Commit-based time windows provide 50-200x performance improvement
- **Multi-Workspace Aware**: Handles database rotation and multiple projects
- **Production Ready**: Comprehensive error handling and fallback behavior

### Architecture

The chat history collection uses a layered approach:

1. **Database Layer** (`cursor_db/`):
   - Connection management and query execution
   - Cross-platform database discovery
   - SQL query optimization and result processing

2. **Integration Layer** (`composer_integration.py`):
   - Extracts structured conversation data
   - Handles session management and threading
   - Provides clean API for higher-level components

3. **Filtering Layer** (`ai_context_filter.py`):
   - AI-powered boundary detection
   - Context-aware conversation filtering
   - Maintains conversation coherence

4. **Context Management** (`context_collection.py`):
   - Orchestrates the complete context collection pipeline
   - Integrates chat history with other context sources
   - Provides unified context for journal generation

### Benefits

- **Rich Context**: Provides complete conversation history for comprehensive journal entries
- **Intelligent Filtering**: Uses AI to identify relevant conversations without manual curation
- **Reliable Performance**: Optimized queries and caching for consistent speed
- **User Privacy**: Processes data locally without external transmission
- **Seamless Integration**: Works automatically with existing Cursor workflows

### Technical Details

The implementation provides several key technical advantages:

**Database Efficiency**: Direct SQL queries with optimized indexes and time-based filtering provide exceptional performance compared to sequential processing approaches.

**Context Preservation**: The system maintains complete message threading and conversation flow, ensuring that AI-generated journal entries have full context for accurate narrative generation.

**Error Resilience**: Comprehensive error handling ensures the system gracefully handles database locks, missing files, and other edge cases without interrupting the journal workflow.

**Platform Compatibility**: Unified abstraction layer handles platform-specific database locations and file system differences transparently.

This approach enables the creation of rich, contextually-aware journal entries that capture not just what was done, but the complete thought process and problem-solving approach behind the work.

## Terminal Context

### Command Collection Strategy

The `collect_ai_terminal_commands()` function targets development-relevant commands:

**Command Types**:
- Git operations (commit, push, branch, merge)
- Test execution (npm test, pytest, jest)
- Build operations (npm build, make, cargo build)
- File operations during development
- Package management (npm install, pip install)
- Environment setup and debugging

**Narrative Preservation**:
- Commands in chronological order
- Failed attempts with error context
- Command sequences showing problem-solving
- Both successful and unsuccessful workflows

**Content Filtering**:
- Exclude routine navigation (ls, cd)
- Include failed commands with errors
- Focus on commands that tell the development story

## Performance Optimization

### Telemetry Integration

All collection functions are instrumented with comprehensive telemetry:

```python
@trace_git_operation("operation_name", 
                    performance_thresholds={"duration": 1.0},
                    error_categories=["api", "network", "parsing"])
```

**Monitoring Features**:
- **Duration Tracking**: Operation timing with thresholds
- **Error Categorization**: Structured error classification
- **Memory Tracking**: Context size monitoring
- **Circuit Breaker**: Automatic fallback for failing operations

### Smart File Sampling

For large commits, the system uses intelligent file sampling:

```python
sampled_files = smart_file_sampling(all_changed_files)
```

**Sampling Strategy**:
- Representative file selection
- Preserve important file types (source, tests, configs)
- Maintain analysis quality while limiting scope
- Clear indicators when sampling occurs

### Circuit Breaker Pattern

The system includes circuit breaker protection:

```python
_telemetry_circuit_breaker
```

**Protection Features**:
- Automatic fallback for repeated failures
- Graceful degradation of analysis quality
- Preserved core functionality during outages
- Automatic recovery when services restore

## Error Handling

### Exception Types

**Git Operations**:
- `git.InvalidGitRepositoryError`: Invalid or corrupted repository
- `git.BadName`: Invalid commit hash or reference
- `TypeError`: Unexpected git operation results

**File System**:
- `FileNotFoundError`: Missing repository or files
- `PermissionError`: Insufficient filesystem access
- `OSError`: General filesystem errors

### Graceful Degradation

The context collection system follows graceful degradation principles:

1. **Always Return Valid Structure**: Even on errors, return properly typed empty structures
2. **Partial Success**: Collect available context even if some sources fail
3. **Clear Error Indication**: Log errors but don't fail journal generation
4. **Fallback Content**: Provide minimal context rather than complete failure

### Error Recovery

**Validation Strategy**:
```python
if since_commit is None or max_messages_back is None:
    raise ValueError("Required parameters must not be None")
```

**Defensive Programming**:
```python
if diffs is None:
    raise TypeError("Git diff operation returned None - possibly due to repository corruption")
```

## Integration Points

### MCP Server Integration

Context collection functions are called from core journal operations:
- **Git hook operations**: Primary context collection entry point
- Error handling preserves journal operation success
- Telemetry data flows to system monitoring

### AI Generation Pipeline

Collected context feeds into AI generation system:
- Structured data contracts via TypedDict
- Clear separation between collection and generation
- Optimized data formats for AI processing

### Configuration System

Context collection respects configuration settings:
- Performance threshold configuration
- Telemetry enable/disable settings
- Sampling strategy parameters

## See Also

- **[Journal Core](journal-core.md)** - How collected context is used for AI generation
- **[Telemetry](telemetry.md)** - Comprehensive monitoring and tracing
- **[MCP API Specification](mcp-api-specification.md)** - How context flows through MCP operations
- **[Implementation Guide](implementation-guide.md)** - Development patterns and practices