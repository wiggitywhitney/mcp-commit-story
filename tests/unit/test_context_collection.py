import pytest
import git
import os
from pathlib import Path
from typing import get_type_hints
from mcp_commit_story.context_types import ChatMessage, ChatHistory
from mcp_commit_story.context_collection import collect_chat_history, collect_git_context
from unittest.mock import Mock, patch

# Assume these will be imported from the journal module
# from mcp_commit_story.journal import collect_commit_metadata, extract_code_diff, gather_discussion_notes, capture_file_changes, collect_chat_history, collect_ai_terminal_commands

def setup_temp_repo_with_commit(tmp_path):
    repo = git.Repo.init(tmp_path)
    file_path = Path(tmp_path) / "file.txt"
    file_path.write_text("hello")
    repo.index.add([str(file_path)])
    commit = repo.index.commit("test commit")
    return repo, commit

def test_collect_git_context_metadata_fields(tmp_path):
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    assert isinstance(ctx, dict)
    assert 'metadata' in ctx
    meta = ctx['metadata']
    for field in ['hash', 'author', 'date', 'message']:
        assert field in meta

def test_collect_git_context_diff_summary(tmp_path):
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    assert 'diff_summary' in ctx
    assert isinstance(ctx['diff_summary'], str)

def test_collect_git_context_changed_files_and_stats(tmp_path):
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    assert 'changed_files' in ctx
    assert isinstance(ctx['changed_files'], list)
    assert 'file_stats' in ctx
    for key in ['source', 'config', 'docs', 'tests']:
        assert key in ctx['file_stats']
        assert isinstance(ctx['file_stats'][key], int)

def test_collect_chat_history_thoroughness_and_boundary():
    """
    collect_chat_history should:
    - Search backward for the last mcp-commit-story new-entry command (or similar)
    - If not found, review all available conversation history
    - Review ALL chat messages and terminal commands within this boundary
    - Be thorough and not skip or summarize large portions
    - Exclude sensitive data and ambiguous notes
    - Format output as a list of dicts with 'speaker' and 'text' or just 'text'
    """
    # This test would mock a conversation and check that only the correct boundary is used,
    # all relevant notes are included, and filtering/formatting is correct.
    pass

# Architecture Decision: Terminal Command Collection Removed (2025-06-27)
# Terminal command collection tests removed as functionality no longer supported

def test_collect_chat_history_type_hint():
    hints = get_type_hints(collect_chat_history)
    assert 'return' in hints
    assert hints['return'].__name__ == 'ChatHistory'

# Architecture Decision: Terminal Command Collection Removed (2025-06-27)
# Terminal command type hint tests removed as functionality no longer supported

def test_collect_git_context_invalid_repo(tmp_path):
    # Create a directory that is not a git repo
    non_repo_path = tmp_path / "not_a_repo"
    non_repo_path.mkdir()
    with pytest.raises(git.InvalidGitRepositoryError):
        collect_git_context("HEAD", repo=git.Repo(str(non_repo_path)))

def test_collect_git_context_bad_commit_hash(tmp_path):
    repo = git.Repo.init(tmp_path)
    # No commits yet, so any hash is bad
    with pytest.raises(git.BadName):
        collect_git_context("deadbeef", repo=repo)

def test_collect_chat_history_structure_raises_on_none():
    """Test that collect_chat_history raises ValueError for None parameters."""
    # Function now validates parameters and raises ValueError for None
    with pytest.raises(ValueError, match="collect_chat_history: either commit or since_commit must be provided"):
        collect_chat_history()

# Architecture Decision: Terminal Command Collection Removed (2025-06-27)
# Terminal command structure tests removed as functionality no longer supported

def test_collect_chat_history_structure_valid():
    # Use dummy values for since_commit and max_messages_back
    result = collect_chat_history(since_commit='dummy_commit', max_messages_back=10)
    assert isinstance(result, dict)
    assert set(result.keys()) == set(ChatHistory.__annotations__.keys())
    for msg in result['messages']:
        assert set(msg.keys()) == set(ChatMessage.__annotations__.keys())

# Architecture Decision: Terminal Command Collection Removed (2025-06-27)
# Terminal command structure validation tests removed as functionality no longer supported 

# Test bubbleId preservation in message transformation
def test_collect_chat_history_preserves_bubble_id(mock_query_cursor_chat_database, mock_filter_chat_for_commit):
    """Test that collect_chat_history preserves bubbleId from ComposerChatProvider messages."""
    # Mock ComposerChatProvider data with bubbleId
    mock_chat_data = {
        'chat_history': [
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
    }
    
    mock_query_cursor_chat_database.return_value = mock_chat_data
    mock_filter_chat_for_commit.return_value = mock_chat_data['chat_history']
    
    # Mock commit object
    mock_commit = Mock()
    mock_commit.hexsha = 'abc123'
    
    # Call collect_chat_history
    result = collect_chat_history(commit=mock_commit)
    
    # Verify bubbleId is preserved in final ChatMessage format
    assert len(result['messages']) == 2
    
    user_message = result['messages'][0]
    assert user_message['speaker'] == 'Human'
    assert user_message['text'] == 'Test user message'
    assert user_message['bubbleId'] == 'bubble_user_1'  # This should be preserved
    assert user_message['timestamp'] == 1234567890
    assert user_message['composerId'] == 'comp123'
    
    assistant_message = result['messages'][1]
    assert assistant_message['speaker'] == 'Assistant'
    assert assistant_message['text'] == 'Test assistant message'
    assert assistant_message['bubbleId'] == 'bubble_assistant_1'  # This should be preserved
    assert assistant_message['timestamp'] == 1234567891
    assert assistant_message['composerId'] == 'comp123'


def test_collect_chat_history_handles_missing_bubble_id(mock_query_cursor_chat_database, mock_filter_chat_for_commit):
    """Test backward compatibility when bubbleId is missing from ComposerChatProvider messages."""
    # Mock ComposerChatProvider data without bubbleId (backward compatibility)
    mock_chat_data = {
        'chat_history': [
            {
                'role': 'user',
                'content': 'Test user message',
                'timestamp': 1234567890,
                'sessionName': 'test_session',
                'composerId': 'comp123'
                # No bubbleId field
            }
        ]
    }
    
    mock_query_cursor_chat_database.return_value = mock_chat_data
    mock_filter_chat_for_commit.return_value = mock_chat_data['chat_history']
    
    # Mock commit object
    mock_commit = Mock()
    mock_commit.hexsha = 'abc123'
    
    # Call collect_chat_history
    result = collect_chat_history(commit=mock_commit)
    
    # Verify it handles missing bubbleId gracefully
    assert len(result['messages']) == 1
    
    user_message = result['messages'][0]
    assert user_message['speaker'] == 'Human'
    assert user_message['text'] == 'Test user message'
    assert 'bubbleId' not in user_message  # Should not be present when missing from source
    assert user_message['timestamp'] == 1234567890
    assert user_message['composerId'] == 'comp123'


def test_collect_chat_history_preserves_all_metadata_fields(mock_query_cursor_chat_database, mock_filter_chat_for_commit):
    """Test that all metadata fields (timestamp, sessionName, bubbleId) are preserved correctly."""
    # Mock ComposerChatProvider data with all metadata fields
    mock_chat_data = {
        'chat_history': [
            {
                'role': 'user',
                'content': 'Complete metadata test',
                'timestamp': 1234567890,
                'sessionName': 'complete_session',
                'composerId': 'comp123',
                'bubbleId': 'bubble_complete_1'
            }
        ]
    }
    
    mock_query_cursor_chat_database.return_value = mock_chat_data
    mock_filter_chat_for_commit.return_value = mock_chat_data['chat_history']
    
    # Mock commit object
    mock_commit = Mock()
    mock_commit.hexsha = 'abc123'
    
    # Call collect_chat_history
    result = collect_chat_history(commit=mock_commit)
    
    # Verify all metadata fields are preserved
    assert len(result['messages']) == 1
    
    message = result['messages'][0]
    assert message['speaker'] == 'Human'
    assert message['text'] == 'Complete metadata test'
    assert message['timestamp'] == 1234567890
    assert message['composerId'] == 'comp123'
    assert message['bubbleId'] == 'bubble_complete_1'
    
    # Verify all expected fields are present (note: sessionName removed, composerId added)
    expected_fields = {'speaker', 'text', 'timestamp', 'composerId', 'bubbleId'}
    assert set(message.keys()) == expected_fields 

def test_sessionname_not_collected(mock_query_cursor_chat_database, mock_filter_chat_for_commit):
    """Test that sessionName is NOT collected in chat messages."""
    # Mock ComposerChatProvider data with sessionName
    mock_chat_data = {
        'chat_history': [
            {
                'role': 'user',
                'content': 'Hello',
                'timestamp': 1640995200000,
                'sessionName': 'test_session',
                'composerId': 'composer-123',
                'bubbleId': 'bubble-123'
            },
            {
                'role': 'assistant', 
                'content': 'Hi there',
                'timestamp': 1640995300000,
                'sessionName': 'test_session',
                'composerId': 'composer-123',
                'bubbleId': 'bubble-456'
            }
        ]
    }
    
    mock_query_cursor_chat_database.return_value = mock_chat_data
    mock_filter_chat_for_commit.return_value = mock_chat_data['chat_history']
    
    # Mock commit object
    mock_commit = Mock()
    mock_commit.hexsha = 'abc123'
    
    # Call collect_chat_history
    result = collect_chat_history(commit=mock_commit)
    
    user_message = result['messages'][0]
    assistant_message = result['messages'][1]
    
    # sessionName should NOT be present
    assert 'sessionName' not in user_message
    assert 'sessionName' not in assistant_message
    
    # composerId and bubbleId should still be present
    assert user_message['composerId'] == 'composer-123'
    assert user_message['bubbleId'] == 'bubble-123'
    assert assistant_message['composerId'] == 'composer-123'
    assert assistant_message['bubbleId'] == 'bubble-456'


# Tests for file_diffs field integration (Subtask 67.2)

def test_collect_git_context_includes_file_diffs_field(tmp_path):
    """Test that collect_git_context() includes the file_diffs field."""
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    
    # Verify file_diffs field is present
    assert 'file_diffs' in ctx
    assert isinstance(ctx['file_diffs'], dict)


@patch('mcp_commit_story.context_collection.get_commit_file_diffs')
def test_collect_git_context_successful_diff_collection(mock_get_diffs, tmp_path):
    """Test successful diff collection integration."""
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    
    # Mock the diff collection function to return expected data
    expected_diffs = {
        'file.txt': '@@ -0,0 +1 @@\n+hello\n'
    }
    mock_get_diffs.return_value = expected_diffs
    
    ctx = collect_git_context(commit.hexsha, repo=repo)
    
    # Verify get_commit_file_diffs was called with correct parameters
    mock_get_diffs.assert_called_once_with(repo, commit)
    
    # Verify file_diffs field contains the expected data
    assert ctx['file_diffs'] == expected_diffs


@patch('mcp_commit_story.context_collection.get_commit_file_diffs')
def test_collect_git_context_large_repo_performance(mock_get_diffs, tmp_path):
    """Test performance handling with large repos - diffs should still be collected."""
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    
    # Mock large repo scenario
    mock_get_diffs.return_value = {'file.txt': 'diff content'}
    
    ctx = collect_git_context(commit.hexsha, repo=repo)
    
    # Even for large repos, file_diffs should be included
    assert 'file_diffs' in ctx
    assert ctx['file_diffs'] == {'file.txt': 'diff content'}
    mock_get_diffs.assert_called_once()


@patch('mcp_commit_story.context_collection.get_commit_file_diffs')
def test_collect_git_context_handles_diff_errors(mock_get_diffs, tmp_path):
    """Test error handling when diff collection fails."""
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    
    # Mock diff collection failure
    mock_get_diffs.side_effect = Exception("Diff collection failed")
    
    # collect_git_context should handle the error gracefully
    ctx = collect_git_context(commit.hexsha, repo=repo)
    
    # Should still have file_diffs field, but empty due to error
    assert 'file_diffs' in ctx
    assert ctx['file_diffs'] == {}


@patch('mcp_commit_story.context_collection.get_commit_file_diffs')
def test_collect_git_context_empty_diff_collection(mock_get_diffs, tmp_path):
    """Test when diff collection returns empty results."""
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    
    # Mock empty diff collection
    mock_get_diffs.return_value = {}
    
    ctx = collect_git_context(commit.hexsha, repo=repo)
    
    # Should have file_diffs field with empty dict
    assert 'file_diffs' in ctx
    assert ctx['file_diffs'] == {}
    mock_get_diffs.assert_called_once_with(repo, commit) 