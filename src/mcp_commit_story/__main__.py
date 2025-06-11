#!/usr/bin/env python3
"""MCP Commit Story Server Entry Point.

This module serves as the entry point for the MCP server when invoked via:
`python -m mcp_commit_story`

It initializes the MCP server with stdio transport, loads configuration,
and provides proper error handling and telemetry.

The server uses the existing FastMCP architecture from server.py and provides
comprehensive telemetry, logging, and graceful shutdown handling.
"""

import sys
import logging
import traceback
import signal
import os
from typing import Optional, Dict, Any, Union

from mcp_commit_story.config import load_config, ConfigError, Config
from mcp_commit_story.telemetry import get_mcp_metrics, setup_telemetry, shutdown_telemetry
from mcp_commit_story.server import create_mcp_server

# Configure module-level logging
logger = logging.getLogger(__name__)

# Global server instance for graceful shutdown
_server_instance: Optional[Any] = None


def validate_server_config(config_path: Optional[str] = None) -> Union[Config, bool]:
    """
    Validate server configuration with comprehensive error reporting.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Config object if validation succeeds, False if validation fails
        
    Raises:
        ConfigError: If configuration is invalid
        Exception: For other configuration loading errors
    """
    try:
        config = load_config(config_path)
        logger.info(f"Configuration validated successfully. Telemetry enabled: {config.telemetry_enabled}")
        return config
    except ConfigError as e:
        logger.error(f"Configuration validation failed: {e}")
        logger.error("Please check your .mcp-commit-storyrc.yaml file for errors")
        return False
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Run 'mcp-commit-story init' to create a default configuration")
        return False
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        logger.debug(f"Configuration error details: {traceback.format_exc()}")
        return False


def setup_server_telemetry(config: Union[Config, Dict[str, Any]]) -> bool:
    """
    Set up telemetry with fail-fast approach on critical errors.
    
    Args:
        config: Server configuration (Config object or dictionary)
        
    Returns:
        bool: True if telemetry was enabled and configured successfully
        
    Raises:
        Exception: If telemetry setup fails and is required
    """
    try:
        config_dict = config.as_dict() if hasattr(config, 'as_dict') else config
        telemetry_enabled = setup_telemetry(config_dict)
        if telemetry_enabled:
            logger.info("Telemetry system initialized successfully")
        else:
            logger.info("Telemetry disabled via configuration")
        return telemetry_enabled
    except Exception as e:
        # Fail-fast approach: if telemetry setup fails, abort server startup
        logger.error(f"Critical telemetry setup failure: {e}")
        logger.error("Server startup aborted due to telemetry initialization failure")
        logger.debug(f"Telemetry error details: {traceback.format_exc()}")
        raise


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, initiating graceful shutdown")
        
        # Record telemetry if available
        try:
            metrics = get_mcp_metrics()
            if metrics:
                metrics.record_counter("server_signal_shutdown", 1, attributes={"signal": signal_name})
        except Exception:
            # Don't let telemetry errors prevent shutdown
            pass
        
        # Attempt graceful server shutdown
        global _server_instance
        if _server_instance and hasattr(_server_instance, 'shutdown'):
            try:
                _server_instance.shutdown()
            except Exception as e:
                logger.warning(f"Error during server shutdown: {e}")
        
        # Clean up telemetry
        try:
            shutdown_telemetry()
        except Exception as e:
            logger.warning(f"Error during telemetry shutdown: {e}")
        
        # Exit with appropriate signal-based exit code
        exit_code = 128 + signum  # Standard Unix convention
        logger.info(f"Exiting with code {exit_code} due to signal {signal_name}")
        sys.exit(exit_code)
    
    # Register handlers for common shutdown signals
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination request
    
    # Register SIGHUP for config reload if available
    if hasattr(signal, 'SIGHUP'):
        def reload_handler(signum, frame):
            logger.info("Received SIGHUP, reloading configuration")
            try:
                global _server_instance
                if _server_instance and hasattr(_server_instance, 'reload_config'):
                    _server_instance.reload_config()
                    logger.info("Configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Error reloading configuration: {e}")
        
        signal.signal(signal.SIGHUP, reload_handler)


def main() -> int:
    """
    Initialize and run the MCP server with stdio transport.
    
    Returns:
        int: Exit code following Unix conventions:
             0   = Success
             1   = General error
             2   = Misuse of shell command
             130 = Script terminated by Control-C (SIGINT)
             143 = Script terminated by SIGTERM
    """
    global _server_instance
    
    # Initialize variables for proper cleanup in finally block
    metrics = None
    telemetry_initialized = False
    
    # Get metrics instance early for comprehensive telemetry
    try:
        # First attempt to get metrics - this may fail if telemetry isn't initialized yet
        metrics = get_mcp_metrics()
    except Exception:
        # Metrics not available yet, will try again after telemetry setup
        pass
    
    if metrics:
        metrics.record_counter("server_start_attempt", 1)
    
    try:
        # Setup basic logging first
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.info("Starting MCP Commit Story server")
        
        # Set up signal handlers early
        setup_signal_handlers()
        
        # Load and validate configuration
        config = validate_server_config()
        if config is False:
            # Configuration validation failed
            if metrics:
                metrics.record_counter("server_config_error", 1)
            logger.error("Configuration validation failed")
            return 2  # Misuse of shell command
        
        logger.debug(f"Loaded configuration with telemetry_enabled={getattr(config, 'telemetry_enabled', 'unknown')}")
        
        # Setup telemetry with fail-fast approach
        telemetry_initialized = setup_server_telemetry(config)
        
        # Get metrics instance after telemetry setup
        if not metrics:
            try:
                metrics = get_mcp_metrics()
            except Exception as e:
                logger.warning(f"Could not obtain metrics instance: {e}")
        
        # Create and configure server using existing FastMCP architecture
        logger.info("Creating MCP server instance")
        server = create_mcp_server()
        _server_instance = server
        
        # Record successful startup
        if metrics:
            metrics.record_counter("server_started", 1)
            metrics.record_counter("server_config_loaded", 1, attributes={"telemetry_enabled": str(telemetry_initialized)})
        
        logger.info("MCP server initialized successfully, starting main loop")
        logger.info("Server ready to accept stdio transport connections")
        
        # Run the server - this will block until the server exits
        # FastMCP handles stdio transport internally
        exit_code = 0  # Default success code
        
        # Check if server has a run method, otherwise it may auto-run
        if hasattr(server, 'run'):
            exit_code = server.run()
        else:
            # Some FastMCP implementations may auto-start
            logger.info("Server running in auto-start mode")
            # Keep the process alive
            import time
            while True:
                time.sleep(1)
        
        # Clean shutdown
        if metrics:
            metrics.record_counter("server_shutdown", 1)
        logger.info(f"MCP server shutdown completed with exit code {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        if metrics:
            metrics.record_counter("server_keyboard_interrupt", 1)
        logger.info("MCP server interrupted by user")
        return 130  # Standard exit code for SIGINT
        
    except ConfigError as e:
        # Configuration-specific errors
        if metrics:
            metrics.record_counter("server_config_error", 1)
        logger.error(f"Configuration error: {e}")
        logger.error("Fix configuration issues and try again")
        return 2  # Misuse of shell command
        
    except Exception as e:
        # General server startup or runtime errors
        if metrics:
            metrics.record_counter("server_startup_error", 1)
        logger.error(f"Critical error starting MCP server: {e}")
        logger.debug(f"Detailed error information: {traceback.format_exc()}")
        return 1  # General error
        
    finally:
        # Ensure cleanup always happens
        try:
            if telemetry_initialized:
                shutdown_telemetry()
                logger.debug("Telemetry shutdown completed")
        except Exception as e:
            logger.warning(f"Error during final telemetry cleanup: {e}")


if __name__ == "__main__":
    sys.exit(main()) 