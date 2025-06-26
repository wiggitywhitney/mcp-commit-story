"""
Core query execution module for cursor database operations.

Provides the fundamental database query execution functionality with proper
connection management, error handling, parameterized queries, and timeout handling.

Telemetry Instrumentation:
- Tracks query execution duration against 50ms performance threshold
- Records database path and query timing metrics  
- Categorizes errors (database access vs SQL syntax issues)
- 50ms threshold chosen as baseline for simple SQLite SELECT operations
- No sampling applied - all operations tracked for local database access patterns
"""

import sqlite3
import contextlib
import time
from typing import List, Tuple, Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .exceptions import (
    CursorDatabaseQueryError,
    CursorDatabaseAccessError,
    CursorDatabaseNotFoundError
)
from ..telemetry import trace_mcp_operation, PERFORMANCE_THRESHOLDS


@trace_mcp_operation("cursor_db.execute_query")
def execute_cursor_query(
    db_path: str, 
    query: str, 
    parameters: Optional[Tuple[Any, ...]] = None
) -> List[Tuple[Any, ...]]:
    """
    Execute a SQL query against a cursor database with proper error handling.
    
    This is the core low-level query execution function that handles database
    connection management, parameterized queries, and comprehensive error handling.
    Higher-level functions should use this as their foundation.
    
    Telemetry Metrics Tracked:
        - database_path: Which database file was queried
        - query_duration_ms: Execution time in milliseconds
        - error.type: SQLite exception type for failures
        - error.category: "database_access" or "query_syntax" classification
        - threshold_exceeded: Boolean if duration > 50ms threshold
    
    Threshold Rationale:
        50ms chosen as reasonable baseline for local SQLite SELECT operations.
        Accounts for disk I/O and typical cursor database sizes (~1-10MB).
    
    Args:
        db_path: Path to the SQLite database file
        query: SQL query string to execute
        parameters: Optional tuple of parameters for parameterized queries
        
    Returns:
        List of tuples containing query results in SQLite's native format
        
    Raises:
        CursorDatabaseAccessError: For database access issues (file not found, 
            locked, permissions, etc.)
        CursorDatabaseQueryError: For query-related issues (syntax errors,
            parameter mismatches, etc.)
            
    Design Choices (as approved):
        - Fixed 5-second timeout (not configurable)
        - Returns List[Tuple[Any, ...]] - SQLite's native format
        - No connection pooling - one connection per query with proper cleanup
        - Comprehensive error wrapping in custom exceptions
    """
    if parameters is None:
        parameters = ()
    
    # Track telemetry using current span
    start_time = time.time()
    span = trace.get_current_span()
    
    try:
        # Set telemetry attributes
        span.set_attribute("database_path", db_path)
        span.set_attribute("query_duration_ms", 0)  # Will be updated below
        
        # Use context manager for automatic connection cleanup
        # Fixed 5-second timeout as per approved design
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            result = cursor.fetchall()
            
        # Calculate duration and set metrics
        duration_ms = (time.time() - start_time) * 1000
        span.set_attribute("query_duration_ms", duration_ms)
        
        # Check performance threshold
        threshold = PERFORMANCE_THRESHOLDS["execute_cursor_query"]
        span.set_attribute("threshold_exceeded", duration_ms > threshold)
        if duration_ms > threshold:
            span.set_attribute("threshold_ms", threshold)
        
        return result
            
    except Exception as e:
        # Calculate duration for error case
        duration_ms = (time.time() - start_time) * 1000
        span.set_attribute("query_duration_ms", duration_ms)
        
        # Check if it's an sqlite3 exception by type name
        exception_type = type(e).__name__
        error_msg = str(e).lower()
        
        # Set error telemetry attributes
        span.set_attribute("error.type", exception_type)
        span.set_attribute("error.message", str(e))
        span.set_status(Status(StatusCode.ERROR, str(e)))
        
        if exception_type == 'OperationalError':
            # Handle different types of operational errors
            if "unable to open database file" in error_msg or "no such file" in error_msg:
                span.set_attribute("error.category", "database_access")
                raise CursorDatabaseAccessError(
                    f"Cannot access database file: {e}",
                    path=db_path,
                    permission_type="read"
                ) from e
            elif "database is locked" in error_msg:
                span.set_attribute("error.category", "database_access")
                raise CursorDatabaseAccessError(
                    f"Database is locked or busy: {e}",
                    path=db_path,
                    permission_type="write"
                ) from e
            elif "syntax error" in error_msg:
                span.set_attribute("error.category", "query_syntax")
                raise CursorDatabaseQueryError(
                    f"SQL syntax error: {e}",
                    sql=query,
                    parameters=parameters
                ) from e
            else:
                # Generic operational error - treat as access issue
                span.set_attribute("error.category", "database_access")
                raise CursorDatabaseAccessError(
                    f"Database operation failed: {e}",
                    path=db_path
                ) from e
                
        elif exception_type == 'ProgrammingError':
            # Parameter-related errors (wrong number of bindings, etc.)
            span.set_attribute("error.category", "query_syntax")
            raise CursorDatabaseQueryError(
                f"Query parameter error: {e}",
                sql=query,
                parameters=parameters
            ) from e
            
        elif exception_type == 'DatabaseError':
            # Generic database errors - treat as access issues
            span.set_attribute("error.category", "database_access")
            raise CursorDatabaseAccessError(
                f"Database error: {e}",
                path=db_path
            ) from e
        else:
            # Catch any other unexpected errors and wrap them
            span.set_attribute("error.category", "database_access")
            raise CursorDatabaseAccessError(
                f"Unexpected error accessing database: {e}",
                path=db_path
            ) from e 