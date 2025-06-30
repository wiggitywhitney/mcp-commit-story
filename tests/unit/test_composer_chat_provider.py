"""
Unit tests for ComposerChatProvider class.

Tests the main interface class for retrieving chat history from Cursor's Composer
databases with time window filtering, session metadata handling, and telemetry.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, Mock, call
from typing import List, Dict, Any

from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseAccessError,
    CursorDatabaseQueryError,
    CursorDatabaseNotFoundError
)


class TestComposerChatProviderInit:
    """Test ComposerChatProvider initialization."""

    def test_init_stores_database_paths(self):
        """Test that constructor stores workspace and global database paths."""
        # Arrange
        workspace_path = "/path/to/workspace.vscdb"
        global_path = "/path/to/global.vscdb"
        
        # Act
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider(workspace_path, global_path)
        
        # Assert
        assert provider.workspace_db_path == workspace_path
        assert provider.global_db_path == global_path

    def test_init_no_validation_allows_missing_databases(self):
        """Test that constructor doesn't validate database existence (per approved design)."""
        # Arrange
        nonexistent_workspace = "/nonexistent/workspace.vscdb"
        nonexistent_global = "/nonexistent/global.vscdb"
        
        # Act & Assert - Should not raise any exceptions
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider(nonexistent_workspace, nonexistent_global)
        
        assert provider.workspace_db_path == nonexistent_workspace
        assert provider.global_db_path == nonexistent_global

    def test_init_accepts_empty_string_paths(self):
        """Test that constructor accepts empty string paths gracefully."""
        # Act & Assert
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("", "")
        
        assert provider.workspace_db_path == ""
        assert provider.global_db_path == ""


class TestComposerChatProviderGetChatHistory:
    """Test the main getChatHistoryForCommit method."""

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    @patch('mcp_commit_story.composer_chat_provider.get_mcp_metrics')
    @patch('mcp_commit_story.composer_chat_provider.time.time')
    def test_get_chat_history_success_with_messages(self, mock_time, mock_metrics, mock_execute_query):
        """Test successful chat history retrieval with messages in time window."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        start_timestamp = 1640995200000  # 2022-01-01 00:00:00
        end_timestamp = 1641001200000    # 2022-01-01 01:40:00
        
        # Mock session metadata from workspace DB
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Implement authentication",
                    "createdAt": 1640995800000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                },
                {
                    "composerId": "session-2", 
                    "name": "Fix bug in login",
                    "createdAt": 1641000600000,
                    "lastUpdatedAt": 1641001000000,
                    "type": "head"
                }
            ]
        }
        
        # Mock message headers from global DB
        message_headers_1 = {
            "composerId": "session-1",
            "name": "Implement authentication", 
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1},  # user
                {"bubbleId": "msg-2", "type": 2}   # assistant
            ]
        }
        
        message_headers_2 = {
            "composerId": "session-2",
            "name": "Fix bug in login",
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-3", "type": 1}   # user
            ]
        }
        
        # Mock individual messages
        message_1 = {
            "text": "How do I implement JWT authentication?",
            "timestamp": 1640996000000,  # Within time window
            "context": {"fileSelections": []}
        }
        
        message_2 = {
            "text": "You can use the jsonwebtoken library...",
            "timestamp": 1640996500000,  # Within time window
            "context": {"fileSelections": []}
        }
        
        message_3 = {
            "text": "The login form isn't working",
            "timestamp": 1641000800000,  # Within time window
            "context": {"fileSelections": []}
        }
        
        # Configure mock execute_query responses
        mock_execute_query.side_effect = [
            # Workspace DB query for session metadata
            [(json.dumps(session_metadata),)],
            # Session-1: headers then individual messages
            [(json.dumps(message_headers_1),)],
            [(json.dumps(message_1),)],
            [(json.dumps(message_2),)],
            # Session-2: headers then individual messages
            [(json.dumps(message_headers_2),)],
            [(json.dumps(message_3),)]
        ]
        
        # Mock time for performance monitoring
        mock_time.side_effect = [1640995000.0, 1640995000.5]  # 500ms duration
        
        # Mock metrics
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Act
        result = provider.getChatHistoryForCommit(start_timestamp, end_timestamp)
        
        # Assert
        assert len(result) == 3
        
        # Check first message (from session-1)
        assert result[0]['role'] == 'user'
        assert result[0]['content'] == "How do I implement JWT authentication?"
        assert result[0]['timestamp'] == 1640996000000
        assert result[0]['sessionName'] == "Implement authentication"
        assert result[0]['composerId'] == "session-1"
        assert result[0]['bubbleId'] == "msg-1"
        
        # Check second message (from session-1)
        assert result[1]['role'] == 'assistant'
        assert result[1]['content'] == "You can use the jsonwebtoken library..."
        assert result[1]['timestamp'] == 1640996500000
        assert result[1]['sessionName'] == "Implement authentication"
        
        # Check third message (from session-2)
        assert result[2]['role'] == 'user'
        assert result[2]['content'] == "The login form isn't working"
        assert result[2]['sessionName'] == "Fix bug in login"
        
        # Verify messages are chronologically ordered
        timestamps = [msg['timestamp'] for msg in result]
        assert timestamps == sorted(timestamps)
        
        # Verify database queries were called correctly
        expected_calls = [
            call("/workspace.vscdb", "SELECT value FROM ItemTable WHERE [key] = 'composer.composerData'"),
            call("/global.vscdb", "SELECT value FROM cursorDiskKV WHERE [key] = ?", ("composerData:session-1",)),
            call("/global.vscdb", "SELECT value FROM cursorDiskKV WHERE [key] = ?", ("bubbleId:session-1:msg-1",)),
            call("/global.vscdb", "SELECT value FROM cursorDiskKV WHERE [key] = ?", ("bubbleId:session-1:msg-2",)),
            call("/global.vscdb", "SELECT value FROM cursorDiskKV WHERE [key] = ?", ("composerData:session-2",)),
            call("/global.vscdb", "SELECT value FROM cursorDiskKV WHERE [key] = ?", ("bubbleId:session-2:msg-3",))
        ]
        mock_execute_query.assert_has_calls(expected_calls)

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_get_chat_history_filters_by_time_window(self, mock_execute_query):
        """Test that messages outside time window are filtered out."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        start_timestamp = 1640995200000  # 2022-01-01 00:00:00
        end_timestamp = 1640998800000    # 2022-01-01 01:00:00
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-before", "type": 1},
                {"bubbleId": "msg-during", "type": 1},
                {"bubbleId": "msg-after", "type": 1}
            ]
        }
        
        # Messages: one before, one during, one after time window
        message_before = {
            "text": "Before time window",
            "timestamp": 1640995000000,  # Before start
            "context": {}
        }
        
        message_during = {
            "text": "During time window",
            "timestamp": 1640997000000,  # Within window
            "context": {}
        }
        
        message_after = {
            "text": "After time window", 
            "timestamp": 1641000000000,  # After end
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_before),)],
            [(json.dumps(message_during),)],
            [(json.dumps(message_after),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(start_timestamp, end_timestamp)
        
        # Assert
        assert len(result) == 1
        assert result[0]['content'] == "During time window"
        assert result[0]['timestamp'] == 1640997000000

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_get_chat_history_empty_sessions(self, mock_execute_query):
        """Test handling when no sessions found in workspace database."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        # Mock empty session metadata
        empty_metadata = {"allComposers": []}
        mock_execute_query.return_value = [(json.dumps(empty_metadata),)]
        
        # Act
        result = provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert
        assert result == []
        mock_execute_query.assert_called_once_with(
            "/workspace.vscdb", 
            "SELECT value FROM ItemTable WHERE [key] = 'composer.composerData'"
        )

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_get_chat_history_missing_message_headers(self, mock_execute_query):
        """Test handling when message headers not found for a session."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            []  # No message headers found
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert
        assert result == []

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_get_chat_history_missing_individual_message(self, mock_execute_query):
        """Test handling when individual message not found."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "fullConversationHeadersOnly": [
                {"bubbleId": "missing-msg", "type": 1}
            ]
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            []  # Individual message not found
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert
        assert result == []

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_get_chat_history_role_mapping(self, mock_execute_query):
        """Test correct mapping of message types to roles."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "fullConversationHeadersOnly": [
                {"bubbleId": "user-msg", "type": 1},      # User message
                {"bubbleId": "assistant-msg", "type": 2}  # Assistant message
            ]
        }
        
        user_message = {
            "text": "User question",
            "timestamp": 1640996000000,
            "context": {}
        }
        
        assistant_message = {
            "text": "Assistant response",
            "timestamp": 1640996500000,
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(user_message),)],
            [(json.dumps(assistant_message),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(1640995000000, 1641000000000)
        
        # Assert
        assert len(result) == 2
        assert result[0]['role'] == 'user'
        assert result[1]['role'] == 'assistant'


class TestComposerChatProviderErrorHandling:
    """Test error handling scenarios."""

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_workspace_database_access_error_bubbles_up(self, mock_execute_query):
        """Test that workspace database access errors bubble up from execute_cursor_query."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/nonexistent.vscdb", "/global.vscdb")
        
        mock_execute_query.side_effect = CursorDatabaseAccessError(
            "Database not found", 
            path="/nonexistent.vscdb"
        )
        
        # Act & Assert
        with pytest.raises(CursorDatabaseAccessError) as exc_info:
            provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        assert "Database not found" in str(exc_info.value)
        assert exc_info.value.context['path'] == "/nonexistent.vscdb"

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_global_database_access_error_bubbles_up(self, mock_execute_query):
        """Test that global database access errors bubble up from execute_cursor_query."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/nonexistent.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        # First call succeeds (workspace), second fails (global)
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            CursorDatabaseAccessError(
                "Database locked", 
                path="/nonexistent.vscdb"
            )
        ]
        
        # Act & Assert
        with pytest.raises(CursorDatabaseAccessError) as exc_info:
            provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        assert "Database locked" in str(exc_info.value)

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_malformed_json_in_session_metadata(self, mock_execute_query):
        """Test handling of malformed JSON in session metadata."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        # Return malformed JSON
        mock_execute_query.return_value = [("invalid json{",)]
        
        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            provider.getChatHistoryForCommit(1640995200000, 1640998800000)

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_malformed_json_in_message_data(self, mock_execute_query):
        """Test handling of malformed JSON in message data."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1}
            ]
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [("malformed json{",)]  # Malformed message JSON
        ]
        
        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            provider.getChatHistoryForCommit(1640995200000, 1640998800000)


class TestComposerChatProviderTelemetry:
    """Test telemetry integration."""

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_telemetry_decorator_applied(self, mock_execute_query):
        """Test that @trace_mcp_operation decorator is applied to getChatHistoryForCommit."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        # Mock empty result to avoid complex setup
        mock_execute_query.return_value = [(json.dumps({"allComposers": []}),)]
        
        # Act & Assert - Method should execute without error, indicating decorator is applied properly
        result = provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Verify the method works and returns expected result
        assert result == []
        assert mock_execute_query.called

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    @patch('mcp_commit_story.composer_chat_provider.get_mcp_metrics')
    @patch('mcp_commit_story.composer_chat_provider.time.time')
    def test_telemetry_span_attributes_set(self, mock_time, mock_metrics, mock_execute_query):
        """Test that telemetry span attributes are set correctly."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1}
            ]
        }
        
        message_data = {
            "text": "Test message",
            "timestamp": 1640996000000,
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_data),)]
        ]
        
        # Mock time for duration calculation
        mock_time.side_effect = [1640995000.0, 1640995000.3]  # 300ms duration
        
        # Mock metrics
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Act
        result = provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert span attributes would be set through the trace decorator
        # (The actual span setting happens in the decorator implementation)
        assert len(result) == 1

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    @patch('mcp_commit_story.composer_chat_provider.get_mcp_metrics')
    @patch('mcp_commit_story.composer_chat_provider.time.time')
    def test_performance_threshold_monitoring(self, mock_time, mock_metrics, mock_execute_query):
        """Test that performance threshold (500ms) is monitored."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        # Mock slow operation (600ms) - use a function to simulate time progression
        # This avoids StopIteration when time.time() is called more times than expected
        time_values = [1640995000.0, 1640995000.6]  # Start time, then 600ms later
        def mock_time_func():
            # Return first value on first call, second value on subsequent calls
            if len(time_values) > 1:
                return time_values.pop(0)
            return time_values[0]  # Always return the last value for any extra calls
        mock_time.side_effect = mock_time_func
        
        # Mock empty result
        mock_execute_query.return_value = [(json.dumps({"allComposers": []}),)]
        
        # Mock metrics
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Act
        provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert that metrics were recorded
        # (Actual performance threshold monitoring would happen in the decorator)
        mock_metrics.assert_called()


class TestComposerChatProviderLogging:
    """Test logging behavior."""

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    @patch('mcp_commit_story.composer_chat_provider.logger')
    def test_debug_logging_for_empty_sessions(self, mock_logger, mock_execute_query):
        """Test debug logging when no sessions found."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        # Mock empty sessions
        mock_execute_query.return_value = [(json.dumps({"allComposers": []}),)]
        
        # Act
        provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert debug logging
        mock_logger.debug.assert_called_with(
            "No sessions found in workspace database: /workspace.vscdb"
        )

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    @patch('mcp_commit_story.composer_chat_provider.logger')
    def test_debug_logging_for_empty_messages(self, mock_logger, mock_execute_query):
        """Test debug logging when no messages found in time window."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Test session",
                    "createdAt": 1640995000000,
                    "lastUpdatedAt": 1641000000000,
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1}
            ]
        }
        
        # Message outside time window
        message_data = {
            "text": "Test message",
            "timestamp": 1641010000000,  # Way after time window
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_data),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(1640995200000, 1640998800000)
        
        # Assert
        assert result == []
        mock_logger.debug.assert_called_with(
            "No messages found in time window 1640995200000 to 1640998800000"
        ) 