# Implementation Guide

This document provides detailed implementation guidance for developing the mcp-commit-story journal system.

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Project Structure](#project-structure)
3. [Development Methodology](#development-methodology)
4. [Implementation Patterns](#implementation-patterns)
5. [Data Handling](#data-handling)
6. [Git Integration](#git-integration)
7. [Error Handling](#error-handling)
8. [Testing Strategy](#testing-strategy)
9. [Performance and Security](#performance-and-security)
10. [Development Workflow](#development-workflow)
11. [Daily Summary Workflow](#complete-daily-summary-workflow)
12. [Daily Summary Troubleshooting](#daily-summary-troubleshooting-guide)

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.9+
- **MCP Framework**: MCP Python SDK
- **CLI Framework**: Click (for command parsing and user interface)
- **Configuration**: PyYAML (for .mcp-commit-storyrc.yaml files)
- **Git Integration**: GitPython library
- **File I/O**: Standard library (pathlib, datetime)
- **Testing**: pytest for unit/integration tests
- **Observability**: OpenTelemetry for tracing, metrics, and logging

### Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.9"
mcp = "^1.0.0"  # Official MCP Python SDK
click = "^8.0.0"
pyyaml = "^6.0"
gitpython = "^3.1.0"
python-dateutil = "^2.8.0"
opentelemetry-api = "^1.15.0"
opentelemetry-sdk = "^1.15.0"
opentelemetry-exporter-otlp = "^1.15.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-mock = "^3.10.0"
pytest-cov = "^4.0.0"  # Coverage reporting
pytest-watch = "^4.2.0"  # TDD friendly test runner
black = "^23.0.0"
flake8 = "^6.0.0"
mypy = "^1.0.0"
```

---

## Project Structure

```
mcp-commit-story/
├── src/
│   └── mcp_commit_story/
│       ├── __init__.py
│       ├── cli.py        # Click commands
│       ├── server.py     # MCP server implementation
│       ├── journal.py    # Journal entry generation
│       ├── git_utils.py  # Git operations
│       ├── telemetry.py  # OpenTelemetry setup and utilities
│       └── config.py     # Configuration handling
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/                 # Documentation
├── pyproject.toml       # Modern Python packaging
├── README.md
└── .mcp-commit-storyrc.yaml  # Default config
```

### Core Components
- **`cli.py`**: Click commands for setup operations
- **`server.py`**: MCP server implementation with operation handlers
- **`journal.py`**: Journal entry generation and formatting logic
- **`git_utils.py`**: Git operations, intelligent diff collection, hook installation, commit processing
- **`telemetry.py`**: OpenTelemetry setup and utilities
- **`config.py`**: Configuration parsing and validation

---

## Development Methodology

### Test-Driven Development (TDD)
- **Write tests first, then implementation**
- Write failing tests → Implement minimal code → Refactor
- Maintain high test coverage (>90%)
- Test all MCP operations and CLI commands

### TDD Cycle
1. Write a failing test for the desired functionality
2. Run the test to confirm it fails for the right reasons
3. Implement the minimal code to make the test pass
4. Run the test again to confirm it passes
5. Refactor code while keeping tests passing
6. Repeat for the next piece of functionality

---

## Implementation Patterns

### MCP Server Implementation
- Build standard MCP server using MCP Python SDK
- Register tools for each journal operation (new-entry, summarize, etc.)
- Handle async operations for file I/O and git commands
- Return structured responses with success status and file paths
- Instrument key operations with OpenTelemetry for tracing and performance insights

### Code Organization
- Each MCP operation maps to a dedicated handler function
- Separate concerns: git operations, file I/O, text processing
- Use type hints throughout for better IDE support
- Keep functions small and single-purpose

### Dependencies Management
- Minimal external dependencies
- Prefer standard library where possible
- Use well-maintained packages for specialized tasks

---

## Data Handling

### File Organization
- `journal.path` in config sets parent directory containing `daily/` and `summaries/`
- Paths always relative to git repository root
- Missing directories created automatically using on-demand pattern

### On-Demand Directory Creation Pattern

#### Rationale
- Only create journal subdirectories (e.g., daily/, summaries/weekly/) when they are actually needed
- Prevents empty folders, keeps the repo clean, and matches natural usage patterns

#### Implementation
- Use the utility function `ensure_journal_directory(file_path)` before any file write operation
- This function creates all missing parent directories for the given file path
- Does nothing if directories already exist
- Raises PermissionError on failure
- All journal file operations (append, save, etc.) must call this utility before writing

#### Example Usage
```python
from mcp_commit_story.journal import ensure_journal_directory

file_path = Path("journal/daily/2025-05-28-journal.md")
ensure_journal_directory(file_path)
with open(file_path, "a") as f:
    f.write(entry)
```

### Diff Processing
- Examine all files in commit to determine if entry should be created
- When generating file diffs and stats for journal entry content, exclude journal files
- Capture simplified summaries with line counts (e.g., "modified 3 functions in auth.js")
- Binary files noted as "binary file changed"
- Large diffs truncated with note about truncation
- Focus only on code and documentation changes

### Date/Time Handling
- Week boundaries: Monday-Sunday
- Month boundaries: Calendar months (1st to last day)
- All timestamps in local timezone
- ISO format dates in filenames (YYYY-MM-DD)

---

## Git Integration

### Hook Installation
- `mcp-commit-story-setup install-hook` command
- Supports background mode with `--background` flag to prevent blocking commits
- Checks for existing hooks and handles conflicts
- Creates hook that implements recursion prevention logic
- Backs up existing hooks before modification

### Post-Commit Hook Content Generation
The post-commit hook is generated using the `generate_hook_content()` function in `src/mcp_commit_story/git_utils.py`:

- Hook script uses `#!/bin/sh` for portability
- Executes Python worker module for background processing
- All output redirected to `/dev/null` with `|| true` to ensure non-blocking behavior
- Script is intentionally lightweight and non-intrusive
- Never interferes with normal Git operations
- Uses Python worker architecture for enhanced functionality

#### Hook Architecture
The hook uses a Python worker pattern for reliable background processing:
- **Primary hook**: Bash script that triggers Python worker module
- **Python worker**: `git_hook_worker.py` module handles all journal logic
- **Direct generation**: Journal entries created immediately via `journal_workflow` module
- **Summary coordination**: Triggers daily/weekly/monthly summary generation when applicable
- **Error handling**: Graceful degradation with warning logs, never blocks git operations
- **Git timestamp consistency**: Uses git commit timestamps throughout system

#### Example Generated Hook

**Synchronous Mode (Default)**
```sh
#!/bin/sh
# Git hook with direct journal generation and summary coordination
python -m mcp_commit_story.git_hook_worker "$PWD" >/dev/null 2>&1 || true
```

**Background Mode**
```sh
#!/bin/sh
# Get the current commit hash
COMMIT_HASH=$(git rev-parse HEAD)

# Spawn background journal worker (detached from git process)
nohup python -m mcp_commit_story.background_journal_worker \
    --commit-hash "$COMMIT_HASH" \
    --repo-path "$PWD" \
    --timeout 30 \
    >/dev/null 2>&1 &
```

#### Worker Module Features
- **Direct journal generation**: Calls `journal_workflow.handle_journal_entry_creation()` immediately
- **Summary coordination**: Triggers MCP-based summary generation when appropriate
- **Timestamp consistency**: Uses `commit.committed_datetime.isoformat()` for all logging
- **Comprehensive logging**: Structured logging with git commit timestamps in `.git/hooks/mcp-commit-story.log`
- **Error resilience**: Never blocks git operations, logs warnings on failures

### Hook Installation Logic
The function `install_post_commit_hook(repo_path)` in `src/mcp_commit_story/git_utils.py`:

- Installs or replaces the post-commit hook in `.git/hooks`
- Always backs up existing hooks with timestamped filename
- No user prompt or confirmation required (fully automated)
- New hook written using content from `generate_hook_content()`
- Hook set to executable (0o755) for compatibility
- Suitable for CI/CD pipelines and scripting

### Git Hook Workflow

The git hook worker (`git_hook_worker.py`) executes this workflow on every commit:

```
1. Git Hook Trigger
   ↓
2. Python Worker Module (git_hook_worker.py)
   ├─ Direct Journal Generation
   │  ├─ Load git repository and current commit
   │  ├─ Load configuration  
   │  └─ Call journal_workflow.handle_journal_entry_creation()
   │
   └─ Summary Coordination (when applicable)
      ├─ Check if daily summary should be generated
      ├─ Check for weekly/monthly/quarterly triggers
      └─ Trigger MCP-based summary generation
```

#### Direct Journal Generation Flow
```python
# Simplified flow in git_hook_worker.py
def generate_journal_entry_safe(repo_path: str) -> bool:
    repo = git_utils.get_repo(repo_path)
    commit = git_utils.get_current_commit(repo)
    config_obj = config.load_config()
    
    result = journal_workflow.handle_journal_entry_creation(commit, config_obj)
    return result['success']
```

### Daily Summary Trigger System

#### File-Creation-Based Approach
The system uses a stateless, file-creation-based trigger to determine when daily summaries should be generated:

- **Trigger Logic**: When a new journal file is created, check if a summary should be generated for the most recent previous day
- **State-Free**: No state files to maintain or corrupt - relies on file existence checks
- **Gap Handling**: Naturally handles gaps in journal entries (works after days off)
- **Idempotent**: Safe to run multiple times - checks file existence before generating

#### Implementation Functions
Located in `src/mcp_commit_story/daily_summary.py`:

- `extract_date_from_journal_path(file_path)`: Extract YYYY-MM-DD date from journal file path
- `daily_summary_exists(date, summary_dir)`: Check if summary file already exists for a date
- `should_generate_daily_summary(new_file_path, summary_dir)`: Main trigger logic - returns date to summarize or None
- `should_generate_period_summaries(date)`: Determine weekly/monthly/quarterly summary triggers

#### Period Summary Triggers
- **Weekly**: Generate on Mondays for the previous week (Monday-Sunday)
- **Monthly**: Generate on 1st of month for the previous month
- **Quarterly**: Generate on quarter starts (Jan 1, Apr 1, Jul 1, Oct 1) for previous quarter  
- **Yearly**: Generate on January 1st for the previous year

#### Error Handling
- Log warnings and continue on errors (don't break git operations)
- Return `None` for any failure cases
- Handle missing directories, permission errors, and invalid date formats gracefully

### Complete Daily Summary Workflow

#### End-to-End Workflow Process
The daily summary system follows this complete workflow:

1. **Trigger Detection**: Git hook worker checks for daily summary trigger using file-creation-based logic
2. **Direct Generation**: Worker calls consolidated `generate_daily_summary_standalone()` function  
3. **Data Collection**: Function collects all journal entries for the target date
4. **Summary Generation**: AI-powered synthesis creates comprehensive daily summary using real AI integration
5. **File Creation**: Summary saved to `journal/summaries/daily/YYYY-MM-DD-summary.md`
6. **Period Boundaries**: Check for weekly/monthly/quarterly summary triggers
7. **Logging**: All operations logged for troubleshooting and audit

#### Workflow Components Integration
- **Git Hook Worker** (`git_hook_worker.py`): Orchestrates the entire process
- **Daily Summary Logic** (`daily_summary.py`): Implements trigger detection, file management, and consolidated AI generation
- **Configuration** (`config.py`): Journal path and summary settings

#### Automatic vs Manual Triggering
- **Automatic**: Triggered by git commits when journal file creation indicates date change
- **Manual**: Direct MCP tool invocation for specific dates
- **Consistency**: Both methods use identical underlying logic and produce identical results
- **Idempotent**: Safe to run multiple times - duplicate summaries prevented

### Daily Summary Troubleshooting Guide

#### Common Issues and Solutions

**Hook Not Executing**
- **Symptom**: No journal entries or summaries generated after commits
- **Check**: Verify hook exists and is executable: `ls -la .git/hooks/post-commit`
- **Fix**: Reinstall hook: `mcp-commit-story-setup install-hook`
- **Debug**: Check hook log: `cat .git/hooks/mcp-commit-story.log`

**Daily Summary Not Generated**
- **Symptom**: Journal entries exist but no daily summary created
- **Check**: Verify summary directory structure: `journal/summaries/daily/`
- **Causes**: 
  - Same-day commits (no date change detected)
  - Summary already exists for target date
  - Insufficient journal entries for target date
- **Debug**: Review hook log for daily summary trigger decisions

**Permission Errors**
- **Symptom**: Hook fails with permission denied errors
- **Check**: Directory permissions: `ls -la journal/`
- **Fix**: Ensure write permissions: `chmod -R 755 journal/`
- **Note**: Hook designed for graceful degradation - git operations continue

**MCP Server Communication Failures**
- **Symptom**: Hook log shows MCP tool call failures
- **Check**: MCP server running and accessible
- **Debug**: Test manual MCP tool invocation
- **Fallback**: Hook continues with journal entry generation only

**Missing Dependencies**
- **Symptom**: Import errors in hook log
- **Check**: Python environment has all required packages
- **Fix**: Reinstall dependencies: `pip install -e .`
- **Environment**: Ensure hook uses correct Python environment

**Invalid Date Formats**
- **Symptom**: Date extraction failures in hook log  
- **Check**: Journal filenames follow YYYY-MM-DD-journal.md pattern
- **Fix**: Rename files to correct format or recreate entries
- **Prevention**: Use MCP tools for consistent file naming

#### Debug Tools and Commands

**Hook Log Analysis**
```bash
# View recent hook activity
tail -n 50 .git/hooks/mcp-commit-story.log

# Search for specific errors
grep -i "error\|warning" .git/hooks/mcp-commit-story.log

# Monitor hook execution in real-time
tail -f .git/hooks/mcp-commit-story.log
```

**Manual Testing**
```bash
# Test hook worker directly
python -m mcp_commit_story.git_hook_worker "$PWD"

# Test daily summary trigger logic
python -c "
from mcp_commit_story.daily_summary import should_generate_daily_summary
result = should_generate_daily_summary('journal/daily/2025-01-06-journal.md', 'journal/summaries/daily')
print(f'Summary needed for: {result}')
"

# Test MCP tool directly
# (Through MCP client or integrated environment)
```

**File System Verification**
```bash
# Check journal structure
find journal/ -type f -name "*.md" | sort

# Verify summary files
ls -la journal/summaries/daily/

# Check permissions
ls -la journal/ journal/summaries/ journal/summaries/daily/
```

#### Performance Considerations
- **Hook Execution Time**: Designed to complete quickly (<2 seconds typical)
- **Background Processing**: MCP operations run asynchronously
- **Resource Usage**: Minimal impact on git operations
- **Scalability**: Handles repositories with extensive journal history

#### Security and Privacy
- **Local Operations**: All processing happens locally
- **No External Calls**: No network dependencies for core functionality
- **File Permissions**: Respects existing repository security model
- **Error Isolation**: Failures don't expose sensitive information

### Backfill Mechanism
- **Detection**: Check commits since last journal entry in any file
- **Order**: Add missed entries in chronological order
- **Context**: Skip terminal/chat history for backfilled entries
- **Annotation**: Mark entries as backfilled with timestamp

### Commit Processing
- Handle all commit types uniformly (regular, merge, rebase, cherry-pick)
- Process initial commit normally (no previous commit to reference)
- Skip commits that only modify journal files
- For mixed commits (code + journal files), exclude journal files from analysis

---

## Error Handling

### Hard Failures (Fail Fast)
These errors return error status and stop execution:
- Git repository not found
- Journal directory doesn't exist and can't be created
- Invalid MCP connection
- Corrupted git repository

### Soft Failures (Silent Skip)
These errors are skipped silently without user notification:
- Terminal history not accessible (file permissions, format issues)
- Chat history unavailable or API errors  
- AI session command collection fails (unsupported AI tool, API changes)
- Previous commit not found for backfill
- Terminal commands unparseable
- AI assistant doesn't support command history
- Network timeouts when fetching optional data

### Graceful Degradation Philosophy
- **Always generate a journal entry** regardless of available data sources
- **Include what works**, silently omit what doesn't
- **No error messages** clutter the journal output
- **User never sees broken features** - they just don't get that section
- **Future-proof**: adapts when AI tools improve their APIs

### Debug Mode Implementation
```python
import logging

# Configure debug logging
debug_logger = logging.getLogger('mcp_commit_story.debug')

def collect_optional_data(debug=False):
    try:
        data = fetch_optional_data()
        return data
    except Exception as e:
        if debug:
            debug_logger.error(f"Failed to collect optional data: {e}")
        return None
```

### Error Messages
- Brief and actionable for hard failures only
- Include suggestions for resolution where possible
- Never expose internal implementation details
- No error messages for soft failures in normal mode
- Debug mode provides detailed error information

---

## Testing Strategy

### Unit Tests
- Configuration parsing and validation
- Journal entry generation from mock data
- MCP operation handlers
- Git utility functions
- CLI command parsing
- Date/time handling
- Telemetry initialization and configuration

### Integration Tests
- End-to-end git hook workflow
- File creation and appending
- Backfill detection and processing
- Summary generation across date ranges
- Blog post conversion
- Tracing of operations through the entire flow

### Test Fixtures
```python
@pytest.fixture
def mock_git_repo():
    # Create temporary git repo with test commits
    pass

@pytest.fixture
def sample_journal_entries():
    # Load sample journal files
    pass

@pytest.fixture
def mock_terminal_history():
    # Provide test terminal command history
    pass

@pytest.fixture
def mock_telemetry_exporter():
    # Provide a test exporter that captures telemetry events
    pass
```

### Hook Execution Testing
Integration tests for hook execution directly write a debug post-commit hook to `.git/hooks/post-commit` and verify that it is executed after a commit, when run directly, and with `sh post-commit`. This ensures the hook is actually executed in all scenarios, not just installed.

---

## Performance and Security

### Performance Considerations
- Lazy loading for large files
- Stream processing for git logs
- Reasonable timeouts for external commands
- Efficient text processing for large diffs

### Security
- Validate all file paths to prevent directory traversal
- Sanitize git data before processing
- No shell injection vulnerabilities in subprocess calls

---

## Development Workflow

### Initial Setup
1. Set up project structure with pyproject.toml
2. **Write failing tests first** (TDD approach)
3. Implement basic MCP server skeleton
4. Add OpenTelemetry initialization

### Feature Development
5. Add git integration and journal generation
7. Create CLI interface with Click
8. Add configuration system  
9. Implement decision detection in chat history
10. Add reflection capabilities
11. Implement summarization and blogification
12. Add telemetry to key operations
13. Add comprehensive tests (maintaining >90% coverage)
14. Package for distribution

### Initialization Workflow
1. User runs `mcp-commit-story-setup journal-init` in their repository
2. System checks if already initialized (look for `.mcp-commit-storyrc.yaml`)
3. Creates journal directory structure using on-demand pattern
4. Generates default configuration file
5. Prompts to install git post-commit hook
6. Displays next steps and usage instructions

### Configuration Management

#### Configuration Precedence
1. Local config (`.mcp-commit-storyrc.yaml` in repo root)
2. Global config (`~/.mcp-commit-storyrc.yaml`)
3. Built-in defaults

#### Configuration Validation
- Missing/invalid fields use defaults and continue with warnings
- Malformed YAML logs error but continues with defaults
- Invalid sections are ignored with warnings

### Chat History Processing
- Use simple keyword matching for decision-related discussions
- Include context around matched keywords (e.g., previous/next sentences)
- No complex NLP or structured parsing required
- Fall back gracefully if chat history is unavailable

This implementation guide provides the technical foundation for building a robust, well-tested, and maintainable journal system that integrates seamlessly with development workflows. 