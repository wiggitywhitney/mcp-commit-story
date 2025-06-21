# Cursor Database Setup Guide

This guide provides platform-specific instructions for setting up Cursor SQLite database integration with MCP Commit Story.

## Overview

MCP Commit Story automatically detects and reads Cursor's SQLite workspace databases to extract chat history for journal generation. The system supports Windows, macOS, Linux, and WSL environments with automatic platform detection.

## Platform-Specific Locations

### macOS
**Default Location:**
```
~/Library/Application Support/Cursor/User/workspaceStorage/
```

**Setup Requirements:**
- Cursor must be installed via the standard installer
- No additional configuration required
- System automatically detects the standard location

### Windows
**Default Locations:**
```
%APPDATA%\Cursor\User\workspaceStorage\
C:\Users\{username}\AppData\Roaming\Cursor\User\workspaceStorage\
```

**Setup Requirements:**
- Cursor installed in standard location
- Ensure APPDATA environment variable is set (default on Windows)
- No additional configuration required

### Linux
**Default Locations:**
```
~/.config/Cursor/User/workspaceStorage/
$XDG_CONFIG_HOME/Cursor/User/workspaceStorage/
```

**Setup Requirements:**
- Cursor installed via AppImage, Snap, or package manager
- Standard XDG configuration directory structure
- No additional configuration required

### WSL (Windows Subsystem for Linux)
**Default Locations:**
```
/mnt/c/Users/{username}/AppData/Roaming/Cursor/User/workspaceStorage/
/mnt/C/Users/{username}/AppData/Roaming/Cursor/User/workspaceStorage/
~/.config/Cursor/User/workspaceStorage/ (if Cursor installed in WSL)
```

**Setup Requirements:**
- Windows drives mounted under `/mnt/c/` (standard WSL configuration)
- Cursor installed on Windows host system
- Read permissions for Windows user directories

## Custom Configuration

### Environment Variable Override
Set a custom workspace path using the environment variable:

```bash
export CURSOR_WORKSPACE_PATH="/path/to/custom/workspace"
```

This takes priority over all platform-specific default locations.

### Manual Path Configuration
If automatic detection fails, you can specify the workspace path in your MCP configuration:

```yaml
# .mcp-commit-storyrc.yaml
cursor:
  workspace_path: "/path/to/cursor/workspace"
```

## Troubleshooting

### Common Issues

**Database Not Found**
```bash
# Check if Cursor is installed and has been used
ls -la ~/Library/Application\ Support/Cursor/User/workspaceStorage/  # macOS
ls -la ~/.config/Cursor/User/workspaceStorage/                       # Linux
dir %APPDATA%\Cursor\User\workspaceStorage\                         # Windows
```

**Permission Denied**
- Ensure the user running MCP Commit Story has read access to Cursor directories
- On WSL, verify Windows drive mount permissions
- Check file system permissions for the workspace directories

**Multiple Cursor Installations**
If you have multiple Cursor installations (stable, insiders, portable), the system will detect multiple workspace paths. The first valid path found will be used.

**WSL Detection Issues**
If WSL detection fails:
```bash
# Check WSL environment detection
cat /proc/version  # Should contain "Microsoft" or "WSL"
echo $WSL_DISTRO_NAME  # Should be set in WSL2
```

### Validation Commands

**Test Platform Detection:**
```python
from mcp_commit_story.cursor_db.platform import detect_platform, get_cursor_workspace_paths

# Check detected platform
platform = detect_platform()
print(f"Detected platform: {platform}")

# Check discovered workspace paths
paths = get_cursor_workspace_paths()
print(f"Found {len(paths)} potential workspace paths:")
for path in paths:
    print(f"  {path}")
```

**Validate Workspace Access:**
```python
from mcp_commit_story.cursor_db.platform import find_valid_workspace_paths

# Check accessible workspace paths
valid_paths = find_valid_workspace_paths()
print(f"Found {len(valid_paths)} accessible workspace paths:")
for path in valid_paths:
    print(f"  {path}")
```

## Security Considerations

- MCP Commit Story only reads from Cursor databases, never writes
- Chat history data is processed locally and not transmitted externally
- Sensitive information in chat history is sanitized before journal generation
- Database connections use read-only access patterns

## Supported Cursor Versions

The system is compatible with:
- Cursor Stable (all versions)
- Cursor Insiders (all versions)
- Portable Cursor installations
- Custom Cursor installations with standard workspace structure

## Advanced Configuration

### Multiple Workspace Support
If you work with multiple Cursor workspaces, the system will automatically discover all available workspace storage directories and process them in priority order.

### Network Drive Support
The system supports Cursor installations on network drives, though performance may be reduced. Ensure proper network permissions and stable connectivity.

### Performance Optimization
For large workspace directories (>1000 workspace folders), consider:
- Using the environment variable override to specify exact paths
- Implementing custom filtering in your MCP configuration
- Monitoring system performance during database scanning operations 