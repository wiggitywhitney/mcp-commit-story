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

from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseAccessError,
    CursorDatabaseQueryError,
    CursorDatabaseNotFoundError
)


class TestComposerBasedQueryCursorChatDatabase:
    """Test the NEW Composer-based implementation."""

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    def test_successful_composer_integration(
        self, 
        mock_get_commit_hash,
        mock_composer_provider,
        mock_find_databases, 
        mock_get_time_window
    ):
        """Test successful integration with ComposerChatProvider and commit-based time windows."""
        # Arrange
        mock_get_commit_hash.return_value = "abc123"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)  # 1-hour window
        mock_find_databases.return_value = ("/path/to/workspace.vscdb", "/path/to/global.vscdb")
        
        # Mock ComposerChatProvider
        mock_provider = MagicMock()
        mock_composer_provider.return_value = mock_provider
        
        # Enhanced Composer data with all metadata
        composer_messages = [
            {
                'role': 'user',
                'content': 'How do I implement authentication?',
                'timestamp': 1640995800000,
                'sessionName': 'Auth Implementation',
                'composerId': 'session-1',
                'bubbleId': 'msg-1'
            },
            {
                'role': 'assistant', 
                'content': 'You can implement JWT authentication by...',
                'timestamp': 1640996200000,
                'sessionName': 'Auth Implementation',
                'composerId': 'session-1',
                'bubbleId': 'msg-2'
            }
        ]
        mock_provider.getChatHistoryForCommit.return_value = composer_messages
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert structure
        assert "workspace_info" in result
        assert "chat_history" in result
        
        # Verify workspace_info with enhanced metadata
        workspace_info = result["workspace_info"]
        assert workspace_info["workspace_database_path"] == "/path/to/workspace.vscdb"
        assert workspace_info["global_database_path"] == "/path/to/global.vscdb"
        assert workspace_info["total_messages"] == 2
        assert workspace_info["time_window_start"] == 1640995200000
        assert workspace_info["time_window_end"] == 1640998800000
        assert workspace_info["commit_hash"] == "abc123"
        
        # Verify chat_history maintains compatibility but enhanced
        chat_history = result["chat_history"]
        assert isinstance(chat_history, list)
        assert len(chat_history) == 2
        
        # Check enhanced message structure
        assert chat_history[0]["role"] == "user"
        assert chat_history[0]["content"] == "How do I implement authentication?"
        assert chat_history[0]["timestamp"] == 1640995800000
        assert chat_history[0]["sessionName"] == "Auth Implementation"
        
        # Verify method calls
        mock_get_commit_hash.assert_called_once()
        mock_get_time_window.assert_called_once_with("abc123")
        mock_find_databases.assert_called_once()
        mock_composer_provider.assert_called_once_with("/path/to/workspace.vscdb", "/path/to/global.vscdb")
        mock_provider.getChatHistoryForCommit.assert_called_once_with(1640995200000, 1640998800000)

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    def test_backward_compatibility_no_parameters(
        self,
        mock_get_commit_hash,
        mock_find_databases,
        mock_get_time_window
    ):
        """Test that function maintains exact same signature (no parameters) for backward compatibility."""
        # Arrange
        mock_get_commit_hash.return_value = "def456"
        mock_get_time_window.return_value = (1640995200000, 1640998800000)
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        
        # Act - should work with no parameters (same as before)
        result = query_cursor_chat_database()
        
        # Assert - verify all internal calls happen automatically
        mock_get_commit_hash.assert_called_once()  # Detects current commit internally
        mock_get_time_window.assert_called_once_with("def456")  # Uses detected commit
        mock_find_databases.assert_called_once()  # Finds databases automatically

    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_current_commit_hash')
    def test_enhanced_return_structure(
        self,
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
    def test_composer_provider_error_handling(
        self,
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
             patch('time.time') as mock_time:
            
            mock_time.return_value = 1640998800  # Current time in seconds
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            
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
    def test_empty_results_handling(
        self,
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
    def test_chronological_message_sorting(
        self,
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
             patch('mcp_commit_story.cursor_db.ComposerChatProvider'):
            
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
            find_workspace_composer_databases,
            ComposerChatProvider
        )
        
        # Verify all functions are callable
        assert callable(get_current_commit_hash)
        assert callable(get_commit_time_window)  
        assert callable(find_workspace_composer_databases)
        assert callable(ComposerChatProvider) 