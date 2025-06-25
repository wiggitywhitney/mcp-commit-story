"""
Tests for message reconstruction functionality.

This module tests the reconstruct_chat_history function that combines
user prompts and AI generations into a simple message list without
attempting to pair them chronologically.
"""

import pytest
from unittest.mock import patch, MagicMock

# Import will fail initially - this is expected for TDD
try:
    from mcp_commit_story.cursor_db.message_reconstruction import reconstruct_chat_history
except ImportError:
    # Expected during TDD - tests should fail initially
    reconstruct_chat_history = None


class TestReconstructChatHistory:
    """Test the main reconstruct_chat_history function."""
    
    def test_reconstruct_empty_data(self):
        """Test reconstruction with empty prompts and generations."""
        prompts = []
        generations = []
        
        result = reconstruct_chat_history(prompts, generations)
        
        assert result == {
            "messages": [],
            "metadata": {
                "prompt_count": 0,
                "generation_count": 0
            }
        }
    
    def test_reconstruct_only_prompts(self):
        """Test reconstruction with only user prompts, no generations."""
        prompts = [
            {"text": "Hello there", "commandType": 4},
            {"text": "How are you?", "commandType": 4}
        ]
        generations = []
        
        result = reconstruct_chat_history(prompts, generations)
        
        # Verify structure
        assert "messages" in result
        assert "metadata" in result
        
        # Verify metadata
        assert result["metadata"]["prompt_count"] == 2
        assert result["metadata"]["generation_count"] == 0
        
        # Verify messages - should have user messages only
        messages = result["messages"]
        assert len(messages) == 2
        
        # Check first message
        assert messages[0] == {
            "role": "user",
            "content": "Hello there",
            "timestamp": None,
            "type": None
        }
        
        # Check second message
        assert messages[1] == {
            "role": "user", 
            "content": "How are you?",
            "timestamp": None,
            "type": None
        }
    
    def test_reconstruct_only_generations(self):
        """Test reconstruction with only AI generations, no prompts."""
        prompts = []
        generations = [
            {
                "textDescription": "Hello! I'm doing well.",
                "unixMs": 1746792719853,
                "type": "composer",
                "generationUUID": "uuid-1"
            },
            {
                "textDescription": "How can I help you today?",
                "unixMs": 1746792720000,
                "type": "apply", 
                "generationUUID": "uuid-2"
            }
        ]
        
        result = reconstruct_chat_history(prompts, generations)
        
        # Verify metadata
        assert result["metadata"]["prompt_count"] == 0
        assert result["metadata"]["generation_count"] == 2
        
        # Verify messages - should have AI messages only
        messages = result["messages"]
        assert len(messages) == 2
        
        # Check first generation message
        assert messages[0] == {
            "role": "assistant",
            "content": "Hello! I'm doing well.",
            "timestamp": 1746792719853,
            "type": "composer"
        }
        
        # Check second generation message
        assert messages[1] == {
            "role": "assistant",
            "content": "How can I help you today?",
            "timestamp": 1746792720000,
            "type": "apply"
        }
    
    def test_reconstruct_mixed_data(self):
        """Test reconstruction with both prompts and generations."""
        prompts = [
            {"text": "Fix this bug please", "commandType": 4},
            {"text": "What about error handling?", "commandType": 4}
        ]
        generations = [
            {
                "textDescription": "I'll help you fix that bug. The issue is...",
                "unixMs": 1746792719853,
                "type": "composer",
                "generationUUID": "uuid-1"
            }
        ]
        
        result = reconstruct_chat_history(prompts, generations)
        
        # Verify metadata
        assert result["metadata"]["prompt_count"] == 2
        assert result["metadata"]["generation_count"] == 1
        
        # Verify total message count
        messages = result["messages"]
        assert len(messages) == 3  # 2 prompts + 1 generation
        
        # Verify extraction order is preserved (prompts first, then generations)
        # First two should be user messages
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Fix this bug please"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What about error handling?"
        
        # Last should be assistant message
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "I'll help you fix that bug. The issue is..."
        assert messages[2]["timestamp"] == 1746792719853
        assert messages[2]["type"] == "composer"
    
    def test_message_format_user(self):
        """Test user message format adheres to specification."""
        prompts = [{"text": "Test message", "commandType": 4}]
        generations = []
        
        result = reconstruct_chat_history(prompts, generations)
        
        user_message = result["messages"][0]
        
        # Verify all required fields are present
        assert "role" in user_message
        assert "content" in user_message
        assert "timestamp" in user_message
        assert "type" in user_message
        
        # Verify field values for user messages
        assert user_message["role"] == "user"
        assert user_message["content"] == "Test message"
        assert user_message["timestamp"] is None  # No timestamps for prompts
        assert user_message["type"] is None  # No type for prompts
    
    def test_message_format_assistant(self):
        """Test assistant message format adheres to specification."""
        prompts = []
        generations = [{
            "textDescription": "Test response",
            "unixMs": 1234567890,
            "type": "composer",
            "generationUUID": "test-uuid"
        }]
        
        result = reconstruct_chat_history(prompts, generations)
        
        assistant_message = result["messages"][0]
        
        # Verify all required fields are present
        assert "role" in assistant_message
        assert "content" in assistant_message
        assert "timestamp" in assistant_message
        assert "type" in assistant_message
        
        # Verify field values for assistant messages
        assert assistant_message["role"] == "assistant"
        assert assistant_message["content"] == "Test response"
        assert assistant_message["timestamp"] == 1234567890
        assert assistant_message["type"] == "composer"
    
    def test_preserves_extraction_order(self):
        """Test that extraction order is preserved, not sorted by timestamp."""
        prompts = [
            {"text": "First prompt", "commandType": 4},
            {"text": "Second prompt", "commandType": 4}
        ]
        generations = [
            {
                "textDescription": "Later response",
                "unixMs": 2000000000000,  # Later timestamp
                "type": "composer",
                "generationUUID": "uuid-1"
            },
            {
                "textDescription": "Earlier response", 
                "unixMs": 1000000000000,  # Earlier timestamp
                "type": "composer",
                "generationUUID": "uuid-2"
            }
        ]
        
        result = reconstruct_chat_history(prompts, generations)
        
        messages = result["messages"]
        
        # Verify prompts come first in extraction order
        assert messages[0]["content"] == "First prompt"
        assert messages[1]["content"] == "Second prompt"
        
        # Verify generations come after in extraction order (not timestamp order)
        assert messages[2]["content"] == "Later response"
        assert messages[3]["content"] == "Earlier response"
    
    def test_handles_malformed_prompt_data(self):
        """Test graceful handling of malformed prompt data."""
        prompts = [
            {"text": "Valid prompt", "commandType": 4},
            {"missing_text": "Invalid prompt", "commandType": 4},  # Missing 'text' field
            {"text": "Another valid prompt", "commandType": 4}
        ]
        generations = []
        
        result = reconstruct_chat_history(prompts, generations)
        
        # Should process valid prompts, skip malformed ones
        messages = result["messages"]
        assert len(messages) == 2  # Only 2 valid prompts
        
        assert messages[0]["content"] == "Valid prompt"
        assert messages[1]["content"] == "Another valid prompt"
        
        # Metadata should reflect original count (before filtering)
        assert result["metadata"]["prompt_count"] == 3
    
    def test_handles_malformed_generation_data(self):
        """Test graceful handling of malformed generation data."""
        prompts = []
        generations = [
            {
                "textDescription": "Valid response",
                "unixMs": 1746792719853,
                "type": "composer",
                "generationUUID": "uuid-1"
            },
            {
                "missing_description": "Invalid response",  # Missing 'textDescription'
                "unixMs": 1746792720000,
                "type": "composer", 
                "generationUUID": "uuid-2"
            },
            {
                "textDescription": "Another valid response",
                "unixMs": 1746792721000,
                "type": "apply",
                "generationUUID": "uuid-3"
            }
        ]
        
        result = reconstruct_chat_history(prompts, generations)
        
        # Should process valid generations, skip malformed ones
        messages = result["messages"]
        assert len(messages) == 2  # Only 2 valid generations
        
        assert messages[0]["content"] == "Valid response"
        assert messages[1]["content"] == "Another valid response"
        
        # Metadata should reflect original count (before filtering)
        assert result["metadata"]["generation_count"] == 3
    
    def test_truncation_detection_exactly_100(self):
        """Test that we don't add special handling for exactly 100 generations."""
        prompts = [{"text": "Test prompt", "commandType": 4}]
        
        # Generate exactly 100 generations
        generations = []
        for i in range(100):
            generations.append({
                "textDescription": f"Response {i}",
                "unixMs": 1746792719853 + i,
                "type": "composer",
                "generationUUID": f"uuid-{i}"
            })
        
        result = reconstruct_chat_history(prompts, generations)
        
        # Verify we process all messages normally
        assert len(result["messages"]) == 101  # 1 prompt + 100 generations
        assert result["metadata"]["generation_count"] == 100
        
        # Verify no special truncation warnings or flags are added
        assert "truncation_warning" not in result
        assert "truncated" not in result["metadata"]
        
        # The docstring mentions the 100-limit, but no special data handling
    
    def test_content_field_mapping(self):
        """Test correct mapping of content from different source fields."""
        prompts = [{"text": "User message content", "commandType": 4}]
        generations = [{
            "textDescription": "AI message content",
            "unixMs": 1746792719853,
            "type": "composer",
            "generationUUID": "uuid-1"
        }]
        
        result = reconstruct_chat_history(prompts, generations)
        
        messages = result["messages"]
        
        # Verify user content comes from 'text' field
        assert messages[0]["content"] == "User message content"
        
        # Verify AI content comes from 'textDescription' field  
        assert messages[1]["content"] == "AI message content"
    
    def test_no_pairing_logic(self):
        """Test that no attempt is made to pair prompts with generations."""
        # Create prompts and generations that could theoretically be paired
        prompts = [
            {"text": "What is Python?", "commandType": 4},
            {"text": "How do I use loops?", "commandType": 4}
        ]
        generations = [
            {
                "textDescription": "Python is a programming language...",
                "unixMs": 1746792719853,
                "type": "composer", 
                "generationUUID": "uuid-1"
            },
            {
                "textDescription": "Loops in Python can be written...",
                "unixMs": 1746792720000,
                "type": "composer",
                "generationUUID": "uuid-2"
            }
        ]
        
        result = reconstruct_chat_history(prompts, generations)
        
        messages = result["messages"]
        
        # Verify no pairing fields are added
        for message in messages:
            assert "paired_with" not in message
            assert "unpaired" not in message
            assert "parent_id" not in message
            assert "correlation_id" not in message
        
        # Verify extraction order is preserved (all prompts, then all generations)
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "user" 
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "assistant"


class TestFunctionSignature:
    """Test the function signature and docstring requirements."""
    
    def test_function_exists(self):
        """Test that the function can be imported and called."""
        # This test will fail initially during TDD
        assert reconstruct_chat_history is not None
        
        # Should be callable
        assert callable(reconstruct_chat_history)
    
    def test_function_signature(self):
        """Test function accepts correct parameters."""
        # Function should accept prompts and generations parameters
        try:
            # This will fail initially but tests the signature
            result = reconstruct_chat_history([], [])
            assert isinstance(result, dict)
        except TypeError as e:
            # During TDD, check that error suggests correct signature
            error_msg = str(e)
            assert "prompts" not in error_msg or "generations" not in error_msg


@pytest.mark.skipif(reconstruct_chat_history is None, reason="Function not implemented yet")
class TestImplementationRequirements:
    """Tests that verify implementation follows the design requirements."""
    
    def test_returns_dict_with_required_keys(self):
        """Test return value has required top-level keys."""
        result = reconstruct_chat_history([], [])
        
        assert isinstance(result, dict)
        assert "messages" in result
        assert "metadata" in result
        assert isinstance(result["messages"], list)
        assert isinstance(result["metadata"], dict)
    
    def test_metadata_has_required_fields(self):
        """Test metadata contains required count fields."""
        prompts = [{"text": "Test", "commandType": 4}]
        generations = [{
            "textDescription": "Response",
            "unixMs": 1746792719853,
            "type": "composer",
            "generationUUID": "uuid-1"
        }]
        
        result = reconstruct_chat_history(prompts, generations)
        
        metadata = result["metadata"]
        assert "prompt_count" in metadata
        assert "generation_count" in metadata
        assert isinstance(metadata["prompt_count"], int)
        assert isinstance(metadata["generation_count"], int) 