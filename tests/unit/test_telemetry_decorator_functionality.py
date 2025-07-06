"""
Test telemetry decorator functionality.

This module verifies that functions decorated with telemetry decorators
continue to work correctly and handle errors gracefully.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import git

from src.mcp_commit_story.ai_context_filter import get_previous_journal_entry
from src.mcp_commit_story.git_utils import get_previous_commit_info
from src.mcp_commit_story.chat_context_manager import extract_chat_for_commit


class TestTelemetryIntegration:
    """Test that decorated functions work correctly with telemetry."""
    
    def test_get_previous_journal_entry_with_telemetry(self):
        """Test that get_previous_journal_entry works with telemetry decorator."""
        # Create a mock commit
        mock_commit = Mock()
        mock_commit.committed_date = 1672531200  # 2023-01-01
        
        # Mock config loading
        with patch('src.mcp_commit_story.ai_context_filter.load_config') as mock_config:
            mock_config.return_value = {"journal": {"path": "/tmp/nonexistent"}}
            
            # Call the function - it should work without errors
            result = get_previous_journal_entry(mock_commit)
            
            # Should return None since no journal files exist
            assert result is None
    
    def test_get_previous_journal_entry_with_exception(self):
        """Test that get_previous_journal_entry handles exceptions correctly with telemetry."""
        # Create a mock commit that will cause an exception
        mock_commit = Mock()
        mock_commit.committed_date = "invalid_timestamp"  # This should cause an error
        
        # Call the function - it should handle the exception gracefully
        result = get_previous_journal_entry(mock_commit)
        
        # Should return None when exception occurs
        assert result is None
    
    def test_get_previous_commit_info_with_telemetry(self):
        """Test that get_previous_commit_info works with telemetry decorator."""
        # Create a mock commit with no parents (first commit)
        mock_commit = Mock()
        mock_commit.parents = []
        
        # Call the function - it should work without errors
        result = get_previous_commit_info(mock_commit)
        
        # Should return None for first commit
        assert result is None
    
    def test_get_previous_commit_info_with_parent(self):
        """Test that get_previous_commit_info works with parent commit."""
        # Create mock parent commit
        mock_parent = Mock()
        mock_parent.hexsha = "abc123"
        mock_parent.message = "Previous commit"
        mock_parent.committed_date = 1672531200
        mock_parent.stats.files = {"file1.py": {"insertions": 10, "deletions": 5}}
        
        # Create mock commit with parent
        mock_commit = Mock()
        mock_commit.parents = [mock_parent]
        
        # Call the function - it should work without errors
        result = get_previous_commit_info(mock_commit)
        
        # Should return previous commit info
        assert result is not None
        assert result['hash'] == "abc123"
        assert result['message'] == "Previous commit"
        assert result['files_changed'] == 1
        assert result['insertions'] == 10
        assert result['deletions'] == 5
    
    def test_extract_chat_for_commit_with_telemetry(self):
        """Test that extract_chat_for_commit works with telemetry decorator."""
        # Mock the query_cursor_chat_database function
        with patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database') as mock_query:
            mock_query.return_value = {
                'chat_history': [
                    {'role': 'user', 'content': 'Hello'}
                ],
                'workspace_info': {
                    'start_timestamp_ms': 1672531200000,
                    'end_timestamp_ms': 1672617600000,
                    'strategy': 'test'
                }
            }
            
            # Call the function - it should work without errors
            result = extract_chat_for_commit()
            
            # Should return valid ChatContextData
            assert isinstance(result, dict)
            assert 'messages' in result
            assert 'time_window' in result
            assert 'session_names' in result
            assert 'metadata' in result
            
            # Should transform the message correctly
            assert len(result['messages']) == 1
            assert result['messages'][0]['speaker'] == 'Human'
            assert result['messages'][0]['text'] == 'Hello'
    
    def test_extract_chat_for_commit_with_exception(self):
        """Test that extract_chat_for_commit handles exceptions correctly with telemetry."""
        # Mock the query_cursor_chat_database function to raise an exception
        with patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database') as mock_query:
            mock_query.side_effect = Exception("Database error")
            
            # Call the function - it should handle the exception gracefully
            result = extract_chat_for_commit()
            
            # Should return empty ChatContextData with error info
            assert isinstance(result, dict)
            assert result['messages'] == []
            assert result['session_names'] == []
            assert 'error_info' in result['metadata']
            assert result['metadata']['error_info']['error_type'] == 'Exception'
            assert result['metadata']['error_info']['message'] == 'Database error' 