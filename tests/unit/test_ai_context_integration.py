"""
Tests for AI context filtering integration into the data collection pipeline.

This module tests the integration of AI-powered context filtering into the main
data collection pipeline, including function signature updates and error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from git import Commit

from mcp_commit_story.context_collection import collect_chat_history
from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.cursor_db.composer_integration import get_current_commit_hash, get_commit_time_window


class TestFunctionSignatureUpdates:
    """Test that functions now accept commit parameter (fixing HEAD assumption bug)"""

    def test_collect_chat_history_accepts_commit_parameter(self):
        """Test that collect_chat_history can be called with commit parameter"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        # This should work without TypeError
        with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock_query:
            mock_query.return_value = {'chat_history': []}
            
            result = collect_chat_history(commit=mock_commit, max_messages_back=150)
            
            # Should pass commit to underlying function
            mock_query.assert_called_once_with(commit=mock_commit)
            assert isinstance(result, dict)

    def test_query_cursor_chat_database_accepts_commit_parameter(self):
        """Test that query_cursor_chat_database can be called with commit parameter"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        # This should work without TypeError
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_time, \
             patch('mcp_commit_story.composer_chat_provider.ComposerChatProvider') as mock_provider:
            
            mock_find.return_value = ("/workspace/db", "/global/db")
            mock_time.return_value = (1000000, 2000000)
            mock_provider_instance = Mock()
            mock_provider_instance.getChatHistoryForCommit.return_value = []
            mock_provider.return_value = mock_provider_instance
            
            result = query_cursor_chat_database(commit=mock_commit)
            
            # Should use the provided commit instead of detecting HEAD
            mock_time.assert_called_once_with(mock_commit.hexsha)
            assert isinstance(result, dict)

    def test_git_functions_accept_commit_parameter(self):
        """Test that git helper functions accept commit parameter"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        # Test get_current_commit_hash with commit parameter
        with patch('mcp_commit_story.git_utils.get_repo') as mock_get_repo:
            mock_repo = Mock()
            mock_get_repo.return_value = mock_repo
            
            result = get_current_commit_hash(commit=mock_commit)
            
            # Should return the provided commit hash, not detect HEAD
            assert result == "abc123"
            mock_get_repo.assert_not_called()  # Should not need to detect repo

    def test_get_commit_time_window_accepts_commit_object(self):
        """Test that get_commit_time_window can accept commit objects"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        with patch('mcp_commit_story.cursor_db.composer_integration._get_commit_time_window') as mock_time_window, \
             patch('mcp_commit_story.cursor_db.composer_integration.get_repo') as mock_get_repo:
            
            mock_time_window.return_value = {
                'start_timestamp_ms': 1000000,
                'end_timestamp_ms': 2000000
            }
            mock_get_repo.return_value = Mock()  # Mock repo object
            
            result = get_commit_time_window(mock_commit)
            
            # Should handle commit object as well as hash strings
            assert result == (1000000, 2000000)


class TestAIFilteringIntegration:
    """Test integration of AI filtering into collect_chat_history"""

    @patch('mcp_commit_story.context_collection.filter_chat_for_commit')
    @patch('mcp_commit_story.context_collection.query_cursor_chat_database')
    @patch('mcp_commit_story.context_collection.collect_git_context')
    def test_ai_filtering_called_when_messages_exist(self, mock_git_context, mock_query, mock_filter):
        """Test that AI filtering is called when messages are available"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        # Setup mock data
        raw_messages = [
            {'role': 'user', 'content': 'Start work', 'bubbleId': 'msg1', 'timestamp': 1000},
            {'role': 'assistant', 'content': 'Working on it', 'bubbleId': 'msg2', 'timestamp': 2000},
        ]
        
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'changed_files': ['test.py'],
            'diff_summary': 'Test changes'
        }
        mock_query.return_value = {'chat_history': raw_messages}
        mock_filter.return_value = raw_messages[1:]  # Filter to just second message
        
        # Execute
        result = collect_chat_history(commit=mock_commit, max_messages_back=150)
        
        # Verify AI filtering was called with git context
        expected_git_context = mock_git_context.return_value
        mock_filter.assert_called_once_with(raw_messages, mock_commit, expected_git_context)
        
        # Verify result contains only filtered messages
        assert len(result['messages']) == 1
        assert result['messages'][0]['text'] == 'Working on it'

    @patch('mcp_commit_story.context_collection.filter_chat_for_commit')
    @patch('mcp_commit_story.context_collection.query_cursor_chat_database')
    def test_ai_filtering_skipped_for_empty_messages(self, mock_query, mock_filter):
        """Test that AI filtering is skipped when no messages are available"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        mock_query.return_value = {'chat_history': []}
        
        # Execute
        result = collect_chat_history(commit=mock_commit, max_messages_back=150)
        
        # Verify AI filtering was NOT called for empty messages
        mock_filter.assert_not_called()
        
        # Verify result is empty
        assert len(result['messages']) == 0

    @patch('mcp_commit_story.context_collection.filter_chat_for_commit')
    @patch('mcp_commit_story.context_collection.query_cursor_chat_database')
    def test_ai_filtering_error_handling_conservative(self, mock_query, mock_filter):
        """Test conservative error handling when AI filtering fails"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        raw_messages = [
            {'role': 'user', 'content': 'Start work', 'bubbleId': 'msg1', 'timestamp': 1000},
        ]
        
        mock_query.return_value = {'chat_history': raw_messages}
        mock_filter.side_effect = Exception("AI service unavailable")
        
        # Execute - should not raise exception
        result = collect_chat_history(commit=mock_commit, max_messages_back=150)
        
        # Should return all unfiltered messages on error (conservative approach)
        assert len(result['messages']) == 1
        assert result['messages'][0]['speaker'] == 'Human'

    @patch('mcp_commit_story.context_collection.filter_chat_for_commit')
    @patch('mcp_commit_story.context_collection.query_cursor_chat_database')
    @patch('mcp_commit_story.context_collection.collect_git_context')
    def test_telemetry_tracks_filtering_effectiveness(self, mock_git_context, mock_query, mock_filter):
        """Test that telemetry tracks AI filtering effectiveness"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        # Setup filtering that reduces message count
        raw_messages = [
            {'role': 'user', 'content': 'Old work', 'bubbleId': 'msg1', 'timestamp': 1000},
            {'role': 'user', 'content': 'New work', 'bubbleId': 'msg2', 'timestamp': 2000},
            {'role': 'assistant', 'content': 'Working on new', 'bubbleId': 'msg3', 'timestamp': 3000},
        ]
        
        filtered_messages = raw_messages[1:]  # Remove first message
        
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'changed_files': ['test.py'],
            'diff_summary': 'Test changes'
        }
        mock_query.return_value = {'chat_history': raw_messages}
        mock_filter.return_value = filtered_messages
        
        # Execute with telemetry verification
        with patch('opentelemetry.trace.get_current_span') as mock_span:
            mock_span_instance = Mock()
            mock_span.return_value = mock_span_instance
            
            result = collect_chat_history(commit=mock_commit, max_messages_back=150)
            
            # Verify telemetry attributes were set for filtering effectiveness
            mock_span_instance.set_attribute.assert_any_call("ai_filter.messages_before", 3)
            mock_span_instance.set_attribute.assert_any_call("ai_filter.messages_after", 2)
            mock_span_instance.set_attribute.assert_any_call("ai_filter.reduction_count", 1)
            mock_span_instance.set_attribute.assert_any_call("ai_filter.reduction_percentage", 33.33)
            mock_span_instance.set_attribute.assert_any_call("ai_filter.success", True)
            
            # Verify the filtering worked properly
            assert len(result['messages']) == 2  # Should have filtered messages
            mock_filter.assert_called_once()  # AI filtering was called


class TestPipelineIntegration:
    """Test complete pipeline integration"""

    @patch('mcp_commit_story.context_collection.filter_chat_for_commit')
    @patch('mcp_commit_story.composer_chat_provider.ComposerChatProvider')
    @patch('mcp_commit_story.cursor_db.get_commit_time_window')
    @patch('mcp_commit_story.cursor_db.find_workspace_composer_databases')
    @patch('mcp_commit_story.context_collection.collect_git_context')
    def test_end_to_end_pipeline_with_ai_filtering(self, mock_git_context, mock_find, mock_time, mock_provider, mock_filter):
        """Test complete pipeline from orchestrator through AI filtering"""
        mock_commit = Mock(spec=Commit)
        mock_commit.hexsha = "abc123"
        
        # Setup complete pipeline mocks
        mock_find.return_value = ("/workspace/path", "/global/path")
        mock_time.return_value = (1000000, 2000000)
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'changed_files': ['feature_b.py'],
            'diff_summary': 'Add feature B implementation'
        }
        
        # Mock raw messages from ComposerChatProvider
        raw_composer_messages = [
            {'role': 'user', 'content': 'Old work on feature A', 'bubbleId': 'msg1', 'timestamp': 1000},
            {'role': 'user', 'content': 'Now working on feature B', 'bubbleId': 'msg2', 'timestamp': 2000},
            {'role': 'assistant', 'content': 'Feature B implementation', 'bubbleId': 'msg3', 'timestamp': 3000},
        ]
        
        mock_provider_instance = Mock()
        mock_provider_instance.getChatHistoryForCommit.return_value = raw_composer_messages
        mock_provider.return_value = mock_provider_instance
        
        # Mock AI filtering (removes first message about feature A)
        filtered_messages = raw_composer_messages[1:]
        mock_filter.return_value = filtered_messages
        
        # Execute complete pipeline
        result = collect_chat_history(commit=mock_commit, max_messages_back=150)
        
        # Verify the complete flow
        mock_find.assert_called_once()
        mock_time.assert_called_once_with(mock_commit.hexsha)
        mock_filter.assert_called_once()
        
        # Verify result structure and filtering
        assert 'messages' in result
        assert len(result['messages']) == 2  # Should have filtered messages (removed first one)
        
        # Verify AI filtering was effective
        assert result['messages'][0]['text'] == 'Now working on feature B'
        assert result['messages'][1]['text'] == 'Feature B implementation' 