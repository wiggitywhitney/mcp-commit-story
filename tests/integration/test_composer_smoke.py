"""
Smoke tests for Composer integration - basic functionality verification.

These tests verify that core components can instantiate and perform basic operations
using test databases. They are designed to run quickly and provide fast feedback
on fundamental system health.

Test Philosophy:
- Quick validation of core component functionality
- Use test databases (no dependency on real Cursor installation)
- Focus on "does it work" rather than "does it work correctly"
- Catch basic import, instantiation, and connection issues
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mcp_commit_story.composer_chat_provider import ComposerChatProvider
from mcp_commit_story.cursor_db.query_executor import execute_cursor_query
from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError
)


class TestComposerChatProviderSmoke:
    """Smoke tests for ComposerChatProvider basic functionality."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    @pytest.fixture
    def provider(self, test_db_paths):
        """Create ComposerChatProvider instance with test databases."""
        return ComposerChatProvider(
            test_db_paths["workspace"],
            test_db_paths["global"]
        )
    
    def test_provider_can_instantiate(self, test_db_paths):
        """Test that ComposerChatProvider can be instantiated."""
        provider = ComposerChatProvider(
            test_db_paths["workspace"],
            test_db_paths["global"]
        )
        
        assert provider is not None
        assert provider.workspace_db_path == test_db_paths["workspace"]
        assert provider.global_db_path == test_db_paths["global"]
    
    def test_can_connect_to_workspace_database(self, test_db_paths):
        """Test basic connection to workspace database."""
        result = execute_cursor_query(
            test_db_paths["workspace"],
            "SELECT COUNT(*) FROM ItemTable"
        )
        
        assert result is not None
        assert len(result) == 1
        assert result[0][0] >= 1  # At least one item (composer.composerData)
    
    def test_can_connect_to_global_database(self, test_db_paths):
        """Test basic connection to global database."""
        result = execute_cursor_query(
            test_db_paths["global"],
            "SELECT COUNT(*) FROM cursorDiskKV"
        )
        
        assert result is not None
        assert len(result) == 1
        assert result[0][0] >= 3  # At least 3 sessions worth of data
    
    def test_can_retrieve_session_metadata(self, provider):
        """Test retrieval of session metadata from workspace database."""
        sessions = provider._get_session_metadata()
        
        assert sessions is not None
        assert isinstance(sessions, list)
        assert len(sessions) == 3  # Expected 3 test sessions
        
        # Verify session structure
        for session in sessions:
            assert "composerId" in session
            assert "name" in session
            assert "type" in session
            assert session["type"] == "head"
    
    def test_can_retrieve_individual_messages(self, provider):
        """Test retrieval of individual message data."""
        # Test with known session from test data
        test_session_id = "test-session-1"
        test_bubble_id = "bubble-1-1"
        
        message = provider._get_individual_message(test_session_id, test_bubble_id)
        
        assert message is not None
        assert isinstance(message, dict)
        assert "text" in message  # Raw message data uses 'text' field
        assert "messageType" in message
        assert "timestamp" in message
    
    def test_returns_correct_data_structure(self, provider):
        """Test that getChatHistoryForCommit returns expected data structure."""
        # Use a wide time window to catch all test messages
        start_time = 0  # Unix epoch
        end_time = 9999999999999  # Far future
        
        messages = provider.getChatHistoryForCommit(start_time, end_time)
        
        assert messages is not None
        assert isinstance(messages, list)
        
        if messages:  # If messages were found
            for message in messages:
                assert isinstance(message, dict)
                # Verify required fields
                required_fields = ['role', 'content', 'timestamp', 'sessionName', 'composerId', 'bubbleId']
                for field in required_fields:
                    assert field in message, f"Missing required field: {field}"
                
                # Verify role values
                assert message['role'] in ['user', 'assistant']
    
    def test_handles_missing_databases_gracefully(self):
        """Test graceful handling of missing database files."""
        nonexistent_workspace = "/path/to/nonexistent/workspace.vscdb"
        nonexistent_global = "/path/to/nonexistent/global.vscdb"
        
        provider = ComposerChatProvider(nonexistent_workspace, nonexistent_global)
        
        # Should raise appropriate exceptions, not crash
        with pytest.raises((CursorDatabaseNotFoundError, CursorDatabaseAccessError)):
            provider.getChatHistoryForCommit(0, 9999999999999)


class TestQueryExecutorSmoke:
    """Smoke tests for database query executor functionality."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    def test_execute_simple_query(self, test_db_paths):
        """Test execution of a simple SELECT query."""
        result = execute_cursor_query(
            test_db_paths["workspace"],
            "SELECT key FROM ItemTable WHERE key = ?",
            ("composer.composerData",)
        )
        
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == "composer.composerData"
    
    def test_execute_with_parameters(self, test_db_paths):
        """Test parameterized query execution."""
        result = execute_cursor_query(
            test_db_paths["global"],
            "SELECT key FROM cursorDiskKV WHERE key LIKE ?",
            ("composerData:%",)
        )
        
        assert result is not None
        assert len(result) == 3  # Should find 3 session headers
    
    def test_handles_malformed_query(self, test_db_paths):
        """Test handling of malformed SQL queries."""
        with pytest.raises(Exception):  # Should raise some form of database error
            execute_cursor_query(
                test_db_paths["workspace"],
                "INVALID SQL SYNTAX HERE"
            )
    
    def test_handles_nonexistent_database(self):
        """Test handling of nonexistent database files."""
        with pytest.raises((CursorDatabaseNotFoundError, CursorDatabaseAccessError)):
            execute_cursor_query(
                "/path/to/nonexistent.db",
                "SELECT 1"
            )


class TestDatabaseContentSmoke:
    """Smoke tests to verify test database content matches expectations."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    def test_workspace_has_composer_data(self, test_db_paths):
        """Test that workspace database contains expected composer data."""
        result = execute_cursor_query(
            test_db_paths["workspace"],
            "SELECT value FROM ItemTable WHERE key = ?",
            ("composer.composerData",)
        )
        
        assert result is not None
        assert len(result) == 1
        
        # Parse JSON and verify structure
        import json
        composer_data = json.loads(result[0][0])
        assert "allComposers" in composer_data
        assert len(composer_data["allComposers"]) == 3
    
    def test_global_has_session_headers(self, test_db_paths):
        """Test that global database contains session headers."""
        result = execute_cursor_query(
            test_db_paths["global"],
            "SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE 'composerData:%'"
        )
        
        assert result is not None
        assert result[0][0] == 3  # Should have 3 session headers
    
    def test_global_has_message_data(self, test_db_paths):
        """Test that global database contains message data."""
        result = execute_cursor_query(
            test_db_paths["global"],
            "SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'"
        )
        
        assert result is not None
        assert result[0][0] == 15  # Should have 15 individual messages (5+4+6)
    
    def test_message_timestamps_are_reasonable(self, test_db_paths):
        """Test that message timestamps are within reasonable range (not ancient/future)."""
        import json
        import time
        
        # Get all bubble messages
        result = execute_cursor_query(
            test_db_paths["global"],
            "SELECT value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' LIMIT 1"
        )
        
        assert result is not None
        assert len(result) >= 1
        
        # Parse message and check timestamp is reasonable (not ancient or far future)
        message_data = json.loads(result[0][0])
        timestamp = message_data["timestamp"]
        current_time = int(time.time() * 1000)
        
        # Timestamp should be within reasonable range (30 days old to 1 day future for timezone tolerance)
        thirty_days_ago = current_time - (30 * 24 * 60 * 60 * 1000)
        one_day_future = current_time + (24 * 60 * 60 * 1000)
        
        assert timestamp > thirty_days_ago, f"Timestamp {timestamp} is too old (more than 30 days)"
        assert timestamp <= one_day_future, f"Timestamp {timestamp} is too far in the future" 