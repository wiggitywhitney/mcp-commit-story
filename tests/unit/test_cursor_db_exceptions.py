"""
Unit tests for cursor database exception system.

Tests the comprehensive error handling system with custom exceptions
for different failure scenarios in the cursor database module.
"""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

# Import the enhanced exception system we're about to create (will fail initially - that's expected in TDD)
from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseError,
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError,
    CursorDatabaseSchemaError,
    CursorDatabaseQueryError,
    format_error_message,
    get_troubleshooting_hint
)

# Import connection functions to test integration
from mcp_commit_story.cursor_db.connection import (
    get_cursor_chat_database,
    query_cursor_chat_database,
    cursor_chat_database_context
)


class TestCursorDatabaseExceptionHierarchy:
    """Test the exception class hierarchy and inheritance."""
    
    def test_base_exception_inheritance(self):
        """Test that all custom exceptions inherit from CursorDatabaseError."""
        assert issubclass(CursorDatabaseNotFoundError, CursorDatabaseError)
        assert issubclass(CursorDatabaseAccessError, CursorDatabaseError)
        assert issubclass(CursorDatabaseSchemaError, CursorDatabaseError)
        assert issubclass(CursorDatabaseQueryError, CursorDatabaseError)
    
    def test_base_exception_attributes(self):
        """Test that base exception properly stores message and context."""
        error = CursorDatabaseError("Test error", test_context="test_value")
        
        assert error.message == "Test error"
        assert "test_context" in error.context
        assert error.context["test_context"] == "test_value"
        assert "timestamp" in error.context
        assert "platform" in error.context
    
    def test_context_sanitization(self):
        """Test that sensitive information is properly sanitized."""
        error = CursorDatabaseError(
            "Test error",
            password="secret123",
            api_key="key123",
            normal_field="normal_value"
        )
        
        assert error.context["password"] == "[REDACTED]"
        assert error.context["api_key"] == "[REDACTED]"
        assert error.context["normal_field"] == "normal_value"


class TestSpecificExceptionTypes:
    """Test specific exception types and their behavior."""
    
    def test_not_found_error_context(self):
        """Test CursorDatabaseNotFoundError with path context."""
        error = CursorDatabaseNotFoundError(
            "Database not found",
            path="/test/path",
            search_type="auto_discovery"
        )
        
        assert error.context["path"] == "/test/path"
        assert error.context["search_type"] == "auto_discovery"
        assert "cursor" in error.troubleshooting_hint.lower()
    
    def test_access_error_context(self):
        """Test CursorDatabaseAccessError with permission context."""
        error = CursorDatabaseAccessError(
            "Permission denied",
            path="/test/path",
            permission_type="read"
        )
        
        assert error.context["path"] == "/test/path"
        assert error.context["permission_type"] == "read"
        assert "permission" in error.troubleshooting_hint.lower()
    
    def test_schema_error_context(self):
        """Test CursorDatabaseSchemaError with schema context."""
        error = CursorDatabaseSchemaError(
            "Table missing",
            table_name="messages",
            expected_schema="CREATE TABLE messages..."
        )
        
        assert error.context["table_name"] == "messages"
        assert error.context["expected_schema"] == "CREATE TABLE messages..."
        assert "schema" in error.troubleshooting_hint.lower()
    
    def test_query_error_context(self):
        """Test CursorDatabaseQueryError with SQL context."""
        error = CursorDatabaseQueryError(
            "SQL syntax error",
            sql="SELECT * FROM invalid_table",
            parameters=("param1", "param2")
        )
        
        assert error.context["sql"] == "SELECT * FROM invalid_table"
        assert error.context["parameters"] == ("param1", "param2")
        assert "query" in error.troubleshooting_hint.lower()


class TestTroubleshootingHints:
    """Test troubleshooting hint generation."""
    
    def test_not_found_hints(self):
        """Test hints for database not found errors."""
        context = {"path": "/test/path"}
        hint = get_troubleshooting_hint("cursordatabasenotfounderror", context)
        
        assert "recently" in hint.lower()
        assert "workspace" in hint.lower()
        assert "/test/path" in hint
    
    def test_access_hints(self):
        """Test hints for access permission errors."""
        context = {"path": "/test/path", "permission_type": "read"}
        hint = get_troubleshooting_hint("cursordatabaseaccesserror", context)
        
        assert "permission" in hint.lower()
        assert "read access" in hint.lower()
        assert "/test/path" in hint
    
    def test_schema_hints(self):
        """Test hints for schema mismatch errors."""
        context = {"table_name": "messages"}
        hint = get_troubleshooting_hint("cursordatabaseschemaerror", context)
        
        assert "schema" in hint.lower()
        assert "version" in hint.lower()
        assert "messages" in hint
    
    def test_query_hints_with_parameter_mismatch(self):
        """Test hints for query errors with parameter count mismatch."""
        context = {
            "sql": "SELECT * FROM table WHERE id = ? AND name = ?",
            "parameters": ("value1",)  # Only 1 parameter for 2 placeholders
        }
        hint = get_troubleshooting_hint("cursordatabasequeryerror", context)
        
        assert "parameter" in hint.lower()
        assert "2 placeholders" in hint
        assert "1 parameters" in hint
    
    def test_default_hint(self):
        """Test default hint for unknown error types."""
        hint = get_troubleshooting_hint("unknownerror", {})
        
        assert "recently" in hint.lower()
        assert "workspace" in hint.lower()


class TestErrorMessageFormatting:
    """Test error message formatting functionality."""
    
    def test_basic_message_formatting(self):
        """Test basic error message formatting."""
        formatted = format_error_message("Basic error message")
        assert formatted == "Basic error message"
    
    def test_message_with_context(self):
        """Test error message formatting with context."""
        context = {
            "path": "/test/path",
            "operation": "query"
        }
        formatted = format_error_message("Error occurred", context)
        
        assert "Error occurred" in formatted
        assert "Path: /test/path" in formatted
        assert "Operation: query" in formatted
    
    def test_message_with_long_sql(self):
        """Test error message formatting with long SQL."""
        # Make SQL longer than 100 characters to trigger truncation
        long_sql = "SELECT * FROM very_long_table_name WHERE condition1 = ? AND condition2 = ? AND condition3 = ? AND condition4 = ? AND condition5 = ?"
        context = {"sql": long_sql}
        formatted = format_error_message("SQL error", context)
        
        assert "SQL error" in formatted
        assert "SQL:" in formatted
        assert "..." in formatted  # Should be truncated
    
    def test_message_with_troubleshooting_hint(self):
        """Test error message formatting with troubleshooting hint."""
        formatted = format_error_message(
            "Error occurred",
            troubleshooting_hint="Try this solution"
        )
        
        assert "Error occurred" in formatted
        assert "Troubleshooting: Try this solution" in formatted


class TestConnectionFunctionIntegration:
    """Test integration with connection functions."""
    
    def test_get_database_not_found_error(self):
        """Test that get_cursor_chat_database raises proper exception when database not found."""
        with patch('mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths', return_value=[]):
            with pytest.raises(CursorDatabaseNotFoundError) as exc_info:
                get_cursor_chat_database()
            
            assert "no valid" in exc_info.value.message.lower()
            assert exc_info.value.context["search_type"] == "auto_discovery"
    
    def test_get_database_invalid_user_path(self):
        """Test that get_cursor_chat_database raises proper exception for invalid user path."""
        with pytest.raises(CursorDatabaseNotFoundError) as exc_info:
            get_cursor_chat_database("/nonexistent/path/database.db")
        
        assert "not found" in exc_info.value.message.lower()
        assert exc_info.value.context["path"] == "/nonexistent/path/database.db"
    
    def test_query_database_access_error(self):
        """Test that query_cursor_chat_database raises access error for permission issues."""
        # Create a temporary file but make it unreadable
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            # Store original permissions
            original_mode = os.stat(temp_path).st_mode
        
        try:
            # Remove read permissions
            os.chmod(temp_path, 0o000)
            
            # The function should detect permission issues and raise CursorDatabaseAccessError
            with pytest.raises(CursorDatabaseAccessError) as exc_info:
                query_cursor_chat_database(temp_path, "SELECT 1")
            
            assert "permission" in exc_info.value.message.lower()
            assert exc_info.value.context["path"] == temp_path
            assert exc_info.value.context["permission_type"] == "read"
        finally:
            # Restore original permissions before cleanup
            os.chmod(temp_path, original_mode)
            os.unlink(temp_path)
    
    def test_query_database_sql_syntax_error(self):
        """Test that query_cursor_chat_database raises schema error for missing table."""
        # Create a valid SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create a simple database
            conn = sqlite3.connect(temp_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            # Missing table is a schema error, not a query syntax error
            with pytest.raises(CursorDatabaseSchemaError) as exc_info:  # Changed from CursorDatabaseQueryError
                query_cursor_chat_database(temp_path, "SELECT * FROM nonexistent_table")
            
            assert "schema" in exc_info.value.message.lower()  # Changed assertion
        finally:
            os.unlink(temp_path)
    
    def test_context_manager_exception_handling(self):
        """Test that context manager properly handles exceptions."""
        with patch('mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths', return_value=[]):
            with pytest.raises(CursorDatabaseNotFoundError):
                with cursor_chat_database_context() as db_path:
                    # This should not be reached
                    assert False, "Context manager should have raised exception"


class TestExceptionStringRepresentation:
    """Test string representation of exceptions."""
    
    def test_exception_str_representation(self):
        """Test that exceptions have proper string representation."""
        error = CursorDatabaseError("Test error message")
        assert str(error) == "Test error message"
    
    def test_exception_with_context_str(self):
        """Test that exceptions with context still use basic message for str."""
        error = CursorDatabaseNotFoundError(
            "Database not found",
            path="/test/path"
        )
        assert str(error) == "Database not found" 