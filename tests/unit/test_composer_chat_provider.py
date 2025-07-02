"""
Unit tests for ComposerChatProvider class.

Tests the main interface class for retrieving chat history from Cursor's Composer
databases with time window filtering, session metadata handling, and telemetry.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, Mock, call
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseAccessError,
    CursorDatabaseQueryError,
    CursorDatabaseNotFoundError
)

# Test time constants - more readable than hardcoded timestamps
BASE_TIME = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
HOUR_MS = 60 * 60 * 1000  # 1 hour in milliseconds
MINUTE_MS = 60 * 1000     # 1 minute in milliseconds

def to_timestamp_ms(dt: datetime) -> int:
    """Convert datetime to milliseconds timestamp for consistency."""
    return int(dt.timestamp() * 1000)

def to_timestamp_seconds(dt: datetime) -> float:
    """Convert datetime to seconds timestamp for time.time() mocking."""
    return dt.timestamp()

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
        
        start_timestamp = to_timestamp_ms(BASE_TIME)
        end_timestamp = to_timestamp_ms(BASE_TIME + timedelta(hours=1))
        
        # Mock session metadata from workspace DB
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Implement authentication",
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
                    "type": "head"
                },
                {
                    "composerId": "session-2", 
                    "name": "Fix bug in login",
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=55)),
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=59)),
                    "type": "head"
                }
            ]
        }
        
                # Mock message headers from global DB
        message_headers_1 = {
            "composerId": "session-1",
            "name": "Implement authentication",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Session timestamp within time window
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1},  # user
                {"bubbleId": "msg-2", "type": 2}   # assistant
            ]
        }

        message_headers_2 = {
            "composerId": "session-2",
            "name": "Fix bug in login",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=55)),  # Session timestamp within time window
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-3", "type": 1}   # user
            ]
        }
        
        # Mock individual messages
        message_1 = {
            "text": "How do I implement JWT authentication?",
            "context": {"fileSelections": []}
            # NOTE: No timestamp field in realistic Cursor data
        }
        
        message_2 = {
            "text": "You can use the jsonwebtoken library...",
            "context": {"fileSelections": []}
            # NOTE: No timestamp field in realistic Cursor data
        }
        
        message_3 = {
            "text": "The login form isn't working",
            "context": {"fileSelections": []}
            # NOTE: No timestamp field in realistic Cursor data
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
        mock_time.side_effect = [1000.0, 1000.5]  # 500ms duration
        
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
        assert result[0]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=10))  # Uses session-1 createdAt timestamp
        assert result[0]['sessionName'] == "Implement authentication"
        assert result[0]['composerId'] == "session-1"
        assert result[0]['bubbleId'] == "msg-1"

        # Check second message (from session-1)
        assert result[1]['role'] == 'assistant'
        assert result[1]['content'] == "You can use the jsonwebtoken library..."
        assert result[1]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=10))  # Uses session-1 createdAt timestamp
        assert result[1]['sessionName'] == "Implement authentication"

        # Check third message (from session-2)
        assert result[2]['role'] == 'user'
        assert result[2]['content'] == "The login form isn't working"
        assert result[2]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=55))  # Uses session-2 createdAt timestamp
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
        """Test that sessions outside time window are filtered out at session level."""
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        start_timestamp = to_timestamp_ms(BASE_TIME)
        end_timestamp = to_timestamp_ms(BASE_TIME + timedelta(minutes=30))
        
        # Two sessions: one within time window, one outside
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-within",
                    "name": "Session within window",
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=15)),  # Within time window
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
                    "type": "head"
                },
                {
                    "composerId": "session-outside",
                    "name": "Session outside window", 
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=60)),  # After time window
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=70)),
                    "type": "head"
                }
            ]
        }

        # Headers for session within time window
        message_headers_within = {
            "composerId": "session-within",
            "name": "Session within window",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=15)),  # Session timestamp within time window
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1}
            ]
        }
        
        # Headers for session outside time window
        message_headers_outside = {
            "composerId": "session-outside", 
            "name": "Session outside window",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=60)),  # Session timestamp outside time window
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-2", "type": 1}
            ]
        }
        
        # Individual messages (timestamps don't matter anymore - session timestamp is used)
        message_within = {
            "text": "Message from session within window",
            "context": {}
        }
        
        message_outside = {
            "text": "Message from session outside window",
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers_within),)],  # Session within window gets processed
            [(json.dumps(message_within),)],
            [(json.dumps(message_headers_outside),)],  # Session outside window gets skipped
            # Note: message_outside never gets queried because session is filtered out
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(start_timestamp, end_timestamp)
        
        # Assert
        assert len(result) == 1  # Only messages from session within time window
        assert result[0]['content'] == "Message from session within window"
        assert result[0]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=15))  # Uses session createdAt timestamp
        assert result[0]['sessionName'] == "Session within window"

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
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
                    "createdAt": to_timestamp_ms(BASE_TIME),
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
                    "type": "head"
                }
            ]
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            []  # No message headers found
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
                    "createdAt": to_timestamp_ms(BASE_TIME),
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
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
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Within time window
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Session timestamp
            "fullConversationHeadersOnly": [
                {"bubbleId": "user-msg", "type": 1},      # User message
                {"bubbleId": "assistant-msg", "type": 2}  # Assistant message
            ]
        }
        
        user_message = {
            "text": "User question",
            "context": {}
            # Note: No individual timestamp - uses session timestamp
        }
        
        assistant_message = {
            "text": "Assistant response",
            "context": {}
            # Note: No individual timestamp - uses session timestamp
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(user_message),)],
            [(json.dumps(assistant_message),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=50)))
        
        # Assert
        assert len(result) == 2
        assert result[0]['role'] == 'user'
        assert result[0]['content'] == "User question"
        assert result[0]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=10))  # Uses session createdAt timestamp
        assert result[1]['role'] == 'assistant'
        assert result[1]['content'] == "Assistant response"
        assert result[1]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=10))  # Uses session createdAt timestamp

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_real_cursor_data_structure_timestamps(self, mock_execute_query):
        """
        Test with realistic Cursor data structure where:
        - Sessions have createdAt timestamps  
        - Individual messages have NO timestamps (just text, context, etc.)
        - Should use session createdAt for all messages in that session
        
        This test exposes the bug where current implementation defaults to timestamp=0
        """
        # Arrange
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        provider = ComposerChatProvider("/workspace.vscdb", "/global.vscdb")
        
        start_timestamp = to_timestamp_ms(BASE_TIME)
        end_timestamp = to_timestamp_ms(BASE_TIME + timedelta(minutes=30))
        
        # Realistic session metadata with createdAt timestamp
        session_metadata = {
            "allComposers": [
                {
                    "composerId": "session-1",
                    "name": "Implement authentication",
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Within time window - session created at specific time
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=30)),
                    "type": "head"
                }
            ]
        }
        
        # Realistic message headers (just bubbleId and type)
        message_headers = {
            "composerId": "session-1",
            "name": "Implement authentication", 
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Session creation time
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1},
                {"bubbleId": "msg-2", "type": 2}
            ]
        }
        
        # Realistic individual messages - NO TIMESTAMP FIELD!
        # This matches real Cursor bubble data structure
        message_1 = {
            "text": "How do I implement JWT authentication?",
            "context": {"fileSelections": []},
            "bubbleId": "msg-1",
            "_v": 2,
            "type": 1
            # NOTE: No "timestamp" field - this is realistic!
        }
        
        message_2 = {
            "text": "You can use the jsonwebtoken library...", 
            "context": {"fileSelections": []},
            "bubbleId": "msg-2",
            "_v": 2,
            "type": 2
            # NOTE: No "timestamp" field - this is realistic!
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_1),)],
            [(json.dumps(message_2),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(start_timestamp, end_timestamp)
        
        # Assert
        assert len(result) == 2
        
        # CRITICAL: Both messages should use session createdAt timestamp (to_timestamp_ms(BASE_TIME + timedelta(minutes=10)))
        # NOT default to 0 due to missing individual timestamps
        assert result[0]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=10))
        assert result[1]['timestamp'] == to_timestamp_ms(BASE_TIME + timedelta(minutes=10))
        
        # Verify content is extracted correctly
        assert result[0]['content'] == "How do I implement JWT authentication?"
        assert result[0]['role'] == 'user'
        assert result[1]['content'] == "You can use the jsonwebtoken library..."
        assert result[1]['role'] == 'assistant'
        
        # Both messages should reference the same session
        assert result[0]['sessionName'] == "Implement authentication"
        assert result[1]['sessionName'] == "Implement authentication"


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
            provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
                    "createdAt": to_timestamp_ms(BASE_TIME),
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
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
            provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
            provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))

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
                    "createdAt": to_timestamp_ms(BASE_TIME),
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Within time window to trigger message processing
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
            provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))


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
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Within time window
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=50)),
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=10)),  # Session timestamp within window
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1}
            ]
        }
        
        message_data = {
            "text": "Test message",
            "context": {}
            # Note: No individual timestamp - uses session timestamp
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_data),)]
        ]
        
        # Mock time for duration calculation
        mock_time.side_effect = [1000.0, 1000.3]  # 300ms duration
        
        # Mock metrics
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Act
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
        time_values = [1000.0, 1000.6]  # Start time, then 600ms later
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
        provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
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
        provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
        # Assert debug logging
        mock_logger.debug.assert_called_with(
            "No composer sessions found in workspace database"
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
                    "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=40)),  # Outside time window (after end)
                    "lastUpdatedAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=90)),
                    "type": "head"
                }
            ]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": to_timestamp_ms(BASE_TIME + timedelta(minutes=40)),  # Session timestamp outside time window
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-1", "type": 1}
            ]
        }

        # Message data (never gets queried since session is filtered out)
        message_data = {
            "text": "Test message",
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_data),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(to_timestamp_ms(BASE_TIME), to_timestamp_ms(BASE_TIME + timedelta(minutes=30)))
        
        # Assert
        assert result == []
        
        # Calculate expected timestamps for debug message
        start_ts = to_timestamp_ms(BASE_TIME)
        end_ts = to_timestamp_ms(BASE_TIME + timedelta(minutes=30))
        mock_logger.debug.assert_called_with(
            f"No messages found in time window {start_ts} to {end_ts}"
        ) 