"""
Tests for multi-field message extraction bug fix.

Tests that message extraction properly handles different field types:
- User messages (type 1) with text field
- AI messages (type 2) with text field (conversational responses)
- AI messages (type 2) with only thinking.text (should be skipped)
- Tool messages with only toolFormerData (should be skipped)
"""

import json
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp_commit_story.composer_chat_provider import ComposerChatProvider


class TestMultiFieldMessageExtraction:
    """Test message extraction from different field types."""

    @pytest.fixture
    def provider(self):
        """Create ComposerChatProvider instance."""
        return ComposerChatProvider("/workspace.vscdb", "/global.vscdb")

    @pytest.fixture
    def base_time(self):
        """Base timestamp for tests."""
        return datetime(2024, 1, 1, 10, 0, 0)
    
    def to_timestamp_ms(self, dt):
        """Convert datetime to milliseconds timestamp."""
        return int(dt.timestamp() * 1000)

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_user_message_extracts_from_text_field(self, mock_execute_query, provider, base_time):
        """Test that type 1 (user) messages extract content from text field."""
        # Arrange
        session_metadata = {
            "allComposers": [{
                "composerId": "session-1",
                "name": "Test session",
                "createdAt": self.to_timestamp_ms(base_time),
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(minutes=30)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-1", 
            "name": "Test session",
            "createdAt": self.to_timestamp_ms(base_time),
            "fullConversationHeadersOnly": [
                {"bubbleId": "user-msg", "type": 1}  # User message
            ]
        }
        
        user_message_data = {
            "text": "How do I fix this bug?",  # User message has text field
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(user_message_data),)]
        ]
        
        # Act  
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time), 
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert
        assert len(result) == 1
        assert result[0]['role'] == 'user'
        assert result[0]['content'] == "How do I fix this bug?"

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query') 
    def test_ai_conversational_message_extracts_from_text_field(self, mock_execute_query, provider, base_time):
        """Test that type 2 (AI) conversational messages extract content from text field."""
        # Arrange
        session_metadata = {
            "allComposers": [{
                "composerId": "session-1",
                "name": "Test session", 
                "createdAt": self.to_timestamp_ms(base_time),
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(minutes=30)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": self.to_timestamp_ms(base_time),
            "fullConversationHeadersOnly": [
                {"bubbleId": "ai-msg", "type": 2}  # AI message
            ]
        }
        
        ai_conversational_data = {
            "text": "You can fix this by checking the error logs...",  # AI conversational response has text field
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(ai_conversational_data),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time),
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert
        assert len(result) == 1
        assert result[0]['role'] == 'assistant'
        assert result[0]['content'] == "You can fix this by checking the error logs..."

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_ai_thinking_message_skipped_when_no_text_field(self, mock_execute_query, provider, base_time):
        """Test that type 2 (AI) messages with only thinking.text are skipped (empty text field)."""
        # Arrange
        session_metadata = {
            "allComposers": [{
                "composerId": "session-1",
                "name": "Test session",
                "createdAt": self.to_timestamp_ms(base_time),
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(minutes=30)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session", 
            "createdAt": self.to_timestamp_ms(base_time),
            "fullConversationHeadersOnly": [
                {"bubbleId": "ai-thinking", "type": 2}  # AI thinking message
            ]
        }
        
        ai_thinking_data = {
            # No 'text' field - only internal reasoning
            "thinking": {
                "text": "The user is asking about a bug. I should analyze their code and provide step-by-step debugging guidance..."
            },
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(ai_thinking_data),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time),
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert - message should be skipped due to empty text field
        assert len(result) == 0

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_tool_message_skipped_when_no_text_field(self, mock_execute_query, provider, base_time):
        """Test that messages with only toolFormerData are skipped (empty text field)."""
        # Arrange
        session_metadata = {
            "allComposers": [{
                "composerId": "session-1", 
                "name": "Test session",
                "createdAt": self.to_timestamp_ms(base_time),
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(minutes=30)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": self.to_timestamp_ms(base_time),
            "fullConversationHeadersOnly": [
                {"bubbleId": "tool-msg", "type": 2}  # Tool message
            ]
        }
        
        tool_message_data = {
            # No 'text' field - only tool data
            "toolFormerData": {
                "toolName": "file_editor",
                "parameters": {"file": "src/main.py", "content": "..."},
                "result": "File updated successfully"
            },
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(tool_message_data),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time),
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert - message should be skipped due to empty text field
        assert len(result) == 0

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_mixed_message_types_only_text_field_messages_included(self, mock_execute_query, provider, base_time):
        """Test that only messages with text field content are included in results."""
        # Arrange
        session_metadata = {
            "allComposers": [{
                "composerId": "session-1",
                "name": "Test session",
                "createdAt": self.to_timestamp_ms(base_time),
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(minutes=30)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": self.to_timestamp_ms(base_time),
            "fullConversationHeadersOnly": [
                {"bubbleId": "user-msg", "type": 1},      # User message - has text
                {"bubbleId": "ai-thinking", "type": 2},   # AI thinking - no text  
                {"bubbleId": "ai-response", "type": 2},   # AI response - has text
                {"bubbleId": "tool-call", "type": 2}      # Tool call - no text
            ]
        }
        
        user_message = {
            "text": "Can you help me debug this?",
            "context": {}
        }
        
        ai_thinking = {
            "thinking": {"text": "User needs debugging help..."},
            "context": {}
        }
        
        ai_response = {
            "text": "Sure! Let's start by examining the error logs.",
            "context": {}
        }
        
        tool_call = {
            "toolFormerData": {"toolName": "read_file", "parameters": {"file": "error.log"}},
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(user_message),)],
            [(json.dumps(ai_thinking),)],
            [(json.dumps(ai_response),)],
            [(json.dumps(tool_call),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time),
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert - only messages with text field should be included
        assert len(result) == 2
        assert result[0]['role'] == 'user'
        assert result[0]['content'] == "Can you help me debug this?"
        assert result[1]['role'] == 'assistant'
        assert result[1]['content'] == "Sure! Let's start by examining the error logs."

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_empty_text_field_message_skipped(self, mock_execute_query, provider, base_time):
        """Test that messages with empty text field are skipped."""
        # Arrange
        session_metadata = {
            "allComposers": [{
                "composerId": "session-1",
                "name": "Test session",
                "createdAt": self.to_timestamp_ms(base_time),
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(minutes=30)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-1",
            "name": "Test session",
            "createdAt": self.to_timestamp_ms(base_time),
            "fullConversationHeadersOnly": [
                {"bubbleId": "empty-msg", "type": 1}  # User message with empty text
            ]
        }
        
        empty_message = {
            "text": "",  # Empty text field
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(empty_message),)]
        ]
        
        # Act
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time),
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert - empty message should be skipped
        assert len(result) == 0

    @patch('mcp_commit_story.composer_chat_provider.execute_cursor_query')
    def test_session_filtering_still_works_with_message_extraction_fix(self, mock_execute_query, provider, base_time):
        """Test that session time window filtering continues to work correctly."""
        # Arrange - session outside time window
        session_metadata = {
            "allComposers": [{
                "composerId": "session-outside",
                "name": "Outside session",
                "createdAt": self.to_timestamp_ms(base_time + timedelta(hours=2)),  # Outside window
                "lastUpdatedAt": self.to_timestamp_ms(base_time + timedelta(hours=3)),
                "type": "head"
            }]
        }
        
        message_headers = {
            "composerId": "session-outside",
            "name": "Outside session", 
            "createdAt": self.to_timestamp_ms(base_time + timedelta(hours=2)),
            "fullConversationHeadersOnly": [
                {"bubbleId": "msg-outside", "type": 1}
            ]
        }
        
        message_data = {
            "text": "This message is outside the time window",
            "context": {}
        }
        
        mock_execute_query.side_effect = [
            [(json.dumps(session_metadata),)],
            [(json.dumps(message_headers),)],
            [(json.dumps(message_data),)]
        ]
        
        # Act - query for 1 hour window starting at base_time
        result = provider.getChatHistoryForCommit(
            self.to_timestamp_ms(base_time),
            self.to_timestamp_ms(base_time + timedelta(hours=1))
        )
        
        # Assert - session should be filtered out entirely
        assert len(result) == 0 