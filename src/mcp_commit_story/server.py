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
from typing import Callable, Awaitable, Any, TypedDict, Optional, Dict
from mcp.server.fastmcp import FastMCP, Context
from mcp_commit_story.config import load_config, Config, ConfigError
from mcp_commit_story import telemetry
import toml

# Type alias for an async tool handler
ToolHandler = Callable[..., Awaitable[Any]]

# MCP server instance (to be initialized in main)
mcp: FastMCP | None = None

# Request/response types for journal/new-entry
class JournalNewEntryRequest(TypedDict):
    git: Dict[str, Any]  # Should match GitContext from context_types
    chat: Optional[Any]  # Optional chat context
    terminal: Optional[Any]  # Optional terminal context

class JournalNewEntryResponse(TypedDict):
    status: str
    file_path: str
    error: Optional[str]

# Request/response types for journal/add-reflection
class AddReflectionRequest(TypedDict):
    reflection: str
    date: str  # ISO date string (YYYY-MM-DD)

class AddReflectionResponse(TypedDict):
    status: str
    file_path: str
    error: Optional[str]

class MCPError(Exception):
    """
    Base class for MCP server errors.

    Usage:
        Raise MCPError in a tool handler to return a structured error response to the client.
        Example:
            raise MCPError("Invalid input", status="bad-request")
    The error will be caught by the handle_mcp_error decorator and returned as a dict:
        {"status": "bad-request", "error": "Invalid input"}
    """
    def __init__(self, message: str, status: str = "error"):
        self.message = message
        self.status = status
        super().__init__(message)

def handle_mcp_error(func):
    """
    Decorator for handling MCP errors in async tool handlers.

    Usage:
        @handle_mcp_error
        async def my_tool(...):
            ...
            raise MCPError("Something went wrong")

    - Catches MCPError and returns a structured error response
    - Catches generic exceptions and returns a generic error response
    - Preserves async/await compatibility
    - Ensures all errors are returned as dicts, not raw exceptions
    """
    import functools
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            return {"status": e.status, "error": e.message}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return wrapper

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

async def generate_journal_entry(request: JournalNewEntryRequest) -> JournalNewEntryResponse:
    """
    Stub for journal entry generation logic. Returns a dummy success response.
    """
    return {"status": "success", "file_path": "journal/daily/2025-05-26-journal.md", "error": None}

@handle_mcp_error
async def handle_journal_new_entry(request: JournalNewEntryRequest) -> JournalNewEntryResponse:
    """
    Handle the MCP operation 'journal/new-entry'.
    Expects a request with git context (and optionally chat/terminal context).
    Returns a response with status and file_path, or error if failed.
    """
    if "git" not in request:
        raise MCPError("Missing required field: git")
    return await generate_journal_entry(request)

async def add_reflection_to_journal(request: AddReflectionRequest) -> AddReflectionResponse:
    """
    Stub for adding a reflection to the journal. Returns a dummy success response.
    """
    return {"status": "success", "file_path": "journal/daily/2025-05-26-journal.md", "error": None}

@handle_mcp_error
async def handle_journal_add_reflection(request: AddReflectionRequest) -> AddReflectionResponse:
    """
    Handle the MCP operation 'journal/add-reflection'.
    Expects a request with 'reflection' (str) and 'date' (ISO string).
    Returns a response with status and file_path, or error if failed.
    """
    if "reflection" not in request:
        return {"status": "error", "file_path": "", "error": "Missing required field: reflection"}
    if "date" not in request:
        return {"status": "error", "file_path": "", "error": "Missing required field: date"}
    return await add_reflection_to_journal(request)
