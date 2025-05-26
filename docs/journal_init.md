# Journal Initialization & Directory Structure

This document describes how the MCP Journal system initializes its directory structure and the rationale behind it.

## Purpose
The journal directory structure is designed to organize daily entries and summary files for easy retrieval, analysis, and storytelling. Initialization ensures all required directories exist before journal operations begin.

## Directory Structure
Upon initialization, the following structure is created (relative to the configured `journal.path`):

```
journal/
├── daily/
├── summaries/
│   ├── daily/
│   ├── weekly/
│   ├── monthly/
│   └── yearly/
```

- `daily/`: Contains daily journal entry files (e.g., `2025-05-26-journal.md`).
- `summaries/daily/`: Daily summary files.
- `summaries/weekly/`: Weekly summary files.
- `summaries/monthly/`: Monthly summary files.
- `summaries/yearly/`: Yearly summary files.

## Initialization Logic
- The function `create_journal_directories(base_path)` is responsible for creating this structure.
- If any directory already exists, it is left unchanged.
- If `base_path` exists and is not a directory, a `NotADirectoryError` is raised.
- Permission errors or invalid paths raise appropriate exceptions.

## Configuration File Generation

The function `generate_default_config(config_path, journal_path)` creates a new configuration file for the MCP Journal system at the specified path, customizing the journal directory location. If a config file already exists (even if malformed), it is backed up with a unique `.bak` timestamped suffix before writing the new config.

- The generated config uses all default fields from the main config system (`DEFAULT_CONFIG` in `config.py`).
- The `journal.path` field is set to the provided `journal_path` argument.
- The config is written in YAML format, consistent with the rest of the system.
- This function ensures that the config is always consistent with the latest schema and prevents accidental loss of previous config files.

See [src/mcp_commit_story/config.py](../src/mcp_commit_story/config.py) for the config schema and [scripts/mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md) for full requirements.

## Git Repository Validation

Before initializing the journal, the system validates that the target directory is a valid (non-bare) git repository with proper permissions using `validate_git_repository(path)`.

- If the path does not exist, a `FileNotFoundError` is raised.
- If the path exists but is not readable, a `PermissionError` is raised.
- If the path is readable but not a git repo, a `FileNotFoundError` is raised.
- If the path is a bare repo, a `ValueError` is raised.
- Only non-bare, accessible git repositories are valid for journal initialization.

This logic ensures that journals are only initialized in appropriate development repositories and provides clear, actionable error messages for users.

See [src/mcp_commit_story/git_utils.py](../src/mcp_commit_story/git_utils.py) for git detection logic and [scripts/mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md) for requirements.

## Main Journal Initialization Function

The function `initialize_journal(repo_path=None, config_path=None, journal_path=None)` is the main entry point for setting up the MCP Journal system in a repository.

- **Parameters:**
  - `repo_path`: Path to the git repository (defaults to current directory)
  - `config_path`: Path for the config file (defaults to `.mcp-commit-storyrc.yaml` in repo root)
  - `journal_path`: Path for the journal directory (defaults to `journal/` in repo root)
- **Returns:** Dictionary with `{"status": "success/error", "paths": {...}, "message": "..."}`

### Initialization & Rollback Strategy
- Validates the target directory is a non-bare, accessible git repository using `validate_git_repository()`.
- Checks for existing config and journal directory:
  - If both exist, returns an error (already initialized).
  - If only one exists, proceeds to create the missing piece (partial recovery supported).
- Calls `generate_default_config()` and `create_journal_directories()` as needed.
- **No automatic rollback:** Any successfully created files/directories are left in place if an error occurs. The function logs what was created so the user can manually clean up if needed. This is safer than trying to undo filesystem changes.
- Fails fast on the first error and reports what succeeded before failure.

### Error Handling
- All errors are surfaced as Python exceptions or as error status in the return value.
- The function is designed for use by both CLI and MCP server entry points.

See also: [src/mcp_commit_story/journal_init.py](../src/mcp_commit_story/journal_init.py) for implementation details.

## Related Operations
- Initialization is typically performed as part of `journal/init` or the first journal operation.
- The structure is required for all journal entry and summary generation features.

## See Also
- [server_setup.md](server_setup.md)
- [mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md)

## Integration Testing

Integration tests for journal initialization ensure that the full workflow operates correctly in real-world scenarios. These tests cover:

- Clean initialization in a new git repository
- Re-initialization detection (already initialized)
- Partial recovery when only config or journal directory exists
- Failure recovery, ensuring successful parts are left in place and errors are reported

See `tests/integration/test_journal_init_integration.py` for implementation details. These tests use temporary directories and subprocesses to simulate actual usage, providing confidence that all components work together as expected. 