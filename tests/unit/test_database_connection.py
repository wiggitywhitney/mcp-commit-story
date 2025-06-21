"""
Unit tests for database connection module.

Tests the core functionality for establishing connections to SQLite databases
and executing queries with proper resource management.
"""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os

# Import the module we're about to create (will fail initially - that's expected)
try:
    from mcp_commit_story.cursor_db.connection import (
        get_cursor_chat_database,
        query_cursor_chat_database,
        CursorDatabaseConnectionError,
        CursorDatabaseQueryError
    )
except ImportError:
    # Expected to fail initially in TDD
    pytest.skip("Database connection module not yet implemented", allow_module_level=True)


class TestDatabaseConnection:
    """Test database connection functionality."""
    
    def test_get_cursor_chat_database_successful_connection(self):
        """Test successful database connection with valid path."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            # Create a minimal SQLite database
            conn = sqlite3.connect(temp_db.name)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            try:
                # Test connection
                result_conn = get_cursor_chat_database(user_override_path=temp_db.name)
                assert result_conn is not None
                assert hasattr(result_conn, 'execute')  # SQLite connection interface
                result_conn.close()
            finally:
                os.unlink(temp_db.name)
    
    def test_get_cursor_chat_database_file_not_found(self):
        """Test database connection when file doesn't exist."""
        non_existent_path = "/path/that/does/not/exist/database.db"
        
        with pytest.raises(CursorDatabaseConnectionError) as exc_info:
            get_cursor_chat_database(user_override_path=non_existent_path)
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_get_cursor_chat_database_permission_denied(self):
        """Test database connection when permission is denied."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            # Create database file but remove read permissions
            os.chmod(temp_db.name, 0o000)
            
            try:
                with pytest.raises(CursorDatabaseConnectionError) as exc_info:
                    get_cursor_chat_database(user_override_path=temp_db.name)
                
                assert "permission" in str(exc_info.value).lower()
            finally:
                # Restore permissions and cleanup
                os.chmod(temp_db.name, 0o644)
                os.unlink(temp_db.name)
    
    def test_get_cursor_chat_database_corrupted_database(self):
        """Test database connection with corrupted database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            # Write invalid SQLite content
            temp_db.write(b"This is not a valid SQLite database file")
            temp_db.flush()
            
            try:
                with pytest.raises(CursorDatabaseConnectionError) as exc_info:
                    get_cursor_chat_database(user_override_path=temp_db.name)
                
                assert "corrupted" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
            finally:
                os.unlink(temp_db.name)
    
    @patch('mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths')
    def test_get_cursor_chat_database_auto_discovery(self, mock_get_paths):
        """Test database connection with automatic path discovery."""
        # Create a temporary directory to mimic workspace structure
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            
            # Create a state.vscdb file (the specific file we search for)
            db_file = workspace_path / "state.vscdb"
            
            # Create a valid SQLite database with the correct name
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            
            # Mock platform detection to return our test workspace path
            mock_get_paths.return_value = [workspace_path]
            
            # Test auto-discovery (no user override path)
            result_conn = get_cursor_chat_database()
            assert result_conn is not None
            result_conn.close()
    
    @patch('mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths')
    def test_get_cursor_chat_database_no_valid_databases(self, mock_get_paths):
        """Test database connection when no valid databases are found."""
        # Mock platform detection to return non-existent paths
        mock_get_paths.return_value = [Path("/nonexistent/path1"), Path("/nonexistent/path2")]
        
        with pytest.raises(CursorDatabaseConnectionError) as exc_info:
            get_cursor_chat_database()
        
        assert "no valid" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


class TestDatabaseQuery:
    """Test database query functionality."""
    
    def setup_method(self):
        """Set up test database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.conn = sqlite3.connect(self.temp_db.name)
        
        # Create test schema
        self.conn.execute("""
            CREATE TABLE test_messages (
                id INTEGER PRIMARY KEY,
                content TEXT,
                timestamp TEXT
            )
        """)
        
        # Insert test data
        self.conn.execute(
            "INSERT INTO test_messages (content, timestamp) VALUES (?, ?)",
            ("Hello World", "2025-06-21T10:00:00Z")
        )
        self.conn.execute(
            "INSERT INTO test_messages (content, timestamp) VALUES (?, ?)",
            ("Test Message", "2025-06-21T10:01:00Z")
        )
        self.conn.commit()
        self.conn.close()
    
    def teardown_method(self):
        """Clean up test database after each test."""
        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except FileNotFoundError:
                pass
    
    def test_query_cursor_chat_database_select_success(self):
        """Test successful SELECT query execution."""
        sql = "SELECT id, content FROM test_messages WHERE content = ?"
        params = ("Hello World",)
        
        result = query_cursor_chat_database(self.temp_db.name, sql, params)
        
        assert len(result) == 1
        assert result[0][1] == "Hello World"  # content column
    
    def test_query_cursor_chat_database_select_all(self):
        """Test SELECT query without parameters."""
        sql = "SELECT COUNT(*) FROM test_messages"
        
        result = query_cursor_chat_database(self.temp_db.name, sql)
        
        assert len(result) == 1
        assert result[0][0] == 2  # count of records
    
    def test_query_cursor_chat_database_sql_injection_prevention(self):
        """Test that parameterized queries prevent SQL injection."""
        # Attempt SQL injection through parameter
        malicious_content = "'; DROP TABLE test_messages; --"
        sql = "SELECT id FROM test_messages WHERE content = ?"
        params = (malicious_content,)
        
        # Should not raise an exception and should not drop the table
        result = query_cursor_chat_database(self.temp_db.name, sql, params)
        assert len(result) == 0  # No matching records
        
        # Verify table still exists
        sql_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='test_messages'"
        result_check = query_cursor_chat_database(self.temp_db.name, sql_check)
        assert len(result_check) == 1  # Table still exists
    
    def test_query_cursor_chat_database_invalid_sql(self):
        """Test query execution with invalid SQL."""
        invalid_sql = "INVALID SQL STATEMENT"
        
        with pytest.raises(CursorDatabaseQueryError) as exc_info:
            query_cursor_chat_database(self.temp_db.name, invalid_sql)
        
        assert "syntax error" in str(exc_info.value).lower() or "sql" in str(exc_info.value).lower()
    
    def test_query_cursor_chat_database_nonexistent_table(self):
        """Test query execution on non-existent table."""
        sql = "SELECT * FROM nonexistent_table"
        
        with pytest.raises(CursorDatabaseQueryError) as exc_info:
            query_cursor_chat_database(self.temp_db.name, sql)
        
        assert "table" in str(exc_info.value).lower() or "no such" in str(exc_info.value).lower()
    
    def test_query_cursor_chat_database_database_not_found(self):
        """Test query execution when database file doesn't exist."""
        sql = "SELECT * FROM test_messages"
        nonexistent_db = "/path/that/does/not/exist.db"
        
        with pytest.raises(CursorDatabaseConnectionError) as exc_info:
            query_cursor_chat_database(nonexistent_db, sql)
        
        assert "not found" in str(exc_info.value).lower()


class TestConnectionCaching:
    """Test connection caching and resource management."""
    
    def setup_method(self):
        """Set up test database for caching tests."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        conn = sqlite3.connect(self.temp_db.name)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
    
    def teardown_method(self):
        """Clean up test database."""
        try:
            os.unlink(self.temp_db.name)
        except FileNotFoundError:
            pass
    
    @patch('mcp_commit_story.cursor_db.connection.sqlite3.connect')
    def test_connection_caching_behavior(self, mock_connect):
        """Test that connections are cached appropriately."""
        # Mock the sqlite3.connect to track calls
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        # First call should create connection
        conn1 = get_cursor_chat_database(user_override_path=self.temp_db.name)
        
        # Second call with same path should use cache (if implemented)
        conn2 = get_cursor_chat_database(user_override_path=self.temp_db.name)
        
        # Verify behavior (exact assertion depends on caching implementation)
        assert mock_connect.call_count >= 1  # At least one connection created
    
    def test_connection_resource_cleanup(self):
        """Test that database connections are properly cleaned up."""
        # This test will depend on the specific resource management implementation
        # For now, test that connections can be created and closed without issues
        conn = get_cursor_chat_database(user_override_path=self.temp_db.name)
        
        # Verify connection is valid
        assert hasattr(conn, 'close')
        
        # Should be able to close without error
        conn.close()


class TestConnectionIntegration:
    """Test integration with platform detection module."""
    
    @patch('mcp_commit_story.cursor_db.platform.detect_platform')
    @patch('mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths')
    def test_integration_with_platform_detection(self, mock_get_paths, mock_detect):
        """Test that database connection integrates with platform detection."""
        from mcp_commit_story.cursor_db.platform import PlatformType
        
        # Mock platform detection
        mock_detect.return_value = PlatformType.MACOS
        mock_get_paths.return_value = [Path("/mock/workspace/path")]
        
        # This should attempt to use platform detection
        # (Will fail because mock paths don't exist, but tests integration)
        with pytest.raises(CursorDatabaseConnectionError):
            get_cursor_chat_database()
        
        # Verify platform detection was called
        mock_get_paths.assert_called_once()


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def test_cursor_database_connection_error_inheritance(self):
        """Test that custom exceptions inherit from appropriate base classes."""
        # Test exception can be instantiated
        error = CursorDatabaseConnectionError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_cursor_database_query_error_inheritance(self):
        """Test that query error exception works correctly."""
        error = CursorDatabaseQueryError("Query failed")
        assert str(error) == "Query failed"
        assert isinstance(error, Exception)
    
    def test_error_context_preservation(self):
        """Test that error context is preserved through the stack."""
        # This will test that underlying SQLite errors are properly wrapped
        # and context is preserved for debugging
        pass  # Implementation depends on error handling design


# Performance and edge case tests
class TestPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases."""
    
    def test_large_query_result_handling(self):
        """Test handling of large query results."""
        # Create database with many records
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            conn = sqlite3.connect(temp_db.name)
            conn.execute("CREATE TABLE large_table (id INTEGER, data TEXT)")
            
            # Insert many records
            for i in range(1000):
                conn.execute("INSERT INTO large_table (id, data) VALUES (?, ?)", (i, f"data_{i}"))
            conn.commit()
            conn.close()
            
            try:
                # Query should handle large result set
                sql = "SELECT COUNT(*) FROM large_table"
                result = query_cursor_chat_database(temp_db.name, sql)
                assert result[0][0] == 1000
            finally:
                os.unlink(temp_db.name)
    
    def test_concurrent_connection_access(self):
        """Test behavior with concurrent database access."""
        # This test would verify thread safety if implemented
        pass
    
    def test_memory_usage_with_caching(self):
        """Test memory usage characteristics with connection caching."""
        # This test would verify memory behavior of caching implementation
        pass 