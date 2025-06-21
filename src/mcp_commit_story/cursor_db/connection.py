"""
Database connection module for Cursor workspace SQLite databases.

Provides functionality to discover, connect to, and query Cursor's SQLite workspace
databases with proper error handling and resource management.
"""

import sqlite3
import os
from pathlib import Path
from typing import List, Tuple, Optional, Any, Union
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging

from .platform import get_cursor_workspace_paths

logger = logging.getLogger(__name__)


class CursorDatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class CursorDatabaseQueryError(Exception):
    """Raised when database query execution fails."""
    pass


def get_cursor_chat_database(user_override_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """
    Get a connection to a Cursor chat database.
    
    Args:
        user_override_path: Optional path to specific database file.
                          If not provided, will auto-discover using platform detection.
    
    Returns:
        sqlite3.Connection: Active database connection
        
    Raises:
        CursorDatabaseConnectionError: If no valid database found or connection fails
    """
    if user_override_path:
        # Use explicitly provided path
        db_path = Path(user_override_path)
        if not db_path.exists():
            raise CursorDatabaseConnectionError(f"Database file not found: {db_path}")
        
        return _connect_to_database(db_path)
    
    # Auto-discover databases
    discovered_databases = _discover_cursor_databases()
    
    if not discovered_databases:
        raise CursorDatabaseConnectionError(
            "No valid Cursor workspace databases found. "
            "Ensure Cursor has been used recently or provide explicit path."
        )
    
    # Return connection to the most recently modified database
    most_recent_db = discovered_databases[0]  # Already sorted by modification time
    logger.info(f"Connecting to most recent database: {most_recent_db}")
    
    return _connect_to_database(most_recent_db)


@contextmanager
def cursor_chat_database_context(user_override_path: Optional[Union[str, Path]] = None):
    """
    Context manager for database connections with automatic cleanup.
    
    Args:
        user_override_path: Optional path to specific database file
        
    Yields:
        sqlite3.Connection: Active database connection
        
    Example:
        with cursor_chat_database_context() as conn:
            result = conn.execute("SELECT * FROM messages").fetchall()
    """
    conn = None
    try:
        conn = get_cursor_chat_database(user_override_path)
        yield conn
    finally:
        if conn:
            conn.close()


def query_cursor_chat_database(
    database_path: Union[str, Path], 
    sql: str, 
    parameters: Optional[Tuple] = None
) -> List[Tuple[Any, ...]]:
    """
    Execute a query against a Cursor chat database.
    
    Args:
        database_path: Path to the database file
        sql: SQL query to execute
        parameters: Optional tuple of parameters for parameterized queries
        
    Returns:
        List[Tuple]: Query results as list of tuples
        
    Raises:
        CursorDatabaseConnectionError: If database connection fails
        CursorDatabaseQueryError: If query execution fails
    """
    try:
        conn = get_cursor_chat_database(database_path)
        try:
            cursor = conn.cursor()
            
            if parameters:
                cursor.execute(sql, parameters)
            else:
                cursor.execute(sql)
                
            results = cursor.fetchall()
            return results
            
        except sqlite3.Error as e:
            raise CursorDatabaseQueryError(f"Query execution failed: {e}") from e
        finally:
            conn.close()
            
    except CursorDatabaseConnectionError:
        # Re-raise connection errors as-is
        raise
    except CursorDatabaseQueryError:
        # Re-raise query errors as-is
        raise
    except Exception as e:
        raise CursorDatabaseConnectionError(f"Failed to connect to database: {e}") from e


def _discover_cursor_databases() -> List[Path]:
    """
    Discover Cursor workspace databases using platform detection.
    
    Returns:
        List[Path]: List of valid database paths, sorted by modification time (newest first)
    """
    try:
        workspace_paths = get_cursor_workspace_paths()
    except Exception as e:
        logger.warning(f"Platform detection failed: {e}")
        return []
    
    valid_databases = []
    cutoff_time = datetime.now() - timedelta(hours=48)
    
    for workspace_path in workspace_paths:
        if not workspace_path.exists():
            continue
            
        # Search for state.vscdb files specifically
        try:
            for db_file in workspace_path.rglob("state.vscdb"):
                if _is_valid_cursor_database(db_file, cutoff_time):
                    valid_databases.append(db_file)
                    
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not search workspace {workspace_path}: {e}")
            continue
    
    # Sort by modification time, newest first
    valid_databases.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    logger.info(f"Discovered {len(valid_databases)} valid Cursor databases")
    return valid_databases


def _is_valid_cursor_database(db_path: Path, cutoff_time: datetime) -> bool:
    """
    Check if a database file is a valid, recent Cursor database.
    
    Args:
        db_path: Path to database file
        cutoff_time: Minimum modification time for validity
        
    Returns:
        bool: True if database is valid and recent
    """
    try:
        # Check file exists and is readable
        if not db_path.exists() or not os.access(db_path, os.R_OK):
            return False
            
        # Check modification time
        mod_time = datetime.fromtimestamp(db_path.stat().st_mtime)
        if mod_time < cutoff_time:
            logger.debug(f"Database {db_path} too old: {mod_time}")
            return False
            
        # Verify it's a valid SQLite database
        try:
            conn = sqlite3.connect(str(db_path))
            # Try a simple query to verify database integrity
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
            cursor.fetchone()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.debug(f"Database {db_path} failed SQLite validation: {e}")
            return False
            
    except (OSError, PermissionError) as e:
        logger.debug(f"Could not validate database {db_path}: {e}")
        return False


def _connect_to_database(db_path: Path) -> sqlite3.Connection:
    """
    Create a connection to a specific database file.
    
    Args:
        db_path: Path to database file
        
    Returns:
        sqlite3.Connection: Active database connection
        
    Raises:
        CursorDatabaseConnectionError: If connection fails
    """
    try:
        # Check file exists and is readable
        if not db_path.exists():
            raise CursorDatabaseConnectionError(f"Database file not found: {db_path}")
            
        if not os.access(db_path, os.R_OK):
            raise CursorDatabaseConnectionError(f"Permission denied accessing database: {db_path}")
        
        # Attempt connection
        conn = sqlite3.connect(str(db_path))
        
        # Verify it's a valid SQLite database
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
            cursor.fetchone()
            
        except sqlite3.Error as e:
            conn.close()
            raise CursorDatabaseConnectionError(f"Database corrupted or invalid: {db_path} - {e}")
            
        return conn
        
    except sqlite3.Error as e:
        raise CursorDatabaseConnectionError(f"Failed to connect to database {db_path}: {e}") from e
    except Exception as e:
        raise CursorDatabaseConnectionError(f"Unexpected error connecting to {db_path}: {e}") from e


# Convenience functions for common operations
def get_all_cursor_databases() -> List[Path]:
    """
    Get paths to all discovered Cursor databases.
    
    Returns:
        List[Path]: List of valid database paths, sorted by modification time (newest first)
    """
    return _discover_cursor_databases()


def query_all_cursor_databases(sql: str, parameters: Optional[Tuple] = None) -> List[Tuple[Path, List[Tuple[Any, ...]]]]:
    """
    Execute a query against all discovered Cursor databases.
    
    Args:
        sql: SQL query to execute
        parameters: Optional tuple of parameters for parameterized queries
        
    Returns:
        List[Tuple[Path, List[Tuple]]]: List of (database_path, query_results) tuples
    """
    databases = get_all_cursor_databases()
    results = []
    
    for db_path in databases:
        try:
            query_results = query_cursor_chat_database(db_path, sql, parameters)
            results.append((db_path, query_results))
        except (CursorDatabaseConnectionError, CursorDatabaseQueryError) as e:
            logger.warning(f"Failed to query database {db_path}: {e}")
            continue
            
    return results 