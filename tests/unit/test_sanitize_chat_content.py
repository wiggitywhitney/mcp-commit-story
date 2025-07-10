"""
Tests for chat content sanitization functionality.

Tests the security feature that scrubs sensitive information from chat content 
before it gets written to journal entries, preventing API keys, tokens, and 
other secrets from being accidentally logged.
"""

import pytest
from mcp_commit_story.context_collection import sanitize_chat_content


class TestSanitizeChatContent:
    """Test cases for sanitize_chat_content() function."""

    def test_sanitizes_api_keys(self):
        """Should sanitize long alphanumeric strings that look like API keys."""
        content = "Here's my API key: sk_1234567890abcdef1234567890abcdef and then some text"
        result = sanitize_chat_content(content)
        
        # Should preserve first 8 chars + *** for readability
        assert "sk_12345***" in result
        assert "sk_1234567890abcdef1234567890abcdef" not in result
        assert "and then some text" in result

    def test_sanitizes_jwt_tokens(self):
        """Should sanitize JSON Web Tokens."""
        content = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = sanitize_chat_content(content)
        
        assert "jwt.***" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_sanitizes_bearer_tokens(self):
        """Should sanitize Bearer tokens in headers."""
        content = "Authorization: Bearer abc123def456ghi789 for the API call"
        result = sanitize_chat_content(content)
        
        assert "Bearer ***" in result
        assert "abc123def456ghi789" not in result
        assert "for the API call" in result

    def test_sanitizes_environment_variables(self):
        """Should sanitize environment variable assignments."""
        content = "export API_KEY=super_secret_key_12345 and DATABASE_PASSWORD=my_db_pass"
        result = sanitize_chat_content(content)
        
        assert "API_KEY=***" in result or "***=***" in result
        assert "super_secret_key_12345" not in result
        assert "my_db_pass" not in result

    def test_sanitizes_connection_strings(self):
        """Should sanitize database connection strings."""
        content = "postgres://user:secret123@localhost:5432/mydb"
        result = sanitize_chat_content(content)
        
        assert "***:***@" in result
        assert "secret123" not in result

    def test_sanitizes_multiple_secrets_in_one_message(self):
        """Should sanitize multiple different types of secrets in one message."""
        content = """
        I'm using API_KEY=abc123def456 and also this JWT token:
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
        Plus my postgres://admin:password123@db.example.com/prod connection
        """
        result = sanitize_chat_content(content)
        
        # Should sanitize all different types
        assert "abc123def456" not in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result  
        assert "password123" not in result
        # But preserve structure
        assert "I'm using" in result
        assert "and also this" in result
        assert "connection" in result

    def test_preserves_normal_conversation_content(self):
        """Should not modify normal conversation content without secrets."""
        content = "I think we should implement the feature this way because it's more maintainable"
        result = sanitize_chat_content(content)
        
        assert result == content  # Should be unchanged

    def test_preserves_code_examples_without_secrets(self):
        """Should preserve code examples that don't contain secrets."""
        content = """
        Here's how to use the function:
        
        def my_function(param):
            return param + "hello world"
            
        This approach works well.
        """
        result = sanitize_chat_content(content)
        
        assert result == content  # Should be unchanged

    def test_handles_empty_and_none_content(self):
        """Should handle edge cases gracefully."""
        assert sanitize_chat_content("") == ""
        assert sanitize_chat_content(None) == ""

    def test_preserves_short_alphanumeric_strings(self):
        """Should not sanitize short strings that aren't likely to be secrets."""
        content = "The commit hash is abc123 and the version is v1.2.3"
        result = sanitize_chat_content(content)
        
        assert result == content  # Short strings should be preserved

    def test_sanitizes_github_tokens(self):
        """Should sanitize GitHub personal access tokens."""
        content = "Use this token: ghp_1234567890abcdefghijklmnopqrstuvwxyz123456"
        result = sanitize_chat_content(content)
        
        assert "ghp_1234***" in result
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz123456" not in result

    def test_preserves_readability_with_context(self):
        """Should maintain readability by preserving context around sanitized content."""
        content = "Set API_KEY=secret123 in your .env file before running the tests"
        result = sanitize_chat_content(content)
        
        # Should preserve the instruction context
        assert "Set" in result
        assert "in your .env file" in result  
        assert "before running the tests" in result
        # But sanitize the secret
        assert "secret123" not in result 