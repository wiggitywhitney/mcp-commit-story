"""
Tests for AI function executor (docstring-based execution).

Tests follow the approved design decisions:
- JSON context injection format
- Minimal parsing strategy
- Empty default values matching existing stubs
"""

import pytest
import json
import inspect
from unittest.mock import Mock, patch, MagicMock

from src.mcp_commit_story.context_types import (
    JournalContext, 
    SummarySection, 
    AccomplishmentsSection, 
    ToneMoodSection,
    TechnicalSynopsisSection,
    FrustrationsSection,
    DiscussionNotesSection,
    CommitMetadataSection
)


class TestAIFunctionExecutor:
    """Test the AI function executor with approved design decisions."""

    @pytest.fixture
    def sample_journal_context(self):
        """Create a sample JournalContext for testing."""
        return JournalContext(
            git={
                'metadata': {
                    'hash': 'abc123',
                    'author': 'Test User',
                    'date': '2025-06-27',
                    'message': 'Test commit message'
                },
                'diff_summary': 'Added test files',
                'changed_files': ['test.py', 'README.md'],
                'file_stats': {'additions': 10, 'deletions': 2},
                'commit_context': {}
            },
            chat={
                'messages': [
                    {'speaker': 'user', 'text': 'Let me fix this bug'},
                    {'speaker': 'assistant', 'text': 'Here is the solution'}
                ]
            }
        )

    @pytest.fixture
    def mock_function_with_docstring(self):
        """Create a mock function with a docstring for testing."""
        def sample_function(journal_context):
            """
            This is a test docstring for AI execution.
            
            Generate a summary based on the journal context provided.
            Focus on what changed and why.
            """
            pass
        return sample_function

    def test_docstring_extraction_from_function(self, mock_function_with_docstring):
        """Test that docstring is properly extracted from function."""
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        # The function should be able to extract the docstring using inspect.getdoc
        docstring = inspect.getdoc(mock_function_with_docstring)
        
        # Verify the docstring contains the expected content
        assert "This is a test docstring for AI execution" in docstring
        assert "Generate a summary based on the journal context provided" in docstring
        assert "Focus on what changed and why" in docstring
        
        # Verify it's properly formatted (no extra indentation)
        assert docstring.startswith("This is a test docstring for AI execution")
        assert not docstring.startswith("    ")  # No leading indentation

    def test_context_formatting_into_json_prompt(self, sample_journal_context, mock_function_with_docstring):
        """Test that context is properly formatted as JSON and combined with docstring."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        # Mock the invoke_ai function to capture the prompt
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            mock_invoke.return_value = "Test response"
            
            execute_ai_function(mock_function_with_docstring, sample_journal_context)
            
            # Verify the prompt structure
            called_prompt = mock_invoke.call_args[0][0]
            
            # Should contain the docstring
            assert "This is a test docstring for AI execution" in called_prompt
            
            # Should contain JSON context
            assert "```json" in called_prompt
            assert '"hash": "abc123"' in called_prompt
            assert '"message": "Test commit message"' in called_prompt

    @patch('src.mcp_commit_story.ai_function_executor.invoke_ai')
    def test_successful_execution_with_mock_ai(self, mock_invoke, sample_journal_context, mock_function_with_docstring):
        """Test successful AI execution with mocked response."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        mock_invoke.return_value = "Successfully completed the task by fixing the bug."
        
        result = execute_ai_function(mock_function_with_docstring, sample_journal_context)
        
        # Should call invoke_ai once
        assert mock_invoke.call_count == 1
        
        # Should return some result (exact parsing depends on function name)
        assert result is not None

    def test_parsing_for_summary_section_return_type(self, sample_journal_context):
        """Test parsing for SummarySection return type using minimal strategy."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        def generate_summary_section(journal_context):
            """Generate a summary section."""
            pass
            
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            mock_invoke.return_value = "This is a complete summary of the changes made."
            
            result = execute_ai_function(generate_summary_section, sample_journal_context)
            
            # Should return SummarySection with the AI response
            assert isinstance(result, dict)  # SummarySection is a TypedDict
            assert 'summary' in result
            assert result['summary'] == "This is a complete summary of the changes made."

    def test_parsing_for_accomplishments_section_list_type(self, sample_journal_context):
        """Test parsing for AccomplishmentsSection (list) using minimal strategy."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        def generate_accomplishments_section(journal_context):
            """Generate accomplishments list."""
            pass
            
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            # Mock AI response with newline-separated items
            mock_invoke.return_value = """Fixed critical bug in authentication
Added comprehensive test coverage
Improved documentation quality"""
            
            result = execute_ai_function(generate_accomplishments_section, sample_journal_context)
            
            # Should return AccomplishmentsSection with parsed list
            assert isinstance(result, dict)  # AccomplishmentsSection is a TypedDict
            assert 'accomplishments' in result
            assert len(result['accomplishments']) == 3
            assert "Fixed critical bug in authentication" in result['accomplishments']
            assert "Added comprehensive test coverage" in result['accomplishments']
            assert "Improved documentation quality" in result['accomplishments']

    def test_parsing_for_tone_mood_section_multiple_fields(self, sample_journal_context):
        """Test parsing for ToneMoodSection (multiple fields) using minimal strategy."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        def generate_tone_mood_section(journal_context):
            """Generate tone and mood analysis."""
            pass
            
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            # Mock AI response with mood and indicators
            mock_invoke.return_value = """Mood: Focused and determined
Indicators: Systematic approach to debugging, thorough testing, clear commit messages"""
            
            result = execute_ai_function(generate_tone_mood_section, sample_journal_context)
            
            # Should return ToneMoodSection with parsed fields
            assert isinstance(result, dict)  # ToneMoodSection is a TypedDict
            assert 'mood' in result
            assert 'indicators' in result
            assert result['mood'] == "Focused and determined"
            assert "Systematic approach to debugging" in result['indicators']

    def test_graceful_handling_of_parse_errors(self, sample_journal_context):
        """Test graceful handling when AI response can't be parsed."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        def generate_summary_section(journal_context):
            """Generate a summary section."""
            pass
            
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            # Mock AI failure or empty response
            mock_invoke.return_value = ""
            
            result = execute_ai_function(generate_summary_section, sample_journal_context)
            
            # Should return default empty value, not crash
            assert isinstance(result, dict)
            assert 'summary' in result
            assert result['summary'] == ""  # Empty default per approved design

    def test_graceful_handling_of_ai_invocation_failure(self, sample_journal_context, mock_function_with_docstring):
        """Test graceful handling when invoke_ai fails completely."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            # Mock invoke_ai raising an exception
            mock_invoke.side_effect = Exception("Network error")
            
            result = execute_ai_function(mock_function_with_docstring, sample_journal_context)
            
            # Should return default empty result, not crash
            assert result is not None

    def test_all_section_types_have_correct_defaults(self, sample_journal_context):
        """Test that all section types return correct empty defaults on failure."""
        # This test will fail initially since we haven't implemented the executor yet
        from src.mcp_commit_story.ai_function_executor import execute_ai_function
        
        # Define mock functions for each section type
        section_functions = [
            ('generate_summary_section', lambda ctx: None),
            ('generate_technical_synopsis_section', lambda ctx: None), 
            ('generate_accomplishments_section', lambda ctx: None),
            ('generate_frustrations_section', lambda ctx: None),
            ('generate_tone_mood_section', lambda ctx: None),
            ('generate_discussion_notes_section', lambda ctx: None),
            ('generate_commit_metadata_section', lambda ctx: None),
        ]
        
        with patch('src.mcp_commit_story.ai_function_executor.invoke_ai') as mock_invoke:
            mock_invoke.return_value = ""  # Empty response to trigger defaults
            
            for func_name, func in section_functions:
                func.__name__ = func_name  # Set name for parsing logic
                result = execute_ai_function(func, sample_journal_context)
                
                # Verify correct default structure for each type
                assert isinstance(result, dict)
                
                if 'summary' in func_name:
                    assert 'summary' in result
                    assert result['summary'] == ""
                elif 'accomplishments' in func_name or 'frustrations' in func_name:
                    expected_key = 'accomplishments' if 'accomplishments' in func_name else 'frustrations'
                    assert expected_key in result
                    assert result[expected_key] == []
                elif 'tone_mood' in func_name:
                    assert 'mood' in result
                    assert 'indicators' in result
                    assert result['mood'] == ""
                    assert result['indicators'] == "" 