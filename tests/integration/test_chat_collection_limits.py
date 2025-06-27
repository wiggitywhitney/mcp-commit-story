"""
Integration tests for message limiting in chat collection.

These tests verify the integration of limit_chat_messages() with the collect_chat_history()
function to ensure proper message count controls and telemetry logging.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from mcp_commit_story.context_collection import collect_chat_history
from mcp_commit_story.context_types import ChatHistory


@pytest.fixture
def sample_chat_history():
    """Sample chat history with mixed human and AI messages in cursor_db format."""
    return {
        'chat_history': [
            {'role': 'user', 'content': f'Human message {i}'} 
            for i in range(250)  # Over our 200 limit
        ] + [
            {'role': 'assistant', 'content': f'AI message {i}'}
            for i in range(250)  # Over our 200 limit  
        ],
        'workspace_info': {'source': 'test_database'}
    }


@pytest.fixture
def small_chat_history():
    """Sample chat history under the default limits in cursor_db format."""
    return {
        'chat_history': [
            {'role': 'user', 'content': f'Human message {i}'} 
            for i in range(50)  # Under 200 limit
        ] + [
            {'role': 'assistant', 'content': f'AI message {i}'}
            for i in range(50)  # Under 200 limit  
        ],
        'workspace_info': {'source': 'test_database'}
    }


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.limit_chat_messages')
def test_collect_chat_history_default_limits(mock_limit_messages, mock_query_db, sample_chat_history):
    """Test that collect_chat_history applies default 200/200 limits correctly."""
    # Setup mocks
    mock_query_db.return_value = sample_chat_history
    
    # Mock limit_chat_messages to simulate truncation
    truncated_history = {
        'chat_history': sample_chat_history['chat_history'][:400],  # Truncated to 400 total
        'metadata': {
            **sample_chat_history['workspace_info'],
            'truncated_human': True,
            'truncated_ai': True,
            'removed_human_count': 50,
            'removed_ai_count': 50,
            'original_human_count': 250,
            'original_ai_count': 250
        }
    }
    mock_limit_messages.return_value = truncated_history
    
    # Call function
    result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify database query was called
    mock_query_db.assert_called_once()
    
    # Verify limit_chat_messages was called with correct parameters
    mock_limit_messages.assert_called_once_with(
        sample_chat_history, 200, 200
    )
    
    # Verify result structure
    assert isinstance(result, dict)
    assert 'messages' in result
    # Result should be in ChatHistory format with proper speaker names
    assert all('speaker' in msg and 'text' in msg for msg in result['messages'])
    # Verify proper speaker conversion
    for msg in result['messages']:
        assert msg['speaker'] in ['Human', 'Assistant']


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.limit_chat_messages')
@patch('mcp_commit_story.telemetry.get_mcp_metrics')
def test_telemetry_logging_with_truncation(mock_get_metrics, mock_limit_messages, 
                                          mock_query_db, sample_chat_history):
    """Test that telemetry events are logged when message truncation occurs."""
        # Setup mocks
    mock_query_db.return_value = sample_chat_history
    
    # Setup telemetry mock
    mock_metrics = MagicMock()
    mock_get_metrics.return_value = mock_metrics

    # Mock limit_chat_messages to simulate truncation
    truncated_messages = [
        {'role': 'user', 'content': f'Human message {i}'}
        for i in range(200)  # 200 human messages
    ] + [
        {'role': 'assistant', 'content': f'AI message {i}'}
        for i in range(200)  # 200 AI messages
    ]

    truncated_history = {
        'chat_history': truncated_messages,
        'metadata': {
            **sample_chat_history['workspace_info'],
            'truncated_human': True,
            'truncated_ai': True,
            'removed_human_count': 50,
            'removed_ai_count': 50,
            'original_human_count': 250,
            'original_ai_count': 250
        }
    }
    mock_limit_messages.return_value = truncated_history
    
    # Call function
    result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify telemetry was logged with correct format
    # Find the specific truncation call among multiple telemetry calls
    expected_call = call(
        'chat_history_truncation',
        attributes={
            'original_human_count': '250',
            'original_ai_count': '250',
            'removed_human_count': '50',
            'removed_ai_count': '50',
            'max_human_messages': '200',
            'max_ai_messages': '200'
        }
    )
    assert expected_call in mock_metrics.record_counter.call_args_list


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.limit_chat_messages')
@patch('mcp_commit_story.context_collection.get_mcp_metrics')
def test_telemetry_logging_without_truncation(mock_get_metrics, mock_limit_messages,
                                             mock_query_db, small_chat_history):
    """Test that telemetry events are NOT logged when no truncation occurs."""
    # Setup mocks
    mock_query_db.return_value = small_chat_history
    
    # Setup telemetry mock
    mock_metrics = MagicMock()
    mock_get_metrics.return_value = mock_metrics
    
    # Mock limit_chat_messages to return unmodified small history (no truncation)
    untruncated_history = {
        'chat_history': small_chat_history['chat_history'],
        'metadata': {
            **small_chat_history['workspace_info'],
            'truncated_human': False,
            'truncated_ai': False,
            'removed_human_count': 0,
            'removed_ai_count': 0,
            'original_human_count': 50,
            'original_ai_count': 50
        }
    }
    mock_limit_messages.return_value = untruncated_history
    
    # Call function
    result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify telemetry was NOT logged (no truncation)
    mock_metrics.record_counter.assert_not_called()


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.logger')
def test_error_handling_when_limit_unavailable(mock_logger, mock_query_db, sample_chat_history):
    """Test graceful fallback when limit_chat_messages is unavailable."""
    # Setup mocks
    mock_query_db.return_value = sample_chat_history
    
    # Mock ImportError during limit_chat_messages import
    with patch('mcp_commit_story.context_collection.limit_chat_messages', None):
        result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify warning was logged
    mock_logger.warning.assert_called()
    warning_call = mock_logger.warning.call_args[0][0]
    assert 'Message limiting module not available' in warning_call
    
    # Should return unfiltered but converted data
    assert isinstance(result, dict)
    assert len(result['messages']) == 500  # Original untruncated count


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.limit_chat_messages')
@patch('mcp_commit_story.context_collection.logger')
def test_error_handling_when_limit_raises_exception(mock_logger, mock_limit_messages,
                                                   mock_query_db, sample_chat_history):
    """Test graceful fallback when limit_chat_messages raises an exception."""
    # Setup mocks
    mock_query_db.return_value = sample_chat_history
    mock_limit_messages.side_effect = Exception("Database error")
    
    # Call function
    result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify warning was logged
    mock_logger.warning.assert_called()
    warning_call = mock_logger.warning.call_args[0][0]
    assert 'Message limiting failed' in warning_call
    
    # Should return unfiltered but converted data
    assert isinstance(result, dict)
    assert len(result['messages']) == 500  # Original untruncated count


def test_empty_chat_history_handling():
    """Test handling of empty or None chat history."""
    with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock_query:
        # Test with None return
        mock_query.return_value = None
        result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
        assert isinstance(result, dict)
        assert result['messages'] == []
        
        # Test with empty chat_history
        mock_query.return_value = {'chat_history': [], 'workspace_info': {}}
        result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
        assert isinstance(result, dict)
        assert result['messages'] == []


def test_parameter_validation_integration():
    """Test that parameter validation still works correctly."""
    # Test None since_commit
    with pytest.raises(ValueError, match="since_commit and max_messages_back must not be None"):
        collect_chat_history(since_commit=None, max_messages_back=150)
    
    # Test None max_messages_back
    with pytest.raises(ValueError, match="since_commit and max_messages_back must not be None"):
        collect_chat_history(since_commit='test_commit', max_messages_back=None)


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.limit_chat_messages')
def test_integration_with_query_cursor_chat_database(mock_limit_messages, mock_query_db, sample_chat_history):
    """Test integration with the cursor database query function."""
    # Setup mocks
    mock_query_db.return_value = sample_chat_history
    mock_limit_messages.return_value = sample_chat_history
    
    # Call function
    result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify integration points
    mock_query_db.assert_called_once()
    mock_limit_messages.assert_called_once_with(sample_chat_history, 200, 200)
    
    # Verify proper format conversion
    assert isinstance(result, dict)
    for msg in result['messages']:
        assert msg['speaker'] in ['Human', 'Assistant']
        assert 'text' in msg


@patch('mcp_commit_story.context_collection.query_cursor_chat_database')
@patch('mcp_commit_story.context_collection.limit_chat_messages')
def test_speaker_format_conversion(mock_limit_messages, mock_query_db):
    """Test that role to speaker conversion works correctly."""
    # Setup test data with specific roles
    test_data = {
        'chat_history': [
            {'role': 'user', 'content': 'Test human message'},
            {'role': 'assistant', 'content': 'Test AI message'}
        ],
        'workspace_info': {}
    }
    
    mock_query_db.return_value = test_data
    mock_limit_messages.return_value = test_data
    
    # Call function
    result = collect_chat_history(since_commit='test_commit', max_messages_back=150)
    
    # Verify conversion
    assert len(result['messages']) == 2
    assert result['messages'][0]['speaker'] == 'Human'
    assert result['messages'][0]['text'] == 'Test human message'
    assert result['messages'][1]['speaker'] == 'Assistant'
    assert result['messages'][1]['text'] == 'Test AI message' 