# Git Hook Background Mode

## Overview

The MCP Commit Story git hook supports background mode execution to prevent journal generation from blocking git commit operations. This feature allows developers to commit code immediately while journal entries are generated asynchronously in the background.

## Problem

By default, git hooks run synchronously during the commit process. For journal generation that involves:
- AI content generation
- Context collection from chat history
- File system operations
- Network requests

This can add several seconds of delay to each git commit, disrupting developer workflow.

## Solution

Background mode spawns journal generation in a detached background process that runs independently of the git commit operation. The commit completes immediately while journal generation continues in the background.

## Installation

### CLI Installation

Install a background mode hook using the CLI:

```bash
# Install with background mode enabled
mcp-commit-story install-hook --background

# Install with custom timeout
mcp-commit-story install-hook --background --timeout 45

# Install synchronous mode (default)
mcp-commit-story install-hook
```

### Programmatic Installation

```python
from mcp_commit_story.git_utils import install_post_commit_hook

# Install background mode hook
install_post_commit_hook(
    repo_path="/path/to/repo",
    background=True,
    timeout=30
)

# Install synchronous mode hook
install_post_commit_hook(repo_path="/path/to/repo")
```

## Generated Hook Content

### Background Mode Hook

```bash
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

### Synchronous Mode Hook

```bash
#!/bin/sh
python -m mcp_commit_story.git_hook_worker "$PWD" >/dev/null 2>&1 || true
```

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `background` | Enable background mode | `False` |
| `timeout` | Background worker timeout in seconds | `30` |

## Background Worker

The background worker (`background_journal_worker.py`) provides:

- **Detached execution**: Runs independently of git process
- **Timeout protection**: Prevents hanging processes
- **Comprehensive logging**: Logs to `.git/hooks/mcp-background-journal.log`
- **Graceful error handling**: Never impacts git operations
- **Telemetry collection**: Tracks performance and errors

## Logging

Background operations log to:
```
.git/hooks/mcp-background-journal.log
```

Log entries include:
- Process ID for background tracking
- Commit hash being processed
- Execution time and results
- Error details if generation fails

## Error Handling

Background mode implements graceful degradation:

1. **Timeout protection**: Worker terminates after configured timeout
2. **Silent failures**: Errors logged but don't affect git operations
3. **Process isolation**: Background failures don't impact development
4. **Telemetry capture**: Errors tracked for monitoring

## Performance Comparison

| Mode | Git Commit Speed | Journal Generation |
|------|------------------|-------------------|
| Synchronous | 3-10 seconds | Immediate |
| Background | Immediate | 3-10 seconds (async) |

## Monitoring

Telemetry metrics tracked:

- `git_hook.install_total`: Hook installations by mode
- `git_hook.install_success_total`: Successful installations
- `background_journal_generation_total`: Background generations
- `background_journal_generation_duration_seconds`: Processing time

## Best Practices

1. **Use background mode for active development**: Prevents workflow disruption
2. **Use synchronous mode for CI/CD**: Ensures journal generation completes
3. **Monitor background logs**: Check for generation failures
4. **Adjust timeout based on system**: Slower systems may need longer timeouts
5. **Regular log rotation**: Background logs can grow over time

## Troubleshooting

### Common Issues

**Background worker not starting**
- Check system supports `nohup` command
- Verify Python environment is accessible
- Review background log for startup errors

**Journal entries not generated**
- Check `.git/hooks/mcp-background-journal.log` for errors
- Verify background worker has required permissions
- Test with synchronous mode to isolate issues

**Performance issues**
- Increase timeout for slower systems
- Monitor system resources during background generation
- Consider reducing context collection scope

### Debugging Commands

```bash
# Check background log
cat .git/hooks/mcp-background-journal.log

# Test background worker manually
python -m mcp_commit_story.background_journal_worker \
    --commit-hash $(git rev-parse HEAD) \
    --repo-path . \
    --timeout 30

# Test synchronous mode
python -m mcp_commit_story.git_hook_worker "."
```

## Migration

### From Synchronous to Background

1. Reinstall hook with background flag:
   ```bash
   mcp-commit-story install-hook --background
   ```

2. Verify background operation:
   ```bash
   git commit -m "test commit"
   # Should complete immediately
   
   # Check background log
   tail -f .git/hooks/mcp-background-journal.log
   ```

### From Background to Synchronous

1. Reinstall hook without background flag:
   ```bash
   mcp-commit-story install-hook
   ```

2. Verify synchronous operation:
   ```bash
   git commit -m "test commit"
   # Should wait for journal generation
   ```

This feature enables developers to maintain fast commit cycles while preserving comprehensive journal generation. 