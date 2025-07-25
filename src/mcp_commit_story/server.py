"""
MCP Server Initialization for mcp-commit-story

This module provides the entrypoint and core setup logic for the MCP server, including:
- Dynamic version loading from pyproject.toml
- Configuration loading and validation (now with hot reload support)
- Telemetry integration (if available)
- Essential MCP tool registration (journal_add_reflection, journal_capture_context)

Provides two core MCP tools:
- journal_add_reflection: Add manual reflections to journal entries
- journal_capture_context: Capture AI context for future journal entries

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
from mcp_commit_story.reflection_core import add_manual_reflection
from mcp_commit_story.journal_handlers import handle_journal_capture_context

# Configure logging
logger = logging.getLogger(__name__)

# Type alias for an async tool handler
ToolHandler = Callable[..., Awaitable[Any]]

# MCP server instance (to be initialized in main)
mcp: FastMCP | None = None

# Request/response types for journal/add-reflection
class AddReflectionRequest(TypedDict):
    reflection: str
    date: str  # ISO date string (YYYY-MM-DD)

class AddReflectionResponse(TypedDict):
    status: str
    file_path: str
    error: Optional[str]

# Request/response types for journal/capture-context
class CaptureContextRequest(TypedDict):
    text: Optional[str]  # AI-generated project context to capture (None triggers full dump)

class CaptureContextResponse(TypedDict):
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
    - Detect common validation errors (dict_type, Pydantic) and provide helpful guidance
    
    Enhanced error handling:
    - Recognizes FastMCP/Pydantic validation errors by error message patterns
    - Converts validation errors to user-friendly "bad-request" responses
    - Includes example correct formats in error messages
    
    Returns:
        For successful operations: The original function's return value
        For failed operations: {"status": "error", "error": "error_message"} or {"status": "bad-request", "error": "helpful_guidance"}
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
            # Check for common validation errors and provide helpful guidance
            error_msg = str(e)
            if "dict_type" in error_msg or "Input should be a valid dictionary" in error_msg:
                # This is likely a validation error from FastMCP or Pydantic
                error_response = {
                    "status": "bad-request", 
                    "error": f"Invalid input format. Expected a dictionary, got {type(e).__name__}. "
                            f"Example correct format: {{'text': 'your context here'}} or {{'text': None}} for AI dump. "
                            f"Original error: {error_msg}"
                }
                error_type = "validation_error"
            else:
                # Unexpected error - log and convert to standardized response
                error_response = {"status": "error", "error": f"Internal error: {error_msg}"}
                error_type = "internal_error"
            
            # Record failed operation metrics
            if metrics:
                duration = time.time() - start_time
                metrics.record_tool_call(operation_name, False, error_type=error_type)
                metrics.record_operation_duration(operation_name, duration, success=False)
            
            logging.error(f"Error in MCP operation {operation_name}: {e}")
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
    Register essential journal tools with the MCP server.
    
    This server provides two core MCP tools:
    - journal_add_reflection: Add manual reflections to journal entries
    - journal_capture_context: Capture AI context for future journal entries
    """
    
    @server.tool()
    @trace_mcp_operation("journal_add_reflection")
    async def journal_add_reflection(request: AddReflectionRequest) -> AddReflectionResponse:
        """Add a manual reflection to the journal for a specific date."""
        return await handle_journal_add_reflection(request)
    
    @server.tool()
    @trace_mcp_operation("journal_capture_context")
    async def journal_capture_context(request: CaptureContextRequest) -> CaptureContextResponse:
        """Capture AI's current project context to provide context for future journal entries."""
        return await handle_journal_capture_context_mcp(request)



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
@trace_mcp_operation("capture_context.handle_mcp", attributes={
    "operation_type": "mcp_handler", 
    "content_type": "ai_context"
})
async def handle_journal_capture_context_mcp(request: CaptureContextRequest) -> CaptureContextResponse:
    """MCP handler for capturing AI context - lightweight delegation to implementation.
    
    Provides enhanced error handling for common input validation issues:
    - Catches dict_type validation errors from FastMCP/Pydantic
    - Provides helpful error messages with example correct formats
    - Maintains backward compatibility with missing 'text' fields
    
    Args:
        request: CaptureContextRequest with optional 'text' field
            - {'text': 'your context here'} - captures specific text
            - {'text': None} - triggers AI context dump
            - {} - defaults to None, triggers AI context dump
            
    Returns:
        CaptureContextResponse with status, file_path, and optional error
        
    Raises:
        MCPError: For invalid input formats with helpful guidance
    """
    # Note: text can be None to trigger a full context dump
    
    # Validate request structure and provide helpful error messages
    if not isinstance(request, dict):
        raise MCPError(
            f"Invalid request format. Expected a dictionary, got {type(request).__name__}. "
            f"Example correct format: {{'text': 'your context here'}} or {{'text': None}} for AI dump",
            status="bad-request"
        )
    
    # Note: 'text' field is optional - if missing, defaults to None which triggers AI dump
    # This maintains backward compatibility and allows for flexible usage
    
    # Call the actual implementation (sync function)
    result = handle_journal_capture_context(request.get("text"))
    
    return {
        "status": result["status"],
        "file_path": result.get("file_path", ""),
        "error": result.get("error")
    }



# Create alias for test compatibility
handle_add_reflection = handle_journal_add_reflection



