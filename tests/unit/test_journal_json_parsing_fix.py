"""Tests for JSON vs Plain Text Parsing Fix in AI Generators

This test file demonstrates the core issue where AI returns JSON like {"summary": "content"}
but the parsing code expects plain text and treats the entire JSON string as the content.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.mcp_commit_story.journal_generate import (
    generate_summary_section,
    generate_technical_synopsis_section,
    generate_accomplishments_section,
    generate_frustrations_section,
    generate_tone_mood_section,
    generate_discussion_notes_section
)
from src.mcp_commit_story.context_types import JournalContext


@pytest.fixture
def sample_journal_context():
    """Sample journal context for testing"""
    return JournalContext(
        git={
            'metadata': {'message': 'Fix parsing issue', 'hash': 'abc123'},
            'changed_files': ['src/parser.py'],
            'file_stats': {}
        },
        chat={
            'messages': [
                {'role': 'user', 'content': 'I need to fix this parsing bug'},
                {'role': 'assistant', 'content': 'Let me help you with that'}
            ]
        },
        journal={}
    )


class TestJSONParsingIssue:
    """Test cases that demonstrate the JSON vs plain text parsing mismatch"""
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_summary_section_json_response_parsing_issue(self, mock_invoke_ai, sample_journal_context):
        """Test that shows summary section incorrectly parses JSON response as plain text"""
        # AI returns JSON format (what actually happens)
        mock_invoke_ai.return_value = '{"summary": "Fixed the parsing bug that was causing JSON to be treated as plain text"}'
        
        result = generate_summary_section(sample_journal_context)
        
        # Current broken behavior: entire JSON string becomes the summary
        # This should FAIL initially, showing the bug
        assert result['summary'] != '{"summary": "Fixed the parsing bug that was causing JSON to be treated as plain text"}'
        # What we actually want: just the content from inside the JSON
        assert result['summary'] == "Fixed the parsing bug that was causing JSON to be treated as plain text"
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_technical_synopsis_json_response_parsing_issue(self, mock_invoke_ai, sample_journal_context):
        """Test that shows technical synopsis incorrectly parses JSON response as plain text"""
        # AI returns JSON format (what actually happens)
        mock_invoke_ai.return_value = '{"technical_synopsis": "Implemented proper JSON parsing by extracting content from AI response objects"}'
        
        result = generate_technical_synopsis_section(sample_journal_context)
        
        # Current broken behavior: entire JSON string becomes the technical_synopsis
        # This should FAIL initially, showing the bug
        assert result['technical_synopsis'] != '{"technical_synopsis": "Implemented proper JSON parsing by extracting content from AI response objects"}'
        # What we actually want: just the content from inside the JSON
        assert result['technical_synopsis'] == "Implemented proper JSON parsing by extracting content from AI response objects"
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_accomplishments_section_json_response_parsing_issue(self, mock_invoke_ai, sample_journal_context):
        """Test that shows accomplishments section incorrectly parses JSON response as plain text"""
        # AI returns JSON format (what actually happens)
        mock_invoke_ai.return_value = '{"accomplishments": ["Fixed JSON parsing bug", "Added proper error handling", "Updated tests"]}'
        
        result = generate_accomplishments_section(sample_journal_context)
        
        # Current broken behavior: JSON string gets split by newlines incorrectly
        # This should FAIL initially, showing the bug
        expected_accomplishments = ["Fixed JSON parsing bug", "Added proper error handling", "Updated tests"]
        assert result['accomplishments'] != ['{"accomplishments": ["Fixed JSON parsing bug", "Added proper error handling", "Updated tests"]}']
        # What we actually want: the list from inside the JSON
        assert result['accomplishments'] == expected_accomplishments
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_frustrations_section_json_response_parsing_issue(self, mock_invoke_ai, sample_journal_context):
        """Test that shows frustrations section incorrectly parses JSON response as plain text"""
        # AI returns JSON format (what actually happens)
        mock_invoke_ai.return_value = '{"frustrations": ["Spent hours debugging this parsing issue", "Documentation was unclear about expected format"]}'
        
        result = generate_frustrations_section(sample_journal_context)
        
        # Current broken behavior: JSON string gets split by newlines incorrectly
        # This should FAIL initially, showing the bug
        expected_frustrations = ["Spent hours debugging this parsing issue", "Documentation was unclear about expected format"]
        assert result['frustrations'] != ['{"frustrations": ["Spent hours debugging this parsing issue", "Documentation was unclear about expected format"]}']
        # What we actually want: the list from inside the JSON
        assert result['frustrations'] == expected_frustrations
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_tone_mood_section_json_response_parsing_issue(self, mock_invoke_ai, sample_journal_context):
        """Test that shows tone/mood section incorrectly parses JSON response as plain text"""
        # AI returns JSON format (what actually happens)
        mock_invoke_ai.return_value = '{"mood": "frustrated", "indicators": "multiple debugging attempts, time pressure"}'
        
        result = generate_tone_mood_section(sample_journal_context)
        
        # Current broken behavior: JSON string gets parsed incorrectly
        # This should FAIL initially, showing the bug
        assert result['mood'] != '{"mood": "frustrated", "indicators": "multiple debugging attempts, time pressure"}'
        assert result['indicators'] != '{"mood": "frustrated", "indicators": "multiple debugging attempts, time pressure"}'
        # What we actually want: the values from inside the JSON
        assert result['mood'] == "frustrated"
        assert result['indicators'] == "multiple debugging attempts, time pressure"
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_discussion_notes_json_response_parsing_issue(self, mock_invoke_ai, sample_journal_context):
        """Test that shows discussion notes incorrectly parses JSON response as plain text"""
        # AI returns JSON format (what actually happens)
        mock_invoke_ai.return_value = '{"discussion_notes": ["User: I need to fix this parsing bug", "Assistant: Let me help you with that"]}'
        
        result = generate_discussion_notes_section(sample_journal_context)
        
        # Current broken behavior: JSON string gets split by newlines incorrectly
        # This should FAIL initially, showing the bug
        expected_discussion_notes = ["User: I need to fix this parsing bug", "Assistant: Let me help you with that"]
        assert result['discussion_notes'] != ['{"discussion_notes": ["User: I need to fix this parsing bug", "Assistant: Let me help you with that"]}']
        # What we actually want: the list from inside the JSON
        assert result['discussion_notes'] == expected_discussion_notes


class TestEdgeCasesForJSONParsing:
    """Test edge cases that should be handled properly"""
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_plain_text_response_still_works(self, mock_invoke_ai, sample_journal_context):
        """Test that plain text responses (legacy) still work after fix"""
        # AI returns plain text (should still work)
        mock_invoke_ai.return_value = 'This is a plain text summary without JSON'
        
        result = generate_summary_section(sample_journal_context)
        
        # Should handle plain text responses gracefully
        assert result['summary'] == 'This is a plain text summary without JSON'
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_malformed_json_falls_back_gracefully(self, mock_invoke_ai, sample_journal_context):
        """Test that malformed JSON responses fall back to plain text"""
        # AI returns malformed JSON
        mock_invoke_ai.return_value = '{"summary": "Missing closing quote and brace'
        
        result = generate_summary_section(sample_journal_context)
        
        # Should fall back to treating as plain text when JSON parsing fails
        assert result['summary'] == '{"summary": "Missing closing quote and brace'
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_empty_json_response_handled(self, mock_invoke_ai, sample_journal_context):
        """Test that empty JSON responses are handled properly"""
        # AI returns empty JSON
        mock_invoke_ai.return_value = '{}'
        
        result = generate_summary_section(sample_journal_context)
        
        # Should handle empty JSON gracefully
        assert result['summary'] == ""
    
    @patch('src.mcp_commit_story.journal_generate.invoke_ai')
    def test_wrong_json_field_falls_back(self, mock_invoke_ai, sample_journal_context):
        """Test that JSON with wrong field names falls back to fallback value"""
        # AI returns JSON with wrong field name
        mock_invoke_ai.return_value = '{"wrong_field": "Some content"}'
        
        result = generate_summary_section(sample_journal_context)
        
        # Should return fallback value when JSON is valid but expected field missing
        assert result['summary'] == "" 