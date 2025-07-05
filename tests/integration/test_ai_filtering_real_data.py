"""
Integration test for AI filtering with real OpenAI API calls.

This test verifies that the OpenAI API key is properly configured and that
basic AI filtering functionality works with real API calls. It should be run
manually after confirming API key setup.
"""
import pytest
import os
from unittest.mock import Mock
from mcp_commit_story.ai_invocation import invoke_ai
from mcp_commit_story.ai_context_filter import filter_chat_for_commit


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="OpenAI API key not configured")
def test_openai_api_key_setup():
    """Test that OpenAI API key is properly configured and accessible."""
    # Simple AI call to verify API key works
    try:
        # First, let's test direct provider call to get more specific error info
        from mcp_commit_story.ai_provider import OpenAIProvider
        
        provider = OpenAIProvider()
        direct_result = provider.call("Say 'API test successful'", {})
        
        # If direct call works, test through invoke_ai
        result = invoke_ai("Say 'API test successful'", {})
        
        print(f"Direct provider result: '{direct_result}'")
        print(f"invoke_ai result: '{result}'")
        
        # Test with direct result first
        if direct_result:
            assert isinstance(direct_result, str)
            assert len(direct_result) > 0
            print(f"✅ Direct OpenAI API test successful: {direct_result}")
        else:
            pytest.fail("Direct OpenAI provider call returned empty string")
            
        # Then test invoke_ai if it should work
        if result:
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ invoke_ai test successful: {result}")
        else:
            pytest.fail("invoke_ai returned empty string - check logs for error details")
            
    except Exception as e:
        pytest.fail(f"OpenAI API setup failed: {e}")
        
    # If we get here, at least one approach worked
    assert True


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="OpenAI API key not configured")
def test_ai_filtering_real_api_call():
    """Test AI filtering with a real API call using simple test data."""
    # Create simple test messages that should have a clear boundary
    test_messages = [
        {'bubbleId': 'msg_1', 'role': 'user', 'content': 'Working on bug fixes'},
        {'bubbleId': 'msg_2', 'role': 'assistant', 'content': 'Bug is fixed'},
        {'bubbleId': 'msg_3', 'role': 'user', 'content': 'Now starting feature X implementation'},
        {'bubbleId': 'msg_4', 'role': 'assistant', 'content': 'Implementing feature X'},
    ]
    
    # Mock commit and git context
    mock_commit = Mock()
    mock_commit.hexsha = "abc123"
    mock_commit.message = "Implement feature X"
    
    git_context = {
        'metadata': {
            'hash': 'abc123',
            'message': 'Implement feature X',
            'author': 'test@example.com',
            'date': '2025-01-01T00:00:00'
        },
        'changed_files': ['feature_x.py'],
        'diff_summary': 'Added feature X implementation'
    }
    
    try:
        # This will make a real AI API call
        result = filter_chat_for_commit(test_messages, mock_commit, git_context)
        
        # Verify we got a reasonable result
        assert isinstance(result, list)
        assert len(result) <= len(test_messages)  # Should not add messages
        assert len(result) > 0  # Should not remove everything
        
        # Verify all returned messages have bubbleId
        for msg in result:
            assert 'bubbleId' in msg
            
        print(f"✅ AI filtering test successful: {len(test_messages)} → {len(result)} messages")
        
    except Exception as e:
        pytest.fail(f"AI filtering with real API failed: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_ai_filtering_quality_manual_verification():
    """
    Manual test for verifying AI filtering quality with realistic conversation data.
    
    This test should be run manually with a human reviewing the output quality.
    It demonstrates the filtering working with more realistic conversation patterns.
    """
    # More realistic conversation with clear work transition
    realistic_messages = [
        {'bubbleId': 'msg_1', 'role': 'user', 'content': 'I need to fix the authentication bug'},
        {'bubbleId': 'msg_2', 'role': 'assistant', 'content': 'I can help with that. What specific authentication issue are you seeing?'},
        {'bubbleId': 'msg_3', 'role': 'user', 'content': 'Users cant login, getting 500 error'},
        {'bubbleId': 'msg_4', 'role': 'assistant', 'content': 'That sounds like a server-side issue. Let me help you debug it.'},
        {'bubbleId': 'msg_5', 'role': 'user', 'content': 'Found it - missing environment variable. Fixed now.'},
        {'bubbleId': 'msg_6', 'role': 'assistant', 'content': 'Great! Make sure to commit that fix.'},
        {'bubbleId': 'msg_7', 'role': 'user', 'content': 'Done. Now I want to add user profile caching'},
        {'bubbleId': 'msg_8', 'role': 'assistant', 'content': 'Good idea. Profile caching will improve performance. Where do you want to implement it?'},
        {'bubbleId': 'msg_9', 'role': 'user', 'content': 'In the user service. Let me add Redis caching'},
        {'bubbleId': 'msg_10', 'role': 'assistant', 'content': 'Perfect. Here is how you can implement Redis caching for user profiles...'},
    ]
    
    mock_commit = Mock()
    mock_commit.hexsha = "def456"
    mock_commit.message = "Add user profile caching with Redis"
    
    git_context = {
        'metadata': {
            'hash': 'def456', 
            'message': 'Add user profile caching with Redis',
            'author': 'developer@company.com',
            'date': '2025-01-01T12:00:00'
        },
        'changed_files': ['user_service.py', 'cache_config.py'],
        'diff_summary': 'Added Redis caching for user profiles'
    }
    
    # Skip if no API key
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OpenAI API key not configured")
    
    print("\n" + "="*50)
    print("MANUAL VERIFICATION TEST")
    print("="*50)
    print(f"Original conversation: {len(realistic_messages)} messages")
    print("Expected boundary: Around message 7 (transition to caching work)")
    print("Expected result: Messages 7-10 (4 messages about caching)")
    
    try:
        result = filter_chat_for_commit(realistic_messages, mock_commit, git_context)
        print(f"\nAI filtering result: {len(result)} messages")
        print("\nFiltered messages:")
        for i, msg in enumerate(result):
            print(f"  {i+1}. [{msg['bubbleId']}] {msg['role']}: {msg['content']}")
            
        print(f"\n✅ Test completed. Please manually verify the filtering quality.")
        print("Expected: Messages should be about user profile caching work only")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise 