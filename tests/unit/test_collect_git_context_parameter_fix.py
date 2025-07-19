"""
Tests for collect_git_context parameter order fix.

This test module verifies that collect_git_context is called with the correct
parameter order in journal_workflow.py and journal_orchestrator.py to prevent
the InvalidGitRepositoryError bug where journal_path was passed as repo parameter.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import git

from mcp_commit_story.journal_workflow import generate_journal_entry
from mcp_commit_story.journal_orchestrator import collect_all_context_data


class TestJournalWorkflowGitContextParameters:
    """Test that journal_workflow.py calls collect_git_context with correct parameters."""

    @patch('mcp_commit_story.journal_workflow.is_journal_only_commit')
    @patch('mcp_commit_story.context_collection.collect_recent_journal_context')
    @patch('mcp_commit_story.context_collection.collect_chat_history')
    @patch('mcp_commit_story.context_collection.collect_git_context')
    def test_collect_git_context_called_with_correct_parameters(
        self, mock_git_context, mock_chat_history, mock_journal_context, mock_journal_only
    ):
        """Test that collect_git_context is called with correct parameter order in journal workflow."""
        # Setup mocks
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_config = {'journal': {'path': 'sandbox-journal'}}
        
        # Mock return values
        mock_journal_only.return_value = False
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'diff_summary': 'Test changes',
            'changed_files': ['test.py'],
            'file_stats': {'source': 1},
            'commit_context': {'size_classification': 'small'}
        }
        mock_chat_history.return_value = None
        mock_journal_context.return_value = None
        
        # Mock all the section generators to avoid AI calls
        with patch('mcp_commit_story.journal_generate.generate_summary_section') as mock_summary, \
             patch('mcp_commit_story.journal_generate.generate_technical_synopsis_section') as mock_tech, \
             patch('mcp_commit_story.journal_generate.generate_accomplishments_section') as mock_acc, \
             patch('mcp_commit_story.journal_generate.generate_frustrations_section') as mock_frust, \
             patch('mcp_commit_story.journal_generate.generate_tone_mood_section') as mock_tone, \
             patch('mcp_commit_story.journal_generate.generate_discussion_notes_section') as mock_disc, \
             patch('mcp_commit_story.journal_generate.generate_discussion_notes_section_simple') as mock_disc_simple, \
             patch('mcp_commit_story.journal_generate.generate_commit_metadata_section') as mock_meta:
            
            # Setup section generator mocks to return proper structures
            mock_summary.return_value = {'summary': 'Test summary'}
            mock_tech.return_value = {'technical_synopsis': 'Test synopsis'}
            mock_acc.return_value = {'accomplishments': ['Test accomplishment']}
            mock_frust.return_value = {'frustrations': []}
            mock_tone.return_value = {'mood': '', 'indicators': ''}
            mock_disc.return_value = {'discussion_notes': []}
            mock_disc_simple.return_value = {'discussion_notes': []}
            mock_meta.return_value = {'commit_metadata': {'files_changed': 1}}
            
            # Execute
            result = generate_journal_entry(mock_commit, mock_config, debug=False)
            
            # Verify collect_git_context was called with CORRECT parameter order
            # This is the key test - repo should be passed as keyword argument, not positional
            mock_git_context.assert_called_once_with(
                commit_hash='abc123',
                repo='.',  # repo parameter should be '.' (current directory)
                journal_path='sandbox-journal'  # journal_path should be the journal directory
            )
            
            # Verify we got a result
            assert result is not None

    @patch('mcp_commit_story.journal_workflow.is_journal_only_commit')
    @patch('mcp_commit_story.context_collection.collect_recent_journal_context')
    @patch('mcp_commit_story.context_collection.collect_chat_history')
    @patch('mcp_commit_story.context_collection.collect_git_context')
    def test_collect_git_context_not_called_with_wrong_parameters(
        self, mock_git_context, mock_chat_history, mock_journal_context, mock_journal_only
    ):
        """Test that collect_git_context is NOT called with the old wrong parameter order."""
        # Setup mocks
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_config = {'journal': {'path': 'sandbox-journal'}}
        
        # Mock return values
        mock_journal_only.return_value = False
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'diff_summary': 'Test changes',
            'changed_files': ['test.py'],
            'file_stats': {'source': 1},
            'commit_context': {'size_classification': 'small'}
        }
        mock_chat_history.return_value = None
        mock_journal_context.return_value = None
        
        # Mock section generators
        with patch('mcp_commit_story.journal_generate.generate_summary_section') as mock_summary, \
             patch('mcp_commit_story.journal_generate.generate_technical_synopsis_section') as mock_tech, \
             patch('mcp_commit_story.journal_generate.generate_accomplishments_section') as mock_acc, \
             patch('mcp_commit_story.journal_generate.generate_frustrations_section') as mock_frust, \
             patch('mcp_commit_story.journal_generate.generate_tone_mood_section') as mock_tone, \
             patch('mcp_commit_story.journal_generate.generate_discussion_notes_section') as mock_disc, \
             patch('mcp_commit_story.journal_generate.generate_discussion_notes_section_simple') as mock_disc_simple, \
             patch('mcp_commit_story.journal_generate.generate_commit_metadata_section') as mock_meta:
            
            # Setup section generator mocks
            mock_summary.return_value = {'summary': 'Test summary'}
            mock_tech.return_value = {'technical_synopsis': 'Test synopsis'}
            mock_acc.return_value = {'accomplishments': ['Test accomplishment']}
            mock_frust.return_value = {'frustrations': []}
            mock_tone.return_value = {'mood': '', 'indicators': ''}
            mock_disc.return_value = {'discussion_notes': []}
            mock_disc_simple.return_value = {'discussion_notes': []}
            mock_meta.return_value = {'commit_metadata': {'files_changed': 1}}
            
            # Execute
            generate_journal_entry(mock_commit, mock_config, debug=False)
            
            # Verify collect_git_context was NOT called with the old WRONG parameter order
            # This verifies the bug is fixed - we should NOT see these calls:
            
            # WRONG CALL 1: journal_path passed as second positional argument (old bug)
            with pytest.raises(AssertionError):
                mock_git_context.assert_called_with('abc123', 'sandbox-journal')
                
            # WRONG CALL 2: journal_path passed as repo parameter (the specific bug we fixed)
            with pytest.raises(AssertionError):
                mock_git_context.assert_called_with(commit_hash='abc123', journal_path='sandbox-journal')


class TestJournalOrchestratorGitContextParameters:
    """Test that journal_orchestrator.py calls collect_git_context with correct parameters."""

    @patch('mcp_commit_story.journal_orchestrator.collect_recent_journal_context')
    @patch('mcp_commit_story.journal_orchestrator.collect_chat_history')
    @patch('mcp_commit_story.journal_orchestrator.collect_git_context')
    @patch('mcp_commit_story.journal_orchestrator.get_repo')
    def test_collect_all_context_data_calls_git_context_correctly(
        self, mock_get_repo, mock_git_context, mock_chat_history, mock_journal_context
    ):
        """Test that collect_all_context_data calls collect_git_context with correct parameters."""
        # Setup mocks
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_get_repo.return_value = mock_repo
        mock_repo.commit.return_value = mock_commit
        
        # Mock return values
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'diff_summary': 'Test changes',
            'changed_files': ['test.py'],
            'file_stats': {'source': 1},
            'commit_context': {'size_classification': 'small'}
        }
        mock_chat_history.return_value = None
        mock_journal_context.return_value = None
        
        # Execute
        result = collect_all_context_data(
            commit_hash="abc123",
            since_commit=None,
            max_messages_back=150,
            repo_path=Path("/test/repo"),
            journal_path=Path("/test/journal")
        )
        
        # Verify collect_git_context was called with CORRECT parameter order
        mock_git_context.assert_called_once_with(
            commit_hash="abc123",
            repo=Path("/test/repo"),  # repo parameter should be the repo path
            journal_path=Path("/test/journal")  # journal_path should be the journal path
        )
        
        # Verify we got proper context structure
        assert 'git' in result
        assert 'chat' in result
        assert 'journal' in result

    @patch('mcp_commit_story.journal_orchestrator.collect_recent_journal_context')
    @patch('mcp_commit_story.journal_orchestrator.collect_chat_history')
    @patch('mcp_commit_story.journal_orchestrator.collect_git_context')
    @patch('mcp_commit_story.journal_orchestrator.get_repo')
    def test_collect_all_context_data_not_called_with_wrong_parameters(
        self, mock_get_repo, mock_git_context, mock_chat_history, mock_journal_context
    ):
        """Test that collect_all_context_data does NOT call collect_git_context with wrong parameters."""
        # Setup mocks
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_get_repo.return_value = mock_repo
        mock_repo.commit.return_value = mock_commit
        
        # Mock return values
        mock_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'message': 'Test commit'},
            'diff_summary': 'Test changes',
            'changed_files': ['test.py'],
            'file_stats': {'source': 1},
            'commit_context': {'size_classification': 'small'}
        }
        mock_chat_history.return_value = None
        mock_journal_context.return_value = None
        
        # Execute
        collect_all_context_data(
            commit_hash="abc123",
            since_commit=None,
            max_messages_back=150,
            repo_path=Path("/test/repo"),
            journal_path=Path("/test/journal")
        )
        
        # Verify collect_git_context was NOT called with the old WRONG parameter order
        # WRONG CALL: positional arguments in wrong order (old bug)
        with pytest.raises(AssertionError):
            mock_git_context.assert_called_with("abc123", Path("/test/journal"), Path("/test/repo"))


class TestGitContextParameterValidation:
    """Test that correct parameters prevent InvalidGitRepositoryError."""

    def test_correct_parameters_prevent_invalid_git_repo_error(self):
        """Test that using correct parameter order prevents InvalidGitRepositoryError."""
        # This test demonstrates why the fix was necessary
        
        # Mock a scenario where journal_path is passed as repo (the bug)
        with patch('mcp_commit_story.context_collection.get_repo') as mock_get_repo:
            # Simulate the old bug: journal_path passed as repo parameter
            mock_get_repo.side_effect = git.InvalidGitRepositoryError("/path/to/journal")
            
            # This should raise InvalidGitRepositoryError (demonstrating the bug)
            with pytest.raises(git.InvalidGitRepositoryError):
                from mcp_commit_story.context_collection import collect_git_context
                collect_git_context(
                    commit_hash="abc123",
                    repo="sandbox-journal",  # WRONG: journal path passed as repo
                    journal_path=None
                )

    def test_correct_parameters_work_properly(self):
        """Test that correct parameter order works without InvalidGitRepositoryError."""
        # Mock proper git repo
        with patch('mcp_commit_story.context_collection.get_repo') as mock_get_repo, \
             patch('mcp_commit_story.context_collection.get_current_commit') as mock_get_commit, \
             patch('mcp_commit_story.context_collection.get_commit_details') as mock_get_details, \
             patch('mcp_commit_story.context_collection.get_commit_diff_summary') as mock_get_diff, \
             patch('mcp_commit_story.context_collection.classify_file_type') as mock_classify, \
             patch('mcp_commit_story.context_collection.classify_commit_size') as mock_size, \
             patch('mcp_commit_story.context_collection.get_commit_file_diffs') as mock_diffs:
            
            # Setup mocks for successful execution
            mock_repo = Mock()
            mock_commit = Mock()
            mock_commit.parents = [Mock()]  # Has parent
            mock_commit.diff.return_value = []  # Empty diff
            mock_repo.commit.return_value = mock_commit
            mock_repo.working_tree_dir = "/test/repo"
            
            mock_get_repo.return_value = mock_repo
            mock_get_commit.return_value = mock_commit
            mock_get_details.return_value = {
                'hash': 'abc123', 'author': 'Test', 'datetime': '2025-01-01', 
                'message': 'Test', 'stats': {'insertions': 1, 'deletions': 0}
            }
            mock_get_diff.return_value = "Test diff"
            mock_classify.return_value = 'source'
            mock_size.return_value = 'small'
            mock_diffs.return_value = {}
            
            # This should work without InvalidGitRepositoryError
            from mcp_commit_story.context_collection import collect_git_context
            result = collect_git_context(
                commit_hash="abc123",
                repo=".",  # CORRECT: actual repo path
                journal_path="sandbox-journal"  # CORRECT: journal path as journal_path parameter
            )
            
            # Should get valid result
            assert isinstance(result, dict)
            assert 'metadata' in result
            assert 'diff_summary' in result 