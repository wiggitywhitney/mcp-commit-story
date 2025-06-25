"""
Unit tests for cursor database query executor module.

Tests the core query execution functionality with proper connection management,
error handling, parameterized queries, and timeout handling.
"""

import sqlite3
import tempfile
import time
from pathlib import Path
from typing import List, Tuple, Any
from unittest.mock import patch, MagicMock, Mock, call

import pytest

from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseQueryError,
    CursorDatabaseAccessError,
    CursorDatabaseNotFoundError
)
from mcp_commit_story.cursor_db.query_executor import execute_cursor_query


class TestExecuteCursorQuery:
    """Test the main execute_cursor_query function."""

    def test_execute_simple_query_success(self):
        """Test successful execution of a simple query."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT id, name FROM users"
        expected_result = [(1, "Alice"), (2, "Bob")]
        
        # Mock the sqlite3 connection and cursor
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query)
            
            # Assert
            assert result == expected_result
            mock_sqlite3.connect.assert_called_once_with(mock_db_path, timeout=5.0)
            mock_cursor.execute.assert_called_once_with(mock_query, ())
            mock_cursor.fetchall.assert_called_once()

    def test_execute_parameterized_query_success(self):
        """Test successful execution of a parameterized query."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT * FROM messages WHERE id = ? AND created_at > ?"
        mock_params = (123, "2025-01-01")
        expected_result = [(123, "Test message", "2025-01-02")]
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query, mock_params)
            
            # Assert
            assert result == expected_result
            mock_cursor.execute.assert_called_once_with(mock_query, mock_params)

    def test_execute_query_with_empty_result(self):
        """Test query execution that returns no results."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT * FROM users WHERE name = ?"
        mock_params = ("NonExistent",)
        expected_result = []
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query, mock_params)
            
            # Assert
            assert result == expected_result
            assert isinstance(result, list)

    def test_connection_timeout_configuration(self):
        """Test that connection uses the correct 5-second timeout."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT 1"
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [(1,)]
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            execute_cursor_query(mock_db_path, mock_query)
            
            # Assert
            mock_sqlite3.connect.assert_called_once_with(mock_db_path, timeout=5.0)

    def test_connection_context_manager_cleanup(self):
        """Test that connection is properly cleaned up using context manager."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT 1"
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [(1,)]
            mock_conn.cursor.return_value = mock_cursor
            
            # Use MagicMock for context manager support
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_conn
            mock_context.__exit__.return_value = None
            mock_sqlite3.connect.return_value = mock_context
            
            # Act
            execute_cursor_query(mock_db_path, mock_query)
            
            # Assert
            mock_sqlite3.connect.assert_called_once_with(mock_db_path, timeout=5.0)
            mock_context.__enter__.assert_called_once()
            mock_context.__exit__.assert_called_once()


class TestQueryExecutorErrorHandling:
    """Test error handling scenarios for the query executor."""

    def test_invalid_database_path_raises_access_error(self):
        """Test that invalid database path raises CursorDatabaseAccessError."""
        # Arrange
        invalid_db_path = "/nonexistent/path/to/database.db"
        mock_query = "SELECT 1"
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            # Simulate sqlite3.OperationalError for file not found
            mock_sqlite3.connect.side_effect = sqlite3.OperationalError("unable to open database file")
            
            # Act & Assert
            with pytest.raises(CursorDatabaseAccessError) as exc_info:
                execute_cursor_query(invalid_db_path, mock_query)
            
            assert "unable to open database file" in str(exc_info.value)
            assert exc_info.value.context['path'] == invalid_db_path

    def test_malformed_query_raises_query_error(self):
        """Test that malformed SQL raises CursorDatabaseQueryError."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        malformed_query = "SELCT * FRM users"  # Typos in SQL
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            # Simulate sqlite3.OperationalError for syntax error
            mock_cursor.execute.side_effect = sqlite3.OperationalError("near \"SELCT\": syntax error")
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act & Assert
            with pytest.raises(CursorDatabaseQueryError) as exc_info:
                execute_cursor_query(mock_db_path, malformed_query)
            
            assert "syntax error" in str(exc_info.value)
            assert exc_info.value.context['sql'] == malformed_query

    def test_locked_database_raises_access_error(self):
        """Test that locked database raises CursorDatabaseAccessError."""
        # Arrange
        mock_db_path = "/fake/path/to/locked.db"
        mock_query = "SELECT 1"
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            # Simulate sqlite3.OperationalError for database locked
            mock_sqlite3.connect.side_effect = sqlite3.OperationalError("database is locked")
            
            # Act & Assert
            with pytest.raises(CursorDatabaseAccessError) as exc_info:
                execute_cursor_query(mock_db_path, mock_query)
            
            assert "database is locked" in str(exc_info.value)
            assert exc_info.value.context['path'] == mock_db_path

    def test_parameter_mismatch_raises_query_error(self):
        """Test that parameter count mismatch raises CursorDatabaseQueryError."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT * FROM users WHERE id = ? AND name = ?"
        wrong_params = (123,)  # Missing second parameter
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            # Simulate sqlite3.ProgrammingError for parameter count mismatch
            mock_cursor.execute.side_effect = sqlite3.ProgrammingError("Incorrect number of bindings")
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act & Assert
            with pytest.raises(CursorDatabaseQueryError) as exc_info:
                execute_cursor_query(mock_db_path, mock_query, wrong_params)
            
            assert "Incorrect number of bindings" in str(exc_info.value)
            assert exc_info.value.context['sql'] == mock_query
            assert exc_info.value.context['parameters'] == wrong_params

    def test_connection_timeout_raises_access_error(self):
        """Test that connection timeout raises CursorDatabaseAccessError."""
        # Arrange
        mock_db_path = "/fake/path/to/busy.db"
        mock_query = "SELECT 1"
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            # Simulate timeout by raising OperationalError
            mock_sqlite3.connect.side_effect = sqlite3.OperationalError("database is locked")
            
            # Act & Assert
            with pytest.raises(CursorDatabaseAccessError) as exc_info:
                execute_cursor_query(mock_db_path, mock_query)
            
            assert "database is locked" in str(exc_info.value)

    def test_generic_database_error_wrapping(self):
        """Test that generic database errors are properly wrapped."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT 1"
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            # Simulate generic DatabaseError
            mock_sqlite3.connect.side_effect = sqlite3.DatabaseError("Generic database error")
            
            # Act & Assert
            with pytest.raises(CursorDatabaseAccessError) as exc_info:
                execute_cursor_query(mock_db_path, mock_query)
            
            assert "Generic database error" in str(exc_info.value)


class TestQueryExecutorParameterSafety:
    """Test parameter safety and SQL injection prevention."""

    def test_parameterized_query_prevents_sql_injection(self):
        """Test that parameterized queries safely handle malicious input."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT * FROM users WHERE name = ?"
        malicious_param = ("'; DROP TABLE users; --",)
        expected_result = []  # No results for the malicious input
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query, malicious_param)
            
            # Assert - The malicious SQL should be treated as a parameter, not executed
            assert result == expected_result
            mock_cursor.execute.assert_called_once_with(mock_query, malicious_param)
            # Verify the dangerous string was passed as a parameter, not concatenated into SQL
            args, kwargs = mock_cursor.execute.call_args
            assert args[0] == mock_query  # Original query unchanged
            assert args[1] == malicious_param  # Malicious input as parameter

    def test_none_parameters_handled_correctly(self):
        """Test that None parameters are handled correctly."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT * FROM users WHERE name = ?"
        none_params = (None,)
        expected_result = [(1, None)]
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query, none_params)
            
            # Assert
            assert result == expected_result
            mock_cursor.execute.assert_called_once_with(mock_query, none_params)

    def test_empty_parameters_tuple_handling(self):
        """Test that empty parameters tuple is handled correctly."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT COUNT(*) FROM users"
        empty_params = ()
        expected_result = [(5,)]
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query, empty_params)
            
            # Assert
            assert result == expected_result
            mock_cursor.execute.assert_called_once_with(mock_query, empty_params)


class TestQueryExecutorReturnFormat:
    """Test the return format specifications."""

    def test_return_type_is_list_of_tuples(self):
        """Test that the function returns List[Tuple[Any, ...]] as specified."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT id, name, email FROM users"
        expected_result = [
            (1, "Alice", "alice@example.com"),
            (2, "Bob", "bob@example.com"),
            (3, "Charlie", None)  # Test None handling in results
        ]
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query)
            
            # Assert
            assert isinstance(result, list)
            assert all(isinstance(row, tuple) for row in result)
            assert result == expected_result

    def test_single_column_result_format(self):
        """Test return format for single column queries."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT COUNT(*) FROM users"
        expected_result = [(42,)]  # Single tuple with one element
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query)
            
            # Assert
            assert result == expected_result
            assert isinstance(result[0], tuple)
            assert len(result[0]) == 1

    def test_mixed_data_types_in_result(self):
        """Test that mixed data types are preserved in the result."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_query = "SELECT id, name, score, is_active, created_at FROM users"
        expected_result = [
            (1, "Alice", 95.5, True, "2025-01-01 10:00:00"),
            (2, "Bob", 87, False, "2025-01-02 11:30:00"),
            (3, "Charlie", None, None, None)
        ]
        
        with patch('mcp_commit_story.cursor_db.query_executor.sqlite3') as mock_sqlite3:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = expected_result
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite3.connect.return_value.__enter__.return_value = mock_conn
            
            # Act
            result = execute_cursor_query(mock_db_path, mock_query)
            
            # Assert
            assert result == expected_result
            # Verify data types are preserved
            row = result[0]
            assert isinstance(row[0], int)    # id
            assert isinstance(row[1], str)    # name
            assert isinstance(row[2], float)  # score
            assert isinstance(row[3], bool)   # is_active
            assert isinstance(row[4], str)    # created_at 