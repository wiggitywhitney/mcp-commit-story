"""
Test git_hook_worker journal integration functionality.

This module tests the direct journal generation wrapper that replaces signal-based journal creation
in git_hook_worker.py.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from git import InvalidGitRepositoryError

from mcp_commit_story.git_hook_worker import generate_journal_entry_safe


class TestGenerateJournalEntrySafe:
    """Test the generate_journal_entry_safe wrapper function."""

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.handle_journal_entry_creation')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_successful_generation(self, mock_log, mock_get_repo, mock_get_commit, 
                                   mock_load_config, mock_handle_creation):
        """Test successful journal entry generation and saving."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = 'test123'
        mock_config = {'journal': {'path': '/tmp/journal'}}
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = mock_config
        mock_handle_creation.return_value = {
            'success': True,
            'skipped': False,
            'file_path': '/tmp/journal/daily/2025-07-13-journal.md',
            'entry_sections': 4
        }
        
        # Call the function
        result = generate_journal_entry_safe('/test/repo')
        
        # Verify dependencies were called correctly
        mock_get_repo.assert_called_once_with('/test/repo')
        mock_get_commit.assert_called_once_with(mock_repo)
        mock_load_config.assert_called_once()
        mock_handle_creation.assert_called_once_with(mock_commit, mock_config)
        
        # Verify result
        assert result is True
        
                # Verify success logging - should have multiple calls including file path
        assert mock_log.call_count >= 2  # Should log both generation success and file save
        
        # Check that both success and file save messages were logged
        logged_messages = [call[0][0] for call in mock_log.call_args_list]
        assert any("Journal entry generated successfully for commit test123" in msg for msg in logged_messages)
        assert any("Journal entry saved to:" in msg for msg in logged_messages)

    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_git_repo_detection_failure(self, mock_log, mock_get_repo):
        """Test handling of git repository detection failure."""
        # Configure mock to raise InvalidGitRepositoryError
        mock_get_repo.side_effect = InvalidGitRepositoryError('Not a git repo')
        
        # Call the function
        result = generate_journal_entry_safe('/invalid/repo')
        
        # Verify error was logged
        mock_log.assert_called_with(
            "Git repository detection failed: Not a git repo", 
            "error", 
            '/invalid/repo'
        )
        
        # Verify result
        assert result is False

    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_config_loading_failure(self, mock_log, mock_get_repo, mock_get_commit, mock_load_config):
        """Test handling of configuration loading failure."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        
        # Configure config loading to fail
        mock_load_config.side_effect = Exception('Config error')
        
        # Call the function
        result = generate_journal_entry_safe('/test/repo')
        
        # Verify error was logged
        mock_log.assert_called_with(
            "Configuration loading failed: Config error", 
            "error", 
            '/test/repo'
        )
        
        # Verify result
        assert result is False

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.handle_journal_entry_creation')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_journal_generation_failure(self, mock_log, mock_get_repo, mock_get_commit, 
                                        mock_load_config, mock_handle_creation):
        """Test handling of journal generation failure."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = 'test456'
        mock_config = {'journal': {'path': '/tmp/journal'}}
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = mock_config
        
        # Configure journal creation to fail
        mock_handle_creation.return_value = {
            'success': False,
            'error': 'Journal generation error',
            'file_path': None
        }
        
        # Call the function
        result = generate_journal_entry_safe('/test/repo')
        
        # Verify error was logged
        mock_log.assert_called_with(
            "Journal generation failed: Journal generation error", 
            "error", 
            '/test/repo'
        )
        
        # Verify result
        assert result is False

    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_none_repo_path_input(self, mock_log):
        """Test handling of None repo path input."""
        # Call the function with None
        result = generate_journal_entry_safe(None)
        
        # Verify error was logged
        mock_log.assert_called_with(
            "Invalid repo path: None", 
            "error", 
            None
        )
        
        # Verify result
        assert result is False

    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_empty_repo_path_input(self, mock_log):
        """Test handling of empty repo path input."""
        # Call the function with empty string
        result = generate_journal_entry_safe('')
        
        # Verify error was logged
        mock_log.assert_called_with(
            "Invalid repo path: ", 
            "error", 
            ''
        )
        
        # Verify result
        assert result is False

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.handle_journal_entry_creation')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_telemetry_success_recording(self, mock_log, mock_get_repo, 
                                         mock_get_commit, mock_load_config, mock_handle_creation):
        """Test that telemetry is recorded for successful generation."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = 'test789'
        mock_config = {'journal': {'path': '/tmp/journal'}}
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = mock_config
        mock_handle_creation.return_value = {
            'success': True,
            'skipped': False,
            'file_path': '/tmp/journal/daily/2025-07-13-journal.md',
            'entry_sections': 3
        }
        
        # Call the function
        result = generate_journal_entry_safe('/test/repo')
        
        # Verify result
        assert result is True

    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_failure_recording(self, mock_log, mock_get_repo):
        """Test that failure is recorded for failed generation."""
        # Configure mock to raise InvalidGitRepositoryError
        mock_get_repo.side_effect = InvalidGitRepositoryError('Not a git repo')
        
        # Call the function
        result = generate_journal_entry_safe('/invalid/repo')
        
        # Verify result is False
        assert result is False
        
        # Verify error was logged
        mock_log.assert_called_with(
            "Git repository detection failed: Not a git repo",
            "error",
            "/invalid/repo"
        )
        
        # Verify result
        assert result is False 

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.handle_journal_entry_creation')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_journal_entry_generation_and_saving_end_to_end(self, mock_log, mock_get_repo, 
                                                             mock_get_commit, mock_load_config, mock_handle_creation, tmp_path):
        """Test that journal entry generation and saving works end-to-end after bug fix."""
        # Setup mocks for successful generation and saving
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_commit.committed_datetime.strftime.return_value = "2025-07-13"
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = {
            'journal': {'path': str(tmp_path / 'journal')}
        }
        
        # Setup expected journal file path
        expected_file = tmp_path / 'journal' / 'daily' / '2025-07-13-journal.md'
        
        # Mock successful journal creation with file saving
        mock_handle_creation.return_value = {
            'success': True,
            'skipped': False,
            'file_path': str(expected_file),
            'entry_sections': 4
        }
        
        # Create the expected file to simulate actual file creation
        expected_file.parent.mkdir(parents=True, exist_ok=True)
        expected_file.write_text("# Test Journal Entry\n\nTest content")
        
        # Call function
        result = generate_journal_entry_safe(str(tmp_path))
        
        # Should return True (reports success)
        assert result is True
        
        # Should call the complete workflow function
        mock_handle_creation.assert_called_once_with(mock_commit, mock_load_config.return_value)
        
        # FIXED: File should now exist because we're using handle_journal_entry_creation()
        # which does both generation AND saving
        assert expected_file.exists(), f"Journal file should be saved to {expected_file} but wasn't found" 

def test_journal_entry_file_path_is_correct():
    """Test that journal entries are saved to correct path: journal/daily/ not journal/journal/daily/"""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo_path = Path(temp_dir)
        
        # Mock git repository and commit
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.committed_datetime.strftime.return_value = "2025-07-13"
        
        # Mock config with journal path
        mock_config = Mock()
        mock_config.journal_path = str(test_repo_path / "journal")
        
        with patch('mcp_commit_story.git_hook_worker.git_utils.get_repo', return_value=mock_repo), \
             patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit', return_value=mock_commit), \
             patch('mcp_commit_story.git_hook_worker.setup_hook_logging'), \
             patch('mcp_commit_story.git_hook_worker.config.load_config', return_value=mock_config), \
             patch('mcp_commit_story.context_collection.collect_chat_history', return_value=None), \
             patch('mcp_commit_story.context_collection.collect_git_context', return_value={}), \
             patch('mcp_commit_story.context_collection.collect_recent_journal_context', return_value=None), \
             patch('mcp_commit_story.journal_generate.generate_summary_section', return_value="Test summary"), \
             patch('mcp_commit_story.journal_generate.generate_technical_synopsis_section', return_value="Test synopsis"), \
             patch('mcp_commit_story.journal_generate.generate_accomplishments_section', return_value="Test accomplishments"), \
             patch('mcp_commit_story.journal_generate.generate_frustrations_section', return_value="Test frustrations"), \
             patch('mcp_commit_story.journal_generate.generate_tone_mood_section', return_value="Test mood"), \
             patch('mcp_commit_story.journal_generate.generate_discussion_notes_section', return_value="Test notes"), \
             patch('mcp_commit_story.journal_generate.generate_commit_metadata_section', return_value="Test metadata"):
            
            # Call the function - this will use the REAL journal_workflow.handle_journal_entry_creation
            # which includes our fix for the double journal/ path bug
            result = generate_journal_entry_safe(str(test_repo_path))
            
            # Verify success
            assert result is True
            
            # Check that file was saved to CORRECT path: journal/daily/
            expected_correct_path = test_repo_path / "journal" / "daily" / "2025-07-13-journal.md"
            wrong_path = test_repo_path / "journal" / "journal" / "daily" / "2025-07-13-journal.md"
            
            # This test should now PASS because we fixed the path resolution
            assert expected_correct_path.exists(), f"Journal entry should be saved to {expected_correct_path}"
            assert not wrong_path.exists(), f"Journal entry should NOT be saved to {wrong_path}" 


class TestDailySummaryDirectIntegration:
    """Test the direct daily summary generation integration (replacing signal creation)."""

    @patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('mcp_commit_story.git_hook_worker.period_summary_placeholder')
    @patch('sys.exit')
    @patch('sys.argv', ['git_hook_worker.py', '/test/repo'])
    @patch('os.path.exists')
    def test_daily_summary_direct_call_success(self, mock_exists, mock_sys_exit, mock_period_placeholder, 
                                               mock_setup_logging, mock_extract_metadata,
                                               mock_journal_safe, mock_period_triggers,
                                               mock_daily_trigger, mock_generate_standalone):
        """Test git hook worker calls generate_daily_summary_standalone directly instead of creating signals."""
        from mcp_commit_story.git_hook_worker import main
        
        # Mock filesystem checks
        mock_exists.return_value = True  # Repository exists
        
        # Mock trigger functions
        mock_daily_trigger.return_value = "2025-01-15"  # Daily summary needed
        mock_period_triggers.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        
        # Mock successful standalone generation
        mock_generate_standalone.return_value = {
            'date': '2025-01-15',
            'summary': 'Generated summary content'
        }
        
        # Mock other functions
        mock_extract_metadata.return_value = {'hash': 'test123'}
        mock_journal_safe.return_value = True
        
        # Run the main function
        main()
        
        # Verify standalone generation was called instead of signal creation
        mock_generate_standalone.assert_called_once_with("2025-01-15", '/test/repo', {'hash': 'test123'})
        
        # Verify period summary placeholder was not called since no period summaries were triggered
        assert mock_period_placeholder.call_count == 0, "Should not call period summary placeholder when no periods are triggered"
    
    @patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('mcp_commit_story.git_hook_worker.period_summary_placeholder')
    @patch('sys.exit')
    @patch('sys.argv', ['git_hook_worker.py', '/test/repo'])
    @patch('os.path.exists')
    def test_daily_summary_direct_call_failure(self, mock_exists, mock_sys_exit, mock_period_placeholder, 
                                               mock_setup_logging, mock_extract_metadata,
                                               mock_journal_safe, mock_period_triggers,
                                               mock_daily_trigger, mock_generate_standalone):
        """Test git hook worker handles standalone generation failure gracefully."""
        from mcp_commit_story.git_hook_worker import main
        
        # Mock filesystem checks
        mock_exists.return_value = True  # Repository exists
        
        # Mock trigger functions
        mock_daily_trigger.return_value = "2025-01-15"  # Daily summary needed
        mock_period_triggers.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        
        # Mock failed standalone generation
        mock_generate_standalone.side_effect = Exception("AI generation failed")
        
        # Mock other functions
        mock_extract_metadata.return_value = {'hash': 'test123'}
        mock_journal_safe.return_value = True
        
        # Run the main function - should not crash
        main()
        
        # Verify standalone generation was attempted
        mock_generate_standalone.assert_called_once_with("2025-01-15", '/test/repo', {'hash': 'test123'})
        
        # Verify period summary placeholder was not called since no period summaries were triggered
        assert mock_period_placeholder.call_count == 0, "Should not call period summary placeholder when no periods are triggered"
    
    @patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('mcp_commit_story.git_hook_worker.period_summary_placeholder')
    @patch('sys.exit')
    @patch('sys.argv', ['git_hook_worker.py', '/test/repo'])
    @patch('os.path.exists')
    def test_no_daily_summary_trigger_no_call(self, mock_exists, mock_sys_exit, mock_period_placeholder, 
                                              mock_setup_logging, mock_extract_metadata,
                                              mock_journal_safe, mock_period_triggers,
                                              mock_daily_trigger, mock_generate_standalone):
        """Test git hook worker does not call standalone generation when no trigger conditions met."""
        from mcp_commit_story.git_hook_worker import main
        
        # Mock filesystem checks
        mock_exists.return_value = True  # Repository exists
        
        # Mock trigger functions - no daily summary needed
        mock_daily_trigger.return_value = None
        mock_period_triggers.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        
        # Mock other functions
        mock_extract_metadata.return_value = {'hash': 'test123'}
        mock_journal_safe.return_value = True
        
        # Run the main function
        main()
        
        # Verify standalone generation was NOT called
        mock_generate_standalone.assert_not_called()
        
        # Verify period summary placeholder was NOT called since no periods were triggered
        assert mock_period_placeholder.call_count == 0, "Should not call period summary placeholder when no periods are triggered"

    @patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('mcp_commit_story.git_hook_worker.period_summary_placeholder')
    @patch('sys.exit')
    @patch('sys.argv', ['git_hook_worker.py', '/test/repo'])
    @patch('os.path.exists')
    def test_period_summaries_use_placeholder(self, mock_exists, mock_sys_exit, mock_period_placeholder, 
                                               mock_setup_logging, mock_extract_metadata,
                                               mock_journal_safe, mock_period_triggers,
                                               mock_daily_trigger, mock_generate_standalone):
        """Test that period summaries use placeholder function while daily summaries use direct calls."""
        from mcp_commit_story.git_hook_worker import main
        
        # Mock filesystem checks
        mock_exists.return_value = True  # Repository exists
        
        # Mock trigger functions
        mock_daily_trigger.return_value = "2025-01-15"  # Daily summary needed
        mock_period_triggers.return_value = {
            'weekly': True, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        
        # Mock successful standalone generation
        mock_generate_standalone.return_value = {
            'date': '2025-01-15',
            'summary': 'Generated summary content'
        }
        
        # Mock other functions
        mock_extract_metadata.return_value = {'hash': 'test123'}
        mock_journal_safe.return_value = True
        mock_period_placeholder.return_value = True
        
        # Run the main function
        main()
        
        # Verify standalone generation was called for daily summary
        mock_generate_standalone.assert_called_once_with("2025-01-15", '/test/repo', {'hash': 'test123'})
        
        # Verify period summary placeholder was called for weekly summary
        mock_period_placeholder.assert_called_once_with("weekly", "2025-01-15", {'hash': 'test123'}, '/test/repo') 