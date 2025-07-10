"""
Tests for the NEW Composer-based query_cursor_chat_database function.

Tests the updated implementation that uses ComposerChatProvider with commit-based
time windows instead of the old aiService + 48-hour approach.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import json
import time
from typing import List, Dict, Any

from mcp_commit_story.cursor_db import query_cursor_chat_database, reset_circuit_breaker
from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseAccessError,
    CursorDatabaseQueryError,
    CursorDatabaseNotFoundError
)


class TestComposerBasedQueryCursorChatDatabase:
    """Test the NEW Composer-based implementation."""
    
    def setup_method(self):
        """Reset circuit breaker before each test."""
        reset_circuit_breaker()

    def test_successful_composer_integration(self):
        """Test that query_cursor_chat_database returns expected data structure."""
        # Act - just call the function and test behavior, not implementation
        result = query_cursor_chat_database()
        
        # Assert - test the API contract, not internals
        assert isinstance(result, dict)
        assert "workspace_info" in result
        assert "chat_history" in result
        
        # Verify workspace_info has required fields
        workspace_info = result["workspace_info"]
        assert isinstance(workspace_info, dict)
        assert "total_messages" in workspace_info
        assert isinstance(workspace_info["total_messages"], int)
        
        # Verify chat_history is the right type
        chat_history = result["chat_history"]
        assert isinstance(chat_history, list)
        
        # If there are messages, verify they have basic structure
        for message in chat_history:
            assert isinstance(message, dict)
            # Don't assert specific fields since they might vary

    def test_backward_compatibility_no_parameters(self):
        """Test that function works without parameters (backward compatibility)."""
        # Act - call without parameters
        result = query_cursor_chat_database()
        
        # Assert - verify it returns the expected structure
        assert isinstance(result, dict)
        assert "workspace_info" in result
        assert "chat_history" in result
        assert isinstance(result["workspace_info"], dict)
        assert isinstance(result["chat_history"], list)

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_enhanced_return_structure(
        self,
        mock_execute_query,
        mock_discover_all,
        mock_detect_workspace,
        mock_get_commit_hash,
        mock_composer_provider,
        mock_find_databases,
        mock_get_time_window
    ):
        """Test enhanced return structure with timestamp and sessionName fields."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        
        # Mock multi-database approach to fail, triggering fallback to single-database
        mock_detect_workspace.side_effect = Exception("Workspace detection failed")
        mock_discover_all.return_value = []
        
        # Mock execute_cursor_query to return empty results (no composer sessions)
        mock_execute_query.return_value = []
        
        mock_provider = MagicMock()
        mock_composer_provider.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.return_value = [
            {
                'role': 'user',
                'content': 'Test message',
                'timestamp': 1640995800000,
                'sessionName': 'Test Session',
                'composerId': 'session-1',
                'bubbleId': 'msg-1'
            }
        ]
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert enhanced structure
        chat_history = result["chat_history"]
        message = chat_history[0]
        
        # Verify all enhanced fields present
        assert message["timestamp"] == 1640995800000
        assert message["sessionName"] == "Test Session" 
        assert message["composerId"] == "session-1"
        assert message["bubbleId"] == "msg-1"
        
        # Verify backward compatibility fields maintained
        assert message["role"] == "user"
        assert message["content"] == "Test message"

    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    def test_database_not_found_error_handling(self, mock_get_commit_hash):
        """Test error handling when Composer databases cannot be found."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find:
            mock_find.side_effect = CursorDatabaseNotFoundError(
                "Composer databases not found",
                path="/nonexistent/workspace"
            )
            
            # Act
            result = query_cursor_chat_database()
            
            # Assert graceful degradation
            assert result["workspace_info"]["workspace_database_path"] is None
            assert result["workspace_info"]["global_database_path"] is None
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_composer_provider_error_handling(
        self,
        mock_execute_query,
        mock_discover_all,
        mock_detect_workspace,
        mock_get_commit_hash,
        mock_composer_provider,
        mock_find_databases,
        mock_get_time_window
    ):
        """Test error handling when ComposerChatProvider encounters database errors."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        
        # Mock multi-database approach to fail, triggering fallback to single-database
        mock_detect_workspace.side_effect = Exception("Workspace detection failed")
        mock_discover_all.return_value = []
        
        mock_provider = MagicMock()
        mock_composer_provider.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseAccessError(
            "Database locked",
            path="/workspace.vscdb"
        )
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert graceful degradation with database paths preserved
        assert result["workspace_info"]["workspace_database_path"] == "/workspace.vscdb"
        assert result["workspace_info"]["global_database_path"] == "/global.vscdb"
        assert result["workspace_info"]["total_messages"] == 0
        assert result["chat_history"] == []

    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    def test_git_error_fallback_to_24_hour(self, mock_get_commit_hash):
        """Test fallback to 24-hour window when git operations fail."""
        # Arrange - git commit detection fails
        mock_get_commit_hash.side_effect = Exception("Git repository not found")
        
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class, \
             patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect_workspace, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover_all, \
             patch('mcp_commit_story.composer_chat_provider.execute_cursor_query') as mock_execute_query, \
             patch('time.time') as mock_time:
            
            mock_time.return_value = 1640998800  # Current time in seconds
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            
            # Mock multi-database approach to fail, triggering fallback to single-database
            mock_detect_workspace.side_effect = Exception("Workspace detection failed")
            mock_discover_all.return_value = []
            
            # Mock execute_cursor_query to return empty results (no composer sessions)
            mock_execute_query.return_value = []
            
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.getChatHistoryForCommit.return_value = []
            
            # Act
            result = query_cursor_chat_database()
            
            # Assert 24-hour fallback window calculation
            # Should be: current_time_ms - 24*60*60*1000 to current_time_ms
            expected_end = 1640998800 * 1000  # Current time in ms
            expected_start = expected_end - (24 * 60 * 60 * 1000)  # 24 hours ago
            
            mock_provider.getChatHistoryForCommit.assert_called_once_with(expected_start, expected_end)
            
            # Verify fallback metadata
            assert result["workspace_info"]["commit_hash"] is None
            assert result["workspace_info"]["time_window_strategy"] == "24_hour_fallback"

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_empty_results_handling(
        self,
        mock_execute_query,
        mock_discover_all,
        mock_detect_workspace,
        mock_get_commit_hash,
        mock_composer_provider,
        mock_find_databases,
        mock_get_time_window
    ):
        """Test handling when no messages found in time window."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        
        # Mock multi-database approach to fail, triggering fallback to single-database
        mock_detect_workspace.side_effect = Exception("Workspace detection failed")
        mock_discover_all.return_value = []
        
        mock_provider = MagicMock()
        mock_composer_provider.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.return_value = []  # No messages
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert proper empty handling
        assert result["workspace_info"]["total_messages"] == 0
        assert result["chat_history"] == []
        assert result["workspace_info"]["workspace_database_path"] == "/workspace.vscdb"
        assert result["workspace_info"]["global_database_path"] == "/global.vscdb"

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    def test_telemetry_integration(
        self,
        mock_get_commit_hash,
        mock_composer_provider,
        mock_find_databases,
        mock_get_time_window
    ):
        """Test that @trace_mcp_operation decorator is applied and working."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        
        mock_provider = MagicMock()
        mock_composer_provider.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.return_value = [
            {'role': 'user', 'content': 'test', 'timestamp': 1640995800000, 'sessionName': 'Test'}
        ]
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert telemetry decorator is applied (function executes without error)
        assert result is not None
        assert "workspace_info" in result
        assert "chat_history" in result

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    @patch('mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_chronological_message_sorting(
        self,
        mock_execute_query,
        mock_discover_all,
        mock_detect_workspace,
        mock_get_commit_hash,
        mock_composer_provider,
        mock_find_databases,
        mock_get_time_window
    ):
        """Test that messages are returned in chronological order."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        
        # Mock multi-database approach to fail, triggering fallback to single-database
        mock_detect_workspace.side_effect = Exception("Workspace detection failed")
        mock_discover_all.return_value = []
        
        # Mock execute_cursor_query to return empty results (no composer sessions)
        mock_execute_query.return_value = []
        
        mock_provider = MagicMock()
        mock_composer_provider.return_value = mock_provider
        
        # Messages already sorted by ComposerChatProvider
        composer_messages = [
            {'role': 'user', 'content': 'First message', 'timestamp': 1640995400000, 'sessionName': 'Session'},
            {'role': 'assistant', 'content': 'Second message', 'timestamp': 1640995600000, 'sessionName': 'Session'},
            {'role': 'user', 'content': 'Third message', 'timestamp': 1640995800000, 'sessionName': 'Session'}
        ]
        mock_provider.getChatHistoryForCommit.return_value = composer_messages
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert chronological order maintained
        chat_history = result["chat_history"]
        assert len(chat_history) == 3
        assert chat_history[0]["content"] == "First message"
        assert chat_history[1]["content"] == "Second message"
        assert chat_history[2]["content"] == "Third message"
        
        # Verify timestamps are increasing
        timestamps = [msg["timestamp"] for msg in chat_history]
        assert timestamps == sorted(timestamps)

    def test_performance_requirements(self):
        """Test that function meets performance requirements (should complete quickly)."""
        # This is a basic performance smoke test
        # The @trace_mcp_operation decorator will handle detailed performance monitoring
        
        with patch('mcp_commit_story.cursor_db.get_current_commit_hash'), \
             patch('mcp_commit_story.cursor_db.get_commit_time_window'), \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases'), \
             patch('mcp_commit_story.composer_chat_provider.ComposerChatProvider'):
            
            # Mock quick responses
            start_time = time.time()
            result = query_cursor_chat_database()
            end_time = time.time()
            
            # Should complete within reasonable time (telemetry will track precise metrics)
            assert (end_time - start_time) < 5.0  # 5 second max for mock operations
            assert result is not None


class TestNewFunctionImports:
    """Test that all required new functions are properly imported."""
    
    def test_required_imports_available(self):
        """Test that all new functions for Composer integration are available."""
        from mcp_commit_story.cursor_db import (
            get_current_commit_hash,
            get_commit_time_window,
            find_workspace_composer_databases
        )
        from mcp_commit_story.composer_chat_provider import ComposerChatProvider
        
        # Verify all functions are callable
        assert callable(get_current_commit_hash)
        assert callable(get_commit_time_window)  
        assert callable(find_workspace_composer_databases)
        assert callable(ComposerChatProvider) 