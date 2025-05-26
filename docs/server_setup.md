# MCP Server Setup & Configuration

This guide explains how to set up and configure the MCP server for the `mcp-commit-story` project.

## What is the MCP Server?
The MCP server is a Python service that exposes journal operations (such as `journal/new-entry`, `journal/summarize`, etc.) for engineering teams. It integrates with Git, collects commit and context data, and generates structured journal entries for retrospectives, storytelling, and analysis.

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
Run the server using your preferred Python environment:
```sh
python -m mcp_commit_story.server
```
Or, if you have a CLI entry point:
```sh
mcp-commit-story-server
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

The MCP server exposes journal operations such as `journal/new-entry` via async handler functions. Each handler expects a specific request dict and returns a structured response dict.

**Example: journal/new-entry**

- **Request:**
  ```python
  {
      "git": { ... },           # Required git context (see engineering spec)
      "chat": { ... },          # Optional chat context
      "terminal": { ... }       # Optional terminal context
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

## Journal Operations: journal/add-reflection

The MCP server exposes the `journal/add-reflection` operation for adding a manual reflection to a specific day's journal file.

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
- The `handle_mcp_error` decorator ensures that both custom and generic exceptions are caught and returned as a status+message dict, never as a raw exception.
- This makes the server safer and more predictable for all clients. 