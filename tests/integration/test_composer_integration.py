"""Integration tests for Composer chat system - full workflow validation."""

import os
import time
import pytest
from pathlib import Path

from mcp_commit_story.composer_chat_provider import ComposerChatProvider


class TestComposerWorkflowIntegration:
    """Integration tests for complete Composer chat workflow."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    def test_complete_chat_history_retrieval_workflow(self, test_db_paths):
        """Test the complete workflow from commit to chat history retrieval."""
        
        # Use ComposerChatProvider directly with wide time window
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        
        # Test with wide time window to capture all test messages
        start_time = 0  # Unix epoch
        end_time = 9999999999999  # Far future
        
        messages = provider.getChatHistoryForCommit(start_time, end_time)
        
        # Verify complete workflow results
        assert messages is not None
        assert isinstance(messages, list)
        assert len(messages) == 15  # Total messages across all 3 sessions
        
        # Verify messages are sorted chronologically
        for i in range(1, len(messages)):
            assert messages[i]['timestamp'] >= messages[i-1]['timestamp']
        
        # Verify message structure and content
        for message in messages:
            assert isinstance(message, dict)
            required_fields = ['role', 'content', 'timestamp', 'sessionName', 'composerId', 'bubbleId']
            for field in required_fields:
                assert field in message
            
            assert message['role'] in ['user', 'assistant']
            assert isinstance(message['content'], str)
            assert len(message['content']) > 0
            assert isinstance(message['timestamp'], int)
    
    def test_session_name_extraction(self, test_db_paths):
        """Test that session names are correctly extracted and attached to messages."""
        
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        messages = provider.getChatHistoryForCommit(0, 9999999999999)
        
        # Verify expected session names from test data
        expected_sessions = {
            "Implement error handling tests",
            "Review integration patterns", 
            "Performance optimization discussion"
        }
        
        found_sessions = set(message['sessionName'] for message in messages)
        assert found_sessions == expected_sessions
    
    def test_chronological_message_ordering(self, test_db_paths):
        """Test that messages are returned in chronological order across sessions."""
        
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        messages = provider.getChatHistoryForCommit(0, 9999999999999)
        
        # Verify chronological ordering
        timestamps = [msg['timestamp'] for msg in messages]
        assert timestamps == sorted(timestamps), "Messages should be in chronological order"
        
        # In realistic Cursor data, messages within the same session share the session's createdAt timestamp
        # But different sessions should have different timestamps
        unique_timestamps = set(timestamps)
        
        # We have 3 sessions, so should have exactly 3 unique timestamps
        assert len(unique_timestamps) == 3, f"Expected 3 unique session timestamps, got {len(unique_timestamps)}"
        
        # Verify session grouping: messages from same session have same timestamp
        session_timestamps = {}
        for msg in messages:
            session_id = msg['composerId']
            if session_id not in session_timestamps:
                session_timestamps[session_id] = msg['timestamp']
            else:
                assert session_timestamps[session_id] == msg['timestamp'], \
                    f"All messages in session {session_id} should have same timestamp"


class TestComposerPerformanceIntegration:
    """Integration tests for performance validation."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    def test_full_workflow_performance_threshold(self, test_db_paths):
        """Test that full workflow completes within 500ms threshold."""
        
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        
        start_time = time.time()
        messages = provider.getChatHistoryForCommit(0, 9999999999999)
        duration = time.time() - start_time
        
        # Verify performance threshold
        assert duration < 0.5, f"Full workflow took {duration:.3f}s, should be < 500ms"
        
        # Verify we got the expected results
        assert len(messages) == 15
    
    def test_database_connection_performance(self, test_db_paths):
        """Test database connection performance meets 50ms threshold."""
        
        from mcp_commit_story.cursor_db.query_executor import execute_cursor_query
        
        start_time = time.time()
        result = execute_cursor_query(test_db_paths["workspace"], "SELECT COUNT(*) FROM ItemTable")
        duration = time.time() - start_time
        
        # Verify database connection threshold
        assert duration < 0.05, f"Database connection took {duration:.3f}s, should be < 50ms"
        
        # Verify query worked
        assert result is not None
        assert len(result) == 1
