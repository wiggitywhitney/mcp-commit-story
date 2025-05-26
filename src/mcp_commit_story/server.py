"""
MCP Server Initialization for mcp-commit-story

This module provides the entrypoint and core setup logic for the MCP server, including:
- Dynamic version loading from pyproject.toml
- Configuration loading and validation
- Telemetry integration (if available)
- Tool registration stub (to be filled in by other modules)

Intended for use as the main server entrypoint for the mcp-commit-story project.
"""
import os
import logging
from typing import Callable, Awaitable, Any
from mcp.server.fastmcp import FastMCP, Context
from mcp_commit_story.config import load_config, Config, ConfigError
from mcp_commit_story import telemetry
import toml

# Type alias for an async tool handler
ToolHandler = Callable[..., Awaitable[Any]]

# MCP server instance (to be initialized in main)
mcp: FastMCP | None = None

def get_version_from_pyproject(pyproject_path: str = "pyproject.toml") -> str:
    """
    Read the project version from pyproject.toml.
    Returns '0.0.0' if the file is missing or malformed.
    """
    try:
        data = toml.load(pyproject_path)
        return data["project"]["version"]
    except Exception as e:
        logging.error(f"Failed to read version from {pyproject_path}: {e}")
        return "0.0.0"

def register_tools(server: FastMCP) -> None:
    """
    Register all journal tools with the MCP server.
    This is a stub; actual tool registration should be implemented in other modules.
    """
    # Example:
    # @server.tool()
    # async def journal_new_entry(...): ...
    pass

def create_mcp_server() -> FastMCP:
    """
    Create and configure the MCP server instance for mcp-commit-story.
    - Loads configuration from .mcp-commit-storyrc.yaml
    - Integrates telemetry if enabled and available
    - Registers all journal tools (stub)
    - Returns a FastMCP server instance ready to run
    Raises ConfigError or other exceptions on startup failure.
    """
    app_name = "mcp-commit-story"
    version = get_version_from_pyproject()
    # Load config and setup telemetry before server instantiation
    try:
        config = load_config()
        # Only call telemetry.setup_telemetry if it exists
        setup_telemetry = getattr(telemetry, "setup_telemetry", None)
        if callable(setup_telemetry) and config.telemetry_enabled:
            setup_telemetry(config)
        logging.info("MCP server startup complete.")
    except ConfigError as ce:
        logging.error(f"Configuration error during startup: {ce}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during startup: {e}")
        raise
    server = FastMCP(app_name, version=version)
    register_tools(server)
    return server
