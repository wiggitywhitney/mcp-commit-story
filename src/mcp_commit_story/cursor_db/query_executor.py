"""
Core query execution module for cursor database operations.

Provides the fundamental database query execution functionality with proper
connection management, error handling, parameterized queries, and timeout handling.
"""

import sqlite3
import contextlib
from typing import List, Tuple, Any, Optional

from .exceptions import (
    CursorDatabaseQueryError,
    CursorDatabaseAccessError,
    CursorDatabaseNotFoundError
)


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
    
    try:
        # Use context manager for automatic connection cleanup
        # Fixed 5-second timeout as per approved design
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            return cursor.fetchall()
            
    except Exception as e:
        # Check if it's an sqlite3 exception by type name
        exception_type = type(e).__name__
        error_msg = str(e).lower()
        
        if exception_type == 'OperationalError':
            # Handle different types of operational errors
            if "unable to open database file" in error_msg or "no such file" in error_msg:
                raise CursorDatabaseAccessError(
                    f"Cannot access database file: {e}",
                    path=db_path,
                    permission_type="read"
                ) from e
            elif "database is locked" in error_msg:
                raise CursorDatabaseAccessError(
                    f"Database is locked or busy: {e}",
                    path=db_path,
                    permission_type="write"
                ) from e
            elif "syntax error" in error_msg:
                raise CursorDatabaseQueryError(
                    f"SQL syntax error: {e}",
                    sql=query,
                    parameters=parameters
                ) from e
            else:
                # Generic operational error - treat as access issue
                raise CursorDatabaseAccessError(
                    f"Database operation failed: {e}",
                    path=db_path
                ) from e
                
        elif exception_type == 'ProgrammingError':
            # Parameter-related errors (wrong number of bindings, etc.)
            raise CursorDatabaseQueryError(
                f"Query parameter error: {e}",
                sql=query,
                parameters=parameters
            ) from e
            
        elif exception_type == 'DatabaseError':
            # Generic database errors - treat as access issues
            raise CursorDatabaseAccessError(
                f"Database error: {e}",
                path=db_path
            ) from e
        else:
            # Catch any other unexpected errors and wrap them
            raise CursorDatabaseAccessError(
                f"Unexpected error accessing database: {e}",
                path=db_path
            ) from e 