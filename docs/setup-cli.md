# Setup CLI Reference

## Overview

The MCP Commit Story provides a **focused setup CLI** that handles journal initialization and git hook installation. This CLI is designed to work seamlessly with the MCP server architecture, where setup operations use human-friendly commands and operational features leverage AI-agent integration.

## Architecture Philosophy

The system uses a **purposeful separation of concerns**:

- **Setup CLI**: Human-friendly commands for one-time configuration tasks
- **MCP Server**: Rich operational features for AI agents and integrated development environments

This approach delivers the best experience for each use case - simple setup commands for humans, and rich structured operations for AI automation.

## Available Commands

### `journal-init` - Initialize Journal System

```bash
mcp-commit-story-setup journal-init [OPTIONS]
```

Initialize journal configuration and directory structure in a git repository.

**Options**:
- `--repo-path PATH`: Path to git repository (default: current directory)
- `--config-path PATH`: Path for config file (default: `.mcp-commit-storyrc.yaml`)
- `--journal-path PATH`: Path for journal directory (default: `journal/`)

**Features**:
- ✅ Creates journal directory structure
- ✅ Generates default configuration file
- ✅ Validates git repository
- ✅ JSON output for scripting
- ✅ Comprehensive error handling

### `install-hook` - Install Git Post-Commit Hook

```bash
mcp-commit-story-setup install-hook [OPTIONS]
```

Install git post-commit hook for automated journal entry creation.

**Options**:
- `--repo-path PATH`: Path to git repository (default: current directory)

**Features**:
- ✅ Installs automated git hook
- ✅ Backs up existing hooks
- ✅ Non-blocking hook execution
- ✅ Cross-platform compatibility
- ✅ JSON output for scripting

## JSON Output Format

All commands provide structured JSON output for both success and error cases:

**Success Example**:
```json
{
  "status": "success",
  "result": {
    "message": "Journal initialized successfully.",
    "paths": {
      "config": "/path/to/.mcp-commit-storyrc.yaml",
      "journal": "/path/to/journal"
    }
  }
}
```

**Error Example**:
```json
{
  "status": "error",
  "message": "Not a git repository",
  "code": 1,
  "details": "Technical details for debugging"
}
```

## Working with Operational Features

For journal operations like adding entries, reflections, and generating summaries, use the **MCP server integration**:

### AI Agent Integration (Recommended)

```python
# Example: Using MCP client in AI agent
await mcp_client.call_tool("journal/add-reflection", {
    "text": "Today I implemented a clean CLI architecture...",
    "date": "2025-06-03"
})
```

### Editor Integration

Configure the MCP server in your editor (e.g., Cursor) for integrated journal operations.

### Automated Workflows

The `install-hook` command sets up automatic journal entries on every git commit.

## Installation & Usage

### Install Package

```bash
pip install mcp-commit-story
```

### Quick Start

```bash
# Initialize journal in current git repository
mcp-commit-story-setup journal-init

# Install automated git hooks
mcp-commit-story-setup install-hook
```

### Get Help

```bash
mcp-commit-story-setup --help
mcp-commit-story-setup journal-init --help
mcp-commit-story-setup install-hook --help
```

## Benefits of This Architecture

### 🎯 **Focused Design**
Each component does what it's best at - CLI for setup, MCP for operations.

### 🤖 **AI-First Operations** 
Rich structured data exchange enables sophisticated AI-powered journaling.

### 🔧 **Human-Friendly Setup**
Simple commands handle the configuration tasks humans need to do.

### 📈 **Scalable Integration**
Easy to extend with new operational capabilities via MCP server.

### ⚡ **Automated Workflows**
Git hooks eliminate manual intervention in development workflows.

## Error Codes

Standard error codes for programmatic use:

- `0`: Success
- `1`: General error (not a git repo, permission denied, etc.)
- `2`: Already initialized
- `3`: Invalid arguments/usage
- `4`: File system errors

## Testing

The CLI setup commands are comprehensively tested in `tests/unit/test_cli_limitations.py`:

- ✅ Command availability and help text
- ✅ JSON output format validation
- ✅ Error handling scenarios
- ✅ Console script entry points
- ✅ Configuration validation

## Related Documentation

- **[Architecture](architecture.md)** - Complete system design overview
- **[MCP API Specification](mcp-api-specification.md)** - Operational features reference
- **[Journal Init](journal_init.md)** - Detailed initialization documentation
- **[Server Setup](server_setup.md)** - MCP server configuration

## Implementation Details

- **Framework**: Click (elegant command parsing)
- **Entry Point**: `src/mcp_commit_story/cli.py`
- **Console Script**: `mcp-commit-story-setup`
- **Configuration**: Defined in `pyproject.toml`
- **Output**: Structured JSON for all operations 