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

## Telemetry
- The server integrates with OpenTelemetry if enabled in your config file.
- Telemetry is optional and can be disabled by setting `telemetry.enabled: false` in your config.

## Extending the Server
- To add new journal operations, implement async tool functions and register them in `register_tools()` in `src/mcp_commit_story/server.py`.
- Follow the AI function pattern and engineering spec for consistency.

## More Information
- See `docs/ai_function_pattern.md` for function design guidelines.
- See the engineering spec and PRD for full requirements.
- For testing standards, see `docs/testing_standards.md`. 