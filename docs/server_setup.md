# MCP Server Setup & Configuration

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

## Launching the Server

### Primary Entry Point (Recommended)
Run the server using the official MCP server entry point:
```sh
python -m mcp_commit_story
```

This entry point provides:
- **Comprehensive telemetry and monitoring** with startup/shutdown metrics
- **Robust error handling** with proper exit codes (0=success, 1=error, 2=config error, 130=SIGINT)
- **Signal handling** for graceful shutdown (SIGINT, SIGTERM) and config reload (SIGHUP)
- **Configuration validation** with clear error messages for invalid or missing settings
- **Structured logging** throughout the server lifecycle

### Alternative Launch Methods
For development or specific use cases, you can also run:
```sh
python -m mcp_commit_story.server  # Direct server module (legacy)
```

The server uses **stdio transport** by default for maximum compatibility with AI clients and editors.

## Configuration
- The server loads configuration from `.mcp-commit-storyrc.yaml` in your project root (or `~/.mcp-commit-storyrc.yaml` for global defaults).
- Configuration options include journal paths, auto-generation, telemetry, and more. See the example config in the main README or engineering spec.
- The server version is read dynamically from `pyproject.toml` to ensure consistency.

## Hot Config Reload & Strict Validation

The MCP server supports **hot configuration reload** and strict validation:

- Call `reload_config()` on the server's config object to reload configuration from disk at runtime. This will re-validate all required fields and apply any changes immediately.
- **Strict validation**: All required config fields (such as `journal.path`, `git.exclude_patterns`, and `telemetry.enabled`) must be present and valid in the config file. If any required field is missing or invalid, the server will fail fast on startup or reload, raising a clear error.
- Defaults are only applied for optional fields. Required fields must be explicitly set in the config file.
- If you edit `.mcp-commit-storyrc.yaml` while the server is running, call `server.reload_config()` to apply changes. If the new config is invalid, the reload will fail and the previous config will remain active.

**Example:**
```python
server = create_mcp_server()
# ... later, after editing config file ...
server.reload_config()  # Will raise ConfigError if config is invalid
```

**Troubleshooting:**
- If you see a `ConfigError` on startup or reload, check that all required fields are present and valid in your config file.
- See the engineering spec and PRD for a full list of required fields and their types.

## Telemetry
- The server integrates with OpenTelemetry if enabled in your config file.
- Telemetry is optional and can be disabled by setting `telemetry.enabled: false` in your config.

## Extending the Server
- To add new journal operations, implement async tool functions and register them in `register_tools()` in `src/mcp_commit_story/server.py`.
- Follow the AI function pattern and engineering spec for consistency.

## Journal Operations: Request/Response Types

The MCP server exposes journal operations such as `journal/add-reflection` and `journal/capture-context` via async handler functions. Each handler expects a specific request dict and returns a structured response dict.

**Example: journal/add-reflection**

- **Request:**
  ```python
  {
      "reflection": "Today I learned...",   # Required reflection text (string)
      "date": "2025-05-26"                  # Required ISO date string (YYYY-MM-DD)
  }
  ```
- **Response:**
  ```python
  {
      "status": "success",    # or "error"
      "file_path": "journal/daily/2025-05-26-journal.md",
      "error": None            # Error message if status == "error"
  }
  ```

All errors are returned as a dict with `status: "error"` and an `error` message, never as a raw exception. See the engineering spec for full type details.




## More Information
- See `docs/ai_function_pattern.md` for function design guidelines.
- See the engineering spec and PRD for full requirements.
- For testing standards, see `docs/testing_standards.md`.

## Error Handling

All MCP tool handlers in this project use a standard error handling decorator for robust, structured error responses.

- The `MCPError` class allows tool authors to raise errors with a specific status and message.
- The `handle_mcp_error` decorator wraps all MCP tool functions to catch exceptions, convert them to standardized error responses, collect metrics, and log errors for debugging.

When an operation succeeds, the decorator returns the original function's result. When an operation fails, it returns: `{"status": "error", "error": "error_message"}`

All MCP handlers use this decorator to ensure consistent error formatting across the system.