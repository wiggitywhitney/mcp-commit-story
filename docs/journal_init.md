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

## Error Handling
- All errors are surfaced as Python exceptions and should be handled by the caller.
- See `src/mcp_commit_story/journal_init.py` for implementation details.

## Related Operations
- Initialization is typically performed as part of `journal/init` or the first journal operation.
- The structure is required for all journal entry and summary generation features.

## See Also
- [server_setup.md](server_setup.md)
- [mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md) 