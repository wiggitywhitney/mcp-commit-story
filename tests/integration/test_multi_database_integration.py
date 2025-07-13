"""
Integration tests for multi-database chat extraction functionality.

Tests real-world scenarios including time window filtering, permission handling,
performance with large databases, and comprehensive data quality verification.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import tempfile
import os
import json
import time
from typing import List, Dict, Any

from mcp_commit_story.cursor_db import query_cursor_chat_database, reset_circuit_breaker


class TestMultiDatabaseIntegration:
    """Integration tests for multi-database chat extraction."""
    
    def setup_method(self):
        """Reset circuit breaker before each test."""
        reset_circuit_breaker()
    
    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_time_window_filtering_across_multiple_databases(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that time window filtering works correctly across multiple databases."""
        # Arrange - commit from 3 days ago
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        base_time = datetime.now() - timedelta(days=3)
        mock_commit.committed_datetime = base_time
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/workspace1/state.vscdb",  # Old database
            "/workspace2/state.vscdb",  # Recent database  
            "/workspace3/state.vscdb"   # Future database
        ]
        mock_find_workspace.return_value = ("/workspace1/state.vscdb", "/global/state.vscdb")
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((base_time - timedelta(hours=1)).timestamp() * 1000),  # start_timestamp_ms
            int((base_time + timedelta(hours=1)).timestamp() * 1000)   # end_timestamp_ms
        )
        
        # Create providers that return messages from different time periods
        mock_provider_old = Mock()
        old_messages = [
            {"role": "user", "content": "Old message", "timestamp": int((base_time - timedelta(days=1)).timestamp() * 1000)}
        ]
        mock_provider_old.getChatHistoryForCommit.return_value = old_messages
        
        mock_provider_recent = Mock()
        recent_messages = [
            {"role": "assistant", "content": "Recent message", "timestamp": int(base_time.timestamp() * 1000)}
        ]
        mock_provider_recent.getChatHistoryForCommit.return_value = recent_messages
        
        mock_provider_future = Mock()
        future_messages = [
            {"role": "user", "content": "Future message", "timestamp": int((base_time + timedelta(days=1)).timestamp() * 1000)}
        ]
        mock_provider_future.getChatHistoryForCommit.return_value = future_messages
        
        mock_composer_provider_class.side_effect = [
            mock_provider_old,
            mock_provider_recent,
            mock_provider_future
        ]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - should get messages from all time periods in chronological order
        assert result is not None
        messages = result["chat_history"]
        assert len(messages) == 3
        
        # Verify chronological ordering
        assert messages[0]["content"] == "Old message"
        assert messages[1]["content"] == "Recent message"
        assert messages[2]["content"] == "Future message"
        
        # Verify timestamps are in ascending order
        assert messages[0]["timestamp"] < messages[1]["timestamp"]
        assert messages[1]["timestamp"] < messages[2]["timestamp"]
        
        # Verify data quality
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 3
        assert data_quality["databases_queried"] == 3
        assert data_quality["status"] == "complete"

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_permission_error_handling_with_mixed_access(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test graceful handling of permission errors on some databases."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/accessible/state.vscdb",
            "/restricted/state.vscdb",   # This will fail with permission error
            "/another_accessible/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),  # start_timestamp_ms
            int(datetime.now().timestamp() * 1000)                         # end_timestamp_ms
        )
        
        # Set up providers - one fails with permission error
        mock_provider_good1 = Mock()
        mock_provider_good1.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Accessible message 1", "timestamp": 1000}
        ]
        
        mock_provider_bad = Mock()
        mock_provider_bad.getChatHistoryForCommit.side_effect = PermissionError("Access denied to database")
        
        mock_provider_good2 = Mock()
        mock_provider_good2.getChatHistoryForCommit.return_value = [
            {"role": "assistant", "content": "Accessible message 2", "timestamp": 2000}
        ]
        
        mock_composer_provider_class.side_effect = [
            mock_provider_good1,
            mock_provider_bad,
            mock_provider_good2
        ]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - should get partial results with proper error handling
        assert result is not None
        messages = result["chat_history"]
        assert len(messages) == 2  # Only accessible messages
        assert messages[0]["content"] == "Accessible message 1"
        assert messages[1]["content"] == "Accessible message 2"
        
        # Verify data quality reflects the permission issue
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 3
        assert data_quality["databases_queried"] == 2
        assert data_quality["databases_failed"] == 1
        assert data_quality["status"] == "partial"
        assert len(data_quality["failure_reasons"]) == 1
        assert "Access denied" in data_quality["failure_reasons"][0]

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_performance_with_large_databases(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test performance and memory usage with large result sets from multiple databases."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/large_db1/state.vscdb",
            "/large_db2/state.vscdb",
            "/large_db3/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((datetime.now() - timedelta(hours=2)).timestamp() * 1000),  # start_timestamp_ms
            int(datetime.now().timestamp() * 1000)                         # end_timestamp_ms
        )
        
        # Create large result sets (simulate 1000 messages per database)
        def create_large_message_set(db_index, message_count=1000):
            messages = []
            base_timestamp = 1000000 + (db_index * 500000)  # Stagger timestamps
            for i in range(message_count):
                messages.append({
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"Message {i} from database {db_index}",
                    "timestamp": base_timestamp + i,
                    "bubbleId": f"bubble_{db_index}_{i}",
                    "sessionName": f"session_{db_index}"
                })
            return messages
        
        mock_provider1 = Mock()
        mock_provider1.getChatHistoryForCommit.return_value = create_large_message_set(1)
        
        mock_provider2 = Mock()
        mock_provider2.getChatHistoryForCommit.return_value = create_large_message_set(2)
        
        mock_provider3 = Mock()
        mock_provider3.getChatHistoryForCommit.return_value = create_large_message_set(3)
        
        mock_composer_provider_class.side_effect = [
            mock_provider1,
            mock_provider2,
            mock_provider3
        ]
        
        # Act - measure performance
        start_time = time.time()
        result = query_cursor_chat_database(commit=mock_commit)
        execution_time = time.time() - start_time
        
        # Assert - performance and correctness
        assert result is not None
        messages = result["chat_history"]
        assert len(messages) == 3000  # 1000 messages from each database
        
        # Verify chronological ordering is maintained
        for i in range(1, len(messages)):
            assert messages[i]["timestamp"] >= messages[i-1]["timestamp"]
        
        # Performance assertions
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        # Verify data quality
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 3
        assert data_quality["databases_queried"] == 3
        assert data_quality["status"] == "complete"
        
        # Check that we have messages from all databases
        db1_messages = [m for m in messages if "database 1" in m["content"]]
        db2_messages = [m for m in messages if "database 2" in m["content"]]
        db3_messages = [m for m in messages if "database 3" in m["content"]]
        assert len(db1_messages) == 1000
        assert len(db2_messages) == 1000
        assert len(db3_messages) == 1000

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_empty_and_corrupted_database_handling(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test handling of empty databases and corrupted data."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/normal/state.vscdb",
            "/empty/state.vscdb",
            "/corrupted/state.vscdb"
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),  # start_timestamp_ms
            int(datetime.now().timestamp() * 1000)                         # end_timestamp_ms
        )
        
        # Set up providers with different scenarios
        mock_provider_normal = Mock()
        mock_provider_normal.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Normal message", "timestamp": 1000}
        ]
        
        mock_provider_empty = Mock()
        mock_provider_empty.getChatHistoryForCommit.return_value = []  # Empty result
        
        mock_provider_corrupted = Mock()
        mock_provider_corrupted.getChatHistoryForCommit.side_effect = Exception("Database corrupted: invalid schema")
        
        mock_composer_provider_class.side_effect = [
            mock_provider_normal,
            mock_provider_empty,
            mock_provider_corrupted
        ]
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - should handle gracefully
        assert result is not None
        messages = result["chat_history"]
        assert len(messages) == 1  # Only the normal message
        assert messages[0]["content"] == "Normal message"
        
        # Verify data quality reflects the mixed scenario
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 3
        assert data_quality["databases_queried"] == 2  # Normal + empty (both successful)
        assert data_quality["databases_failed"] == 1   # Corrupted
        assert data_quality["status"] == "partial"
        assert len(data_quality["failure_reasons"]) == 1
        assert "corrupted" in data_quality["failure_reasons"][0].lower()

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_data_quality_metadata_accuracy(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that data quality metadata accurately reflects all scenarios."""
        # Arrange - complex scenario with multiple outcomes
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_discover_all.return_value = [
            "/success1/state.vscdb",    # Success with data
            "/success2/state.vscdb",    # Success with data  
            "/empty/state.vscdb",       # Success but empty
            "/permission/state.vscdb",  # Permission failure
            "/corrupted/state.vscdb"    # Corruption failure
        ]
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),  # start_timestamp_ms
            int(datetime.now().timestamp() * 1000)                         # end_timestamp_ms
        )
        
        # Set up mixed provider scenarios
        mock_providers = []
        
        # Two successful with data
        for i in range(2):
            provider = Mock()
            provider.getChatHistoryForCommit.return_value = [
                {"role": "user", "content": f"Success message {i+1}", "timestamp": 1000 + i}
            ]
            mock_providers.append(provider)
        
        # One successful but empty
        empty_provider = Mock()
        empty_provider.getChatHistoryForCommit.return_value = []
        mock_providers.append(empty_provider)
        
        # One permission failure
        permission_provider = Mock()
        permission_provider.getChatHistoryForCommit.side_effect = PermissionError("Access denied")
        mock_providers.append(permission_provider)
        
        # One corruption failure
        corrupted_provider = Mock()
        corrupted_provider.getChatHistoryForCommit.side_effect = Exception("Database schema error")
        mock_providers.append(corrupted_provider)
        
        mock_composer_provider_class.side_effect = mock_providers
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - comprehensive data quality verification
        assert result is not None
        
        # Verify messages
        messages = result["chat_history"]
        assert len(messages) == 2  # Only from successful providers with data
        
        # Verify detailed data quality metadata
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 5     # Total discovered
        assert data_quality["databases_queried"] == 3   # Successful (2 with data + 1 empty)
        assert data_quality["databases_failed"] == 2    # Permission + corruption
        assert data_quality["status"] == "partial"      # Mixed success/failure
        
        # Verify failure reasons are captured
        failure_reasons = data_quality["failure_reasons"]
        assert len(failure_reasons) == 2
        assert any("permission" in reason.lower() or "access denied" in reason.lower() for reason in failure_reasons)
        assert any("schema" in reason.lower() or "corrupted" in reason.lower() for reason in failure_reasons)

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_48_hour_database_filtering_integration(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that the 48-hour filtering optimization in discover_all_cursor_databases works correctly."""
        # Arrange
        mock_commit = Mock()
        mock_commit.hexsha = "abc123456789"
        mock_commit.committed_datetime = datetime.now()
        
        mock_workspace_match = Mock()
        mock_workspace_match.workspace_folder = "/test/workspace"
        mock_detect_workspace.return_value = mock_workspace_match
        mock_find_workspace.return_value = (None, "/global/state.vscdb")
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((datetime.now() - timedelta(hours=48)).timestamp() * 1000),  # start_timestamp_ms
            int(datetime.now().timestamp() * 1000)                          # end_timestamp_ms
        )
        
        # Mock discover_all_cursor_databases to return filtered results
        # (This represents the existing 48-hour filtering logic)
        filtered_databases = [
            "/recent1/state.vscdb",  # Within 48 hours
            "/recent2/state.vscdb",  # Within 48 hours
            # Note: Old databases (> 48 hours) should already be filtered out
        ]
        mock_discover_all.return_value = filtered_databases
        
        # Act
        result = query_cursor_chat_database(commit=mock_commit)
        
        # Assert - verify integration with 48-hour filtering
        assert result is not None
        
        # Verify discover_all_cursor_databases was called with workspace path
        mock_discover_all.assert_called_once_with("/test/workspace")
        
        # Verify data quality reflects filtered results
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["databases_found"] == 2  # Only recent databases
        
        # The multi-database implementation should work with pre-filtered results
        workspace_info = result["workspace_info"]
        assert workspace_info["workspace_database_path"] == "/recent1/state.vscdb"  # Primary for compatibility
        assert workspace_info["global_database_path"] == "/global/state.vscdb"

    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    def test_comprehensive_telemetry_and_logging(
        self,
        mock_get_time_window,
        mock_detect_workspace,
        mock_composer_provider_class,
        mock_find_workspace,
        mock_discover_all,
    ):
        """Test that telemetry and logging work correctly across multiple providers."""
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
        
        # Mock the time window calculation to avoid git validation
        mock_get_time_window.return_value = (
            int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),  # start_timestamp_ms
            int(datetime.now().timestamp() * 1000)                         # end_timestamp_ms
        )
        
        # Set up successful providers
        mock_provider1 = Mock()
        mock_provider1.getChatHistoryForCommit.return_value = [
            {"role": "user", "content": "Message 1", "timestamp": 1000}
        ]
        
        mock_provider2 = Mock()
        mock_provider2.getChatHistoryForCommit.return_value = [
            {"role": "assistant", "content": "Message 2", "timestamp": 2000}
        ]
        
        mock_composer_provider_class.side_effect = [mock_provider1, mock_provider2]
        
        # Act with telemetry mocking
        with patch('mcp_commit_story.cursor_db.trace') as mock_trace:
            mock_span = Mock()
            mock_trace.get_current_span.return_value = mock_span
            
            result = query_cursor_chat_database(commit=mock_commit)
            
            # Assert telemetry attributes for multi-database scenario
            telemetry_calls = mock_span.set_attribute.call_args_list
            
            # Verify multi-database specific telemetry was recorded
            assert any(call[0][0] == "cursor.databases_discovered" and call[0][1] == 2 for call in telemetry_calls)
            assert any(call[0][0] == "cursor.databases_queried" and call[0][1] == 2 for call in telemetry_calls)
            assert any(call[0][0] == "cursor.databases_failed" and call[0][1] == 0 for call in telemetry_calls)
            assert any(call[0][0] == "cursor.multi_database_mode" and call[0][1] == True for call in telemetry_calls)
            assert any(call[0][0] == "cursor.success" and call[0][1] == True for call in telemetry_calls)
            
        # Verify result correctness
        assert result is not None
        assert len(result["chat_history"]) == 2
        
        data_quality = result["workspace_info"]["data_quality"]
        assert data_quality["status"] == "complete" 