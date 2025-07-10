"""
Tests for multi-database chat extraction in query_cursor_chat_database function.

Tests the enhanced implementation that uses discover_all_cursor_databases() to
query multiple workspace databases with a single global database, combining
results chronologically and providing data quality metadata.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import json
import time
from typing import List, Dict, Any

from mcp_commit_story.cursor_db import query_cursor_chat_database, reset_circuit_breaker


class TestMultiDatabaseChatExtraction:
    """Test multi-database chat extraction functionality."""
    
    def setup_method(self):
        """Reset circuit breaker before each test."""
        reset_circuit_breaker()

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_query_uses_discover_all_cursor_databases(
        self,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that query_cursor_chat_database uses discover_all_cursor_databases."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()

        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/workspace/.cursor/session1/state.vscdb",
            "/workspace/.cursor/session2/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock provider instances
        mock_provider1 = Mock()
        mock_provider1.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Message 1", "timestamp": 1000}
        ]
        mock_provider2 = Mock()
        mock_provider2.getChatHistoryForCommit.return_value = [
            {"role": "assistant", "content": "Message 2", "timestamp": 2000}
        ]
        
        mock_composer_provider_class.side_effect = [mock_provider1, mock_provider2]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert
        mock_discover_all.assert_called_once_with("/test/workspace")
        assert mock_composer_provider_class.call_count == 2
        mock_composer_provider_class.assert_has_calls([
            call("/workspace/.cursor/session1/state.vscdb", "/global/state.vscdb"),
            call("/workspace/.cursor/session2/state.vscdb", "/global/state.vscdb")
        ])

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_multiple_providers_created_with_same_global_db(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that multiple ComposerChatProvider instances use same global database."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/workspace1/state.vscdb",
            "/workspace2/state.vscdb",
            "/workspace3/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/shared/global.vscdb")
        
        mock_provider = Mock()
        mock_provider.getChatHistoryForCommit.return_value = []
        mock_composer_provider_class.return_value = mock_provider
        
        # Act
        query_cursor_chat_database(commit=mock_commit)
        
        # Assert - all providers should be created with same global database
        assert mock_composer_provider_class.call_count == 3
        # Check only the constructor calls, not the method calls
        constructor_calls = [call for call in mock_composer_provider_class.call_args_list]
        expected_calls = [
            call("/workspace1/state.vscdb", "/shared/global.vscdb"),
            call("/workspace2/state.vscdb", "/shared/global.vscdb"),
            call("/workspace3/state.vscdb", "/shared/global.vscdb")
        ]
        assert constructor_calls == expected_calls

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_chronological_ordering_of_combined_results(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that messages from multiple databases are combined chronologically."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/workspace1/state.vscdb",
            "/workspace2/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock providers with messages in non-chronological order per database
        mock_provider1 = Mock()
        mock_provider1.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Third message", "timestamp": 3000},
            {"role": "user", "content": "First message", "timestamp": 1000}
        ]
        
        mock_provider2 = Mock()
        mock_provider2.getChatHistoryForCommit.return_value = [
            {"role": "assistant", "content": "Fourth message", "timestamp": 4000},
            {"role": "assistant", "content": "Second message", "timestamp": 2000}
        ]
        
        mock_composer_provider_class.side_effect = [mock_provider1, mock_provider2]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - messages should be chronologically ordered
        messages = result["chat_history"]
        assert len(messages) == 4
        assert messages[0]["content"] == "First message"
        assert messages[0]["timestamp"] == 1000
        assert messages[1]["content"] == "Second message"
        assert messages[1]["timestamp"] == 2000
        assert messages[2]["content"] == "Third message"
        assert messages[2]["timestamp"] == 3000
        assert messages[3]["content"] == "Fourth message"
        assert messages[3]["timestamp"] == 4000

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_partial_results_when_some_databases_fail(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that system continues with partial results when some databases fail."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789" 
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/good/state.vscdb",
            "/corrupted/state.vscdb",
            "/another_good/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock providers - middle one fails
        mock_provider_good1 = Mock()
        mock_provider_good1.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Good message 1", "timestamp": 1000}
        ]
        
        mock_provider_bad = Mock()
        mock_provider_bad.getChatHistoryForCommit.side_effect = Exception("Database corrupted")
        
        mock_provider_good2 = Mock()
        mock_provider_good2.getChatHistoryForCommit.return_value = [
            {"role": "assistant", "content": "Good message 2", "timestamp": 2000}
        ]
        
        mock_composer_provider_class.side_effect = [
            mock_provider_good1,
            mock_provider_bad,
            mock_provider_good2
        ]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - should get partial results with data quality metadata
        assert result is not None
        messages = result["chat_history"]
        assert len(messages) == 2  # Only messages from good databases
        assert messages[0]["content"] == "Good message 1"
        assert messages[1]["content"] == "Good message 2"
        
        # Check data quality metadata
        workspace_info = result["workspace_info"]
        assert "data_quality" in workspace_info
        data_quality = workspace_info["data_quality"]
        assert data_quality["databases_found"] == 3
        assert data_quality["databases_queried"] == 2  # Only successful ones
        assert data_quality["databases_failed"] == 1
        assert data_quality["status"] == "partial"
        assert len(data_quality["failure_reasons"]) == 1
        assert "corrupted" in data_quality["failure_reasons"][0]

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_data_quality_metadata_for_complete_success(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test data quality metadata when all databases succeed."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/db1/state.vscdb",
            "/db2/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        mock_provider = Mock()
        mock_provider.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Message", "timestamp": 1000}
        ]
        mock_composer_provider_class.return_value = mock_provider
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert data quality metadata for complete success
        workspace_info = result["workspace_info"] 
        assert "data_quality" in workspace_info
        data_quality = workspace_info["data_quality"]
        assert data_quality["databases_found"] == 2
        assert data_quality["databases_queried"] == 2
        assert data_quality["databases_failed"] == 0
        assert data_quality["status"] == "complete"
        assert data_quality["failure_reasons"] == []

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_backward_compatibility_single_database(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test backward compatibility when only single database found."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = ["/single/state.vscdb"]  # Only one database
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        mock_provider = Mock()
        mock_provider.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Single DB message", "timestamp": 1000}
        ]
        mock_composer_provider_class.return_value = mock_provider
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - should work exactly as before
        assert result is not None
        messages = result["chat_history"]
        assert len(messages) == 1
        assert messages[0]["content"] == "Single DB message"
        
        # Data quality should show complete success
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 1
        assert data_quality["databases_queried"] == 1
        assert data_quality["status"] == "complete"

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_error_handling_when_no_databases_found(
        self, 
        mock_detect_workspace,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test proper error handling when no databases are discovered."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = []  # No databases found
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - should return empty result with proper metadata
        assert result is not None
        assert result["chat_history"] == []
        workspace_info = result["workspace_info"]
        assert workspace_info["total_messages"] == 0
        
        # Data quality should reflect no databases found
        data_quality = workspace_info["data_quality"]
        assert data_quality["databases_found"] == 0
        assert data_quality["databases_queried"] == 0
        assert data_quality["status"] == "complete"  # No failures, just no data

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_telemetry_attributes_for_multi_database(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that telemetry includes multi-database specific attributes."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = ["/db1/state.vscdb", "/db2/state.vscdb"]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        mock_provider = Mock()
        mock_provider.getChatHistoryForCommit.return_value = []
        mock_composer_provider_class.return_value = mock_provider
        
        # Act
        with patch('mcp_commit_story.cursor_db.trace') as mock_trace:
            mock_span = Mock()
            mock_trace.get_current_span.return_value = mock_span
            
            result = query_cursor_chat_database(commit=mock_commit)
            
            # Assert telemetry attributes were set
            expected_attributes = {
                "cursor.databases_discovered": 2,
                "cursor.databases_queried": 2,
                "cursor.databases_failed": 0,
                "cursor.multi_database_mode": True
            }
            
            # Check that span.set_attribute was called with these values
            for attr_name, expected_value in expected_attributes.items():
                mock_span.set_attribute.assert_any_call(attr_name, expected_value) 

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') 
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    def test_within_session_message_order_preservation(
        self, 
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that messages within sessions maintain correct order when combining from multiple databases.
        
        This test addresses the issue where individual messages don't have timestamps - only sessions do.
        All messages within a session get the same timestamp (session_created_at), so sorting by timestamp
        alone could jumble the message order within sessions.
        """
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/workspace1/state.vscdb",
            "/workspace2/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock providers with multiple messages per session, all with same timestamp
        # This simulates the real scenario where all messages in a session have session_created_at timestamp
        mock_provider1 = Mock()
        mock_provider1.getChatHistoryForCommit.return_value = [
            # Session A: created at 1000ms - all messages get timestamp 1000
            {"role": "user", "content": "Message 1 in session A", "timestamp": 1000, "composerId": "session-A", "bubbleId": "msg-A1"},
            {"role": "assistant", "content": "Message 2 in session A", "timestamp": 1000, "composerId": "session-A", "bubbleId": "msg-A2"},
            {"role": "user", "content": "Message 3 in session A", "timestamp": 1000, "composerId": "session-A", "bubbleId": "msg-A3"},
        ]
        
        mock_provider2 = Mock()  
        mock_provider2.getChatHistoryForCommit.return_value = [
            # Session B: created at 2000ms - all messages get timestamp 2000
            {"role": "user", "content": "Message 1 in session B", "timestamp": 2000, "composerId": "session-B", "bubbleId": "msg-B1"},
            {"role": "assistant", "content": "Message 2 in session B", "timestamp": 2000, "composerId": "session-B", "bubbleId": "msg-B2"},
            
            # Session C: also created at 1000ms (same as session A) - all messages get timestamp 1000
            {"role": "user", "content": "Message 1 in session C", "timestamp": 1000, "composerId": "session-C", "bubbleId": "msg-C1"},
            {"role": "assistant", "content": "Message 2 in session C", "timestamp": 1000, "composerId": "session-C", "bubbleId": "msg-C2"},
        ]
        
        mock_composer_provider_class.side_effect = [mock_provider1, mock_provider2]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - verify multi-criteria sorting preserves session order and within-session order
        messages = result["chat_history"]
        assert len(messages) == 7
        
        # Verify session A messages (timestamp 1000, composerId "session-A") come first in correct order
        session_a_messages = [m for m in messages if m["composerId"] == "session-A"]
        assert len(session_a_messages) == 3
        assert session_a_messages[0]["content"] == "Message 1 in session A"
        assert session_a_messages[1]["content"] == "Message 2 in session A" 
        assert session_a_messages[2]["content"] == "Message 3 in session A"
        
        # Verify session C messages (timestamp 1000, composerId "session-C") come after session A (alphabetical composerId)
        session_c_messages = [m for m in messages if m["composerId"] == "session-C"]
        assert len(session_c_messages) == 2
        assert session_c_messages[0]["content"] == "Message 1 in session C"
        assert session_c_messages[1]["content"] == "Message 2 in session C"
        
        # Verify session B messages (timestamp 2000) come last in correct order
        session_b_messages = [m for m in messages if m["composerId"] == "session-B"]
        assert len(session_b_messages) == 2
        assert session_b_messages[0]["content"] == "Message 1 in session B"
        assert session_b_messages[1]["content"] == "Message 2 in session B"
        
        # Verify overall chronological ordering: Session A -> Session C -> Session B
        # (Sessions A and C both have timestamp 1000, so they're ordered by composerId alphabetically)
        expected_order = [
            "Message 1 in session A",  # timestamp: 1000, composerId: session-A
            "Message 2 in session A", 
            "Message 3 in session A",
            "Message 1 in session C",  # timestamp: 1000, composerId: session-C (after A alphabetically)
            "Message 2 in session C",
            "Message 1 in session B",  # timestamp: 2000, composerId: session-B
            "Message 2 in session B"
        ]
        
        actual_order = [m["content"] for m in messages]
        assert actual_order == expected_order, f"Expected: {expected_order}, Got: {actual_order}" 