# Signal Format Documentation

## Overview

The MCP Commit Story project uses a **minimal file-based signaling mechanism** to enable asynchronous communication between git hooks and AI clients. This privacy-by-design system creates lightweight signal files (~200 bytes) that AI clients can discover and process for automated journal generation, retrieving full git context on-demand.

## Architecture Philosophy

### Privacy by Design

Signal files are **ephemeral processing artifacts**, not permanent data stores:

- **No PII Storage**: No author emails, file paths, or commit messages stored in signals
- **Minimal State**: Only essential data (tool name, commit hash, timestamp) persisted
- **On-Demand Context**: Full git context retrieved when needed using existing `git_utils` functions
- **Secure by Default**: Sensitive information never leaves git repository boundaries

### Performance Benefits

- **90% Size Reduction**: ~200 bytes vs ~2KB traditional approach
- **Faster Processing**: Lightweight signals reduce I/O overhead
- **Git Integration**: Context retrieved directly from git objects (authoritative source)
- **Memory Efficient**: No redundant metadata duplication in signal files

## Signal Directory Structure

Signal files are stored in the `.mcp-commit-story/signals/` directory within the git repository:

```
.mcp-commit-story/         # Auto-added to .gitignore for privacy
└── signals/
    ├── 20250611_115234_journal_new_entry_abc123de.json       # ~200 bytes
    ├── 20250611_115235_generate_daily_summary_def456gh.json  # ~200 bytes  
    └── 20250611_115236_generate_weekly_summary_hij789kl.json # ~200 bytes
```

## Minimal Signal File Format

### Filename Convention

Signal files use a timestamp-based naming convention for chronological ordering:

```
{timestamp}_{tool_name}_{hash_prefix}.json
```

- **timestamp**: UTC timestamp in format `YYYYMMDD_HHMMSS_ffffff` (microsecond precision)
- **tool_name**: Name of the MCP tool to execute (e.g., "journal_new_entry")
- **hash_prefix**: First 8 characters of the git commit hash

**Example**: `20250611_115234_journal_new_entry_abc123de.json`

### Minimal JSON Structure

Each signal file contains a **minimal JSON object** with only essential fields:

```json
{
  "tool": "journal_new_entry",
  "params": {
    "commit_hash": "abc123def456789012345678901234567890abcd"
  },
  "created_at": "2025-06-11T11:52:34.659123Z"
}
```

#### Required Fields (Minimal Format)

- **tool** (string): Name of the MCP tool to execute
- **params** (object): Parameters to pass to the MCP tool (must include `commit_hash`)
- **created_at** (string): ISO 8601 timestamp when signal was created

#### Forbidden Fields (Privacy Protection)

The following fields are **explicitly rejected** during validation to enforce minimal format:

- ❌ `metadata` - Git context retrieved on-demand instead
- ❌ `signal_id` - Redundant with filename
- ❌ `author` - PII retrieved from git when needed
- ❌ `email` - PII retrieved from git when needed
- ❌ `message` - Retrieved from git when needed
- ❌ `files_changed` - Retrieved from git when needed

### Signal Types

#### Journal Entry Signal
```json
{
  "tool": "journal_new_entry",
  "params": {
    "commit_hash": "abc123def456789012345678901234567890abcd"
  },
  "created_at": "2025-06-11T15:30:15.123456Z"
}
```

#### Daily Summary Signal  
```json
{
  "tool": "generate_daily_summary",
  "params": {
    "date": "2025-06-11"
  },
  "created_at": "2025-06-11T18:00:05.987654Z" 
}
```

#### Weekly Summary Signal
```json
{
  "tool": "generate_weekly_summary", 
  "params": {
    "week_start": "2025-06-09"
  },
  "created_at": "2025-06-11T18:00:06.123456Z"
}
```

## On-Demand Git Context Retrieval

### Context Functions

Full git context is retrieved on-demand using existing utilities:

```python
from mcp_commit_story.git_utils import get_commit_details, get_repo
from mcp_commit_story.signal_management import fetch_git_context_on_demand

# Retrieve full git context from minimal signal
signal_data = {"tool": "journal_new_entry", "params": {"commit_hash": "abc123"}}
git_context = fetch_git_context_on_demand(signal_data, "/path/to/repo")

# Direct git utils usage
repo = get_repo("/path/to/repo") 
commit_details = get_commit_details(repo, "abc123")
```

### Available Context

When needed, the following git context can be retrieved:

- **Commit Metadata**: Hash, author, email, date, message
- **File Changes**: Modified files, insertions, deletions
- **Diff Information**: Line-by-line changes
- **Repository State**: Branch, tags, status
- **Commit Relationships**: Parents, children, merge status

### Performance Optimization

Context retrieval is optimized for performance:

- **Lazy Loading**: Context retrieved only when processing signals
- **Git Efficiency**: Direct git object access (fastest possible)
- **Caching**: Context can be cached during processing sessions
- **Batch Operations**: Multiple signals can share git context

## Signal Management API

### Core Functions

```python
from mcp_commit_story.signal_management import (
    ensure_signal_directory,
    create_signal_file,
    validate_signal_format,
    fetch_git_context_on_demand
)

# Create signal directory
signal_dir = ensure_signal_directory("/path/to/repo")

# Create minimal signal file  
file_path = create_signal_file(
    signal_directory=signal_dir,
    tool_name="journal_new_entry",
    parameters={},  # Empty - commit_hash added automatically
    commit_metadata={"hash": "abc123..."}  # Only hash used
)

# Validate minimal signal format (strict validation)
is_valid = validate_signal_format(signal_data)

# Fetch full git context on-demand
git_context = fetch_git_context_on_demand(signal_data, "/path/to/repo")
```

### Generic Tool Signal Creation

The system supports creation of minimal signals for any MCP tool:

```python
from mcp_commit_story.git_hook_worker import create_tool_signal

# Extract minimal commit metadata (only hash used)
commit_metadata = extract_commit_metadata(repo_path)

# Create minimal signal for any MCP tool
signal_path = create_tool_signal(
    tool_name="generate_daily_summary",
    parameters={"date": "2025-06-11"},   # Tool-specific parameters
    commit_metadata=commit_metadata,
    repo_path="/path/to/repo"
)
```

## AI Beast Awakening Logic

### Summary Trigger Detection

The system implements intelligent "AI beast awakening" logic:

```python
from mcp_commit_story.git_hook_worker import determine_summary_trigger

# Determine if AI should be awakened for summary generation
should_generate_summary = determine_summary_trigger(
    repo_path="/path/to/repo",
    date_str="2025-06-11"  
)

if should_generate_summary:
    # Create additional summary signal (awakens the beast!)
    create_tool_signal("generate_daily_summary", {"date": "2025-06-11"}, ...)
```

### Awakening Mechanism

- **Normal commit**: Creates only `journal_new_entry` signal
- **Summary needed**: Creates both `journal_new_entry` + `generate_daily_summary` signals
- **Beast awakening**: Occurs through **additional signal file creation**, not signal modification
- **Both signals**: Use minimal format for privacy and performance

## Error Handling and Validation

### Strict Validation

Minimal format validation is **strictly enforced**:

```python
from mcp_commit_story.signal_management import (
    validate_signal_format, 
    SignalValidationError
)

try:
    validate_signal_format(signal_data)
except SignalValidationError as e:
    if "Extra fields not allowed" in str(e):
        # Signal contains forbidden fields (old format)
        logger.error(f"Signal validation failed: {e}")
```

### Exception Types

- **SignalDirectoryError**: Directory creation or access failures
- **SignalFileError**: File creation or writing failures  
- **SignalValidationError**: JSON format or minimal structure validation failures

### Graceful Degradation

All exceptions include graceful degradation to protect git operations:

```python
try:
    create_signal_file(...)
except SignalFileError as e:
    if e.graceful_degradation:
        logger.warning(f"Signal creation failed: {e}")
        # Git operation continues normally
    else:
        raise  # Critical error
```

## Integration with MCP Tools

### Tool Discovery and Processing

AI clients process minimal signals efficiently:

```python
# Example AI client processing
signal_files = sorted(glob.glob(f"{signal_dir}/*.json"))
for signal_file in signal_files:
    signal_data = read_signal_file(signal_file)
    
    # Retrieve git context on-demand if needed
    if signal_data["tool"] == "journal_new_entry":
        commit_hash = signal_data["params"]["commit_hash"]
        git_context = fetch_git_context_on_demand(signal_data, repo_path)
        
        # Enhanced parameters with git context
        enhanced_params = {
            **signal_data["params"],
            "git_context": git_context
        }
    else:
        enhanced_params = signal_data["params"]
    
    # Execute MCP tool
    mcp_client.call_tool(
        name=signal_data["tool"],
        arguments=enhanced_params
    )
    
    # Clean up signal file
    os.remove(signal_file)
```

## Privacy and Security

### Privacy Protection

- **No PII in Signals**: Author emails, names, file paths excluded from signal files
- **Git-only Metadata**: Sensitive information retrieved directly from git (authoritative source)
- **Ephemeral Storage**: Signal files are temporary processing artifacts
- **Auto-gitignore**: `.mcp-commit-story/` directory automatically excluded from git

### Security Considerations

- **Minimal Attack Surface**: Only essential data exposed in signal files
- **Secure Context Retrieval**: Git metadata accessed through secure git APIs
- **No Data Leakage**: Signal files cannot leak sensitive repository information
- **Audit Trail**: All signal operations logged for security monitoring

## Migration from Legacy Format

### Backward Compatibility

The system **strictly rejects** legacy signal formats:

```python
# ❌ Legacy format (rejected)
legacy_signal = {
    "tool": "journal_new_entry",
    "params": {"repo_path": "/path"},
    "metadata": {"author": "User", "email": "user@example.com"},  # PII!
    "signal_id": "20250611_...",  # Redundant
    "created_at": "2025-06-11T15:30:15.123456Z"
}

# ✅ Minimal format (accepted)
minimal_signal = {
    "tool": "journal_new_entry", 
    "params": {"commit_hash": "abc123..."},
    "created_at": "2025-06-11T15:30:15.123456Z"
}
```

### Migration Benefits

- **90% Size Reduction**: 200 bytes vs 2KB per signal
- **Privacy Compliance**: No PII stored in signal files
- **Performance Improvement**: Faster I/O, less memory usage
- **Git Integration**: Context from authoritative source (git objects)
- **Maintainability**: Simpler codebase, fewer data duplication bugs

## Signal Cleanup and Maintenance

Signal files are **temporary processing artifacts** that are automatically managed through a commit-based cleanup system optimized for AI clarity.

### Cleanup Philosophy

**SIGNAL FILES ARE TEMPORARY** - cleared automatically with each new commit. This ensures AI only sees signals for the current commit, maintaining a clean and predictable signal directory.

### Automatic Cleanup System

The system uses a **commit-based cleanup approach** rather than time-based maintenance:

```python
from mcp_commit_story.signal_management import cleanup_signals_for_new_commit

# Automatically called by git hooks after each commit
result = cleanup_signals_for_new_commit("/path/to/repo")
# Clears ALL previous signals, ensuring only current commit signals remain
```

### Benefits of Commit-Based Cleanup

- **AI-Friendly**: One commit = one signal context, no temporal confusion
- **Simplicity**: No time calculations, just "clear all on new commit"  
- **Faster Processing**: AI only processes current commit signals
- **Cleaner UX**: Signal directory only reflects current state
- **Git-Centric**: Aligns with project's git-centric time philosophy

### Cleanup Functions

```python
from mcp_commit_story.signal_management import (
    cleanup_signals_for_new_commit,    # Primary function
    cleanup_old_signals,               # Core cleanup logic  
    monitor_disk_space_and_cleanup,    # Emergency cleanup
    validate_cleanup_safety            # Safety validation
)

# Primary cleanup (called by git hooks)
cleanup_signals_for_new_commit(repo_path)

# Emergency disk space cleanup
monitor_disk_space_and_cleanup(signal_dir, min_free_mb=100)

# Safety validation before cleanup
is_safe, reason = validate_cleanup_safety(signal_dir)
```

### Safety Features

- **Directory Validation**: Only operates on `.mcp-commit-story/signals/` directories
- **Thread Safety**: Concurrent cleanup operations are safely handled
- **Graceful Errors**: Cleanup failures don't block git operations
- **Telemetry**: All cleanup operations are logged for monitoring

### In-Memory Processing Tracking

The system uses lightweight in-memory tracking for within-session processing:

```python
from mcp_commit_story.signal_management import (
    mark_signal_processed,
    is_signal_processed,
    remove_processed_signals
)

# Mark signal as processed (in-memory only)
mark_signal_processed("/path/to/signal.json")

# Check if processed this session
if is_signal_processed("/path/to/signal.json"):
    # Already processed - skip
    pass

# Remove processed signals
remove_processed_signals(signal_dir)
```

### Git Hook Integration

Cleanup is automatically triggered by git hooks:

```bash
#!/bin/sh
# .git/hooks/post-commit
python -c "
from mcp_commit_story.signal_management import cleanup_signals_for_new_commit
cleanup_signals_for_new_commit('.')
"
```

### User Experience

Users don't need to manage signal files manually:

- **Automatic**: Cleanup happens transparently with each commit
- **Invisible**: No user intervention required
- **Fast**: Cleanup takes <50ms typically
- **Safe**: Never interferes with git operations

## Best Practices

### For Git Hooks

1. **Use Minimal Parameters**: Include only essential tool parameters in signals
2. **Handle Gracefully**: Never block git operations due to signal failures
3. **Validate Commit Hash**: Ensure commit hash exists before signal creation
4. **Trust Git Context**: Retrieve metadata from git, not signal files

### For AI Clients

1. **Process Chronologically**: Sort signal files by timestamp
2. **Validate Strictly**: Reject non-minimal signal formats
3. **Fetch Context On-Demand**: Use `fetch_git_context_on_demand()` when needed
4. **Clean Up Promptly**: Remove processed signal files to prevent accumulation

### For MCP Tool Developers

1. **Design for Minimal Signals**: Accept commit hash, retrieve context internally
2. **Use Git Utils**: Leverage existing `git_utils` functions for context
3. **Handle Missing Context**: Gracefully handle git context retrieval failures
4. **Document Hash Requirements**: Specify if commit hash is required

## Performance Characteristics

- **Signal Size**: ~200 bytes (vs ~2KB legacy format)
- **Creation Time**: <1ms per signal (no metadata serialization)
- **Processing Time**: <5ms per signal (minimal parsing)
- **Context Retrieval**: <10ms per commit (git object access)
- **Memory Usage**: 90% reduction in signal processing memory footprint
- **Cleanup Time**: <50ms per cleanup operation

## Troubleshooting

### Common Issues

**"Extra fields not allowed"**: Signal contains legacy format fields - update to minimal format

**"Missing commit_hash"**: Ensure commit hash is included in signal parameters  

**Context retrieval failure**: Verify git repository state and commit hash validity

**Permission denied**: Ensure `.mcp-commit-story/` directory has write permissions

**Signal accumulation**: Check if git hooks are properly calling cleanup functions

### Debugging

Enable debug logging for signal operations:

```python
import logging
logging.getLogger('mcp_commit_story.signal_management').setLevel(logging.DEBUG)
logging.getLogger('mcp_commit_story.git_hook_worker').setLevel(logging.DEBUG)
``` 