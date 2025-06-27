"""
Unit tests for message limiting functionality.

Tests the limit_chat_messages function with separate human/AI limits based on 
research findings showing that 200/200 limits are appropriate for solo developers.
"""

import pytest
from typing import Dict, List, Any
from unittest.mock import patch

# Import the function we're testing (this will fail initially - that's expected in TDD)
from mcp_commit_story.cursor_db.message_limiting import limit_chat_messages


class TestMessageLimitingBasicFunctionality:
    """Test basic message limiting functionality."""
    
    def test_limit_chat_messages_signature(self):
        """Test that function has correct signature."""
        # This will initially fail until we implement the function
        result = limit_chat_messages({}, max_human_messages=200, max_ai_messages=200)
        assert isinstance(result, dict)
    
    def test_both_under_limits(self):
        """Test scenario where both human and AI messages are under limits."""
        chat_history = {
            'messages': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'},
                {'role': 'user', 'content': 'How are you?'},
                {'role': 'assistant', 'content': 'I am doing well, thank you!'}
            ],
            'metadata': {'database_path': '/test/path'}
        }
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should return all messages unchanged
        assert len(result['messages']) == 4
        assert result['messages'] == chat_history['messages']
        
        # Should preserve existing metadata
        assert 'database_path' in result['metadata']
        
        # Should add truncation metadata
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
        assert result['metadata']['removed_human_count'] == 0
        assert result['metadata']['removed_ai_count'] == 0
    
    def test_human_over_ai_under(self):
        """Test scenario where human messages exceed limit but AI messages don't."""
        messages = []
        # Create 15 human messages and 5 AI messages
        for i in range(15):
            messages.append({'role': 'user', 'content': f'Human message {i}'})
            if i < 5:
                messages.append({'role': 'assistant', 'content': f'AI response {i}'})
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should keep most recent 10 human messages and all 5 AI messages
        human_messages = [m for m in result['messages'] if m['role'] == 'user']
        ai_messages = [m for m in result['messages'] if m['role'] == 'assistant']
        
        assert len(human_messages) == 10
        assert len(ai_messages) == 5
        
        # Should keep chronological order
        assert result['messages'][0]['role'] in ['user', 'assistant']
        
        # Should indicate truncation occurred
        assert result['metadata']['truncated_human'] is True
        assert result['metadata']['truncated_ai'] is False
        assert result['metadata']['removed_human_count'] == 5
        assert result['metadata']['removed_ai_count'] == 0
    
    def test_both_over_limits(self):
        """Test scenario where both message types exceed their limits."""
        messages = []
        # Create 20 human messages and 20 AI messages alternating
        for i in range(20):
            messages.append({'role': 'user', 'content': f'Human message {i}'})
            messages.append({'role': 'assistant', 'content': f'AI response {i}'})
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should keep most recent 10 of each type
        human_messages = [m for m in result['messages'] if m['role'] == 'user']
        ai_messages = [m for m in result['messages'] if m['role'] == 'assistant']
        
        assert len(human_messages) == 10
        assert len(ai_messages) == 10
        
        # Should indicate both types were truncated
        assert result['metadata']['truncated_human'] is True
        assert result['metadata']['truncated_ai'] is True
        assert result['metadata']['removed_human_count'] == 10
        assert result['metadata']['removed_ai_count'] == 10


class TestMessageLimitingBoundaryConditions:
    """Test boundary conditions and edge cases."""
    
    def test_exact_limit_boundaries(self):
        """Test when message counts exactly equal the limits."""
        messages = []
        # Create exactly 10 human and 10 AI messages
        for i in range(10):
            messages.append({'role': 'user', 'content': f'Human {i}'})
            messages.append({'role': 'assistant', 'content': f'AI {i}'})
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should keep all messages (no truncation)
        assert len(result['messages']) == 20
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
        assert result['metadata']['removed_human_count'] == 0
        assert result['metadata']['removed_ai_count'] == 0
    
    def test_empty_chat_history(self):
        """Test handling of empty chat history."""
        chat_history = {'messages': [], 'metadata': {}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        assert len(result['messages']) == 0
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
        assert result['metadata']['removed_human_count'] == 0
        assert result['metadata']['removed_ai_count'] == 0
    
    def test_missing_messages_key(self):
        """Test handling when 'messages' key is missing."""
        chat_history = {'metadata': {'database_path': '/test'}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should handle gracefully and return empty messages
        assert 'messages' in result
        assert len(result['messages']) == 0
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
    
    def test_missing_metadata_key(self):
        """Test handling when 'metadata' key is missing."""
        chat_history = {
            'messages': [
                {'role': 'user', 'content': 'Test'},
                {'role': 'assistant', 'content': 'Response'}
            ]
        }
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should create metadata section
        assert 'metadata' in result
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
    
    def test_zero_limits(self):
        """Test behavior with zero limits."""
        chat_history = {
            'messages': [
                {'role': 'user', 'content': 'Test'},
                {'role': 'assistant', 'content': 'Response'}
            ],
            'metadata': {}
        }
        
        result = limit_chat_messages(chat_history, max_human_messages=0, max_ai_messages=0)
        
        # Should remove all messages
        assert len(result['messages']) == 0
        assert result['metadata']['truncated_human'] is True
        assert result['metadata']['truncated_ai'] is True
        assert result['metadata']['removed_human_count'] == 1
        assert result['metadata']['removed_ai_count'] == 1


class TestMessageLimitingPreservation:
    """Test preservation of existing metadata and message structure."""
    
    def test_preserve_existing_metadata(self):
        """Test that existing metadata is preserved during truncation."""
        chat_history = {
            'messages': [
                {'role': 'user', 'content': 'Test'},
                {'role': 'assistant', 'content': 'Response'}
            ],
            'metadata': {
                'database_path': '/test/path',
                'original_count': 100,
                'workspace_info': {'name': 'test-workspace'}
            }
        }
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should preserve all existing metadata
        assert result['metadata']['database_path'] == '/test/path'
        assert result['metadata']['original_count'] == 100
        assert result['metadata']['workspace_info']['name'] == 'test-workspace'
        
        # Should add truncation metadata
        assert 'truncated_human' in result['metadata']
        assert 'truncated_ai' in result['metadata']
    
    def test_chronological_order_maintained(self):
        """Test that chronological order is maintained after truncation."""
        # Create messages with timestamps to verify order
        messages = []
        for i in range(20):
            messages.append({
                'role': 'user', 
                'content': f'Message {i}',
                'timestamp': f'2024-01-01T{i:02d}:00:00Z'
            })
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should keep the last 10 messages (most recent)
        assert len(result['messages']) == 10
        
        # Should maintain chronological order
        for i, message in enumerate(result['messages']):
            expected_content = f'Message {i + 10}'  # Last 10 messages (10-19)
            assert message['content'] == expected_content
    
    def test_message_structure_preservation(self):
        """Test that message structure and fields are preserved."""
        messages = [
            {
                'role': 'user',
                'content': 'Test message',
                'timestamp': '2024-01-01T10:00:00Z',
                'metadata': {'source': 'test'},
                'id': 'msg-123'
            }
        ]
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should preserve all message fields
        msg = result['messages'][0]
        assert msg['role'] == 'user'
        assert msg['content'] == 'Test message'
        assert msg['timestamp'] == '2024-01-01T10:00:00Z'
        assert msg['metadata']['source'] == 'test'
        assert msg['id'] == 'msg-123'


class TestMessageLimitingPerformance:
    """Test performance with large message sets."""
    
    def test_performance_with_large_message_set(self):
        """Test performance with 1000+ messages."""
        # Create 1000 messages (500 human, 500 AI)
        messages = []
        for i in range(500):
            messages.append({'role': 'user', 'content': f'Human message {i}' * 50})  # Longer content
            messages.append({'role': 'assistant', 'content': f'AI response {i}' * 50})
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        # Should complete quickly even with large input
        import time
        start_time = time.time()
        
        result = limit_chat_messages(chat_history, max_human_messages=200, max_ai_messages=200)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (under 1 second)
        assert duration < 1.0
        
        # Should correctly limit messages
        human_count = len([m for m in result['messages'] if m['role'] == 'user'])
        ai_count = len([m for m in result['messages'] if m['role'] == 'assistant'])
        
        assert human_count == 200
        assert ai_count == 200
        assert result['metadata']['removed_human_count'] == 300
        assert result['metadata']['removed_ai_count'] == 300


class TestMessageLimitingDefaults:
    """Test the default values established by research."""
    
    def test_research_validated_defaults(self):
        """Test that the function works with research-validated default values."""
        # Create a session that exceeds our research findings but is under defaults
        messages = []
        # Research showed max 50 per type, so test with 100 per type
        for i in range(100):
            messages.append({'role': 'user', 'content': f'Message {i}'})
            messages.append({'role': 'assistant', 'content': f'Response {i}'})
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        # Use research-validated defaults
        result = limit_chat_messages(chat_history, max_human_messages=200, max_ai_messages=200)
        
        # Should not truncate (under limits)
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
        assert len([m for m in result['messages'] if m['role'] == 'user']) == 100
        assert len([m for m in result['messages'] if m['role'] == 'assistant']) == 100
    
    def test_extreme_edge_case_protection(self):
        """Test protection against extreme edge cases that defaults are designed for."""
        # Create an extreme case (like automation gone wrong)
        messages = []
        for i in range(1000):  # Much larger than any real usage
            messages.append({'role': 'user', 'content': f'Auto message {i}'})
            messages.append({'role': 'assistant', 'content': f'Auto response {i}'})
        
        chat_history = {'messages': messages, 'metadata': {}}
        
        # Use research-validated defaults
        result = limit_chat_messages(chat_history, max_human_messages=200, max_ai_messages=200)
        
        # Should truncate to protect against excessive context
        assert result['metadata']['truncated_human'] is True
        assert result['metadata']['truncated_ai'] is True
        assert len([m for m in result['messages'] if m['role'] == 'user']) == 200
        assert len([m for m in result['messages'] if m['role'] == 'assistant']) == 200
        assert result['metadata']['removed_human_count'] == 800
        assert result['metadata']['removed_ai_count'] == 800


class TestMessageLimitingRoleHandling:
    """Test handling of message roles and unexpected values."""
    
    def test_unexpected_role_values(self):
        """Test handling of messages with unexpected role values."""
        chat_history = {
            'messages': [
                {'role': 'user', 'content': 'Normal user'},
                {'role': 'assistant', 'content': 'Normal assistant'},
                {'role': 'system', 'content': 'System message'},
                {'role': 'unknown', 'content': 'Unknown role'},
                {'content': 'No role field'}  # Missing role
            ],
            'metadata': {}
        }
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should handle gracefully and preserve all messages since limits aren't exceeded
        assert len(result['messages']) == 5
        
        # Should only count user/assistant messages in truncation logic
        assert result['metadata']['truncated_human'] is False
        assert result['metadata']['truncated_ai'] is False
    
    def test_missing_role_field(self):
        """Test handling of messages missing the role field."""
        chat_history = {
            'messages': [
                {'content': 'Message without role'},
                {'role': 'user', 'content': 'User message'},
                {'text': 'Different content field'}  # No 'content' field
            ],
            'metadata': {}
        }
        
        result = limit_chat_messages(chat_history, max_human_messages=10, max_ai_messages=10)
        
        # Should handle gracefully and not crash
        assert 'messages' in result
        assert 'metadata' in result


if __name__ == "__main__":
    pytest.main() 