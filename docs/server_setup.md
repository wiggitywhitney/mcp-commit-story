# Server Setup

This guide explains how to set up and configure the MCP server for the `mcp-commit-story` project.

## What is the MCP Server?
The MCP server is a Python service that exposes journal operations (such as `journal/add-reflection`, `journal/capture-context`, etc.) for engineering teams. It integrates with Git, collects commit and context data, and provides additional functionality beyond the automatic journal generation that happens via git hooks.

## Architecture Overview

The MCP Commit Story system uses a hybrid approach:

- **Automatic Journal Generation**: Git post-commit hooks → `git_hook_worker.py` → direct journal creation
- **Additional Operations**: MCP server provides manual tools, reflections, context capture, and setup operations
- **AI Integration**: Both paths use the same underlying AI-powered journal generation logic

The MCP server complements the automatic git hook system by providing:

1. **Manual journal operations** for special cases (missed commits, batch processing)
2. **User interaction tools** (add reflections, capture context)  
3. **Setup and configuration** (initialize journals, install hooks)
4. **Summary generation** (daily, weekly, monthly summaries)

This design ensures journal entries are created automatically during normal development while providing rich tooling for enhanced workflow integration.

## Installation
1. **Clone the repository:**
   ```sh
   git clone <repo-url>
   cd mcp-commit-story
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   # or, if using poetry or uv:
   poetry install
   # or
   uv pip install -r requirements.txt
   ```

## Configuration

The server uses a YAML configuration file (`.mcp-commit-storyrc.yaml`) that supports environment variable interpolation using `${VAR_NAME}` syntax.

### Example Configuration

```yaml
# .mcp-commit-storyrc.yaml
journal:
  path: journal/

git:
  exclude_patterns:
    - journal/**
    - .mcp-commit-storyrc.yaml

ai:
  openai_api_key: "${OPENAI_API_KEY}"

telemetry:
  enabled: false
```

### Configuration Sections

- `journal.path`: Directory for journal files
- `git.exclude_patterns`: Files to exclude from git processing
- `ai.openai_api_key`: OpenAI API key (supports ${VAR_NAME} syntax)
- `telemetry.enabled`: Enable/disable telemetry

## Error Handling

The server provides clear error messages for configuration issues:

1. **Missing Configuration**
   ```
   ConfigError: Missing required config: journal.path
   ```

2. **Invalid Environment Variables**
   ```
   ConfigError: Environment variable 'OPENAI_API_KEY' not found
   ```

## See Also

- [AI Provider Setup](ai-provider-setup.md)
- [Implementation Guide](implementation-guide.md)