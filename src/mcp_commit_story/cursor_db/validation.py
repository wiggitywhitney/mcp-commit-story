"""
Basic database structure validation for Cursor SQLite workspaces.

This module provides minimal validation functions to ensure Cursor databases
have the basic structure needed for chat data extraction. All complex chat
data validation is handled in separate modules.
"""

import sqlite3
from typing import Dict, Any

from .exceptions import CursorDatabaseSchemaError, CursorDatabaseQueryError


def validate_database_basics(conn: sqlite3.Connection) -> bool:
    """
    Validate basic database structure requirements.
    
    Verifies that the database has the minimum structure needed for
    chat data extraction:
    - ItemTable exists
    - ItemTable has key and value columns
    - Database can be queried successfully
    
    Args:
        conn: SQLite database connection
        
    Returns:
        True if database meets basic requirements
        
    Raises:
        CursorDatabaseSchemaError: If required structure is missing
        CursorDatabaseQueryError: If database cannot be queried
    """
    try:
        cursor = conn.cursor()
        
        # Check if ItemTable exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'"
        )
        if not cursor.fetchone():
            raise CursorDatabaseSchemaError(
                "Missing required ItemTable - database may not be a valid Cursor workspace"
            )
        
        # Verify ItemTable has required columns
        cursor.execute("PRAGMA table_info(ItemTable)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]  # Column name is at index 1
        
        if 'key' not in column_names:
            raise CursorDatabaseSchemaError(
                "ItemTable missing required 'key' column"
            )
            
        if 'value' not in column_names:
            raise CursorDatabaseSchemaError(
                "ItemTable missing required 'value' column"
            )
        
        # Verify we can query the table
        cursor.execute("SELECT COUNT(*) FROM ItemTable")
        cursor.fetchone()  # Just verify the query works
        
        return True
        
    except sqlite3.Error as e:
        raise CursorDatabaseQueryError(f"Database query failed: {e}") from e


def check_database_integrity(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Perform basic SQLite integrity checks.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        Dictionary with integrity check results
        
    Raises:
        CursorDatabaseQueryError: If integrity checks cannot be performed
    """
    try:
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        # Run quick check  
        cursor.execute("PRAGMA quick_check")
        quick_check_result = cursor.fetchone()[0]
        
        is_healthy = (
            integrity_result == "ok" and 
            quick_check_result == "ok"
        )
        
        return {
            'healthy': is_healthy,
            'integrity_check': integrity_result,
            'quick_check': quick_check_result
        }
        
    except sqlite3.Error as e:
        raise CursorDatabaseQueryError(f"Integrity check failed: {e}") from e 