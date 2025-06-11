# Signal Format Documentation

## Overview

The MCP Commit Story project uses a file-based signaling mechanism to enable asynchronous communication between git hooks and AI clients. This system allows git hooks to create signal files that AI clients can discover and process for automated journal generation.

## Signal Directory Structure

Signal files are stored in the `.mcp-commit-story/signals/` directory within the git repository:

```
.mcp-commit-story/
└── signals/
    ├── 20250611_115234_659123_journal_new_entry_abc123de.json
    ├── 20250611_115235_127456_generate_daily_summary_def456gh.json
    └── 20250611_115236_891234_generate_weekly_summary_hij789kl.json
```

## Signal File Format

### Filename Convention

Signal files use a timestamp-based naming convention for chronological ordering and uniqueness:

```
{timestamp}_{tool_name}_{hash_prefix}.json
```

- **timestamp**: UTC timestamp in format `YYYYMMDD_HHMMSS_ffffff` (microsecond precision)
- **tool_name**: Name of the MCP tool to execute (e.g., "journal_new_entry")
- **hash_prefix**: First 8 characters of the git commit hash
- **collision handling**: If files collide, a 4-digit counter suffix is added (`_0001`, `_0002`, etc.)

**Example**: `20250611_115234_659123_journal_new_entry_abc123de.json`

### JSON Structure

Each signal file contains a JSON object with the following required fields:

```json
{
  "tool": "journal_new_entry",
  "params": {
    "date": "2025-06-11",
    "commit_hash": "abc123de",
    "custom_param": "value"
  },
  "metadata": {
    "hash": "abc123def456",
    "author": "John Doe",
    "email": "john@example.com", 
    "date": "2025-06-11T07:36:12-04:00",
    "message": "Implement signal file management",
    "files_changed": ["src/signal_management.py", "tests/test_signals.py"],
    "insertions": 355,
    "deletions": 12,
    "files_modified": 2
  },
  "created_at": "2025-06-11T11:52:34.659123Z",
  "signal_id": "20250611_115234_659123_journal_new_entry_abc123de"
}
```

#### Required Fields

- **tool** (string): Name of the MCP tool to execute
- **params** (object): Parameters to pass to the MCP tool
- **metadata** (object): Git commit metadata with standard scope
- **created_at** (string): ISO 8601 timestamp when signal was created
- **signal_id** (string): Unique identifier matching the filename (without .json)

#### Metadata Scope

The metadata object includes standard commit context information:

- **hash**: Full git commit hash
- **author**: Commit author name
- **email**: Commit author email
- **date**: Commit date in ISO 8601 format
- **message**: Commit message
- **files_changed**: Array of modified file paths
- **insertions**: Number of lines added
- **deletions**: Number of lines removed  
- **files_modified**: Number of files changed

Additional fields are allowed and will be preserved.

## Signal Management API

### Core Functions

```python
from mcp_commit_story.signal_management import (
    ensure_signal_directory,
    create_signal_file,
    validate_signal_format
)

# Create signal directory
signal_dir = ensure_signal_directory("/path/to/repo")

# Create signal file
file_path = create_signal_file(
    signal_directory=signal_dir,
    tool_name="journal_new_entry",
    parameters={"date": "2025-06-11"},
    commit_metadata=commit_info
)

# Validate signal format
is_valid = validate_signal_format(signal_data)
```

### Generic Tool Signal Creation

The system supports creation of signals for any MCP tool through the generic `create_tool_signal()` function in the git hook worker:

```python
from mcp_commit_story.git_hook_worker import create_tool_signal

# Extract commit metadata
commit_metadata = extract_commit_metadata(repo_path)

# Create signal for any MCP tool
signal_path = create_tool_signal(
    tool_name="generate_daily_summary",  # Any MCP tool name
    parameters={"date": "2025-06-11"},   # Tool-specific parameters
    commit_metadata=commit_metadata,     # Standard git context
    repo_path="/path/to/repo"           # Repository path
)
```

**Supported Tool Types:**
- `journal_new_entry` - Create new journal entries
- `generate_daily_summary` - Generate daily summaries
- `generate_weekly_summary` - Generate weekly summaries  
- `generate_monthly_summary` - Generate monthly summaries
- Any other MCP tool implemented in the server

**Benefits of Generic Design:**
- Single implementation supports all MCP tools
- Consistent signal format across tool types
- Comprehensive telemetry for all signal creation
- Reduced code duplication and maintenance overhead

### Utility Functions

```python
from mcp_commit_story.signal_management import (
    get_signal_directory_path,
    is_signal_directory_ready,
    count_signal_files,
    get_latest_signal_file,
    read_signal_file
)

# Get expected signal directory path
signal_path = get_signal_directory_path("/path/to/repo")

# Check if directory exists and is writable
is_ready = is_signal_directory_ready("/path/to/repo")

# Count signal files
file_count = count_signal_files(signal_dir)

# Get most recent signal file
latest_file = get_latest_signal_file(signal_dir)

# Read and parse signal file
signal_data = read_signal_file("/path/to/signal.json")
```

## Error Handling

The signal management system implements graceful degradation to ensure git operations are never blocked:

### Exception Types

- **SignalDirectoryError**: Directory creation or access failures
- **SignalFileError**: File creation or writing failures  
- **SignalValidationError**: JSON format or structure validation failures

### Graceful Degradation

All exceptions include a `graceful_degradation` flag:

```python
try:
    create_signal_file(...)
except SignalFileError as e:
    if e.graceful_degradation:
        # Log error but continue git operation
        logger.warning(f"Signal creation failed: {e}")
    else:
        # Critical error - may need to abort
        raise
```

## Thread Safety

Signal creation is thread-safe for concurrent git hook executions:

- Uses `threading.Lock()` for atomic file creation
- Microsecond timestamps prevent filename collisions
- Collision detection with counter suffixes as backup

## Integration with MCP Tools

### Tool Discovery

AI clients can discover signals by:

1. Monitoring the signals directory for new files
2. Parsing signal files in chronological order (filename sorting)
3. Executing the specified MCP tool with provided parameters
4. Using commit metadata for enhanced context

### Processing Workflow

```python
# Example AI client processing
signal_files = sorted(glob.glob(f"{signal_dir}/*.json"))
for signal_file in signal_files:
    signal_data = read_signal_file(signal_file)
    
    # Execute MCP tool
    mcp_client.call_tool(
        name=signal_data["tool"],
        arguments=signal_data["params"]
    )
    
    # Process or archive signal file
    os.remove(signal_file)  # or move to processed/
```

## Best Practices

### For Git Hooks

1. Always use `ensure_signal_directory()` before creating signals
2. Handle all exceptions gracefully to avoid blocking commits
3. Include relevant commit metadata in the signal
4. Use descriptive tool names and parameters

### For AI Clients

1. Process signals in chronological order (filename sorting)
2. Validate signal format before processing
3. Handle malformed or incomplete signals gracefully
4. Clean up or archive processed signal files
5. Monitor for new signals using file system events

### For MCP Tool Developers

1. Design tools to accept commit metadata for enhanced context
2. Use structured parameters that serialize well to JSON
3. Handle missing or invalid parameters gracefully
4. Document expected parameter schemas

## Performance Considerations

- Signal files are lightweight JSON documents (typically < 10KB)
- Directory scanning performance scales linearly with signal count
- Microsecond timestamps provide 1,000,000 unique files per second
- Thread locks ensure safe concurrent access without performance penalties

## Security Considerations

- Signal directory is within `.mcp-commit-story/` (typically git-ignored)
- Signal files contain commit metadata but no sensitive authentication data
- File permissions inherit from parent directory
- AI clients should validate all signal content before processing

## Troubleshooting

### Common Issues

**Permission Errors**: Ensure git user has write access to repository directory

**Signal Files Not Created**: Check `ensure_signal_directory()` return value and disk space

**Malformed JSON**: Use `validate_signal_format()` to verify signal structure

**Filename Collisions**: System handles automatically with counter suffixes

**Directory Not Found**: Run `ensure_signal_directory()` to create structure

### Debugging

Enable debug logging to trace signal operations:

```python
import logging
logging.getLogger('mcp_commit_story.signal_management').setLevel(logging.DEBUG)
```

## Examples

### Basic Journal Entry Signal

```json
{
  "tool": "journal_new_entry",
  "params": {
    "date": "2025-06-11",
    "commit_hash": "abc123de"
  },
  "metadata": {
    "hash": "abc123def456",
    "author": "Developer",
    "email": "dev@example.com",
    "date": "2025-06-11T15:30:00Z",
    "message": "Fix critical bug in user authentication",
    "files_changed": ["src/auth.py", "tests/test_auth.py"],
    "insertions": 25,
    "deletions": 8,
    "files_modified": 2
  },
  "created_at": "2025-06-11T15:30:15.123456Z",
  "signal_id": "20250611_153015_123456_journal_new_entry_abc123de"
}
```

### Daily Summary Signal

```json
{
  "tool": "generate_daily_summary", 
  "params": {
    "date": "2025-06-11",
    "include_stats": true
  },
  "metadata": {
    "hash": "def456ghi789",
    "author": "Team Lead",
    "email": "lead@example.com", 
    "date": "2025-06-11T18:00:00Z",
    "message": "End of day commit - summary trigger",
    "files_changed": [],
    "insertions": 0,
    "deletions": 0,
    "files_modified": 0
  },
  "created_at": "2025-06-11T18:00:05.987654Z",
  "signal_id": "20250611_180005_987654_generate_daily_summary_def456gh"
}
``` 