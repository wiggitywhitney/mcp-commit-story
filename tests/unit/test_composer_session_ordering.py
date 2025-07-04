"""
Tests for multi-session message ordering determinism.

Tests that messages from different sessions with identical timestamps
have consistent, deterministic ordering across multiple runs.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp_commit_story.composer_chat_provider import ComposerChatProvider


class TestComposerSessionOrdering:
    """Test deterministic ordering of messages across multiple sessions."""

    @pytest.fixture
    def provider(self):
        """Create ComposerChatProvider instance."""
        return ComposerChatProvider("/workspace/test.vscdb", "/global/test.vscdb")

    @pytest.fixture
    def identical_timestamp_sessions(self):
        """Mock data with two sessions having identical timestamps."""
        # Same timestamp for both sessions (the bug condition)
        identical_timestamp = 1747412764075
        
        return [
            {
                'composerId': 'session-aaa-111',
                'name': 'Session A',
                'createdAt': identical_timestamp,
                'lastUpdatedAt': identical_timestamp
            },
            {
                'composerId': 'session-bbb-222', 
                'name': 'Session B',
                'createdAt': identical_timestamp,
                'lastUpdatedAt': identical_timestamp
            }
        ]

    @pytest.fixture
    def mock_session_messages(self):
        """Mock messages for each session."""
        return {
            'session-aaa-111': [
                {
                    'role': 'user',
                    'content': 'Session A User Message',
                    'timestamp': 1747412764075,
                    'sessionName': 'Session A',
                    'composerId': 'session-aaa-111',
                    'bubbleId': 'bubble-a1'
                },
                {
                    'role': 'assistant',
                    'content': 'Session A AI Response',
                    'timestamp': 1747412764075,
                    'sessionName': 'Session A',
                    'composerId': 'session-aaa-111',
                    'bubbleId': 'bubble-a2'
                }
            ],
            'session-bbb-222': [
                {
                    'role': 'user',
                    'content': 'Session B User Message',
                    'timestamp': 1747412764075,
                    'sessionName': 'Session B',
                    'composerId': 'session-bbb-222',
                    'bubbleId': 'bubble-b1'
                },
                {
                    'role': 'assistant',
                    'content': 'Session B AI Response',
                    'timestamp': 1747412764075,
                    'sessionName': 'Session B',
                    'composerId': 'session-bbb-222',
                    'bubbleId': 'bubble-b2'
                }
            ]
        }

    def test_identical_timestamp_sessions_have_consistent_ordering(self, provider, identical_timestamp_sessions, mock_session_messages):
        """Test that sessions with identical timestamps have consistent ordering across runs."""
        
        with patch.object(provider, '_get_session_metadata') as mock_get_sessions, \
             patch.object(provider, '_get_message_headers') as mock_get_headers, \
             patch.object(provider, '_get_session_messages') as mock_get_messages:
            
            # Setup mocks
            mock_get_sessions.return_value = identical_timestamp_sessions
            mock_get_headers.return_value = {'fullConversationHeadersOnly': []}
            
            def mock_session_messages_side_effect(composer_id, session_name, headers, timestamp):
                return mock_session_messages[composer_id]
            
            mock_get_messages.side_effect = mock_session_messages_side_effect
            
            # Run the same query multiple times
            results = []
            for i in range(5):  # Run 5 times to check consistency
                result = provider.getChatHistoryForCommit(
                    start_timestamp_ms=1747412764000,
                    end_timestamp_ms=1747412764999
                )
                
                # Extract just the session order
                session_order = [msg['composerId'] for msg in result]
                results.append(session_order)
            
            # All runs should produce the same order
            first_result = results[0]
            for i, result in enumerate(results[1:], 1):
                assert result == first_result, f"Run {i+1} produced different order: {result} vs {first_result}"

    def test_current_implementation_is_non_deterministic(self, provider, identical_timestamp_sessions, mock_session_messages):
        """Test that current implementation produces non-deterministic results (should fail initially)."""
        
        with patch.object(provider, '_get_session_metadata') as mock_get_sessions, \
             patch.object(provider, '_get_message_headers') as mock_get_headers, \
             patch.object(provider, '_get_session_messages') as mock_get_messages:
            
            # Setup mocks
            mock_get_sessions.return_value = identical_timestamp_sessions
            mock_get_headers.return_value = {'fullConversationHeadersOnly': []}
            
            def mock_session_messages_side_effect(composer_id, session_name, headers, timestamp):
                return mock_session_messages[composer_id]
            
            mock_get_messages.side_effect = mock_session_messages_side_effect
            
            # Run multiple times and check if we get different orderings
            seen_orders = set()
            for i in range(10):  # Run 10 times
                result = provider.getChatHistoryForCommit(
                    start_timestamp_ms=1747412764000,
                    end_timestamp_ms=1747412764999
                )
                
                # Extract composer IDs to see session order
                session_order = tuple(msg['composerId'] for msg in result)
                seen_orders.add(session_order)
            
            # With current buggy implementation, we should see multiple different orders
            # This test should FAIL initially (proving the bug exists)
            assert len(seen_orders) == 1, f"Non-deterministic ordering detected: {seen_orders}"

    def test_within_session_order_preserved(self, provider, identical_timestamp_sessions, mock_session_messages):
        """Test that within-session message order is preserved (should pass)."""
        
        with patch.object(provider, '_get_session_metadata') as mock_get_sessions, \
             patch.object(provider, '_get_message_headers') as mock_get_headers, \
             patch.object(provider, '_get_session_messages') as mock_get_messages:
            
            # Setup mocks  
            mock_get_sessions.return_value = identical_timestamp_sessions
            mock_get_headers.return_value = {'fullConversationHeadersOnly': []}
            
            def mock_session_messages_side_effect(composer_id, session_name, headers, timestamp):
                return mock_session_messages[composer_id]
            
            mock_get_messages.side_effect = mock_session_messages_side_effect
            
            result = provider.getChatHistoryForCommit(
                start_timestamp_ms=1747412764000,
                end_timestamp_ms=1747412764999
            )
            
            # Group messages by session
            session_a_messages = [msg for msg in result if msg['composerId'] == 'session-aaa-111']
            session_b_messages = [msg for msg in result if msg['composerId'] == 'session-bbb-222']
            
            # Check that within each session, user message comes before AI response
            assert len(session_a_messages) == 2
            assert session_a_messages[0]['role'] == 'user'
            assert session_a_messages[1]['role'] == 'assistant'
            
            assert len(session_b_messages) == 2
            assert session_b_messages[0]['role'] == 'user'
            assert session_b_messages[1]['role'] == 'assistant'

    def test_deterministic_ordering_with_composer_id_tiebreaker(self, provider, identical_timestamp_sessions, mock_session_messages):
        """Test that adding composerId as secondary sort key makes ordering deterministic."""
        
        with patch.object(provider, '_get_session_metadata') as mock_get_sessions, \
             patch.object(provider, '_get_message_headers') as mock_get_headers, \
             patch.object(provider, '_get_session_messages') as mock_get_messages:
            
            # Setup mocks
            mock_get_sessions.return_value = identical_timestamp_sessions
            mock_get_headers.return_value = {'fullConversationHeadersOnly': []}
            
            def mock_session_messages_side_effect(composer_id, session_name, headers, timestamp):
                return mock_session_messages[composer_id]
            
            mock_get_messages.side_effect = mock_session_messages_side_effect
            
            result = provider.getChatHistoryForCommit(
                start_timestamp_ms=1747412764000,
                end_timestamp_ms=1747412764999
            )
            
            # With composerId as tiebreaker, session-aaa-111 should come before session-bbb-222
            # (lexicographically: 'session-aaa-111' < 'session-bbb-222')
            session_order = [msg['composerId'] for msg in result]
            
            # Expected order: all session-aaa-111 messages first, then all session-bbb-222 messages
            expected_order = ['session-aaa-111', 'session-aaa-111', 'session-bbb-222', 'session-bbb-222']
            
            assert session_order == expected_order, f"Expected {expected_order}, got {session_order}" 