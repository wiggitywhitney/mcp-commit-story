# Product Requirements Document (PRD)

## Project Title
Engineering Journal MCP Server

## Overview
A Model Context Protocol (MCP) server designed to capture and generate engineering journal entries within a code repository. The journal records commits, technical progress, decision-making context, and emotional tone, with the goal of producing content that can be analyzed for patterns and reused for storytelling (e.g., blog posts, conference talks).

## Goals
- Record accurate, structured engineering activity and emotional context
- Enable narrative storytelling across daily, weekly, and monthly timelines
- Identify patterns and trends in development work over time
- Keep entries truthful (anti-hallucination), useful, and minimally intrusive
- Integrate seamlessly with Git workflows and existing dev tools

## Technology Stack
- Python 3.9+
- Anthropic MCP Python SDK
- Click (CLI)
- PyYAML (config)
- GitPython
- Standard library (pathlib, datetime)
- pytest for testing
- OpenTelemetry for tracing, metrics, and logging

## MCP Server Configuration and Integration

The MCP server must be launchable as a standalone process and expose the required journal operations (e.g., `journal/new-entry`, `journal/summarize`, etc.) as specified in this document. The server should be discoverable by compatible clients (such as AI-powered editors, agents, or other tools) via a standard configuration mechanism.

- **Server Launch:**
  - The method for launching the MCP server is not prescribed by this specification. It may be started via a CLI command, Python entry point, or any other mechanism appropriate to the environment.
  - The server must remain running and accessible to clients for the duration of its use.

- **Client/Editor Integration:**
  - Clients (such as editors or agents) should be able to connect to the MCP server using a configuration block similar to the following:

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
  - The actual command, arguments, and environment variables will depend on the deployment and are not specified here.
  - Environment variables such as API keys may be required if the underlying MCP SDK or AI provider requires them, but are not strictly necessary for local operation unless needed by dependencies.

- **Separation of Concerns:**
  - The MCP server configuration (how it is launched and discovered) is separate from the journal system's own configuration, which is managed via `.mcp-journalrc.yaml` as described elsewhere in this specification.

## Key Features
- MCP server with tools for journal operations (new-entry, summarize, blogify, etc.)
- CLI interface for all operations
- Journal entries per Git commit, written to daily Markdown files
- Chat and terminal history collection for context
- Configurable via .mcp-journalrc.yaml (local and global precedence)
- Error handling: fail fast on hard errors, skip with notes on soft errors
- Git integration: post-commit hook, backfill, commit processing
- Testing: TDD, >90% coverage, unit/integration/fixtures
- Telemetry: OpenTelemetry instrumentation for observability

## Implementation Guidelines
- Test-driven development
- High test coverage
- Modular code: separate CLI, server, journal, git utils, config, telemetry
- Use type hints
- Small, single-purpose functions
- Minimal external dependencies
- Secure file and path handling
- Instrumented operations with appropriate traces for monitoring

## Deliverables
- Working MCP server with all journal operations
- CLI tool for all features
- Journal directory structure with daily and summary files
- Configuration system
- Git integration (hook, backfill)
- Comprehensive tests
- Documentation (README, usage, config)
- Telemetry integration for performance monitoring

## Out of Scope
- Web interface
- Scheduled background agents
- Plugin system
- Project management tool integration

## Success Criteria
- Zero friction for normal dev workflow
- Valuable output for retrospectives
- Easy to customize and extend
- Reliable operation across different environments
- Observable performance and behavior
- Minimal overhead from telemetry collection

---

# Full Engineering Specification

## Recursion Prevention (Anti-Recursion)
- If a commit only modifies journal files, skip journal entry generation entirely.
- If a commit modifies both code and journal files, generate an entry, but exclude journal files from the diff/stat analysis.
- This logic is always-on and not configurable.

## Manual Reflection Prioritization
- Manual reflections (user-added) are always prioritized in all summaries (daily, weekly, monthly, yearly).
- Summaries have a dedicated "Manual Reflections" section at the top, visually distinct from inferred content.
- If no manual reflections exist, the section is omitted gracefully.

## Daily Summary Generation
- CLI and MCP tool support a `--day` or `--date` option for generating a summary for a specific day.
- Daily summaries are stored in `journal/summaries/daily/`.
- Auto-generation of daily summaries is possible if enabled in the config (`auto_summarize`).

## Error Handling Philosophy
- Hard failures (e.g., missing repo) return actionable error messages and stop execution.
- Soft failures (e.g., missing terminal/chat history) are omitted silently unless `--debug` is set.
- Debug mode surfaces all soft failures to stderr, but never clutters journal output.

## Pattern/Trend Analysis
- The system is designed to help identify patterns and trends in development work over time, not just record events.

## Telemetry Integration
- OpenTelemetry used to instrument key operations for tracing and performance insights
- Each MCP operation includes appropriate traces for monitoring
- Telemetry can be configured or disabled via configuration
- Minimal overhead to maintain system performance
- Useful for debugging and performance optimization

## Configuration Example
```yaml
journal:
  path: journal/
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
  section_order:
    - summary
    - accomplishments
    - frustrations
    - tone
    - commit_details
    - reflections
  auto_summarize:
    daily: true
    weekly: true
    monthly: true
    yearly: true
```

---

# Engineering Journal MCP Server — Complete Developer Specification

## Overview
This document specifies a Model Context Protocol (MCP) server designed to capture and generate engineering journal entries within a code repository. The journal captures technical progress, decision-making context, and emotional tone, with the goal of producing content that can later be reused for storytelling (e.g., blog posts, conference talks).

## Goals
- Record accurate, structured engineering activity and emotional context
- Enable narrative storytelling across daily, weekly, and monthly timelines
- Keep entries truthful (anti-hallucination), useful, and minimally intrusive
- Integrate seamlessly with Git workflows and existing dev tools

---

## Technology Stack

### Core Technologies
- **Language**: Python 3.9+
- **MCP Framework**: Official Anthropic MCP Python SDK
- **CLI Framework**: Click (for command parsing and user interface)
- **Configuration**: PyYAML (for .mcp-journalrc.yaml files)
- **Git Integration**: GitPython library
- **File I/O**: Standard library (pathlib, datetime)
- **Testing**: pytest for unit/integration tests
- **Observability**: OpenTelemetry for tracing, metrics, and logging

### Project Structure
```
mcp-journal/
├── src/
│   └── mcp_journal/
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
├── pyproject.toml       # Modern Python packaging
├── README.md
└── .mcp-journalrc.yaml  # Default config
```

### Development Methodology
- **Test-Driven Development (TDD)** - Write tests first, then implementation
- Write failing tests → Implement minimal code → Refactor
- Maintain high test coverage (>90%)
- Test all MCP operations and CLI commands

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

## Implementation

### MCP Server Overview
- Build standard MCP server using Anthropic's Python SDK
- Register tools for each journal operation (new-entry, summarize, etc.)
- Handle async operations for file I/O and git commands
- Return structured responses with success status and file paths
- Instrument key operations with OpenTelemetry for tracing and performance insights

### Core Components
```
src/mcp_journal/
├── __init__.py
├── cli.py        # Click commands
├── server.py     # MCP server implementation  
├── journal.py    # Journal entry generation
├── git_utils.py  # Git operations
├── telemetry.py  # OpenTelemetry setup and utilities
└── config.py     # Configuration handling
```

### File Structure
```
journal/
├── daily/
│   ├── 2025-05-14.md
│   ├── 2025-05-15.md
│   └── ...
├── summaries/
│   ├── daily/
│   │   ├── 2025-05-14-summary.md
│   │   └── ...
│   ├── weekly/
│   │   ├── 2025-05-week3.md
│   │   └── ...
│   ├── monthly/
│   │   ├── 2025-05.md
│   │   └── ...
│   └── yearly/
│       ├── 2025.md
│       └── ...
└── .mcp-journalrc.yaml
```

### Configuration
Configurable via a `.mcp-journalrc.yaml` file at repo root. Global defaults supported via `~/.mcp-journalrc.yaml`.

#### Configuration Precedence
1. Local config (`.mcp-journalrc.yaml` in repo root)
2. Global config (`~/.mcp-journalrc.yaml`)
3. Built-in defaults

#### Configuration Validation
- Missing/invalid fields use defaults and continue with warnings
- Malformed YAML logs error but continues with defaults
- Invalid sections are ignored with warnings

#### Example Configuration:
```yaml
journal:
  path: journal/
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
  section_order:
    - summary
    - accomplishments
    - frustrations
    - tone
    - commit_details
    - reflections
  auto_summarize:
    daily: true     # Generate daily summary on first commit of new day
    weekly: true    # Generate weekly summary on first commit of week (Monday)
    monthly: true   # Generate monthly summary on first commit of month
    yearly: true    # Generate yearly summary on first commit of year

# Minimal telemetry configuration
telemetry:
  enabled: true                 # Toggle telemetry collection
  service_name: "mcp-journal"   # Service name for traces
```

---

## Journal Entry Behavior

### Triggering
- **Default**: One journal entry per Git commit
- Entries written to daily Markdown files, named `YYYY-MM-DD.md`
- Timestamps included per entry (e.g., `4:02 PM — Commit abc123`)
- Files appended in chronological order

### Chat History Collection Method
- **Primary method**: AI scans backward through current conversation
- **How it works**: AI has access to its own chat history within the current session
- **Boundary**: Look back until finding previous commit reference OR 18-hour limit
- **Usage**: Chat history may inform summary, accomplishments, frustrations, discussion notes, and tone/mood sections
- **No external file access required** - AI uses its own conversation context
- **Decision excerpts**: May include relevant conversation snippets in Discussion Notes section

### Data Sources
#### Required:
- Git commit message and metadata
- File diffs (simplified summaries with line counts)

#### Optional (if available):
- Terminal history (from `.bash_history`, `.zsh_history`, timestamped if possible)
- Chat history with dev agents (scanned in reverse until a reference to the previous git commit is found)
- **Discussion excerpts** from chat history showing decision-making context
- **AI session terminal commands** - commands executed by AI assistants during the work session

### History Collection Boundaries
- **Terminal history**: Between previous commit timestamp and current commit timestamp
- **Chat history**: From current commit backward until finding previous commit reference OR 18-hour safety limit
- **AI session commands**: Request from AI assistant for commands executed during current work session
- **No filtering**: Include all commands/messages within boundaries

### Anti-Hallucination Rules
- Never infer *why* something was done unless evidence exists
- Mood/tone must be backed by language cues ("ugh", "finally", etc.)
- If data is unavailable (e.g., terminal history), omit that section

### Journal Entry Structure

#### Discussion Notes Speaker Attribution
- In the Discussion Notes section, always prefix each statement with **Human:** or **Agent:** (or **AI:**), to clearly indicate the speaker.
- Use bold or clear formatting to make the distinction obvious.

#### Example (Markdown format):
```markdown
### 2:17 PM — Commit def456

## Summary
A friendly, succinct summary that captures what was accomplished. Can be multiple sentences if needed to convey the facts clearly. Written in a natural, human-readable style that would make sense to your future self.

## Accomplishments
- Facts based on file diffs and chat context

## Frustrations or Roadblocks
- Inferred from repeated terminal commands, failure messages, or explicit mentions in chat

## Terminal Commands (AI Session)
Commands executed by AI during this work session:
- `git add . && git status`
- `npm test` x3
- `git diff auth.js`
- `git commit -m "fix: update validation logic"`

## Discussion Notes (from chat)
> **Human:** Should we use PostgreSQL or MongoDB? I'm leaning toward PostgreSQL because we need ACID compliance for financial data...
>
> **Agent:** PostgreSQL is a solid choice for ACID compliance. If you need horizontal scaling later, you can consider sharding or a managed service.
>
> **Human:** Let's go with the fetch-on-demand approach instead of pre-loading everything. Simpler to implement and probably good enough for now.
>
> **Agent:** Agreed. This will also reduce memory usage and make the codebase easier to maintain.

## Tone + Mood (inferred)
> Mood: Focused and energized  
> Indicators: "finally", rapid commits, lack of errors

## Behind the Commit
- Commit hash, message, files touched

## Reflections
- Only include reflections manually added by human using `mcp-journal add-reflection`
- Never infer or generate reflections from chat context
```

Empty sections are omitted. Manual entries and reflections are clearly labeled and interleaved by timestamp.

### AI Tone/Style Configuration

The user can control the tone and style of AI-generated summaries in journal entries by setting the `ai_tone` field in `.mcp-journalrc.yaml`.

**Supported values:**
- `neutral` (default): Objective, factual, and balanced. No strong personality.
- `concise`: Short, direct, and minimal. Focuses on brevity and essentials.
- `explanatory`: Clear, step-by-step, and focused on making things easy to understand.
- `technical`: Uses precise, domain-specific language. For advanced/engineering audiences.
- `reflective`: Thoughtful, introspective, and focused on lessons learned.
- `friendly`: Warm, encouraging, and positive—but still professional.

If an unsupported value is set, the system will fall back to `neutral` and log a warning.

#### Example Configuration:
```yaml
journal:
  path: journal/
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
  section_order:
    - summary
    - accomplishments
    - frustrations
    - tone
    - commit_details
    - reflections
  auto_summarize:
    daily: true
    weekly: true
    monthly: true
    yearly: true
```

#### Journal Entry Structure Note
- The **Summary** section of each journal entry will reflect the selected `ai_tone` style.

---

## MCP Server Implementation

### MCP Operations
1. `journal/new-entry` - Create a new journal entry from current git state
2. `journal/summarize` - Generate weekly/monthly summaries  
3. `journal/blogify` - Convert journal entry(s) to blog post format
4. `journal/backfill` - Check for missed commits and create entries
5. `journal/install-hook` - Install git post-commit hook
6. `journal/add-reflection` - Add a manual reflection to today's journal
7. `journal/init` - Initialize journal in current repository

### Operation Details

#### journal/new-entry
- Check for missed commits and backfill if needed
- Generate entry for current commit
- Return path to updated file

#### journal/summarize
- Options: `--week`, `--month`, `--range`
- Default to most recent period if no date specified
- Support specific dates (e.g., `--week 2025-01-13`)
- Support arbitrary ranges (e.g., `--range "2025-01-01:2025-01-31"`)

#### journal/init
- Create initial journal directory structure
- Generate default configuration file
- Install git post-commit hook (with user confirmation)
- Return initialization status and created paths

#### journal/add-reflection
- Accept reflection text as parameter
- Append to today's journal file with timestamp
- Support markdown formatting in reflection
- Return path to updated file

### Data Formats
- All operations return pre-formatted markdown strings
- Success operations return file path + status
- Hard failures return error status with message

---

## CLI Interface

### Command Structure
```bash
mcp-journal [operation] [options]
```

### Supported Commands
- `mcp-journal init` - Initialize journal in current repository
- `mcp-journal new-entry [--debug]` - Create journal entry for current commit (with AI command collection)
- `mcp-journal add-reflection "text"` - Add manual reflection to today's journal
- `mcp-journal summarize --week [--debug]` - Generate summary for most recent week
- `mcp-journal summarize --month [--debug]` - Generate summary for most recent month
- `mcp-journal summarize --week 2025-01-13` - Week containing specific date
- `mcp-journal summarize --range "2025-01-01:2025-01-31"` - Arbitrary range
- `mcp-journal blogify <file1> [file2] ...` - Convert to blog post
- `mcp-journal install-hook` - Install git post-commit hook
- `mcp-journal backfill [--debug]` - Manually trigger missed commit check

### Global Options
- `--config <path>` - Override config file location
- `--dry-run` - Preview operations without writing files
- `--verbose` - Detailed output for debugging
- `--debug` - Show all errors and warnings, including soft failures

---

## Data Handling Details

### File Organization
- `journal.path` in config sets parent directory containing `daily/` and `summaries/`
- Paths always relative to git repository root
- Missing directories created automatically

### Diff Processing
- Capture simplified summaries with line counts (e.g., "modified 3 functions in auth.py")
- Binary files noted as "binary file changed"
- Large diffs truncated with note about truncation

### Date/Time Handling
- Week boundaries: Monday-Sunday
- Month boundaries: Calendar months (1st to last day)
- All timestamps in local timezone
- ISO format dates in filenames (YYYY-MM-DD)

---

## Error Handling

### Hard Failures (Fail Fast)
These errors return error status and stop execution:
- Git repository not found
- Journal directory doesn't exist and can't be created
- Invalid MCP connection
- Corrupted git repository

### Soft Failures (Silent Skip)
These errors are skipped with optional notes in output:
- Terminal history not accessible
- Chat history unavailable
- Previous commit not found for backfill
- Terminal commands unparseable

### Error Messages
- Brief and actionable
- Include suggestions for resolution where possible
- Never expose internal implementation details

---

## Git Integration

### Hook Installation
- `mcp-journal install-hook` command
- Checks for existing hooks and prompts for action
- Creates simple hook:
  ```bash
  #!/bin/sh
  mcp-journal new-entry
  ```
- Backs up existing hooks before modification

### Backfill Mechanism
- Detection: Check commits since last journal entry in any file
- Order: Add missed entries in chronological order
- Context: Skip terminal/chat history for backfilled entries
- Annotation: Mark entries as backfilled with timestamp

### Commit Processing
- Skip commits that only modify journal files
- For mixed commits (code + journal files), exclude journal files from analysis

---

## Testing Plan

### Unit Tests
- Configuration parsing and validation
- Journal entry generation from mock data
- MCP operation handlers
- Git utility functions
- CLI command parsing
- Date/time handling

### Integration Tests
- End-to-end git hook workflow
- File creation and appending
- Backfill detection and processing
- Summary generation across date ranges
- Blog post conversion

### Test Fixtures
- Sample git repositories with various states
- Mock terminal histories
- Sample chat histories
- Various configuration files
- Mock telemetry exporters for verification

### Test Utilities
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

---

### Implementation Guidelines

### Code Organization
- Each MCP operation maps to a dedicated handler function
- Separate concerns: git operations, file I/O, text processing
- Use type hints throughout for better IDE support
- Keep functions small and single-purpose

### Chat History Processing
- Use simple keyword matching for decision-related discussions
- Include context around matched keywords (e.g., previous/next sentences)
- No complex NLP or structured parsing required
- Fall back gracefully if chat history is unavailable

### AI Terminal History Collection
- **Primary method**: Directly prompt the AI assistant for terminal session history
- **Example prompts**: 
  - "Can you give me a history of your terminal session?"
  - "What commands did you execute during this work session?"
- **No file parsing or API integration required** - works through conversation
- Format commands chronologically as executed
- Deduplicate only adjacent identical commands (e.g., "npm test x3")
- **Always attempt collection, but fail silently if unsupported**
- When successful, provides rich context about problem-solving process
- When unavailable, journal entry proceeds without terminal section

### Implementation Pattern
```python
import logging

# Configure debug logging
debug_logger = logging.getLogger('mcp_journal.debug')

def format_terminal_commands(commands):
    """Deduplicate adjacent identical commands"""
    if not commands:
        return []
    
    formatted = []
    current_cmd = commands[0]
    count = 1
    
    for cmd in commands[1:]:
        if cmd == current_cmd:
            count += 1
        else:
            formatted.append(f"{current_cmd} x{count}" if count > 1 else current_cmd)
            current_cmd = cmd
            count = 1
    
    # Add final command
    formatted.append(f"{current_cmd} x{count}" if count > 1 else current_cmd)
    return formatted

def collect_ai_terminal_history(debug=False):
    try:
        commands = ai_session.get_terminal_commands()
        return format_terminal_commands(commands)
    except AttributeError as e:
        if debug:
            debug_logger.error(f"AI assistant doesn't support terminal commands: {e}")
        return None
    except APIError as e:
        if debug:
            debug_logger.error(f"API error getting terminal history: {e}")
        return None
    except Exception as e:
        if debug:
            debug_logger.error(f"Unexpected error collecting terminal history: {e}")
        return None

def generate_entry(debug=False):
    terminal_commands = collect_ai_terminal_history(debug)
    if terminal_commands:
        add_terminal_section(terminal_commands)
    elif debug:
        debug_logger.info("Terminal commands section omitted (data unavailable)")
    # Continue with other sections...
```

### Dependencies
- Minimal external dependencies
- Prefer standard library where possible
- Use well-maintained packages for specialized tasks

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

## Future Enhancements (Out of Scope for MVP)

### Potential Features
- Scheduled summarization via background agent
- Web interface for browsing/editing entries
- Tagging system for entries or tasks
- Plugin support for detecting test coverage, benchmarks
- Rich text formatting in terminal output
- Integration with project management tools

### Integration Opportunities
- IDE plugins for manual entry creation
- Slack/Discord bot for entry sharing
- GitHub Actions for automated summaries
- Export to various formats (PDF, HTML)

### Hyperlinked Commit Hashes in Journal Entries
- In the "Behind the Commit" section, if a remote repository is detected, the commit hash must be hyperlinked to the commit page on the remote (e.g., GitHub, GitLab).
- The system should support at least GitHub and GitLab, and fall back to plain text if no supported remote is found.
- Example:
  - Commit hash: [`cda9ef2`](https://github.com/your-org/your-repo/commit/cda9ef2)

### Configurable AI Tone/Style for Summaries
- Allow the user to control the tone and style of AI-generated summaries in journal entries by setting the `ai_tone` field in `.mcp-journalrc.yaml`.
- The value of `ai_tone` can be any free-form string, such as a tone, style, persona, or creative instruction. This value will be passed directly to the AI to guide summary generation.
- There is no fixed list of supported values. Users may specify anything, e.g., "concise and technical", "in the style of a pirate", "for a 10-year-old", "sarcastic", "neutral", etc.
- If omitted, the default is "neutral and factual".
- Results may vary depending on the AI's capabilities and the specificity of the instruction.

#### Example Configuration:
```yaml
journal:
  path: journal/
  ai_tone: "like a pirate, but concise"
  auto_generate: true
  include_terminal: true
  include_chat: true
  include_mood: true
  section_order:
    - summary
    - accomplishments
    - frustrations
    - tone
    - commit_details
    - reflections
  auto_summarize:
    daily: true
    weekly: true
    monthly: true
    yearly: true
```

#### Example Values for `ai_tone`:
- "concise and technical"
- "friendly and encouraging"
- "in the style of a pirate"
- "for a 10-year-old"
- "sarcastic"
- "neutral"
- "explanatory, as if teaching a beginner"

---

## Final Notes

This tool is designed to be **developer-friendly**, **minimally intrusive**, and **genuinely useful**. It prioritizes narrative fidelity and long-term story value over exhaustive tracking or rigid formats. Every entry should help the future user say: "This is what I did, how it felt, and what I learned."

### Success Criteria
- Zero friction when working normally
- Valuable output for retrospectives
- Easy to customize and extend
- Reliable operation across different environments

### Development Workflow
1. Set up project structure with pyproject.toml
2. **Write failing tests first** (TDD approach)
3. Implement basic MCP server skeleton
4. Add `journal/init` command and initialization flow
5. Add git integration and journal generation
6. Create CLI interface with Click
7. Add configuration system  
8. Implement decision detection in chat history
9. Add reflection capabilities
10. Implement summarization and blogification
11. Add comprehensive tests (maintaining >90% coverage)
12. Package for distribution

### Initialization Workflow
1. User runs `mcp-journal init` in their repository
2. System checks if already initialized (look for `.mcp-journalrc.yaml`)
3. Creates journal directory structure
4. Generates default configuration file
5. Prompts to install git post-commit hook
6. Displays next steps and usage instructions