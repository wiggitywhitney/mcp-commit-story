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

## Error Handling
- All errors are surfaced as Python exceptions and should be handled by the caller.
- See `src/mcp_commit_story/journal_init.py` for implementation details.

## Related Operations
- Initialization is typically performed as part of `journal/init` or the first journal operation.
- The structure is required for all journal entry and summary generation features.

## See Also
- [server_setup.md](server_setup.md)
- [mcp-commit-story-prd.md](../scripts/mcp-commit-story-prd.md) 