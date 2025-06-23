"""
Database connection and query functions for Cursor chat databases.

Provides functions to discover, connect to, and query Cursor's SQLite chat databases
with comprehensive error handling and cross-platform support.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple, Any, Optional, Union
from contextlib import contextmanager
import time

from .platform import get_cursor_workspace_paths
from .exceptions import (
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError,
    CursorDatabaseSchemaError,
    CursorDatabaseQueryError
)

logger = logging.getLogger(__name__)


def get_cursor_chat_database(user_override_path: Optional[Union[str, Path]] = None) -> str:
    """
    Get the path to a Cursor chat database, with auto-discovery and validation.
    
    Args:
        user_override_path: Optional path to specific database file to use instead of auto-discovery
        
    Returns:
        str: Path to a valid Cursor chat database file
        
    Raises:
        CursorDatabaseNotFoundError: When no valid database can be found
        CursorDatabaseAccessError: When database exists but cannot be accessed
    """
    logger.info("Starting Cursor chat database discovery")
    
    if user_override_path:
        # User provided specific path - validate it
        db_path = Path(user_override_path)
        logger.info(f"Using user-provided database path: {db_path}")
        
        if not db_path.exists():
            error = CursorDatabaseNotFoundError(
                f"User-specified database file not found: {db_path}",
                path=str(db_path),
                search_type="user_override"
            )
            logger.error(f"Database not found: {error.message}", extra={
                'error_type': error.__class__.__name__,
                'context': error.context,
                'troubleshooting_hint': error.troubleshooting_hint
            })
            raise error
        
        return _validate_database_file(db_path)
    
    # Auto-discovery mode
    try:
        workspace_paths = get_cursor_workspace_paths()
        logger.info(f"Found {len(workspace_paths)} potential workspace paths")
    except Exception as e:
        error = CursorDatabaseNotFoundError(
            "Failed to detect Cursor workspace paths",
            platform_detection_error=str(e),
            search_type="auto_discovery"
        )
        logger.error(f"Platform detection failed: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e
    
    # Search for state.vscdb files in workspace paths
    valid_databases = []
    searched_paths = []
    
    for workspace_path in workspace_paths:
        workspace_dir = Path(workspace_path)
        searched_paths.append(str(workspace_dir))
        
        if not workspace_dir.exists():
            logger.debug(f"Workspace directory does not exist: {workspace_dir}")
            continue
            
        # Look for state.vscdb files specifically
        try:
            for db_file in workspace_dir.rglob("state.vscdb"):
                logger.debug(f"Found potential database: {db_file}")
                
                # Check if file was modified within last 48 hours (recent workspace activity)
                try:
                    file_age_hours = (time.time() - db_file.stat().st_mtime) / 3600
                    if file_age_hours > 48:
                        logger.debug(f"Skipping old database (age: {file_age_hours:.1f}h): {db_file}")
                        continue
                        
                    # Validate the database file
                    validated_path = _validate_database_file(db_file)
                    valid_databases.append((validated_path, file_age_hours))
                    logger.info(f"Found valid recent database (age: {file_age_hours:.1f}h): {db_file}")
                    
                except (CursorDatabaseAccessError, CursorDatabaseQueryError) as e:
                    logger.warning(f"Database validation failed for {db_file}: {e.message}")
                    continue
                except OSError as e:
                    logger.warning(f"Cannot access file stats for {db_file}: {e}")
                    continue
                    
        except OSError as e:
            logger.warning(f"Cannot search workspace directory {workspace_dir}: {e}")
            continue
    
    if not valid_databases:
        error = CursorDatabaseNotFoundError(
            "No valid Cursor chat databases found in recent workspace activity",
            searched_paths=searched_paths,
            search_criteria="state.vscdb files modified within 48 hours",
            search_type="auto_discovery"
        )
        logger.error(f"No databases found: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        })
        raise error
    
    # Return the most recently modified database
    valid_databases.sort(key=lambda x: x[1])  # Sort by age (ascending)
    selected_db = valid_databases[0][0]
    logger.info(f"Selected most recent database: {selected_db}")
    
    return selected_db


def _validate_database_file(db_path: Path) -> str:
    """
    Validate that a file is a readable SQLite database.
    
    Args:
        db_path: Path to database file to validate
        
    Returns:
        str: Validated database path
        
    Raises:
        CursorDatabaseAccessError: When file cannot be accessed
        CursorDatabaseQueryError: When file is not a valid SQLite database
    """
    try:
        # Check read permissions
        if not db_path.is_file():
            error = CursorDatabaseAccessError(
                f"Database path is not a readable file: {db_path}",
                path=str(db_path),
                permission_type="read"
            )
            logger.error(f"File access error: {error.message}", extra={
                'error_type': error.__class__.__name__,
                'context': error.context,
                'troubleshooting_hint': error.troubleshooting_hint
            })
            raise error
        
        # Try to open as SQLite database
        try:
            with sqlite3.connect(str(db_path)) as conn:
                # Basic SQLite integrity check
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                cursor.fetchone()  # Just verify we can read
                
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            # Check if it's an access/permission issue
            if "unable to open database file" in error_msg or "permission denied" in error_msg:
                error = CursorDatabaseAccessError(
                    f"Permission denied accessing database: {e}",
                    path=str(db_path),
                    permission_type="read",
                    sqlite_error=str(e)
                )
                logger.error(f"Database access denied: {error.message}", extra={
                    'error_type': error.__class__.__name__,
                    'context': error.context,
                    'troubleshooting_hint': error.troubleshooting_hint
                })
                raise error from e
            else:
                # Other operational errors are likely corruption
                error = CursorDatabaseQueryError(
                    f"Database file appears corrupted or invalid: {e}",
                    path=str(db_path),
                    corruption_type="sqlite_operational_error",
                    sqlite_error=str(e)
                )
                logger.error(f"Database corruption detected: {error.message}", extra={
                    'error_type': error.__class__.__name__,
                    'context': error.context,
                    'troubleshooting_hint': error.troubleshooting_hint
                }, exc_info=True)
                raise error from e
                
        except sqlite3.DatabaseError as e:
            error = CursorDatabaseQueryError(
                f"Database file appears corrupted or invalid: {e}",
                path=str(db_path),
                corruption_type="sqlite_error",
                sqlite_error=str(e)
            )
            logger.error(f"Database error: {error.message}", extra={
                'error_type': error.__class__.__name__,
                'context': error.context,
                'troubleshooting_hint': error.troubleshooting_hint
            }, exc_info=True)
            raise error from e
            
    except PermissionError as e:
        error = CursorDatabaseAccessError(
            f"Permission denied accessing database: {e}",
            path=str(db_path),
            permission_type="read",
            system_error=str(e)
        )
        logger.error(f"Permission error: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e
    except OSError as e:
        error = CursorDatabaseAccessError(
            f"System error accessing database: {e}",
            path=str(db_path),
            permission_type="read",
            system_error=str(e)
        )
        logger.error(f"System error: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e
    
    return str(db_path)


def query_cursor_chat_database(database_path: str, sql: str, parameters: Optional[Tuple] = None) -> List[Tuple[Any, ...]]:
    """
    Execute a SQL query against a Cursor chat database.
    
    Args:
        database_path: Path to the SQLite database file
        sql: SQL query to execute (use ? placeholders for parameters)
        parameters: Optional tuple of parameters for the SQL query
        
    Returns:
        List of tuples containing query results (raw SQLite format)
        
    Raises:
        CursorDatabaseAccessError: When database cannot be accessed
        CursorDatabaseSchemaError: When required tables/columns are missing
        CursorDatabaseQueryError: When SQL syntax is invalid or parameter binding fails
    """
    if parameters is None:
        parameters = ()
    
    logger.debug(f"Executing query on database: {database_path}")
    logger.debug(f"SQL: {sql}")
    logger.debug(f"Parameters: {parameters}")
    
    # Validate database file first
    _validate_database_file(Path(database_path))
    
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(sql, parameters)
                results = cursor.fetchall()
                logger.debug(f"Query returned {len(results)} rows")
                return results
                
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                
                # Check for common schema issues
                if "no such table" in error_msg or "no such column" in error_msg:
                    # Extract table/column name from error message
                    import re
                    table_match = re.search(r"no such table: (\w+)", error_msg)
                    column_match = re.search(r"no such column: (\w+)", error_msg)
                    
                    missing_item = None
                    if table_match:
                        missing_item = f"table '{table_match.group(1)}'"
                    elif column_match:
                        missing_item = f"column '{column_match.group(1)}'"
                    
                    error = CursorDatabaseSchemaError(
                        f"Database schema mismatch: {missing_item or 'required element'} not found",
                        sql=sql,
                        schema_error=str(e),
                        missing_element=missing_item
                    )
                    logger.error(f"Schema error: {error.message}", extra={
                        'error_type': error.__class__.__name__,
                        'context': error.context,
                        'troubleshooting_hint': error.troubleshooting_hint
                    })
                    raise error from e
                
                # Check for syntax errors
                elif "syntax error" in error_msg or "malformed" in error_msg:
                    error = CursorDatabaseQueryError(
                        f"SQL syntax error: {e}",
                        sql=sql,
                        syntax_error=str(e)
                    )
                    logger.error(f"SQL syntax error: {error.message}", extra={
                        'error_type': error.__class__.__name__,
                        'context': error.context,
                        'troubleshooting_hint': error.troubleshooting_hint
                    })
                    raise error from e
                
                else:
                    # Generic operational error
                    error = CursorDatabaseAccessError(
                        f"Database operation failed: {e}",
                        path=database_path,
                        operation="query_execution",
                        sql=sql,
                        operational_error=str(e)
                    )
                    logger.error(f"Database operation failed: {error.message}", extra={
                        'error_type': error.__class__.__name__,
                        'context': error.context,
                        'troubleshooting_hint': error.troubleshooting_hint
                    }, exc_info=True)
                    raise error from e
                    
            except sqlite3.ProgrammingError as e:
                # Usually parameter binding issues
                error = CursorDatabaseQueryError(
                    f"Query parameter error: {e}",
                    sql=sql,
                    parameters=parameters,
                    parameter_count=len(parameters) if parameters else 0,
                    programming_error=str(e)
                )
                logger.error(f"Parameter binding error: {error.message}", extra={
                    'error_type': error.__class__.__name__,
                    'context': error.context,
                    'troubleshooting_hint': error.troubleshooting_hint
                })
                raise error from e
                
    except sqlite3.DatabaseError as e:
        error = CursorDatabaseQueryError(
            f"Database corruption detected: {e}",
            path=database_path,
            corruption_type="database_error",
            database_error=str(e)
        )
        logger.error(f"Database corruption: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e
    except PermissionError as e:
        error = CursorDatabaseAccessError(
            f"Permission denied accessing database: {e}",
            path=database_path,
            permission_type="read",
            system_error=str(e)
        )
        logger.error(f"Permission denied: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e
    except OSError as e:
        error = CursorDatabaseAccessError(
            f"System error accessing database: {e}",
            path=database_path,
            permission_type="read", 
            system_error=str(e)
        )
        logger.error(f"System error: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e


@contextmanager
def cursor_chat_database_context(user_override_path: Optional[Union[str, Path]] = None):
    """
    Context manager for cursor chat database operations.
    
    Automatically handles database discovery, connection, and cleanup.
    
    Args:
        user_override_path: Optional path to specific database file
        
    Yields:
        str: Path to validated database file
        
    Example:
        with cursor_chat_database_context() as db_path:
            results = query_cursor_chat_database(db_path, "SELECT * FROM messages LIMIT 10")
    """
    db_path = None
    try:
        db_path = get_cursor_chat_database(user_override_path)
        logger.info(f"Database context established: {db_path}")
        yield db_path
    finally:
        if db_path:
            logger.debug(f"Database context closed: {db_path}")


def query_multiple_databases(sql: str, parameters: Optional[Tuple] = None, 
                           max_databases: int = 3) -> List[Tuple[str, List[Tuple[Any, ...]]]]:
    """
    Execute a query against multiple recent Cursor databases.
    
    Useful for gathering data across multiple workspace sessions.
    
    Args:
        sql: SQL query to execute
        parameters: Optional parameters for the query
        max_databases: Maximum number of databases to query
        
    Returns:
        List of tuples: (database_path, query_results)
    """
    try:
        workspace_paths = get_cursor_workspace_paths()
    except Exception as e:
        error = CursorDatabaseNotFoundError(
            "Failed to detect workspace paths for multi-database query",
            platform_detection_error=str(e)
        )
        logger.error(f"Multi-database query failed: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        }, exc_info=True)
        raise error from e
    
    databases_found = []
    
    # Collect all valid databases with timestamps
    for workspace_path in workspace_paths:
        workspace_dir = Path(workspace_path)
        if not workspace_dir.exists():
            continue
            
        try:
            for db_file in workspace_dir.rglob("state.vscdb"):
                try:
                    file_age_hours = (time.time() - db_file.stat().st_mtime) / 3600
                    if file_age_hours > 48:  # Skip old databases
                        continue
                        
                    validated_path = _validate_database_file(db_file)
                    databases_found.append((validated_path, file_age_hours))
                    
                except (CursorDatabaseAccessError, CursorDatabaseQueryError, OSError):
                    continue
        except OSError:
            continue
    
    if not databases_found:
        error = CursorDatabaseNotFoundError(
            "No valid databases found for multi-database query",
            search_criteria="state.vscdb files modified within 48 hours"
        )
        logger.error(f"No databases for multi-query: {error.message}", extra={
            'error_type': error.__class__.__name__,
            'context': error.context,
            'troubleshooting_hint': error.troubleshooting_hint
        })
        raise error
    
    # Sort by recency and limit
    databases_found.sort(key=lambda x: x[1])
    selected_databases = databases_found[:max_databases]
    
    results = []
    for db_path, _ in selected_databases:
        try:
            query_results = query_cursor_chat_database(db_path, sql, parameters)
            results.append((db_path, query_results))
        except Exception as e:
            logger.warning(f"Query failed for database {db_path}: {e}")
            continue
    
    return results 