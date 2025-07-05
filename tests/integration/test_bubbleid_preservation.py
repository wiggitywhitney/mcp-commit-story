"""
Integration tests for bubbleId preservation through the full chat collection pipeline.

These tests verify that bubbleId fields from Cursor's database are preserved
through the entire pipeline from ComposerChatProvider to final ChatMessage format.
"""

import pytest
from unittest.mock import Mock, patch
from mcp_commit_story.context_collection import collect_chat_history
from mcp_commit_story.composer_chat_provider import ComposerChatProvider


class TestBubbleIdPreservationIntegration:
    """Integration tests for bubbleId preservation through the full pipeline."""

    def test_full_pipeline_preserves_bubble_id(self):
        """Test that bubbleId is preserved from ComposerChatProvider through collect_chat_history."""
        # Mock ComposerChatProvider to return messages with bubbleId
        mock_composer_messages = [
            {
                'role': 'user',
                'content': 'Test user message',
                'timestamp': 1234567890,
                'sessionName': 'test_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_user_1'
            },
            {
                'role': 'assistant',
                'content': 'Test assistant message',
                'timestamp': 1234567891,
                'sessionName': 'test_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_assistant_1'
            }
        ]
        
        # Mock the full pipeline
        with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock_query, \
             patch('mcp_commit_story.context_collection.filter_chat_for_commit') as mock_filter, \
             patch('mcp_commit_story.context_collection.collect_git_context') as mock_git_context:
            
            # Setup mocks
            mock_query.return_value = {'chat_history': mock_composer_messages}
            mock_filter.return_value = mock_composer_messages
            mock_git_context.return_value = {'metadata': {'hash': 'abc123'}}
            
            # Mock commit object
            mock_commit = Mock()
            mock_commit.hexsha = 'abc123'
            
            # Call collect_chat_history (full pipeline)
            result = collect_chat_history(commit=mock_commit)
            
            # Verify bubbleId is preserved through the entire pipeline
            assert len(result['messages']) == 2
            
            user_message = result['messages'][0]
            assert user_message['speaker'] == 'Human'
            assert user_message['text'] == 'Test user message'
            assert user_message['bubbleId'] == 'bubble_user_1'
            assert user_message['timestamp'] == 1234567890
            assert user_message['sessionName'] == 'test_session'
            
            assistant_message = result['messages'][1]
            assert assistant_message['speaker'] == 'Assistant'
            assert assistant_message['text'] == 'Test assistant message'
            assert assistant_message['bubbleId'] == 'bubble_assistant_1'
            assert assistant_message['timestamp'] == 1234567891
            assert assistant_message['sessionName'] == 'test_session'

    def test_ai_filtering_preserves_bubble_id(self):
        """Test that AI filtering preserves bubbleId when filtering messages."""
        # Mock ComposerChatProvider messages with bubbleId
        original_messages = [
            {
                'role': 'user',
                'content': 'Irrelevant old message',
                'timestamp': 1234567880,
                'sessionName': 'old_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_old_1'
            },
            {
                'role': 'user',
                'content': 'Relevant new message',
                'timestamp': 1234567890,
                'sessionName': 'new_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_new_1'
            },
            {
                'role': 'assistant',
                'content': 'Relevant assistant response',
                'timestamp': 1234567891,
                'sessionName': 'new_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_new_2'
            }
        ]
        
        # Mock AI filtering to filter out the old message
        filtered_messages = [
            {
                'role': 'user',
                'content': 'Relevant new message',
                'timestamp': 1234567890,
                'sessionName': 'new_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_new_1'
            },
            {
                'role': 'assistant',
                'content': 'Relevant assistant response',
                'timestamp': 1234567891,
                'sessionName': 'new_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_new_2'
            }
        ]
        
        # Mock the full pipeline
        with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock_query, \
             patch('mcp_commit_story.context_collection.filter_chat_for_commit') as mock_filter, \
             patch('mcp_commit_story.context_collection.collect_git_context') as mock_git_context:
            
            # Setup mocks
            mock_query.return_value = {'chat_history': original_messages}
            mock_filter.return_value = filtered_messages  # AI filtering applied
            mock_git_context.return_value = {'metadata': {'hash': 'abc123'}}
            
            # Mock commit object
            mock_commit = Mock()
            mock_commit.hexsha = 'abc123'
            
            # Call collect_chat_history (full pipeline with AI filtering)
            result = collect_chat_history(commit=mock_commit)
            
            # Verify AI filtering preserved bubbleId for remaining messages
            assert len(result['messages']) == 2
            
            user_message = result['messages'][0]
            assert user_message['speaker'] == 'Human'
            assert user_message['text'] == 'Relevant new message'
            assert user_message['bubbleId'] == 'bubble_new_1'  # bubbleId preserved after filtering
            
            assistant_message = result['messages'][1]
            assert assistant_message['speaker'] == 'Assistant'
            assert assistant_message['text'] == 'Relevant assistant response'
            assert assistant_message['bubbleId'] == 'bubble_new_2'  # bubbleId preserved after filtering

    def test_pipeline_backward_compatibility_without_bubble_id(self):
        """Test that the pipeline works correctly when bubbleId is not present (backward compatibility)."""
        # Mock ComposerChatProvider messages without bubbleId
        mock_composer_messages = [
            {
                'role': 'user',
                'content': 'Test user message',
                'timestamp': 1234567890,
                'sessionName': 'test_session',
                'composerId': 'comp123'
                # No bubbleId field
            }
        ]
        
        # Mock the full pipeline
        with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock_query, \
             patch('mcp_commit_story.context_collection.filter_chat_for_commit') as mock_filter, \
             patch('mcp_commit_story.context_collection.collect_git_context') as mock_git_context:
            
            # Setup mocks
            mock_query.return_value = {'chat_history': mock_composer_messages}
            mock_filter.return_value = mock_composer_messages
            mock_git_context.return_value = {'metadata': {'hash': 'abc123'}}
            
            # Mock commit object
            mock_commit = Mock()
            mock_commit.hexsha = 'abc123'
            
            # Call collect_chat_history (full pipeline)
            result = collect_chat_history(commit=mock_commit)
            
            # Verify backward compatibility (no bubbleId field)
            assert len(result['messages']) == 1
            
            user_message = result['messages'][0]
            assert user_message['speaker'] == 'Human'
            assert user_message['text'] == 'Test user message'
            assert 'bubbleId' not in user_message  # Should not be present
            assert user_message['timestamp'] == 1234567890
            assert user_message['sessionName'] == 'test_session'

    def test_ai_filtering_error_preserves_bubble_id(self):
        """Test that when AI filtering fails, bubbleId is still preserved in unfiltered messages."""
        # Mock ComposerChatProvider messages with bubbleId
        mock_composer_messages = [
            {
                'role': 'user',
                'content': 'Test user message',
                'timestamp': 1234567890,
                'sessionName': 'test_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_user_1'
            }
        ]
        
        # Mock the pipeline with AI filtering failure
        with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock_query, \
             patch('mcp_commit_story.context_collection.filter_chat_for_commit') as mock_filter, \
             patch('mcp_commit_story.context_collection.collect_git_context') as mock_git_context:
            
            # Setup mocks
            mock_query.return_value = {'chat_history': mock_composer_messages}
            mock_filter.side_effect = Exception("AI filtering failed")  # Simulate AI failure
            mock_git_context.return_value = {'metadata': {'hash': 'abc123'}}
            
            # Mock commit object
            mock_commit = Mock()
            mock_commit.hexsha = 'abc123'
            
            # Call collect_chat_history (should handle AI filtering failure gracefully)
            result = collect_chat_history(commit=mock_commit)
            
            # Verify bubbleId is preserved even when AI filtering fails
            assert len(result['messages']) == 1
            
            user_message = result['messages'][0]
            assert user_message['speaker'] == 'Human'
            assert user_message['text'] == 'Test user message'
            assert user_message['bubbleId'] == 'bubble_user_1'  # bubbleId preserved despite AI failure
            assert user_message['timestamp'] == 1234567890
            assert user_message['sessionName'] == 'test_session' 