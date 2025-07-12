"""
TDD tests for direct AI invocation in journal generators.

These tests verify that the 6 AI-powered generators correctly:
1. Make direct AI calls with invoke_ai()
2. Format prompts with JSON context 
3. Parse responses correctly (text, list, complex)
4. Handle errors gracefully
5. Preserve telemetry
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import inspect

import mcp_commit_story.journal_generate as journal
from mcp_commit_story.context_types import (
    JournalContext, 
    SummarySection, 
    TechnicalSynopsisSection,
    AccomplishmentsSection, 
    FrustrationsSection, 
    ToneMoodSection, 
    DiscussionNotesSection
)


# Test data
SAMPLE_CONTEXT = {
    'git': {
        'metadata': {
            'hash': 'abc123',
            'author': 'Alice <alice@example.com>',
            'date': '2025-05-24 12:00:00',
            'message': 'Add user authentication feature',
        },
        'changed_files': ['auth.py', 'user.py'],
    },
    'chat': {
        'messages': [
            {'speaker': 'Human', 'text': 'We need to add authentication to protect user data.'},
            {'speaker': 'Agent', 'text': 'Agreed, this will improve security.'},
        ]
    }
}


class TestGenerateSummarySection:
    """Test generate_summary_section AI invocation behavior."""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_calls_invoke_ai_with_correct_prompt(self, mock_invoke_ai):
        """Test that the function calls invoke_ai with properly formatted prompt."""
        mock_invoke_ai.return_value = "Sample summary response"
        
        result = journal.generate_summary_section(SAMPLE_CONTEXT)
        
        # Verify invoke_ai was called once
        assert mock_invoke_ai.call_count == 1
        
        # Verify the prompt structure
        call_args = mock_invoke_ai.call_args[0]
        prompt = call_args[0]
        context_arg = call_args[1]
        
        # Should contain the docstring
        docstring = inspect.getdoc(journal.generate_summary_section)
        assert docstring in prompt
        
        # Should contain JSON context
        assert "journal_context object has the following structure:" in prompt
        assert json.dumps(SAMPLE_CONTEXT, indent=2, default=str) in prompt
        
        # Context arg should be empty dict
        assert context_arg == {}
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_parses_response_as_simple_text(self, mock_invoke_ai):
        """Test that response is parsed as simple text for summary."""
        mock_invoke_ai.return_value = "This is a test summary response."
        
        result = journal.generate_summary_section(SAMPLE_CONTEXT)
        
        assert 'summary' in result
        assert result['summary'] == "This is a test summary response."
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_handles_empty_response(self, mock_invoke_ai):
        """Test handling of empty AI response."""
        mock_invoke_ai.return_value = ""
        
        result = journal.generate_summary_section(SAMPLE_CONTEXT)
        
        assert 'summary' in result
        assert result['summary'] == ""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_handles_ai_failure(self, mock_invoke_ai):
        """Test error handling when AI invocation fails."""
        mock_invoke_ai.side_effect = Exception("AI service unavailable")
        
        result = journal.generate_summary_section(SAMPLE_CONTEXT)
        
        # Should return fallback content based on git context, not raise exception
        assert 'summary' in result
        assert result['summary'] != ""  # Should have fallback content
        assert "Add user authentication feature" in result['summary']  # Contains commit message
    
    def test_handles_none_context(self):
        """Test handling of None journal context."""
        result = journal.generate_summary_section(None)
        
        assert 'summary' in result
        assert result['summary'] == ""


class TestGenerateAccomplishmentsSection:
    """Test generate_accomplishments_section AI invocation behavior."""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_calls_invoke_ai_with_correct_prompt(self, mock_invoke_ai):
        """Test that the function calls invoke_ai with properly formatted prompt."""
        mock_invoke_ai.return_value = "- Fixed authentication bug\n- Added user validation"
        
        result = journal.generate_accomplishments_section(SAMPLE_CONTEXT)
        
        # Verify invoke_ai was called once
        assert mock_invoke_ai.call_count == 1
        
        # Verify the prompt contains docstring and JSON context
        call_args = mock_invoke_ai.call_args[0]
        prompt = call_args[0]
        
        docstring = inspect.getdoc(journal.generate_accomplishments_section)
        assert docstring in prompt
        assert json.dumps(SAMPLE_CONTEXT, indent=2, default=str) in prompt
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_parses_response_as_list(self, mock_invoke_ai):
        """Test that response is parsed as list by splitting on newlines."""
        mock_invoke_ai.return_value = "- Fixed authentication bug\n- Added user validation\n- Improved error handling"
        
        result = journal.generate_accomplishments_section(SAMPLE_CONTEXT)
        
        assert 'accomplishments' in result
        assert len(result['accomplishments']) == 3
        assert "- Fixed authentication bug" in result['accomplishments']
        assert "- Added user validation" in result['accomplishments']
        assert "- Improved error handling" in result['accomplishments']
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_filters_empty_lines(self, mock_invoke_ai):
        """Test that empty lines are filtered from list parsing."""
        mock_invoke_ai.return_value = "- Fixed bug\n\n- Added feature\n   \n- Improved code"
        
        result = journal.generate_accomplishments_section(SAMPLE_CONTEXT)
        
        assert len(result['accomplishments']) == 3
        assert all(line.strip() for line in result['accomplishments'])
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_handles_empty_response(self, mock_invoke_ai):
        """Test handling of empty AI response."""
        mock_invoke_ai.return_value = ""
        
        result = journal.generate_accomplishments_section(SAMPLE_CONTEXT)
        
        assert 'accomplishments' in result
        # Should have fallback content based on git context
        assert len(result['accomplishments']) > 0
        assert any("Add user authentication feature" in acc for acc in result['accomplishments'])


class TestGenerateFrustrationsSection:
    """Test generate_frustrations_section AI invocation behavior."""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_parses_response_as_list(self, mock_invoke_ai):
        """Test that response is parsed as list by splitting on newlines."""
        mock_invoke_ai.return_value = "- Spent hours debugging config\n- Authentication kept failing\n- Documentation was unclear"
        
        result = journal.generate_frustrations_section(SAMPLE_CONTEXT)
        
        assert 'frustrations' in result
        assert len(result['frustrations']) == 3
        assert "- Spent hours debugging config" in result['frustrations']
        assert "- Authentication kept failing" in result['frustrations']
        assert "- Documentation was unclear" in result['frustrations']


class TestGenerateDiscussionNotesSection:
    """Test generate_discussion_notes_section AI invocation behavior."""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_parses_response_as_list(self, mock_invoke_ai):
        """Test that response is parsed as list by splitting on newlines."""
        mock_invoke_ai.return_value = '> **Human:** "We need authentication"\n> **AI:** "Agreed, for security"'
        
        result = journal.generate_discussion_notes_section(SAMPLE_CONTEXT)
        
        assert 'discussion_notes' in result
        assert len(result['discussion_notes']) == 2
        assert '> **Human:** "We need authentication"' in result['discussion_notes']
        assert '> **AI:** "Agreed, for security"' in result['discussion_notes']


class TestGenerateTechnicalSynopsisSection:
    """Test generate_technical_synopsis_section AI invocation behavior."""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_calls_invoke_ai_with_correct_prompt(self, mock_invoke_ai):
        """Test that the function calls invoke_ai with properly formatted prompt."""
        mock_invoke_ai.return_value = "Technical implementation details here"
        
        result = journal.generate_technical_synopsis_section(SAMPLE_CONTEXT)
        
        # Verify invoke_ai was called once
        assert mock_invoke_ai.call_count == 1
        
        # Verify the prompt contains docstring and JSON context
        call_args = mock_invoke_ai.call_args[0]
        prompt = call_args[0]
        
        docstring = inspect.getdoc(journal.generate_technical_synopsis_section)
        assert docstring in prompt
        assert json.dumps(SAMPLE_CONTEXT, indent=2, default=str) in prompt
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_parses_response_as_simple_text(self, mock_invoke_ai):
        """Test that response is parsed as simple text for technical synopsis."""
        mock_invoke_ai.return_value = "Technical implementation used OAuth2 with JWT tokens."
        
        result = journal.generate_technical_synopsis_section(SAMPLE_CONTEXT)
        
        assert 'technical_synopsis' in result
        assert result['technical_synopsis'] == "Technical implementation used OAuth2 with JWT tokens."


class TestGenerateToneMoodSection:
    """Test generate_tone_mood_section AI invocation behavior (complex parsing)."""
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_parses_mood_and_indicators_from_response(self, mock_invoke_ai):
        """Test complex parsing of mood and indicators from AI response."""
        mock_invoke_ai.return_value = "Mood: Frustrated\nIndicators: Multiple failed attempts, debugging took hours"
        
        result = journal.generate_tone_mood_section(SAMPLE_CONTEXT)
        
        assert 'mood' in result
        assert 'indicators' in result
        assert result['mood'] == "Frustrated"
        assert result['indicators'] == "Multiple failed attempts, debugging took hours"
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_handles_response_without_patterns(self, mock_invoke_ai):
        """Test fallback parsing when mood/indicators patterns not found."""
        mock_invoke_ai.return_value = "Frustrated and tired\nSpent too long debugging"
        
        result = journal.generate_tone_mood_section(SAMPLE_CONTEXT)
        
        assert 'mood' in result
        assert 'indicators' in result
        # Should use first line as mood, second as indicators
        assert result['mood'] == "Frustrated and tired"
        assert result['indicators'] == "Spent too long debugging"
    
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_handles_empty_response(self, mock_invoke_ai):
        """Test handling of empty AI response."""
        mock_invoke_ai.return_value = ""
        
        result = journal.generate_tone_mood_section(SAMPLE_CONTEXT)
        
        assert 'mood' in result
        assert 'indicators' in result
        assert result['mood'] == ""
        assert result['indicators'] == ""


# Test telemetry preservation
class TestTelemetryPreservation:
    """Test that telemetry decorators and metrics are preserved."""
    
    @patch('mcp_commit_story.journal_generate._add_ai_generation_telemetry')
    @patch('mcp_commit_story.journal_generate._record_ai_generation_metrics')
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_accomplishments_preserves_telemetry(self, mock_invoke_ai, mock_record_metrics, mock_add_telemetry):
        """Test that accomplishments generator preserves telemetry calls."""
        mock_invoke_ai.return_value = "- Accomplished something"
        
        journal.generate_accomplishments_section(SAMPLE_CONTEXT)
        
        # Verify telemetry functions were called
        mock_add_telemetry.assert_called_once()
        mock_record_metrics.assert_called_once()
        
        # Verify telemetry called with correct section type
        assert mock_add_telemetry.call_args[0][0] == "accomplishments"
        assert mock_record_metrics.call_args[0][0] == "accomplishments"
        
        # Verify success telemetry
        success_arg = mock_record_metrics.call_args[0][2]  # Third argument is success boolean
        assert success_arg is True
    
    @patch('mcp_commit_story.journal_generate._record_ai_generation_metrics')
    @patch('mcp_commit_story.journal_generate.invoke_ai')
    def test_error_telemetry_on_failure(self, mock_invoke_ai, mock_record_metrics):
        """Test that error telemetry is recorded on failure."""
        mock_invoke_ai.side_effect = Exception("AI service unavailable")
        
        # Should not raise exception due to error handling
        journal.generate_accomplishments_section(SAMPLE_CONTEXT)
        
        # Verify failure telemetry was recorded
        mock_record_metrics.assert_called()
        success_arg = mock_record_metrics.call_args[0][2]  # Third argument is success boolean
        assert success_arg is False 