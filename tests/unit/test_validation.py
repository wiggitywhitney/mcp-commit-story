"""
Unit tests for basic database validation functionality.
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch

from src.mcp_commit_story.cursor_db.validation import (
    validate_database_basics,
    check_database_integrity
)
from src.mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseSchemaError,
    CursorDatabaseQueryError
)


class TestValidateDatabaseBasics:
    """Test basic database structure validation."""

    def test_valid_database_structure(self):
        """Test validation passes for properly structured database."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock ItemTable exists
        mock_cursor.execute.side_effect = [
            None,  # First query: check table exists
            None,  # Second query: get table info
            None,  # Third query: count check
        ]
        mock_cursor.fetchone.side_effect = [
            ('ItemTable',),  # Table exists
            None,  # Count query result
        ]
        mock_cursor.fetchall.return_value = [
            (0, 'key', 'TEXT', 0, None, 0),
            (1, 'value', 'BLOB', 0, None, 0)
        ]
        
        result = validate_database_basics(mock_conn)
        
        assert result is True
        assert mock_cursor.execute.call_count == 3

    def test_missing_item_table(self):
        """Test validation fails when ItemTable is missing."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock no ItemTable found
        mock_cursor.fetchone.return_value = None
        
        with pytest.raises(CursorDatabaseSchemaError, match="Missing required ItemTable"):
            validate_database_basics(mock_conn)

    def test_missing_key_column(self):
        """Test validation fails when key column is missing."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock ItemTable exists but missing key column
        mock_cursor.fetchone.return_value = ('ItemTable',)
        mock_cursor.fetchall.return_value = [
            (0, 'value', 'BLOB', 0, None, 0)  # Only value column
        ]
        
        with pytest.raises(CursorDatabaseSchemaError, match="missing required 'key' column"):
            validate_database_basics(mock_conn)

    def test_missing_value_column(self):
        """Test validation fails when value column is missing."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock ItemTable exists but missing value column
        mock_cursor.fetchone.return_value = ('ItemTable',)
        mock_cursor.fetchall.return_value = [
            (0, 'key', 'TEXT', 0, None, 0)  # Only key column
        ]
        
        with pytest.raises(CursorDatabaseSchemaError, match="missing required 'value' column"):
            validate_database_basics(mock_conn)

    def test_database_query_error(self):
        """Test validation handles SQLite errors gracefully."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock SQLite error
        mock_cursor.execute.side_effect = sqlite3.Error("Database is locked")
        
        with pytest.raises(CursorDatabaseQueryError, match="Database query failed"):
            validate_database_basics(mock_conn)


class TestCheckDatabaseIntegrity:
    """Test database integrity checking functionality."""

    def test_healthy_database(self):
        """Test integrity check for healthy database."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock healthy integrity checks
        mock_cursor.fetchone.side_effect = [
            ('ok',),  # integrity_check result
            ('ok',),  # quick_check result
        ]
        
        result = check_database_integrity(mock_conn)
        
        assert result['healthy'] is True
        assert result['integrity_check'] == 'ok'
        assert result['quick_check'] == 'ok'

    def test_corrupted_database(self):
        """Test integrity check for corrupted database."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock failed integrity checks
        mock_cursor.fetchone.side_effect = [
            ('*** in database main ***\nOn tree page 1 cell 0: invalid nKey value',),
            ('ok',),  # quick_check still passes
        ]
        
        result = check_database_integrity(mock_conn)
        
        assert result['healthy'] is False
        assert 'invalid nKey value' in result['integrity_check']
        assert result['quick_check'] == 'ok'

    def test_integrity_check_error(self):
        """Test integrity check handles SQLite errors gracefully.""" 
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock SQLite error
        mock_cursor.execute.side_effect = sqlite3.Error("Cannot read database")
        
        with pytest.raises(CursorDatabaseQueryError, match="Integrity check failed"):
            check_database_integrity(mock_conn) 