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

## CLI Command for Journal Initialization

You can initialize the MCP Journal system from the command line using the `journal-init` CLI command. This command is implemented in [src/mcp_commit_story/cli.py](../src/mcp_commit_story/cli.py) and provides a standardized JSON output for both success and error cases.

**Usage:**
```bash
python -m mcp_commit_story.cli --repo-path <repo> --config-path <config> --journal-path <journal>
```
All arguments are optional and default to the current directory and standard locations.

**Options:**
- `--repo-path`: Path to git repository (default: current directory)
- `--config-path`: Path for config file (default: .mcp-commit-storyrc.yaml in repo root)
- `--journal-path`: Path for journal directory (default: journal/ in repo root)

**Output Format:**
- On success:
```json
{
  "status": "success",
  "result": {
    "paths": { "config": "/path/to/.mcp-commit-storyrc.yaml", "journal": "/path/to/journal" },
    "message": "Journal initialized successfully."
  }
}
```
- On error:
```json
{
  "status": "error",
  "message": "User-friendly error description",
  "code": 1,
  "details": "Technical error details (optional)"
}
```

**Error Codes:**
- 0: Success
- 1: General error (not a git repo, permission denied, etc.)
- 2: Already initialized
- 3: Invalid arguments/usage
- 4: File system errors (can't create directories, etc.)

This contract ensures both human and programmatic consumers can reliably interpret CLI output.

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

# Post-Commit Hook Content Generation & Installation

## Purpose
The MCP Journal system integrates with Git by installing a post-commit hook that automatically triggers journal entry creation after each commit. This ensures that engineering activity is captured with zero manual effort and minimal workflow disruption.

## Hook Content Generation
- The function `generate_hook_content(command: str = "mcp-commit-story new-entry")` in [src/mcp_commit_story/git_utils.py](../src/mcp_commit_story/git_utils.py) generates the content for the post-commit hook script.
- The generated script uses `#!/bin/sh` as the shebang for maximum portability across Unix-like systems.
- The default command is `mcp-commit-story new-entry`, but a custom command can be provided if needed.
- All output (stdout and stderr) is redirected to `/dev/null` and the command is followed by `|| true` to ensure the hook never blocks a commit, even if the journal entry creation fails.
- The script is lightweight, non-intrusive, and designed to never interfere with normal Git operations.

**Example generated hook content:**
```sh
#!/bin/sh
mcp-commit-story new-entry >/dev/null 2>&1 || true
```

## Hook Installation Logic
- The function `install_post_commit_hook(repo_path: str = None)` installs or replaces the post-commit hook in the target repository's `.git/hooks` directory.
- If a hook already exists, it is backed up with a timestamped suffix before being replaced.
- The installed hook always uses the content generated by `generate_hook_content()` to ensure consistency and compliance with best practices.
- The hook file is set as executable for all users.

## Rationale
- **Portability:** Using `#!/bin/sh` ensures the hook works on all Unix-like systems.
- **Non-blocking:** The `|| true` pattern and output suppression guarantee that journal failures never block commits or clutter the user experience.
- **Simplicity:** The hook is single-purpose and easy to audit or modify if needed.

## Testing & TDD
- All hook content generation and installation logic is covered by unit tests in `tests/unit/test_git_hook_installation.py` and `tests/unit/test_git_utils.py`.
- Tests verify correct script content, shebang, error handling, backup logic, and file permissions.
- The implementation follows strict TDD: tests were written and verified to fail before implementation, and all tests now pass.

## See Also
- [src/mcp_commit_story/git_utils.py](../src/mcp_commit_story/git_utils.py)
- [tests/unit/test_git_hook_installation.py](../tests/unit/test_git_hook_installation.py)
- [tests/unit/test_git_utils.py](../tests/unit/test_git_utils.py)
- [scripts/mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md) 