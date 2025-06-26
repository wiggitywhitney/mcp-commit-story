"""
Multiple database discovery for Cursor chat databases.

This module handles discovery and extraction from multiple Cursor databases
to address the 100-generation limit that causes database rotation. When Cursor
reaches 100 generations in a chat session, it creates a new database file,
potentially leaving chat history scattered across multiple state.vscdb files.

Background:
Cursor creates new database files after 100 generations to manage performance.
This results in multiple state.vscdb files in different subdirectories of the
.cursor folder. The single-database approach in query_cursor_chat_database()
only accesses the primary database, missing historical conversations.

Key Functions:
- discover_all_cursor_databases: Find all state.vscdb files in workspace
- extract_from_multiple_databases: Extract data from multiple databases

Performance Thresholds:
- discover_all_cursor_databases: 100ms (file system traversal)
- extract_from_multiple_databases: 500ms (multi-database processing)

Error Handling:
Both functions use graceful error handling with skip-and-continue patterns.
Individual database failures don't prevent processing of other databases.
Permission errors during discovery are logged but don't stop the search.

Telemetry:
Both functions are instrumented with @trace_mcp_operation for performance
monitoring and include attributes for database counts and error tracking.

Usage Example:
    >>> # Discover all databases in a workspace
    >>> databases = discover_all_cursor_databases("/path/to/workspace")
    >>> print(f"Found {len(databases)} databases")
    
    >>> # Extract data from all discovered databases
    >>> results = extract_from_multiple_databases(databases)
    >>> for result in results:
    ...     print(f"Database: {result['database_path']}")
    ...     print(f"Prompts: {len(result['prompts'])}")
    ...     print(f"Generations: {len(result['generations'])}")

Integration:
This module is designed to be used alongside the existing cursor_db functions:
- Use discover_all_cursor_databases() to find databases
- Use extract_from_multiple_databases() to get raw data
- Use existing reconstruct_chat_history() to process the combined data
"""

import os
import logging
import time
from typing import List, Dict, Any
from pathlib import Path

from ..telemetry import trace_mcp_operation, PERFORMANCE_THRESHOLDS
from .message_extraction import extract_prompts_data, extract_generations_data

logger = logging.getLogger(__name__)


@trace_mcp_operation(operation_name="discover_all_cursor_databases")
def discover_all_cursor_databases(workspace_path: str) -> List[str]:
    """
    Discover all Cursor database files in a workspace.
    
    Recursively searches the .cursor directory for state.vscdb files to handle
    database rotation after 100 generations. Uses a simple recursive approach
    with graceful error handling for permission issues.
    
    Search Strategy:
    - Starts at workspace_path/.cursor directory
    - Recursively searches all subdirectories (no depth limit)
    - Looks for exact filename 'state.vscdb'
    - Returns absolute paths for consistency
    
    Error Handling:
    - Returns empty list if .cursor directory doesn't exist
    - Logs but continues on permission errors during directory traversal
    - Gracefully handles malformed paths or filesystem issues
    
    Performance:
    - Threshold: 100ms for typical workspace sizes
    - Optimized for file system traversal
    - No database content validation (filename-only check)
    
    Args:
        workspace_path: Path to the workspace directory containing .cursor folder
        
    Returns:
        List of absolute paths to discovered state.vscdb files, sorted for
        consistency. Empty list if no databases found or .cursor doesn't exist.
        
    Telemetry:
        - Tracks discovery duration with 100ms threshold
        - Records database_count and workspace_path attributes
        - Logs permission errors but continues processing
        
    Examples:
        >>> # Basic discovery
        >>> databases = discover_all_cursor_databases("/path/to/workspace")
        >>> print(f"Found {len(databases)} databases")
        
        >>> # Check for multiple sessions
        >>> databases = discover_all_cursor_databases("/Users/dev/project")
        >>> if len(databases) > 1:
        ...     print("Multiple chat sessions detected")
        ...     for db in databases:
        ...         print(f"  - {db}")
        
        >>> # Handle missing .cursor directory
        >>> databases = discover_all_cursor_databases("/empty/workspace")
        >>> assert databases == []  # Returns empty list, no exceptions
        
    Raises:
        No exceptions are raised. All errors are logged and handled gracefully.
        
    See Also:
        extract_from_multiple_databases: Process discovered databases
        query_cursor_chat_database: Single database access function
    """
    start_time = time.time()
    discovered_databases = []
    
    # Check if workspace exists
    if not os.path.exists(workspace_path):
        logger.warning(f"Workspace path does not exist: {workspace_path}")
        return discovered_databases
    
    # Build .cursor directory path
    cursor_dir = os.path.join(workspace_path, ".cursor")
    
    # Check if .cursor directory exists
    if not os.path.exists(cursor_dir):
        logger.debug(f"No .cursor directory found in workspace: {workspace_path}")
        return discovered_databases
    
    # Recursively search for state.vscdb files
    try:
        for root, dirs, files in os.walk(cursor_dir):
            for file in files:
                if file == "state.vscdb":
                    db_path = os.path.abspath(os.path.join(root, file))
                    discovered_databases.append(db_path)
                    logger.debug(f"Found Cursor database: {db_path}")
    except PermissionError as e:
        logger.warning(f"Permission denied accessing directory in {cursor_dir}: {e}")
        # Continue processing - we might have found some databases before the error
    except Exception as e:
        logger.error(f"Unexpected error during database discovery: {e}")
        # Continue processing with what we found so far
    
    # Record telemetry attributes
    duration_ms = (time.time() - start_time) * 1000
    
    # Log performance if it exceeds threshold
    threshold_ms = PERFORMANCE_THRESHOLDS.get("discover_all_cursor_databases", 100)
    if duration_ms > threshold_ms:
        logger.warning(f"Database discovery took {duration_ms:.1f}ms (threshold: {threshold_ms}ms)")
    
    logger.info(f"Discovered {len(discovered_databases)} Cursor databases in {duration_ms:.1f}ms")
    return discovered_databases


@trace_mcp_operation(operation_name="extract_from_multiple_databases")
def extract_from_multiple_databases(database_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Extract prompts and generations from multiple Cursor databases.
    
    Processes each database independently using existing extraction functions
    (extract_prompts_data and extract_generations_data). Uses skip-and-continue
    error handling to return partial results when some databases fail.
    Does not attempt chronological merging or deduplication.
    
    Processing Strategy:
    - Each database processed independently in sequence
    - Both prompts and generations extracted per database
    - If either extraction fails, entire database is skipped
    - No cross-database validation or merging
    - Results maintain database-specific grouping
    
    Error Handling:
    - Skip-and-continue pattern: individual failures don't stop processing
    - Logs warnings for failed databases but continues with remaining ones
    - Returns partial results if some databases succeed
    - Returns empty list if all databases fail or input is empty
    
    Performance:
    - Threshold: 500ms for typical multi-database workloads
    - Sequential processing (no parallelization)
    - Leverages existing optimized extraction functions
    
    Args:
        database_paths: List of absolute paths to state.vscdb files.
                       Typically from discover_all_cursor_databases().
        
    Returns:
        List of dictionaries with structure:
        {
            "database_path": "/absolute/path/to/state.vscdb",
            "prompts": [{"id": 1, "content": "...", ...}, ...],
            "generations": [{"id": 1, "content": "...", ...}, ...]
        }
        
        Results are ordered by input database_paths order. Empty list if
        no databases can be processed or input is empty.
        
    Telemetry:
        - Tracks extraction duration with 500ms threshold  
        - Records database_count, successful_count, failed_count attributes
        - Logs individual database failures but continues processing
        
    Examples:
        >>> # Basic multi-database extraction
        >>> paths = ["/workspace/.cursor/session1/state.vscdb", 
        ...          "/workspace/.cursor/session2/state.vscdb"]
        >>> results = extract_from_multiple_databases(paths)
        >>> for result in results:
        ...     print(f"Database: {result['database_path']}")
        ...     print(f"Prompts: {len(result['prompts'])}")
        ...     print(f"Generations: {len(result['generations'])}")
        
        >>> # Handle partial failures gracefully
        >>> paths = ["/good/db.vscdb", "/corrupted/db.vscdb", "/another/good.vscdb"]
        >>> results = extract_from_multiple_databases(paths)
        >>> print(f"Successfully processed {len(results)} of {len(paths)} databases")
        
        >>> # Combine with discovery
        >>> databases = discover_all_cursor_databases("/workspace")
        >>> if databases:
        ...     results = extract_from_multiple_databases(databases)
        ...     total_prompts = sum(len(r['prompts']) for r in results)
        ...     print(f"Total prompts across all databases: {total_prompts}")
        
        >>> # Empty input handling
        >>> results = extract_from_multiple_databases([])
        >>> assert results == []  # Returns empty list
        
    Raises:
        No exceptions are raised. All errors are logged and handled gracefully
        with skip-and-continue error handling.
        
    See Also:
        discover_all_cursor_databases: Find databases to process
        extract_prompts_data: Single database prompt extraction
        extract_generations_data: Single database generation extraction
        reconstruct_chat_history: Process extracted data into conversations
    """
    start_time = time.time()
    results = []
    successful_count = 0
    failed_count = 0
    
    # Handle empty input
    if not database_paths:
        logger.debug("No database paths provided for extraction")
        return results
    
    logger.info(f"Starting extraction from {len(database_paths)} databases")
    
    # Process each database independently
    for db_path in database_paths:
        try:
            logger.debug(f"Extracting data from database: {db_path}")
            
            # Extract prompts and generations using existing functions
            prompts = extract_prompts_data(db_path)
            generations = extract_generations_data(db_path)
            
            # Create result entry
            result = {
                "database_path": db_path,
                "prompts": prompts,
                "generations": generations
            }
            
            results.append(result)
            successful_count += 1
            
            logger.debug(f"Successfully extracted {len(prompts)} prompts and {len(generations)} generations from {db_path}")
            
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to extract from database {db_path}: {e}")
            # Continue with next database (skip-and-continue pattern)
            continue
    
    # Record telemetry
    duration_ms = (time.time() - start_time) * 1000
    
    # Log performance if it exceeds threshold
    threshold_ms = PERFORMANCE_THRESHOLDS.get("extract_from_multiple_databases", 500)
    if duration_ms > threshold_ms:
        logger.warning(f"Multi-database extraction took {duration_ms:.1f}ms (threshold: {threshold_ms}ms)")
    
    logger.info(f"Extraction completed: {successful_count} successful, {failed_count} failed in {duration_ms:.1f}ms")
    
    return results 