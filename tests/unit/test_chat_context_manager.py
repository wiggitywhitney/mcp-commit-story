"""
Unit tests for Chat Context Manager implementation.

This module tests the chat context extraction functionality that provides
enhanced chat data with timestamps, session names, and time window information
for journal generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import time

# These imports will fail initially - that's expected in TDD
from src.mcp_commit_story.chat_context_manager import (
    extract_chat_for_commit,
    TimeWindow,
    ChatContextData
)
from src.mcp_commit_story.context_types import ChatMessage


class TestChatMessageEnhancements:
    """Test enhanced ChatMessage type with optional fields."""
    
    def test_chat_message_accepts_optional_timestamp(self):
        """Test that ChatMessage now accepts optional timestamp field."""
        # Basic message without timestamp (backward compatibility)
        basic_message = ChatMessage(
            speaker="Human",
            text="Hello world"
        )
        assert basic_message["speaker"] == "Human"
        assert basic_message["text"] == "Hello world"
        
        # Enhanced message with timestamp
        enhanced_message = ChatMessage(
            speaker="Assistant", 
            text="Hi there!",
            timestamp=1672531200000  # 2023-01-01T00:00:00Z
        )
        assert enhanced_message["speaker"] == "Assistant"
        assert enhanced_message["text"] == "Hi there!"
        assert enhanced_message["timestamp"] == 1672531200000
    
    def test_chat_message_accepts_optional_session_name(self):
        """Test that ChatMessage now accepts optional sessionName field."""
        # Enhanced message with sessionName
        enhanced_message = ChatMessage(
            speaker="Human",
            text="Let's implement authentication",
            sessionName="Implement user auth feature"
        )
        assert enhanced_message["speaker"] == "Human"
        assert enhanced_message["text"] == "Let's implement authentication"
        assert enhanced_message["sessionName"] == "Implement user auth feature"
    
    def test_chat_message_accepts_all_optional_fields(self):
        """Test ChatMessage with all optional fields together."""
        full_message = ChatMessage(
            speaker="Assistant",
            text="I'll help you with that implementation",
            timestamp=1672531200000,
            sessionName="Implement user auth feature"
        )
        assert full_message["speaker"] == "Assistant"
        assert full_message["text"] == "I'll help you with that implementation"
        assert full_message["timestamp"] == 1672531200000
        assert full_message["sessionName"] == "Implement user auth feature"


class TestNewTypeDefinitions:
    """Test new TimeWindow and ChatContextData types."""
    
    def test_time_window_type_structure(self):
        """Test TimeWindow TypedDict has correct structure."""
        time_window = TimeWindow(
            start_timestamp_ms=1672531200000,
            end_timestamp_ms=1672617600000,
            strategy="commit_based",
            duration_hours=24.0
        )
        
        assert time_window["start_timestamp_ms"] == 1672531200000
        assert time_window["end_timestamp_ms"] == 1672617600000
        assert time_window["strategy"] == "commit_based"
        assert time_window["duration_hours"] == 24.0
    
    def test_chat_context_data_type_structure(self):
        """Test ChatContextData TypedDict has correct structure."""
        messages = [
            ChatMessage(speaker="Human", text="Hello", timestamp=1672531200000)
        ]
        time_window = TimeWindow(
            start_timestamp_ms=1672531200000,
            end_timestamp_ms=1672617600000,
            strategy="commit_based", 
            duration_hours=24.0
        )
        
        context_data = ChatContextData(
            messages=messages,
            time_window=time_window,
            session_names=["Test Session"],
            metadata={"message_count": 1}
        )
        
        assert context_data["messages"] == messages
        assert context_data["time_window"] == time_window
        assert context_data["session_names"] == ["Test Session"]
        assert context_data["metadata"]["message_count"] == 1


class TestExtractChatForCommit:
    """Test the main extract_chat_for_commit function."""
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_extract_chat_calls_query_cursor_chat_database(self, mock_query):
        """Test that extract_chat_for_commit calls existing query function."""
        # Mock the response from query_cursor_chat_database
        mock_query.return_value = {
            'chat_history': [
                {
                    'role': 'user',
                    'content': 'Hello',
                    'timestamp': 1672531200000,
                    'sessionName': 'Test Session'
                }
            ],
            'workspace_info': {
                'start_timestamp_ms': 1672531200000,
                'end_timestamp_ms': 1672617600000,
                'strategy': 'commit_based'
            }
        }
        
        result = extract_chat_for_commit()
        
        # Should call the existing function
        mock_query.assert_called_once()
        
        # Should return ChatContextData structure
        assert isinstance(result, dict)
        assert 'messages' in result
        assert 'time_window' in result
        assert 'session_names' in result
        assert 'metadata' in result
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_transforms_speaker_format(self, mock_query):
        """Test transformation from role to speaker format."""
        mock_query.return_value = {
            'chat_history': [
                {'role': 'user', 'content': 'Question?', 'timestamp': 1672531200000},
                {'role': 'assistant', 'content': 'Answer!', 'timestamp': 1672531260000}
            ],
            'workspace_info': {
                'start_timestamp_ms': 1672531200000,
                'end_timestamp_ms': 1672617600000,
                'strategy': 'commit_based'
            }
        }
        
        result = extract_chat_for_commit()
        
        # Should transform role to speaker format
        messages = result['messages']
        assert messages[0]['speaker'] == 'Human'  # user -> Human
        assert messages[1]['speaker'] == 'Assistant'  # assistant -> Assistant
    
    def test_extracts_unique_session_names(self):
        """Test that session names are no longer extracted since sessionName support was removed."""
        with patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database') as mock_query:
            mock_query.return_value = {
                'chat_history': [
                    {'role': 'user', 'content': 'Hello', 'composerId': 'comp123', 'bubbleId': 'bubble1'},
                    {'role': 'assistant', 'content': 'Hi', 'composerId': 'comp123', 'bubbleId': 'bubble2'},
                    {'role': 'user', 'content': 'New topic', 'composerId': 'comp456', 'bubbleId': 'bubble3'},
                    {'role': 'user', 'content': 'Another message', 'composerId': 'comp123', 'bubbleId': 'bubble4'}
                ],
                'workspace_info': {'start_timestamp_ms': 0, 'end_timestamp_ms': 1000, 'strategy': 'test'}
            }
            
            result = extract_chat_for_commit()
            
            # Should no longer extract session names since sessionName support was removed
            session_names = result['session_names']
            assert len(session_names) == 0  # Should be empty since we removed sessionName support
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_builds_time_window_from_workspace_info(self, mock_query):
        """Test TimeWindow construction from workspace_info."""
        mock_query.return_value = {
            'chat_history': [],
            'workspace_info': {
                'start_timestamp_ms': 1672531200000,
                'end_timestamp_ms': 1672617600000,
                'strategy': 'commit_based'
            }
        }
        
        result = extract_chat_for_commit()
        
        time_window = result['time_window']
        assert time_window['start_timestamp_ms'] == 1672531200000
        assert time_window['end_timestamp_ms'] == 1672617600000
        assert time_window['strategy'] == 'commit_based'
        assert time_window['duration_hours'] == 24.0  # 86400000ms = 24 hours


class TestErrorHandling:
    """Test graceful error handling scenarios."""
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_graceful_degradation_on_query_failure(self, mock_query):
        """Test graceful degradation when query_cursor_chat_database fails."""
        mock_query.side_effect = Exception("Database connection failed")
        
        result = extract_chat_for_commit()
        
        # Should return empty ChatContextData instead of crashing
        assert result['messages'] == []
        assert result['session_names'] == []
        # Metadata should contain error information for debugging
        assert 'error_info' in result['metadata']
        assert result['metadata']['error_info']['error_type'] == 'Exception'
        assert result['metadata']['error_info']['message'] == 'Database connection failed'
        # Should still have a valid time_window with fallback values
        assert 'time_window' in result
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_handles_missing_workspace_info(self, mock_query):
        """Test handling when workspace_info is missing."""
        mock_query.return_value = {
            'chat_history': [
                {'role': 'user', 'content': 'Hello'}
            ]
            # Missing workspace_info
        }
        
        result = extract_chat_for_commit()
        
        # Should handle gracefully with fallback time window
        assert 'time_window' in result
        assert result['time_window']['strategy'] == 'fallback'
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_handles_malformed_chat_history(self, mock_query):
        """Test handling of malformed chat history data."""
        mock_query.return_value = {
            'chat_history': [
                {'role': 'user'},  # Missing content
                {'content': 'No role'},  # Missing role
                {'role': 'unknown', 'content': 'Unknown role'}  # Unknown role
            ],
            'workspace_info': {'start_timestamp_ms': 0, 'end_timestamp_ms': 1000, 'strategy': 'test'}
        }
        
        result = extract_chat_for_commit()
        
        # Should filter out malformed messages gracefully
        valid_messages = [msg for msg in result['messages'] if msg.get('speaker') and msg.get('text')]
        assert len(valid_messages) >= 0  # Should not crash


class TestTelemetryIntegration:
    """Test telemetry span creation and attributes."""
    
    @patch('src.mcp_commit_story.chat_context_manager.HAS_TELEMETRY', True)
    @patch('src.mcp_commit_story.chat_context_manager.tracer')
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_telemetry_span_creation_with_telemetry(self, mock_query, mock_tracer):
        """Test that telemetry span is created when OpenTelemetry is available."""
        mock_span = Mock()
        # Add context manager support to the mock span
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=None)
        mock_tracer.start_span.return_value = mock_span
        
        mock_query.return_value = {
            'chat_history': [
                {'role': 'user', 'content': 'Hello', 'composerId': 'comp123', 'bubbleId': 'bubble1'}
            ],
            'workspace_info': {
                'start_timestamp_ms': 1672531200000,
                'end_timestamp_ms': 1672617600000,
                'strategy': 'commit_based'
            }
        }

        result = extract_chat_for_commit()

        # Should create span with correct name
        mock_tracer.start_span.assert_called_once_with('extract_chat_for_commit')

        # Should call context manager methods
        mock_span.__enter__.assert_called_once()
        mock_span.__exit__.assert_called_once()

        # Should set telemetry attributes
        mock_span.set_attribute.assert_any_call('chat.messages_found', 1)
        mock_span.set_attribute.assert_any_call('chat.session_count', 0)  # Should be 0 since we removed sessionName support
        mock_span.set_attribute.assert_any_call('chat.time_window_hours', 24.0)
        mock_span.set_attribute.assert_any_call('chat.workspace_detected', True)

        # Function should work correctly
        assert isinstance(result, dict)
        assert 'messages' in result
        assert len(result['messages']) == 1
        assert result['messages'][0]['speaker'] == 'Human'
        assert result['messages'][0]['text'] == 'Hello'
    
    @patch('src.mcp_commit_story.chat_context_manager.HAS_TELEMETRY', False)
    @patch('src.mcp_commit_story.chat_context_manager.tracer', None)
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_telemetry_span_creation_without_telemetry(self, mock_query):
        """Test that function works correctly when OpenTelemetry is not available."""
        mock_query.return_value = {
            'chat_history': [
                {'role': 'user', 'content': 'Hello', 'composerId': 'comp123', 'bubbleId': 'bubble1'}
            ],
            'workspace_info': {
                'start_timestamp_ms': 1672531200000,
                'end_timestamp_ms': 1672617600000,
                'strategy': 'commit_based'
            }
        }
        
        result = extract_chat_for_commit()
        
        # Function should work correctly without telemetry
        assert isinstance(result, dict)
        assert 'messages' in result
        assert len(result['messages']) == 1
        assert result['messages'][0]['speaker'] == 'Human'
        assert result['messages'][0]['text'] == 'Hello'


class TestPerformanceRequirements:
    """Test performance under 500ms threshold."""
    
    @patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database')
    def test_performance_under_threshold(self, mock_query):
        """Test that extract_chat_for_commit completes under 500ms threshold."""
        # Mock a realistic response
        mock_query.return_value = {
            'chat_history': [
                {'role': 'user', 'content': f'Message {i}', 'composerId': f'comp{i%3}', 'bubbleId': f'bubble{i}'}
                for i in range(100)  # 100 messages to test with reasonable load
            ],
            'workspace_info': {
                'start_timestamp_ms': 1672531200000,
                'end_timestamp_ms': 1672617600000,
                'strategy': 'commit_based'
            }
        }

        start_time = time.time()
        result = extract_chat_for_commit()
        duration = time.time() - start_time

        # Should complete under 500ms threshold
        assert duration < 0.5, f"Performance test failed: {duration:.3f}s > 0.5s threshold"

        # Should still return valid data
        assert len(result['messages']) == 100
        assert len(result['session_names']) == 0  # Should be 0 since we removed sessionName support


        # Note: Integration tests are implemented separately 