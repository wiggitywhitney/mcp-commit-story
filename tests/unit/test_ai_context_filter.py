import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from mcp_commit_story.ai_context_filter import filter_chat_for_commit, _parse_ai_response, BoundaryResponse


class TestAIContextFilter:
    """Tests for AI-powered context filtering module"""

    @patch('mcp_commit_story.ai_context_filter.invoke_ai')
    @patch('mcp_commit_story.ai_context_filter.collect_git_context')
    @patch('mcp_commit_story.ai_context_filter.get_previous_commit_info')
    @patch('mcp_commit_story.ai_context_filter.get_previous_journal_entry')
    def test_filter_chat_with_clear_boundary(self, mock_journal, mock_prev_commit, mock_git_context, mock_invoke_ai):
        """Test AI boundary detection when there's a clear transition between work"""
        # Setup mocks
        mock_git_context.return_value = {"message": "Add feature X", "files": ["feature_x.py"]}
        mock_prev_commit.return_value = {"hexsha": "abc123", "message": "Fix bug Y"}
        mock_journal.return_value = "Previous work on bug fixes"
        mock_invoke_ai.return_value = json.dumps({
            "bubbleId": "msg_4",
            "confidence": 9,
            "reasoning": "Clear transition from bug fixes to feature X development"
        })
        
        # Test data with proper ChatMessage-like objects
        mock_messages = [
            {'bubbleId': 'msg_1', 'speaker': 'Human', 'text': 'Working on bug Y', 'timestamp': 1000},
            {'bubbleId': 'msg_2', 'speaker': 'Assistant', 'text': 'Bug Y is fixed', 'timestamp': 2000},
            {'bubbleId': 'msg_3', 'speaker': 'Human', 'text': 'Great, let me commit that', 'timestamp': 3000},
            {'bubbleId': 'msg_4', 'speaker': 'Human', 'text': 'Now starting feature X', 'timestamp': 4000},
            {'bubbleId': 'msg_5', 'speaker': 'Assistant', 'text': 'Feature X implementation', 'timestamp': 5000},
        ]
        
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        # Execute
        result = filter_chat_for_commit(mock_messages, mock_commit)
        
        # Verify AI was called
        mock_invoke_ai.assert_called_once()
        
        # Verify result contains messages from boundary onwards
        assert len(result) == 2
        assert result[0]['bubbleId'] == 'msg_4'
        assert result[1]['bubbleId'] == 'msg_5'

    @patch('mcp_commit_story.ai_context_filter.invoke_ai')
    @patch('mcp_commit_story.ai_context_filter.collect_git_context')
    @patch('mcp_commit_story.ai_context_filter.get_previous_commit_info')
    @patch('mcp_commit_story.ai_context_filter.get_previous_journal_entry')
    def test_filter_chat_handles_invalid_bubble_id(self, mock_journal, mock_prev_commit, mock_git_context, mock_invoke_ai):
        """Test handling when AI returns invalid bubbleId"""
        # Setup mocks
        mock_git_context.return_value = {"message": "Add feature", "files": ["feature.py"]}
        mock_prev_commit.return_value = None
        mock_journal.return_value = None
        mock_invoke_ai.return_value = json.dumps({
            "bubbleId": "invalid_id",  # This ID doesn't exist in messages
            "confidence": 5,
            "reasoning": "AI made an error"
        })
        
        mock_messages = [
            {'bubbleId': 'msg_1', 'speaker': 'Human', 'text': 'Start work', 'timestamp': 1000},
            {'bubbleId': 'msg_2', 'speaker': 'Assistant', 'text': 'Working on it', 'timestamp': 2000},
        ]
        
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        # Execute
        result = filter_chat_for_commit(mock_messages, mock_commit)
        
        # Should fallback to first message when invalid bubbleId is returned
        assert len(result) == 2
        assert result[0]['bubbleId'] == 'msg_1'

    @patch('mcp_commit_story.ai_context_filter.invoke_ai')
    @patch('mcp_commit_story.ai_context_filter.collect_git_context')
    @patch('mcp_commit_story.ai_context_filter.get_previous_commit_info')
    @patch('mcp_commit_story.ai_context_filter.get_previous_journal_entry')
    def test_filter_chat_handles_ai_failure(self, mock_journal, mock_prev_commit, mock_git_context, mock_invoke_ai):
        """Test error handling when AI call fails"""
        # Setup mocks
        mock_git_context.return_value = {"message": "Add feature", "files": ["feature.py"]}
        mock_prev_commit.return_value = None
        mock_journal.return_value = None
        mock_invoke_ai.side_effect = Exception("AI service unavailable")
        
        mock_messages = [
            {'bubbleId': 'msg_1', 'speaker': 'Human', 'text': 'Start work', 'timestamp': 1000},
            {'bubbleId': 'msg_2', 'speaker': 'Assistant', 'text': 'Working on it', 'timestamp': 2000},
        ]
        
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        # Execute (should use conservative error strategy by default)
        result = filter_chat_for_commit(mock_messages, mock_commit)
        
        # Should return all messages on error (conservative approach)
        assert len(result) == 2
        assert result == mock_messages

    @patch('mcp_commit_story.ai_context_filter.invoke_ai')
    @patch('mcp_commit_story.ai_context_filter.collect_git_context')
    @patch('mcp_commit_story.ai_context_filter.get_previous_commit_info')
    @patch('mcp_commit_story.ai_context_filter.get_previous_journal_entry')
    def test_filter_chat_aggressive_error_strategy(self, mock_journal, mock_prev_commit, mock_git_context, mock_invoke_ai):
        """Test aggressive error handling strategy"""
        # Setup mocks
        mock_git_context.return_value = {"message": "Add feature", "files": ["feature.py"]}
        mock_prev_commit.return_value = None
        mock_journal.return_value = None
        mock_invoke_ai.side_effect = Exception("AI service unavailable")
        
        mock_messages = [
            {'bubbleId': 'msg_1', 'speaker': 'Human', 'text': 'Start work', 'timestamp': 1000},
        ]
        
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        # Set aggressive error strategy
        with patch.dict(os.environ, {'AI_FILTER_ERROR_STRATEGY': 'aggressive'}):
            result = filter_chat_for_commit(mock_messages, mock_commit)
        
        # Should return empty list with aggressive strategy
        assert len(result) == 0

    @patch('mcp_commit_story.ai_context_filter.invoke_ai')
    @patch('mcp_commit_story.ai_context_filter.collect_git_context')
    @patch('mcp_commit_story.ai_context_filter.get_previous_commit_info')
    @patch('mcp_commit_story.ai_context_filter.get_previous_journal_entry')
    def test_filter_chat_raise_error_strategy(self, mock_journal, mock_prev_commit, mock_git_context, mock_invoke_ai):
        """Test raise error handling strategy"""
        # Setup mocks
        mock_git_context.return_value = {"message": "Add feature", "files": ["feature.py"]}
        mock_prev_commit.return_value = None
        mock_journal.return_value = None
        mock_invoke_ai.side_effect = Exception("AI service unavailable")
        
        mock_messages = [
            {'bubbleId': 'msg_1', 'speaker': 'Human', 'text': 'Start work', 'timestamp': 1000},
        ]
        
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        # Set raise error strategy
        with patch.dict(os.environ, {'AI_FILTER_ERROR_STRATEGY': 'raise'}):
            with pytest.raises(Exception, match="AI service unavailable"):
                filter_chat_for_commit(mock_messages, mock_commit)

    def test_filter_chat_empty_messages(self):
        """Test handling of empty message list"""
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        result = filter_chat_for_commit([], mock_commit)
        assert result == []

    def test_filter_chat_missing_bubble_id(self):
        """Test handling of messages missing bubbleId"""
        mock_messages = [
            {'speaker': 'Human', 'text': 'Start work', 'timestamp': 1000},  # Missing bubbleId
        ]
        
        mock_commit = Mock()
        mock_commit.hexsha = "def456"
        
        # Should return unfiltered messages on validation error
        result = filter_chat_for_commit(mock_messages, mock_commit)
        assert result == mock_messages


class TestParseAIResponse:
    """Tests for AI response parsing"""

    def test_parse_valid_response(self):
        """Test parsing a valid AI response"""
        response = json.dumps({
            "bubbleId": "msg_123",
            "confidence": 8,
            "reasoning": "Clear boundary detected"
        })
        
        result = _parse_ai_response(response)
        
        assert result['bubbleId'] == "msg_123"
        assert result['confidence'] == 8
        assert result['reasoning'] == "Clear boundary detected"

    def test_parse_response_with_whitespace(self):
        """Test parsing response with extra whitespace"""
        response = json.dumps({
            "bubbleId": "  msg_123  ",
            "confidence": 8,
            "reasoning": "  Clear boundary detected  "
        })
        
        result = _parse_ai_response(response)
        
        # Should strip whitespace
        assert result['bubbleId'] == "msg_123"
        assert result['reasoning'] == "Clear boundary detected"

    def test_parse_empty_response(self):
        """Test parsing empty response"""
        with pytest.raises(ValueError, match="Empty AI response"):
            _parse_ai_response("")

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        with pytest.raises(ValueError, match="Invalid JSON"):
            _parse_ai_response("not json")

    def test_parse_missing_bubble_id(self):
        """Test parsing response missing bubbleId"""
        response = json.dumps({
            "confidence": 8,
            "reasoning": "Clear boundary detected"
        })
        
        with pytest.raises(ValueError, match="missing required 'bubbleId' field"):
            _parse_ai_response(response)

    def test_parse_missing_confidence(self):
        """Test parsing response missing confidence"""
        response = json.dumps({
            "bubbleId": "msg_123",
            "reasoning": "Clear boundary detected"
        })
        
        with pytest.raises(ValueError, match="missing required 'confidence' field"):
            _parse_ai_response(response)

    def test_parse_missing_reasoning(self):
        """Test parsing response missing reasoning"""
        response = json.dumps({
            "bubbleId": "msg_123",
            "confidence": 8
        })
        
        with pytest.raises(ValueError, match="missing required 'reasoning' field"):
            _parse_ai_response(response)

    def test_parse_invalid_bubble_id_type(self):
        """Test parsing with invalid bubbleId type"""
        response = json.dumps({
            "bubbleId": 123,  # Should be string
            "confidence": 8,
            "reasoning": "Clear boundary detected"
        })
        
        with pytest.raises(ValueError, match="bubbleId must be a non-empty string"):
            _parse_ai_response(response)

    def test_parse_empty_bubble_id(self):
        """Test parsing with empty bubbleId"""
        response = json.dumps({
            "bubbleId": "",
            "confidence": 8,
            "reasoning": "Clear boundary detected"
        })
        
        with pytest.raises(ValueError, match="bubbleId must be a non-empty string"):
            _parse_ai_response(response)

    def test_parse_invalid_confidence_type(self):
        """Test parsing with invalid confidence type"""
        response = json.dumps({
            "bubbleId": "msg_123",
            "confidence": "8",  # Should be int
            "reasoning": "Clear boundary detected"
        })
        
        with pytest.raises(ValueError, match="confidence must be an integer between 1 and 10"):
            _parse_ai_response(response)

    def test_parse_confidence_out_of_range(self):
        """Test parsing with confidence out of valid range"""
        for invalid_confidence in [0, 11, -1, 100]:
            response = json.dumps({
                "bubbleId": "msg_123",
                "confidence": invalid_confidence,
                "reasoning": "Clear boundary detected"
            })
            
            with pytest.raises(ValueError, match="confidence must be an integer between 1 and 10"):
                _parse_ai_response(response)

    def test_parse_invalid_reasoning_type(self):
        """Test parsing with invalid reasoning type"""
        response = json.dumps({
            "bubbleId": "msg_123",
            "confidence": 8,
            "reasoning": 123  # Should be string
        })
        
        with pytest.raises(ValueError, match="reasoning must be a non-empty string"):
            _parse_ai_response(response)

    def test_parse_empty_reasoning(self):
        """Test parsing with empty reasoning"""
        response = json.dumps({
            "bubbleId": "msg_123",
            "confidence": 8,
            "reasoning": ""
        })
        
        with pytest.raises(ValueError, match="reasoning must be a non-empty string"):
            _parse_ai_response(response) 