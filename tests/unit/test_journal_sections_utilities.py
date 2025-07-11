"""
Tests for journal sections utilities module.

This module tests the shared utilities for journal section generation,
specifically the format_ai_prompt function that replaces the abstraction layer.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.mcp_commit_story.context_types import JournalContext


class TestFormatAIPrompt:
    """Test format_ai_prompt function for direct AI invocation."""

    def test_format_ai_prompt_with_valid_docstring_and_context(self):
        """Test format_ai_prompt with valid docstring and context."""
        from src.mcp_commit_story.journal_ai_utilities import format_ai_prompt
        
        docstring = "Generate a summary of the changes made."
        context = JournalContext(
            git={
                'metadata': {'hash': 'abc123', 'message': 'Fix bug'},
                'changed_files': ['file1.py'],
                'diff_summary': 'Added error handling'
            },
            chat=None,
            journal=None
        )
        
        result = format_ai_prompt(docstring, context)
        
        # Should contain the docstring
        assert "Generate a summary of the changes made." in result
        
        # Should contain JSON context
        assert "json" in result.lower()
        assert "abc123" in result
        assert "Fix bug" in result
        
        # Should be properly formatted
        assert len(result) > len(docstring)

    def test_format_ai_prompt_with_empty_docstring(self):
        """Test format_ai_prompt with empty docstring."""
        from src.mcp_commit_story.journal_ai_utilities import format_ai_prompt
        
        docstring = ""
        context = JournalContext(
            git={'metadata': {'hash': 'abc123'}},
            chat=None,
            journal=None
        )
        
        result = format_ai_prompt(docstring, context)
        
        # Should still contain context even with empty docstring
        assert "abc123" in result
        assert "json" in result.lower()

    def test_format_ai_prompt_with_none_context(self):
        """Test format_ai_prompt with None context."""
        from src.mcp_commit_story.journal_ai_utilities import format_ai_prompt
        
        docstring = "Generate a summary"
        context = None
        
        result = format_ai_prompt(docstring, context)
        
        # Should contain the docstring
        assert "Generate a summary" in result
        
        # Should handle None context gracefully
        assert "null" in result.lower() or "none" in result.lower()

    def test_format_ai_prompt_json_formatting_correct(self):
        """Test that JSON formatting is correct and readable."""
        from src.mcp_commit_story.journal_ai_utilities import format_ai_prompt
        
        docstring = "Test prompt"
        context = JournalContext(
            git={
                'metadata': {'hash': 'test123', 'message': 'Test commit'},
                'changed_files': ['test.py', 'another.py']
            },
            chat=[{'role': 'user', 'content': 'Hello'}],
            journal={'recent_entries': []}
        )
        
        result = format_ai_prompt(docstring, context)
        
        # Should be valid JSON formatting
        assert "```json" in result.lower() or "json" in result.lower()
        
        # Should contain all context elements
        assert "test123" in result
        assert "Test commit" in result
        assert "test.py" in result
        assert "Hello" in result
        
        # Should be indented for readability
        assert "  " in result or "\t" in result
        
    def test_format_ai_prompt_with_complex_context(self):
        """Test format_ai_prompt with complex nested context."""
        from src.mcp_commit_story.journal_ai_utilities import format_ai_prompt
        
        docstring = "Complex test"
        context = JournalContext(
            git={
                'metadata': {
                    'hash': 'complex123',
                    'author': 'Test Author',
                    'date': '2025-07-11',
                    'message': 'Complex commit message'
                },
                'changed_files': ['src/file1.py', 'tests/test_file.py'],
                'file_stats': {'source': 1, 'tests': 1},
                'diff_summary': 'Added new feature with tests'
            },
            chat=[
                {'role': 'user', 'content': 'I need to add this feature'},
                {'role': 'assistant', 'content': 'Here is how to implement it'}
            ],
            journal={
                'recent_entries': ['Previous entry 1', 'Previous entry 2']
            }
        )
        
        result = format_ai_prompt(docstring, context)
        
        # Should contain all nested elements
        assert "complex123" in result
        assert "Test Author" in result
        assert "Complex commit message" in result
        assert "src/file1.py" in result
        assert "I need to add this feature" in result
        assert "Previous entry 1" in result
        
        # Should be properly structured
        assert result.startswith("Complex test")
        assert "json" in result.lower() 