"""
MCP Server Initialization for mcp-commit-story

This module provides the entrypoint and core setup logic for the MCP server, including:
- Dynamic version loading from pyproject.toml
- Configuration loading and validation (now with hot reload support)
- Telemetry integration (if available)
- Tool registration stub (to be filled in by other modules)

Intended for use as the main server entrypoint for the mcp-commit-story project.
"""
import inspect
import logging
import sys
import toml
from datetime import datetime
from typing import Callable, Awaitable, Any, Optional, Dict

if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from mcp.server.fastmcp import FastMCP
from mcp_commit_story.config import load_config, Config, ConfigError
from mcp_commit_story import telemetry
from mcp_commit_story.telemetry import trace_mcp_operation, get_mcp_metrics
from mcp_commit_story.journal_init import initialize_journal
from mcp_commit_story.git_utils import install_post_commit_hook
from mcp_commit_story.journal import append_to_journal_file
from mcp_commit_story.reflection_core import add_manual_reflection

# Configure logging
logger = logging.getLogger(__name__)

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
    Decorator that handles MCP operation errors gracefully and provides standardized error responses.
    
    This decorator wraps MCP tool functions to:
    - Catch any exceptions and convert them to appropriate error responses
    - Provide consistent error formatting across all tools
    - Add metrics collection for operation tracking
    - Log errors appropriately for debugging
    
    Returns:
        For successful operations: The original function's return value
        For failed operations: {"status": "error", "error": "error_message"}
    """
    import functools
    import time
    import logging
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        operation_name = func.__name__
        start_time = time.time()
        
        # Get metrics instance if available
        metrics = None
        try:
            metrics = get_mcp_metrics()
        except Exception:
            # Metrics not available, continue without them
            pass
        
        try:
            result = await func(*args, **kwargs)
            
            # Record successful operation metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_tool_call(operation_name, True)
                metrics.record_operation_duration(operation_name, duration)
            
            return result
        
        except MCPError as e:
            # Expected MCP error - convert to standardized response, preserving custom status
            error_response = {"status": e.status, "error": e.message}
            
            # Record failed operation metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_tool_call(operation_name, False, error_type="mcp_error")
                metrics.record_operation_duration(operation_name, duration, success=False)
            
            logging.warning(f"MCP operation {operation_name} failed: {e}")
            return error_response
        
        except Exception as e:
            # Unexpected error - log and convert to standardized response
            error_response = {"status": "error", "error": f"Internal error: {str(e)}"}
            
            # Record failed operation metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_tool_call(operation_name, False, error_type="internal_error")
                metrics.record_operation_duration(operation_name, duration, success=False)
            
            logging.error(f"Unexpected error in MCP operation {operation_name}: {e}")
            return error_response
    
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
    """
    
    @server.tool()
    @trace_mcp_operation("journal_new_entry")
    async def journal_new_entry(request: JournalNewEntryRequest) -> JournalNewEntryResponse:
        """Create a new journal entry with AI-generated content from git, chat, and terminal context."""
        return await handle_journal_new_entry(request)
    
    @server.tool()
    @trace_mcp_operation("journal_add_reflection")
    async def journal_add_reflection(request: AddReflectionRequest) -> AddReflectionResponse:
        """Add a manual reflection to the journal for a specific date."""
        return await handle_journal_add_reflection(request)
    
    @server.tool()
    @trace_mcp_operation("journal_init")
    async def journal_init(request: dict) -> dict:
        """Initialize journal configuration and directory structure."""
        return await handle_journal_init(request)
    
    @server.tool()
    @trace_mcp_operation("journal_install_hook")
    async def journal_install_hook(request: dict) -> dict:
        """Install git post-commit hook for automated journal entries."""
        return await handle_journal_install_hook(request)
    
    @server.tool()
    @trace_mcp_operation("journal_generate_daily_summary")
    async def journal_generate_daily_summary(request: dict) -> dict:
        """Generate a comprehensive daily summary from all journal entries for a specific date."""
        return await handle_generate_daily_summary(request)



def create_mcp_server(config_path: str = None) -> FastMCP:
    """
    Create and configure the MCP server instance for mcp-commit-story.
    - Loads configuration from .mcp-commit-storyrc.yaml (or given path)
    - Integrates telemetry if enabled and available (with graceful degradation)
    - Registers all journal tools (stub)
    - Returns a FastMCP server instance ready to run
    Raises ConfigError or other exceptions on startup failure.
    """
    app_name = "mcp-commit-story"
    version = get_version_from_pyproject()
    
    # Load config first
    try:
        config = load_config(config_path)
        logging.info(f"Configuration loaded successfully. Telemetry enabled: {config.telemetry_enabled}")
    except ConfigError as ce:
        logging.error(f"Configuration error during startup: {ce}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        raise
    
    # Early telemetry integration with graceful error handling
    telemetry_initialized = False
    try:
        # Only call telemetry.setup_telemetry if it exists
        setup_telemetry = getattr(telemetry, "setup_telemetry", None)
        if callable(setup_telemetry):
            telemetry_initialized = setup_telemetry(config.as_dict())
            if telemetry_initialized:
                logging.info("Telemetry system initialized successfully")
            else:
                logging.info("Telemetry disabled via configuration")
        else:
            logging.warning("Telemetry setup function not available")
    except Exception as e:
        logging.warning(f"Telemetry setup failed, continuing without telemetry: {e}")
        telemetry_initialized = False
    
    # Create server instance
    try:
        server = FastMCP(app_name, version=version)
        register_tools(server)
        
        # Attach config and telemetry status to server for runtime use
        server.config = config
        server.telemetry_initialized = telemetry_initialized
        
        def reload_config():
            config.reload_config()
            logging.info("Config hot reloaded successfully.")
        server.reload_config = reload_config
        
        logging.info("MCP server startup complete.")
        return server
        
    except Exception as e:
        logging.error(f"Error creating MCP server: {e}")
        # If telemetry was initialized, try to shut it down
        if telemetry_initialized:
            try:
                shutdown_telemetry = getattr(telemetry, "shutdown_telemetry", None)
                if callable(shutdown_telemetry):
                    shutdown_telemetry()
            except Exception as shutdown_error:
                logging.warning(f"Error shutting down telemetry during server creation failure: {shutdown_error}")
        raise

async def generate_journal_entry(request: JournalNewEntryRequest) -> JournalNewEntryResponse:
    """
    ⚠️  CRITICAL: SLOW DOWN AND READ CAREFULLY ⚠️
    
    PURPOSE: Generate thoughtful, rich journal entries that capture the complete story 
    of development work - including technical decisions, problem-solving journeys, 
    emotions, and authentic developer experience.
    
    DO NOT SKIM ANYWHERE ALONG THE WAY! Each prompt contains detailed guidelines 
    for extracting meaningful content. Rushing or skipping details results in 
    shallow entries that miss the rich context that makes journal entries valuable.
    
    CONTEXT COLLECTION PHASE:
    AI Agent - First, collect all necessary context by executing these functions:
    
    1. collect_chat_history() in context_collection.py
       - Read the full docstring and execute the AI prompt
       - Extract technical discussions, debugging sessions, decisions
       - Focus on content explaining how commits came about
    
    2. collect_ai_terminal_commands() in context_collection.py  
       - Read the full docstring and execute the AI prompt
       - Extract development workflow commands, both successful and failed
       - Include command sequences that tell a development story
    
    3. collect_git_context() - this is already collected in request.git
       - Use the provided git context directly
    
    CONTENT GENERATION PHASE:
    Execute each section generator with the collected context:
    
    4. generate_summary_section() in journal.py
       - Creates narrative summary of what changed and why
       - Returns: {"summary": "string content"}
    
    5. generate_technical_synopsis_section() in journal.py
       - Provides code-focused analysis of implementation details
       - Returns: {"technical_synopsis": "string content"}
    
    6. generate_accomplishments_section() in journal.py
       - Lists specific achievements and completed work
       - Returns: {"accomplishments": ["achievement1", "achievement2"]}
    
    7. generate_frustrations_section() in journal.py
       - Documents obstacles, challenges, and lessons learned
       - Returns: {"frustrations": ["frustration1", "frustration2"]}
    
    8. generate_tone_mood_section() in journal.py
       - Analyzes emotional context and developer state
       - Returns: {"mood": "mood description", "indicators": "supporting evidence"}
    
    9. generate_discussion_notes_section() in journal.py
       - Extracts key conversation excerpts with speaker attribution
       - Returns: {"discussion_notes": [str_or_dict_entries]}
    
    10. generate_terminal_commands_section() in journal.py
        - Lists relevant commands executed during development
        - Returns: {"terminal_commands": ["command1", "command2"]}
    
    11. generate_commit_metadata_section() in journal.py
        - Provides commit statistics and technical metadata
        - Returns: {"commit_metadata": {"key": "value", ...}}
    
    ASSEMBLY AND SAVE PHASE:
    After executing all generators, assemble and save:
    
    ```python
    from mcp_commit_story.journal import JournalEntry, get_journal_file_path, append_to_journal_file
    from datetime import datetime
    
    # Use proper cross-platform timestamp format - EXTRACT FROM COMMIT DATE
    commit_date_str = request["git"]["metadata"]["date"]  # e.g. "2025-06-04T14:21:24-05:00"
    commit_datetime = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
    timestamp = commit_datetime.strftime("%I:%M %p").lstrip('0')  # e.g., "2:21 PM"
    
    # Extract git metadata
    git_metadata = request["git"]["metadata"]
    commit_hash = git_metadata["hash"]
    
    # Create journal entry with all generated content
    entry = JournalEntry(
        timestamp=timestamp,
        commit_hash=commit_hash,
        summary=summary_result.get("summary"),
        technical_synopsis=technical_synopsis_result.get("technical_synopsis"), 
        accomplishments=accomplishments_result.get("accomplishments", []),
        frustrations=frustrations_result.get("frustrations", []),
        tone_mood=tone_mood_result if tone_mood_result.get("mood") else None,
        discussion_notes=discussion_notes_result.get("discussion_notes", []),
        terminal_commands=terminal_commands_result.get("terminal_commands", []),
        commit_metadata=commit_metadata_result.get("commit_metadata", {})
    )
    
    # Save using established file path system
    date_str = commit_datetime.strftime("%Y-%m-%d")  # Use commit date, not current date
    file_path = get_journal_file_path(date_str, "daily")
    append_to_journal_file(entry.to_markdown(), file_path)
    
    return {
        "status": "success", 
        "file_path": file_path, 
        "error": None
    }
    ```
    
    QUALITY REQUIREMENTS:
    - Follow all anti-hallucination rules in each prompt
    - Extract verbatim quotes for discussion notes - do not paraphrase
    - Only include content with explicit evidence from context
    - Complete all checklists at the end of each prompt
    - Ensure rich, thoughtful content that captures the development story
    
    ERROR HANDLING:
    If any step fails, still attempt to create an entry with available content.
    Empty sections are better than no entry at all.
    """
    
    try:
        from .journal import (
            JournalEntry, get_journal_file_path, append_to_journal_file,
            generate_summary_section, generate_technical_synopsis_section,
            generate_accomplishments_section, generate_frustrations_section,
            generate_tone_mood_section, generate_discussion_notes_section,
            generate_terminal_commands_section, generate_commit_metadata_section
        )
        from .context_types import JournalContext
        
        # Build JournalContext from request data
        journal_context = JournalContext(
            chat=request.get("chat"),
            terminal=request.get("terminal"),
            git=request["git"]
        )
        
        # Generate all sections using the AI functions (now with stub implementations)
        summary_result = generate_summary_section(journal_context)
        technical_synopsis_result = generate_technical_synopsis_section(journal_context)
        accomplishments_result = generate_accomplishments_section(journal_context)
        frustrations_result = generate_frustrations_section(journal_context)
        tone_mood_result = generate_tone_mood_section(journal_context)
        discussion_notes_result = generate_discussion_notes_section(journal_context)
        terminal_commands_result = generate_terminal_commands_section(journal_context)
        commit_metadata_result = generate_commit_metadata_section(journal_context)
        
        # Extract git metadata and create timestamp
        git_metadata = request["git"]["metadata"]
        commit_hash = git_metadata["hash"]
        commit_date_str = git_metadata["date"]
        
        # Handle different date formats
        try:
            if commit_date_str.endswith('Z'):
                commit_datetime = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
            else:
                commit_datetime = datetime.fromisoformat(commit_date_str)
        except ValueError:
            # Fallback to current time if date parsing fails
            commit_datetime = datetime.now()
        
        timestamp = commit_datetime.strftime("%I:%M %p").lstrip('0')
        
        # Create journal entry with all generated content
        entry = JournalEntry(
            timestamp=timestamp,
            commit_hash=commit_hash,
            summary=summary_result.get("summary"),
            technical_synopsis=technical_synopsis_result.get("technical_synopsis"), 
            accomplishments=accomplishments_result.get("accomplishments", []),
            frustrations=frustrations_result.get("frustrations", []),
            tone_mood=tone_mood_result if tone_mood_result.get("mood") else None,
            discussion_notes=discussion_notes_result.get("discussion_notes", []),
            terminal_commands=terminal_commands_result.get("terminal_commands", []),
            commit_metadata=commit_metadata_result.get("commit_metadata", {})
        )
        
        # Save using established file path system
        date_str = commit_datetime.strftime("%Y-%m-%d")
        file_path = get_journal_file_path(date_str, "daily")
        append_to_journal_file(entry.to_markdown(), file_path)
        
        return {
            "status": "success", 
            "file_path": file_path, 
            "error": None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "file_path": "",
            "error": f"Failed to generate journal entry: {str(e)}"
        }

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

@handle_mcp_error
@trace_mcp_operation("reflection.handle_add_reflection", attributes={
    "operation_type": "mcp_handler",
    "content_type": "reflection"
})
async def handle_journal_add_reflection(request: AddReflectionRequest) -> AddReflectionResponse:
    """
    MCP operation: Add a manual reflection to the journal for a given date.
    
    This handler provides comprehensive error handling, telemetry instrumentation,
    and integrates with the reflection_core module for consistent behavior.
    
    Args:
        request: Must contain 'reflection' (or 'text') and 'date' (YYYY-MM-DD)
    Returns:
        AddReflectionResponse: {"status": "success", "file_path": ...} or error dict
    """
    import time
    from opentelemetry import trace
    
    start_time = time.time()
    
    # Add span attributes for MCP operation telemetry
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("mcp.operation", "add_reflection")
        current_span.set_attribute("mcp.handler", "handle_journal_add_reflection")
    
    # Extract and validate request fields (support both field names)
    text = request.get("text") or request.get("reflection")
    date = request.get("date")
    
    if not text:
        raise MCPError("Missing required field: reflection/text")
    
    if not date:
        raise MCPError("Missing required field: date")
    
    # Add content attributes to span
    if current_span:
        current_span.set_attribute("reflection.date", date)
        current_span.set_attribute("reflection.content_length", len(text))
    
    # Call the reflection core function - it handles all telemetry internally
    result = add_manual_reflection(text, date)
    
    # Record success metrics for MCP handler layer
    duration = time.time() - start_time
    metrics = get_mcp_metrics()
    if metrics:
        metrics.record_counter(
            'mcp.handler.operations_total',
            operation='add_reflection',
            handler='handle_journal_add_reflection',
            status='success'
        )
        metrics.record_operation_duration(
            'mcp.handler.duration_seconds',
            duration,
            operation='add_reflection',
            handler='handle_journal_add_reflection'
        )
    
    # Convert result to proper response format
    if result["status"] == "success":
        return {
            "status": "success",
            "file_path": result["file_path"],
            "error": None
        }
    else:
        # This shouldn't happen due to @handle_mcp_error, but just in case
        raise MCPError(result.get("error", "Unknown error occurred"))

@handle_mcp_error
async def handle_journal_init(request: dict) -> dict:
    """
    Handle the MCP operation 'journal/init'.
    Expects a request with optional 'repo_path', 'config_path', and 'journal_path'.
    Calls initialize_journal() and returns a structured response.
    Response format:
        {
            "status": "success" | "error",
            "paths": dict (if success),
            "message": str (if success),
            "error": str (if error)
        }
    """
    repo_path = request.get("repo_path")
    config_path = request.get("config_path")
    journal_path = request.get("journal_path")
    # Support both sync and async initialize_journal
    if inspect.iscoroutinefunction(initialize_journal):
        result = await initialize_journal(repo_path=repo_path, config_path=config_path, journal_path=journal_path)
    else:
        result = initialize_journal(repo_path=repo_path, config_path=config_path, journal_path=journal_path)
    if result.get("status") != "success":
        raise MCPError(result.get("message", "Journal initialization failed"))
    return {
        "status": "success",
        "paths": result.get("paths", {}),
        "message": result.get("message", "Journal initialized successfully")
    }

@handle_mcp_error
async def handle_journal_install_hook(request: dict) -> dict:
    """
    Handle the MCP operation 'journal/install-hook'.
    Expects a request with optional 'repo_path'.
    Calls install_post_commit_hook() and returns a structured response.
    Response format:
        {
            "status": "success" | "error",
            "message": str,
            "backup_path": str or None,
            "hook_path": str or None (if available),
            "error": str (if error)
        }
    """
    repo_path = request.get("repo_path")
    if inspect.iscoroutinefunction(install_post_commit_hook):
        result = await install_post_commit_hook(repo_path=repo_path)
    else:
        result = install_post_commit_hook(repo_path=repo_path)
    if isinstance(result, dict):
        response = {
            "status": result.get("status", "success"),
            "message": result.get("message", "Post-commit hook installed successfully."),
            "backup_path": result.get("backup_path"),
        }
        if "hook_path" in result:
            response["hook_path"] = result["hook_path"]
        return response
    else:
        return {
            "status": "success",
            "message": "Post-commit hook installed successfully.",
            "backup_path": result
        }

# Create alias for test compatibility
handle_add_reflection = handle_journal_add_reflection


# =============================================================================
# Daily Summary MCP Handler (Subtask 27.2)
# =============================================================================

@handle_mcp_error
@trace_mcp_operation("daily_summary.handle_generate", attributes={
    "operation_type": "mcp_handler",
    "content_type": "daily_summary"
})
async def handle_generate_daily_summary(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle the MCP operation 'journal/generate-daily-summary'.
    
    Generates a comprehensive daily summary from all journal entries for a specific date,
    using AI to synthesize the content into a cohesive narrative.
    
    Args:
        request: Must contain 'date' in YYYY-MM-DD format
        
    Returns:
        GenerateDailySummaryResponse with status, file_path, content, and error fields
    """
    import time
    from opentelemetry import trace
    from mcp_commit_story.config import load_config
    from mcp_commit_story.daily_summary import generate_daily_summary_mcp_tool
    
    start_time = time.time()
    
    # Add span attributes for telemetry
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("mcp.operation", "generate_daily_summary")
        current_span.set_attribute("mcp.handler", "handle_generate_daily_summary")
    
    # Validate required fields
    if "date" not in request:
        raise MCPError("Missing required field: date")
    
    date_str = request["date"]
    
    # Validate date format
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise MCPError("Invalid date format. Expected YYYY-MM-DD")
    
    if current_span:
        current_span.set_attribute("daily_summary.date", date_str)
    
    try:
        # Call the daily summary MCP tool function directly
        response = generate_daily_summary_mcp_tool({"date": date_str})
        
        # Record success metrics
        duration = time.time() - start_time
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_counter(
                'mcp.handler.operations_total',
                operation='generate_daily_summary',
                handler='handle_generate_daily_summary',
                status='success'
            )
            metrics.record_operation_duration(
                'mcp.handler.duration_seconds',
                duration,
                operation='generate_daily_summary',
                handler='handle_generate_daily_summary'
            )
        
        if current_span and response.get("file_path"):
            current_span.set_attribute("daily_summary.file_path", response["file_path"])
            if response.get("content"):
                current_span.set_attribute("daily_summary.output_length", len(response["content"]))
        
        return response
        
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error generating daily summary for {date_str}: {e}")
        
        # Record error metrics
        duration = time.time() - start_time
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_counter(
                'mcp.handler.operations_total',
                operation='generate_daily_summary',
                handler='handle_generate_daily_summary',
                status='error'
            )
            metrics.record_operation_duration(
                'mcp.handler.duration_seconds',
                duration,
                operation='generate_daily_summary',
                handler='handle_generate_daily_summary',
                success=False
            )
        
        if current_span:
            current_span.set_attribute("error.category", "generation_failed")
        
        # Re-raise as MCPError to be handled by @handle_mcp_error decorator
        raise MCPError(f"Failed to generate daily summary: {str(e)}")
