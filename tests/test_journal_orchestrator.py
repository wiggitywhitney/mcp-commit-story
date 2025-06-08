"""
Comprehensive tests for the journal orchestration layer.

Following TDD principles - these tests define the expected interface and behavior
before implementation. They will fail initially because journal_orchestrator.py
doesn't exist yet.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import time
from typing import Dict, Any, Optional

# These imports will fail initially - that's expected for TDD
from mcp_commit_story.journal_orchestrator import (
    orchestrate_journal_generation,
    execute_ai_function,
    collect_all_context_data,
    assemble_journal_entry,
    validate_section_result
)
from mcp_commit_story.context_types import JournalContext, ChatHistory, TerminalContext, GitContext
from mcp_commit_story.journal import JournalEntry


class TestAIFunctionExecution:
    """Test the AI function execution pattern."""
    
    def test_execute_ai_function_exists(self):
        """Verify execute_ai_function function exists with correct signature."""
        # This will fail because function doesn't exist yet
        assert callable(execute_ai_function)
    
    def test_execute_ai_function_calls_specific_journal_function(self):
        """Verify execute_ai_function instructs AI to call specific functions."""
        mock_context = JournalContext(
            chat=None,
            terminal=None, 
            git=GitContext(commit_hash="abc123", message="Test commit")
        )
        
        # Should instruct AI agent to call the specific function
        with patch('mcp_commit_story.journal_orchestrator.logger') as mock_logger:
            result = execute_ai_function('generate_summary_section', mock_context)
            
            # Should return dict structure (AI agent response)
            assert isinstance(result, dict)
            # Should log the AI function call
            mock_logger.info.assert_called()
    
    def test_execute_ai_function_with_invalid_function_name(self):
        """Verify execute_ai_function validates function names."""
        mock_context = JournalContext(
            chat=None,
            terminal=None,
            git=GitContext(commit_hash="abc123", message="Test commit")
        )
        
        # Should raise ValueError for invalid function names
        with pytest.raises(ValueError, match="Invalid function name"):
            execute_ai_function('invalid_function_name', mock_context)
    
    def test_execute_ai_function_handles_ai_failures(self):
        """Verify execute_ai_function handles AI execution failures gracefully."""
        mock_context = JournalContext(
            chat=None,
            terminal=None,
            git=GitContext(commit_hash="abc123", message="Test commit") 
        )
        
        # Should handle failures and return empty dict with error metadata
        with patch('mcp_commit_story.journal_orchestrator.ai_agent_call') as mock_ai:
            mock_ai.side_effect = Exception("AI call failed")
            
            result = execute_ai_function('generate_summary_section', mock_context)
            
            assert isinstance(result, dict)
            assert result.get('error') is not None
            assert result.get('content', '') == ''


class TestContextCollection:
    """Test context collection coordination."""
    
    def test_collect_all_context_data_exists(self):
        """Verify collect_all_context_data function exists."""
        assert callable(collect_all_context_data)
    
    @patch('mcp_commit_story.journal_orchestrator.collect_git_context')
    @patch('mcp_commit_story.journal_orchestrator.collect_chat_history')  
    @patch('mcp_commit_story.journal_orchestrator.collect_ai_terminal_commands')
    def test_collect_all_context_data_success(self, mock_terminal, mock_chat, mock_git):
        """Test successful context collection from all three sources."""
        # Setup mocks
        mock_git.return_value = GitContext(commit_hash="abc123", message="Test commit")
        mock_chat.return_value = ChatHistory(messages=["Hello", "World"])
        mock_terminal.return_value = TerminalContext(commands=["git status", "ls -la"])
        
        # Execute
        result = collect_all_context_data("abc123", "since_commit_123", 100, Path("/repo"), Path("/journal"))
        
                # Verify (TypedDict doesn't support isinstance, so check structure)
        assert isinstance(result, dict)
        assert 'git' in result and 'chat' in result and 'terminal' in result
        assert result['git'] is not None
        assert result['chat'] is not None 
        assert result['terminal'] is not None
        
        # Verify individual functions were called with correct parameters
        mock_git.assert_called_once_with("abc123", Path("/repo"), Path("/journal"))
        mock_chat.assert_called_once_with("since_commit_123", 100)
        mock_terminal.assert_called_once_with("since_commit_123", 100)
    
    @patch('mcp_commit_story.journal_orchestrator.collect_git_context')
    @patch('mcp_commit_story.journal_orchestrator.collect_chat_history')
    @patch('mcp_commit_story.journal_orchestrator.collect_ai_terminal_commands')
    def test_collect_all_context_data_partial_failure(self, mock_terminal, mock_chat, mock_git):
        """Test graceful degradation when some context collection fails."""
        # Setup mocks - chat fails but others succeed
        mock_git.return_value = GitContext(commit_hash="abc123", message="Test commit")
        mock_chat.side_effect = Exception("Chat collection failed")
        mock_terminal.return_value = TerminalContext(commands=["git status"])
        
        # Execute
        result = collect_all_context_data("abc123", "since_commit_123", 100, Path("/repo"), Path("/journal"))
        
        # Verify graceful degradation (TypedDict doesn't support isinstance, so check structure)
        assert isinstance(result, dict)
        assert 'git' in result and 'chat' in result and 'terminal' in result
        assert result['git'] is not None  # Git succeeded
        assert result['chat'] is None     # Chat failed, should be None
        assert result['terminal'] is not None  # Terminal succeeded
    
    @patch('mcp_commit_story.journal_orchestrator.collect_git_context')
    @patch('mcp_commit_story.journal_orchestrator.collect_chat_history')
    @patch('mcp_commit_story.journal_orchestrator.collect_ai_terminal_commands')
    def test_collect_all_context_data_git_only_fallback(self, mock_terminal, mock_chat, mock_git):
        """Test fallback to git-only context when AI functions fail."""
        # Setup mocks - only git succeeds
        mock_git.return_value = GitContext(commit_hash="abc123", message="Test commit")
        mock_chat.side_effect = Exception("Chat failed")
        mock_terminal.side_effect = Exception("Terminal failed")
        
        # Execute
        result = collect_all_context_data("abc123", "since_commit_123", 100, Path("/repo"), Path("/journal"))
        
        # Verify git-only fallback (TypedDict doesn't support isinstance, so check structure)
        assert isinstance(result, dict)
        assert 'git' in result and 'chat' in result and 'terminal' in result
        assert result['git'] is not None
        assert result['chat'] is None
        assert result['terminal'] is None


class TestSectionValidation:
    """Test section result validation and fallback logic."""
    
    def test_validate_section_result_exists(self):
        """Verify validate_section_result function exists."""
        assert callable(validate_section_result)
    
    def test_validate_section_result_summary_valid(self):
        """Test validation of valid summary section result."""
        valid_result = {"content": "This is a summary.", "metadata": {}}
        
        validated = validate_section_result('summary', valid_result)
        
        assert isinstance(validated, dict)
        assert validated['content'] == "This is a summary."
        assert 'metadata' in validated
    
    def test_validate_section_result_summary_invalid_fallback(self):
        """Test fallback for invalid summary section result."""
        invalid_result = {"invalid": "data"}
        
        validated = validate_section_result('summary', invalid_result)
        
        # Should provide fallback value
        assert isinstance(validated, dict)
        assert validated['content'] == ""  # Empty string fallback for summary
        assert 'error' in validated
    
    def test_validate_section_result_accomplishments_valid(self):
        """Test validation of valid accomplishments section result."""
        valid_result = {"items": ["Task 1 completed", "Bug fix merged"], "metadata": {}}
        
        validated = validate_section_result('accomplishments', valid_result)
        
        assert isinstance(validated, dict)
        assert isinstance(validated['items'], list)
        assert len(validated['items']) == 2
    
    def test_validate_section_result_accomplishments_invalid_fallback(self):
        """Test fallback for invalid accomplishments section result."""
        invalid_result = {"wrong_key": "data"}
        
        validated = validate_section_result('accomplishments', invalid_result)
        
        # Should provide fallback value
        assert isinstance(validated, dict)
        assert validated['items'] == []  # Empty list fallback for accomplishments
        assert 'error' in validated
    
    def test_validate_section_result_tone_mood_none_fallback(self):
        """Test None fallback for tone_mood section failures."""
        invalid_result = {}
        
        validated = validate_section_result('tone_mood', invalid_result)
        
        assert validated['content'] is None  # None fallback for tone_mood
        assert 'error' in validated


class TestJournalAssembly:
    """Test journal entry assembly logic."""
    
    def test_assemble_journal_entry_exists(self):
        """Verify assemble_journal_entry function exists."""
        assert callable(assemble_journal_entry)
    
    def test_assemble_journal_entry_all_sections_present(self):
        """Test assembly when all sections are present."""
        sections = {
            'summary': {'content': 'Test summary'},
            'technical_synopsis': {'content': 'Technical details'},
            'accomplishments': {'items': ['Task 1', 'Task 2']},
            'frustrations': {'items': []},
            'tone_mood': {'content': 'productive'},
            'discussion_notes': {'items': ['Note 1', 'Note 2']},
            'terminal_commands': {'items': ['git status', 'ls -la']},
            'commit_metadata': {'author': 'test', 'timestamp': '2025-06-08'}
        }
        
        result = assemble_journal_entry(sections)
        
        assert isinstance(result, JournalEntry)
        assert result.summary == 'Test summary'
        assert result.technical_synopsis == 'Technical details'
        assert len(result.accomplishments) == 2
        assert result.accomplishments == ['Task 1', 'Task 2']
    
    def test_assemble_journal_entry_missing_sections_with_fallbacks(self):
        """Test assembly with missing sections uses fallback values."""
        sections = {
            'summary': {'content': 'Only summary present'}
            # All other sections missing
        }
        
        result = assemble_journal_entry(sections)
        
        assert isinstance(result, JournalEntry)
        assert result.summary == 'Only summary present'
        assert result.technical_synopsis == ""  # Fallback
        assert result.accomplishments == []     # Fallback
        assert result.frustrations == []        # Fallback
        assert result.tone_mood is None         # Fallback
        assert result.discussion_notes == []    # Fallback
        assert result.terminal_commands == []   # Fallback
        assert result.commit_metadata == {}     # Fallback


class TestOrchestrationIntegration:
    """Test the main orchestration function integration."""
    
    def test_orchestrate_journal_generation_exists(self):
        """Verify main orchestration function exists with correct signature."""
        assert callable(orchestrate_journal_generation)
    
    @patch('mcp_commit_story.journal_orchestrator.trace_mcp_operation')
    @patch('mcp_commit_story.journal_orchestrator.collect_all_context_data')
    @patch('mcp_commit_story.journal_orchestrator.execute_ai_function')
    @patch('mcp_commit_story.journal_orchestrator.assemble_journal_entry')
    def test_orchestrate_journal_generation_success_flow(self, mock_assemble, mock_execute_ai, mock_collect, mock_trace):
        """Test successful end-to-end orchestration flow."""
        # Setup mocks
        mock_context = JournalContext(
            chat=None,
            terminal=None,
            git=GitContext(commit_hash="abc123", message="Test commit")
        )
        mock_collect.return_value = mock_context
        
        # Mock AI function results for all 8 sections
        ai_results = {
            'generate_summary_section': {'content': 'Test summary'},
            'generate_technical_synopsis_section': {'content': 'Technical details'},
            'generate_accomplishments_section': {'items': ['Task 1']},
            'generate_frustrations_section': {'items': []},
            'generate_tone_mood_section': {'content': 'productive'},
            'generate_discussion_notes_section': {'items': ['Note 1']},
            'generate_terminal_commands_section': {'items': ['git status']},
            'generate_commit_metadata_section': {'author': 'test'}
        }
        
        def mock_ai_function(function_name: str, context: JournalContext) -> Dict[str, Any]:
            return ai_results[function_name]
        
        mock_execute_ai.side_effect = mock_ai_function
        
        mock_journal_entry = JournalEntry(
            timestamp='2025-01-08T12:00:00',
            commit_hash='abc123',
            summary='Test summary',
            technical_synopsis='Technical details',
            accomplishments=['Task 1'],
            frustrations=[],
            tone_mood='productive',
            discussion_notes=['Note 1'],
            terminal_commands=['git status'],
            commit_metadata={'author': 'test'}
        )
        mock_assemble.return_value = mock_journal_entry
        
        # Execute
        result = orchestrate_journal_generation("abc123", str(Path("/journal/path")))
        
        # Verify successful orchestration
        assert isinstance(result, dict)
        assert result['success'] is True
        assert result['journal_entry'] == mock_journal_entry
        assert 'execution_time' in result
        assert 'telemetry' in result
        
        # Verify all phases were called
        mock_collect.assert_called_once()
        assert mock_execute_ai.call_count == 8  # All 8 AI functions called
        mock_assemble.assert_called_once()
        
        # Note: Decorator testing requires more complex setup since it's applied at function definition time
        # The important part is that the orchestration flow works correctly
    
    @patch('mcp_commit_story.journal_orchestrator.collect_all_context_data')
    def test_orchestrate_journal_generation_context_collection_failure(self, mock_collect):
        """Test orchestration when context collection fails completely."""
        # Setup complete failure
        mock_collect.side_effect = Exception("Critical context failure")
        
        # Execute
        result = orchestrate_journal_generation("abc123", str(Path("/journal/path")))
        
        # Verify failure handling
        assert isinstance(result, dict)
        assert result['success'] is False
        assert 'error' in result
        assert result['phase'] == 'context_collection'
        assert 'execution_time' in result
    
    @patch('mcp_commit_story.journal_orchestrator.collect_all_context_data')
    @patch('mcp_commit_story.journal_orchestrator.execute_ai_function')
    def test_orchestrate_journal_generation_partial_ai_failures(self, mock_execute_ai, mock_collect):
        """Test orchestration when some AI functions fail but others succeed."""
        # Setup context collection success
        mock_context = JournalContext(
            chat=None,
            terminal=None, 
            git=GitContext(commit_hash="abc123", message="Test commit")
        )
        mock_collect.return_value = mock_context
        
        # Setup mixed AI function results (some succeed, some fail)
        def mock_ai_function(function_name: str, context: JournalContext) -> Dict[str, Any]:
            if function_name == 'generate_summary_section':
                return {'content': 'Test summary'}
            elif function_name == 'generate_accomplishments_section':
                raise Exception("AI function failed")
            else:
                return {'content': 'Default result'}
        
        mock_execute_ai.side_effect = mock_ai_function
        
        # Execute
        result = orchestrate_journal_generation("abc123", str(Path("/journal/path")))
        
        # Verify graceful degradation
        assert isinstance(result, dict)
        assert result['success'] is True  # Should still succeed with partial results
        assert len(result['errors']) > 0  # Should track failures
        assert any('generate_accomplishments_section' in error['section'] for error in result['errors'])
    
    @patch('mcp_commit_story.journal_orchestrator.collect_all_context_data')
    @patch('mcp_commit_story.journal_orchestrator.execute_ai_function')
    def test_orchestrate_journal_generation_telemetry_collection(self, mock_execute_ai, mock_collect):
        """Test that orchestration collects comprehensive telemetry."""
        # Setup successful flow
        mock_context = JournalContext(
            chat=None,
            terminal=None,
            git=GitContext(commit_hash="abc123", message="Test commit")
        )
        mock_collect.return_value = mock_context
        mock_execute_ai.return_value = {'content': 'Test result'}
        
        # Execute
        result = orchestrate_journal_generation("abc123", str(Path("/journal/path")))
        
        # Verify telemetry structure
        assert 'telemetry' in result
        telemetry = result['telemetry']
        
        assert 'context_collection_time' in telemetry
        assert 'ai_function_times' in telemetry
        assert 'total_ai_functions_called' in telemetry
        assert 'successful_ai_functions' in telemetry
        assert 'failed_ai_functions' in telemetry
        assert 'assembly_time' in telemetry
        
        # Verify AI function timing tracking
        ai_times = telemetry['ai_function_times']
        assert len(ai_times) == 8  # All 8 functions should be tracked
        for function_name in ai_times:
            assert function_name.startswith('generate_')
            assert function_name.endswith('_section')


class TestTelemetryIntegration:
    """Test telemetry integration following telemetry.md patterns."""
    
    @patch('mcp_commit_story.journal_orchestrator.log_telemetry_event')
    def test_telemetry_events_logged_during_orchestration(self, mock_log_telemetry):
        """Test that telemetry events are logged throughout orchestration."""
        # This test will verify telemetry logging patterns match telemetry.md
        # Will fail initially because telemetry integration doesn't exist yet
        
        with patch('mcp_commit_story.journal_orchestrator.collect_all_context_data'):
            with patch('mcp_commit_story.journal_orchestrator.execute_ai_function'):
                orchestrate_journal_generation("abc123", str(Path("/journal/path")))
        
        # Verify telemetry events were logged
        assert mock_log_telemetry.call_count > 0
        
        # Check for specific telemetry event types
        call_args_list = [call[0] for call in mock_log_telemetry.call_args_list]
        event_types = [args[0] for args in call_args_list]
        
        assert "orchestration" in event_types
        assert "ai_function_call" in event_types 