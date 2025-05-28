# On-Demand Directory Creation Pattern for MCP Journal

## Overview
The MCP Journal system uses an on-demand directory creation pattern: directories are created only when needed by file operations, not upfront during initialization. This keeps the repo clean and avoids empty folders.

## Canonical Usage
Always call `ensure_journal_directory(file_path)` before writing to any journal file:

```python
from mcp_commit_story.journal import ensure_journal_directory
file_path = Path("journal/daily/2025-05-28-journal.md")
ensure_journal_directory(file_path)
with open(file_path, "a") as f:
    f.write(entry)
```

## Anti-Patterns (What NOT to Do)
- ❌ Do NOT create all subdirectories at initialization (no more `create_journal_directories`)
- ❌ Do NOT assume parent directories exist before writing
- ❌ Do NOT manually check for directory existence before every write (use the utility)

## Integration Checklist
- [ ] All file-writing functions call `ensure_journal_directory` before writing
- [ ] No code references or uses `create_journal_directories`
- [ ] Tests cover directory creation on-demand (not upfront)
- [ ] Docstrings mention on-demand pattern where relevant

## Task-Specific Guidance
### Task 10: Manual Reflection Addition
- Update `add_reflection_to_journal()` to call `ensure_journal_directory(file_path)` before writing the reflection.
- Do not create directories at init; rely on on-demand pattern.
- Add/Update tests to verify reflections work when parent directories do not exist.

### Task 11: Summary Generation
- Update `save_summary()` to call `ensure_journal_directory(file_path)` for all summary types (daily, weekly, monthly, yearly).
- Do not create summary directories at init; rely on on-demand pattern.
- Add/Update tests to verify summaries are saved correctly when directories do not exist.

### Task 22: Remaining MCP Server Handlers
- Ensure all MCP server handlers that write files use `ensure_journal_directory` before writing.
- Add/Update tests to verify handlers work when directories do not exist.

## References
- See the engineering spec (engineering-mcp-journal-spec-final.md) for rationale and requirements.
- See function docstrings in `journal.py` for usage examples.

## Troubleshooting & Common Errors
- **PermissionError**: Raised if directory creation fails due to permissions. Handle gracefully and report to user.
- **FileNotFoundError**: Should not occur if `ensure_journal_directory` is used correctly.
- **Test Failures**: If tests fail due to missing directories, check that the utility is called before file writes.

## For Developers
- Always use the utility for new file-writing features.
- Review and update tests to cover on-demand directory creation.
- Update docstrings and documentation to mention the pattern where relevant. 