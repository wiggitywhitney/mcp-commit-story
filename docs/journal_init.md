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

## On-Demand Directory Creation Utility

With the refactor to on-demand directory creation, the MCP Journal system now uses a utility function `ensure_journal_directory(file_path)` to create parent directories only when needed. This function is called by all file operations that write to the journal, ensuring that directories are created just-in-time rather than all at once during initialization.

- **Function:** `ensure_journal_directory(file_path)`
- **Location:** [src/mcp_commit_story/journal.py](../src/mcp_commit_story/journal.py)
- **Behavior:**
  - Creates all missing parent directories for the given file path.
  - Does nothing if the directory already exists.
  - Raises `PermissionError` if directory creation fails due to permissions.
  - Used by all journal file write operations to ensure directories exist before writing.

This approach keeps the journal directory structure clean and avoids creating empty folders that may never be used. It also maintains robust error handling and is fully covered by unit tests.

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

**Naming Convention Note:**
The CLI command is named `journal-init` (not just `init`) to avoid ambiguity and to align with the namespaced pattern used for other MCP tool operations. This makes the CLI more discoverable and scalable as additional commands are added.

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

## CLI Behavior for On-Demand Directory Creation and Error Handling

With the on-demand directory creation pattern, the CLI now behaves as follows:
- After running `journal-init`, only the base `journal/` directory is created. Subdirectories (e.g., `daily/`, `summaries/`) are created automatically as needed by CLI commands that write journal entries or summaries.
- If a CLI command attempts to write a journal entry and the required subdirectory does not exist, it is created on demand using the same robust error handling as the core utility function.
- If directory creation fails due to permissions or other file system errors, the CLI reports a user-friendly error message and an appropriate error code (see Error Codes above).
- This behavior is fully covered by tests in `tests/unit/test_cli.py`.

This approach ensures a clean journal structure, robust error handling, and a user-friendly CLI experience.

**CLI On-Demand Directory Creation and Error Handling (2025-05 Update):**
- All CLI commands that write journal files now rely on the on-demand directory creation utility (`ensure_journal_directory`) in [journal.py](../src/mcp_commit_story/journal.py).
- CLI commands no longer create directories directly; all directory creation and error handling is centralized in the utility functions.
- Permission errors and other filesystem issues are caught and reported as user-friendly error messages and error codes, as required by the CLI contract.
- See [cli.py](../src/mcp_commit_story/cli.py) for implementation details.

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

**On-Demand Directory Creation Integration Tests:**
Integration tests now validate that only the base `journal/` directory is created during initialization. Subdirectories (e.g., `daily/`, `summaries/`) are created on-demand by file operations (such as writing a journal entry). See `tests/integration/test_journal_init_integration.py` for updated test cases covering:
- Clean initialization (base directory only)
- File operations that trigger subdirectory creation
- Mixed scenarios (init, then write to nested summary file)
- Error handling for permission issues

These tests ensure the new pattern is robust and that the system behaves as expected in real-world workflows.

## Integration Testing: Git Hook Installation

Integration tests for git hook installation ensure that the post-commit hook can be installed, replaced, and executed correctly in real-world git repositories. These tests cover:

- Clean installation of the post-commit hook in a new repository
- Overwriting and backing up an existing hook
- Verifying that the hook executes after a commit (side effect test)
- Cleanup and removal of hooks and backups

See `tests/integration/test_git_hook_integration.py` for implementation details. These tests use temporary git repositories and subprocesses to simulate actual usage, providing confidence that the hook installation and execution logic is robust and reliable.

### Hook Execution Testing

Integration tests for hook execution directly write a debug post-commit hook to `.git/hooks/post-commit` and verify that it is executed:
- After a commit (git triggers the hook)
- When run directly as an executable
- When run with `sh post-commit`

This approach ensures the hook is actually executed in all relevant scenarios, not just installed. See `tests/integration/test_git_hook_integration.py` for details.

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

## Hook Backup Logic
- Before installing a new post-commit hook, the system calls `backup_existing_hook(hook_path)`.
- This function creates a backup of the existing hook file with a timestamped name: `post-commit.backup.YYYYMMDD-HHMMSS` in the same directory.
- Multiple backups are supported; each backup is unique due to the timestamp.
- If the filesystem is read-only or an IO error occurs, a `PermissionError` or `IOError` is raised and must be handled by the caller.
- All backup logic is covered by unit tests in `tests/unit/test_git_utils.py` (see tests for multiple backups, permission errors, and IO errors).

## Hook Installation Core Logic
- The function `install_post_commit_hook(repo_path)` in [src/mcp_commit_story/git_utils.py](../src/mcp_commit_story/git_utils.py) installs or replaces the post-commit hook in `.git/hooks`.
- If a hook already exists, it is always backed up with a timestamped filename before being replaced (see backup logic above).
- The new hook is written using the content from `generate_hook_content()`.
- The installed hook is set to be executable by user, group, and other (0o755), matching standard Git hook permissions.
- No interactive confirmation is required; the process is fully automated for CI/CD and scripting compatibility.
- All logic is covered by unit tests in `tests/unit/test_git_utils.py` and `tests/unit/test_git_hook_installation.py`.

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

## CLI Command: install-hook

The MCP Journal system provides a CLI command to install or replace the git post-commit hook in your repository. This command is implemented in [src/mcp_commit_story/cli.py](../src/mcp_commit_story/cli.py) and uses the tested logic from `install_post_commit_hook`.

**Usage:**
```bash
python -m mcp_commit_story.cli install-hook --repo-path <repo>
```
All arguments are optional and default to the current directory and standard locations.

**Options:**
- `--repo-path`: Path to git repository (default: current directory)

**Output Format:**
- On success:
```json
{
  "status": "success",
  "result": {
    "message": "Post-commit hook installed successfully.",
    "backup_path": "/path/to/backup"  // or null if no backup was needed
  }
}
```
- On error:
```json
{
  "status": "error",
  "message": "User-friendly error description",
  "code": 1
}
```

**Error Codes:**
- 0: Success
- 1: General error (not a git repo, permission denied, etc.)
- 2: Already installed
- 4: File system errors (can't create hooks, etc.)

**Rationale:**
- The CLI always outputs JSON for both success and error cases, making it easy to use in scripts and CI/CD pipelines.
- All logic is covered by unit tests in `tests/unit/test_cli_install_hook.py`.

## Related Operations
- Post-commit hook installation is typically performed as part of `journal/init` or the first journal operation.
- The hook is required for all journal entry and summary generation features.

## See Also
- [src/mcp_commit_story/git_utils.py](../src/mcp_commit_story/git_utils.py)
- [scripts/mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md)

## Operational Commands: MCP Server Only

**Important**: The MCP Commit Story follows an **MCP-first architecture**. Operational commands like creating journal entries, adding reflections, and generating summaries are **only available via the MCP server**, not through CLI commands.

### Available via MCP Server:
- `journal/new-entry`: Create new journal entries  
- `journal/add-reflection`: Add manual reflections
- `journal/summarize`: Generate summaries
- `journal/blogify`: Create blog-style content

### Setup CLI Commands:
The CLI provides focused setup commands for human-friendly configuration:
- `journal-init`: Initialize journal configuration
- `install-hook`: Install git post-commit hooks

This design delivers the best experience for each use case - simple setup commands for humans, and rich structured operations for AI automation. For operational features, use:
- AI agents with MCP client integration (recommended)
- Direct MCP server integration  
- Automated git hooks (installed via `install-hook`)

See [architecture.md](architecture.md) and [setup-cli.md](setup-cli.md) for complete details on this architecture. 