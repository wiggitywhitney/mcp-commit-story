"""
Test signal replacement in git_hook_worker for direct journal generation.

This module tests that the journal entry signal creation is replaced with direct calls
to generate_journal_entry_safe() while preserving daily/period summary signals.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import sys
import os

# Add the src directory to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp_commit_story import git_hook_worker


class TestSignalReplacement:
    """Test replacement of signal creation with direct journal calls."""

    @patch('os.path.exists')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('sys.exit')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.create_tool_signal_safe')  
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    @patch('sys.argv', ['git_hook_worker.py', '/fake/repo'])
    def test_journal_signal_replaced_with_direct_call(
        self, 
        mock_log_hook, 
        mock_daily_check, 
        mock_period_check, 
        mock_generate_journal,
        mock_signal_create,
        mock_extract_metadata,
        mock_exit,
        mock_setup_logging,
        mock_path_exists
    ):
        """Test that journal entry signal is replaced with direct generate_journal_entry_safe() call."""
        # Setup mocks
        mock_path_exists.return_value = True  # Simulate we're in a git repo
        mock_setup_logging.return_value = None  # No-op for logging setup
        mock_daily_check.return_value = None  # No daily summary needed
        mock_period_check.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        mock_extract_metadata.return_value = {'commit_hash': 'abc123', 'author': 'test'}
        mock_generate_journal.return_value = True  # Journal generation succeeds
        mock_signal_create.return_value = "/path/to/signal.json"
        
        # Call main function
        git_hook_worker.main()
        
        # Verify generate_journal_entry_safe was called instead of journal signal
        mock_generate_journal.assert_called_once_with('/fake/repo')
        
        # Verify no journal_new_entry signal was created
        journal_signal_calls = [call for call in mock_signal_create.call_args_list 
                               if 'journal_new_entry' in str(call)]
        assert len(journal_signal_calls) == 0, "journal_new_entry signal should not be created"
        
        # Verify appropriate logging
        log_calls = mock_log_hook.call_args_list
        direct_journal_logs = [call for call in log_calls if 'journal' in str(call).lower()]
        assert len(direct_journal_logs) > 0, "Should log journal generation activity"

    @patch('os.path.exists')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('sys.exit')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.create_tool_signal_safe')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    @patch('sys.argv', ['git_hook_worker.py', '/fake/repo'])
    def test_daily_summary_direct_generation_replaces_signals(
        self, 
        mock_log_hook, 
        mock_generate_standalone,
        mock_daily_check, 
        mock_period_check, 
        mock_generate_journal,
        mock_signal_create,
        mock_extract_metadata,
        mock_exit,
        mock_setup_logging,
        mock_path_exists
    ):
        """Test that daily summary generation is done directly instead of via signals."""
        # Setup mocks - daily summary needed
        mock_path_exists.return_value = True  # Simulate we're in a git repo
        mock_setup_logging.return_value = None  # No-op for logging setup
        mock_daily_check.return_value = "2024-01-15"  # Daily summary needed
        mock_period_check.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        mock_extract_metadata.return_value = {'commit_hash': 'abc123', 'author': 'test'}
        mock_generate_journal.return_value = True
        mock_signal_create.return_value = "/path/to/signal.json"
        mock_generate_standalone.return_value = {'date': '2024-01-15', 'summary': 'Test summary'}
        
        # Call main function
        git_hook_worker.main()
        
        # Verify daily summary was generated directly, not via signal
        mock_generate_standalone.assert_called_once_with("2024-01-15")
        
        # Verify NO daily summary signal was created
        daily_signal_calls = [call for call in mock_signal_create.call_args_list 
                             if 'generate_daily_summary' in str(call)]
        assert len(daily_signal_calls) == 0, "generate_daily_summary signal should NOT be created"
        
        # Verify direct journal call was made
        mock_generate_journal.assert_called_once_with('/fake/repo')

    @patch('os.path.exists')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('sys.exit')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.create_tool_signal_safe')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    @patch('sys.argv', ['git_hook_worker.py', '/fake/repo'])
    def test_period_summary_signals_preserved(
        self, 
        mock_log_hook, 
        mock_daily_check, 
        mock_period_check, 
        mock_generate_journal,
        mock_signal_create,
        mock_extract_metadata,
        mock_exit,
        mock_setup_logging,
        mock_path_exists
    ):
        """Test that period summary signals are preserved."""
        # Setup mocks - period summaries needed
        mock_path_exists.return_value = True  # Simulate we're in a git repo
        mock_setup_logging.return_value = None  # No-op for logging setup
        mock_daily_check.return_value = "2024-01-15"
        mock_period_check.return_value = {
            'weekly': True, 'monthly': True, 'quarterly': False, 'yearly': False
        }
        mock_extract_metadata.return_value = {'commit_hash': 'abc123', 'author': 'test'}
        mock_generate_journal.return_value = True
        mock_signal_create.return_value = "/path/to/signal.json"
        
        # Call main function
        git_hook_worker.main()
        
        # Verify period summary signals were created
        weekly_calls = [call for call in mock_signal_create.call_args_list 
                       if 'generate_weekly_summary' in str(call)]
        monthly_calls = [call for call in mock_signal_create.call_args_list 
                        if 'generate_monthly_summary' in str(call)]
        
        assert len(weekly_calls) == 1, "generate_weekly_summary signal should be created"
        assert len(monthly_calls) == 1, "generate_monthly_summary signal should be created"
        
        # Verify direct journal call was made
        mock_generate_journal.assert_called_once_with('/fake/repo')

    @patch('os.path.exists')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('sys.exit')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.create_tool_signal_safe')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    @patch('sys.argv', ['git_hook_worker.py', '/fake/repo'])
    def test_error_handling_preserved_when_journal_fails(
        self, 
        mock_log_hook, 
        mock_daily_check, 
        mock_period_check, 
        mock_generate_journal,
        mock_signal_create,
        mock_extract_metadata,
        mock_exit,
        mock_setup_logging,
        mock_path_exists
    ):
        """Test that error handling is preserved when direct journal generation fails."""
        # Setup mocks
        mock_path_exists.return_value = True  # Simulate we're in a git repo
        mock_setup_logging.return_value = None  # No-op for logging setup
        mock_daily_check.return_value = None
        mock_period_check.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        mock_extract_metadata.return_value = {'commit_hash': 'abc123', 'author': 'test'}
        mock_generate_journal.return_value = False  # Journal generation fails
        mock_signal_create.return_value = "/path/to/signal.json"
        
        # Main should not raise an exception even if journal generation fails
        git_hook_worker.main()  # Should complete without exceptions
        
        # Verify journal generation was attempted
        mock_generate_journal.assert_called_once_with('/fake/repo')

    @patch('os.path.exists')
    @patch('mcp_commit_story.git_hook_worker.setup_hook_logging')
    @patch('sys.exit')
    @patch('mcp_commit_story.git_hook_worker.extract_commit_metadata')
    @patch('mcp_commit_story.git_hook_worker.create_tool_signal_safe')
    @patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    @patch('sys.argv', ['git_hook_worker.py', '/fake/repo'])
    def test_no_signal_imports_needed_for_journal(
        self, 
        mock_log_hook, 
        mock_daily_check, 
        mock_period_check, 
        mock_generate_journal,
        mock_signal_create,
        mock_extract_metadata,
        mock_exit,
        mock_setup_logging,
        mock_path_exists
    ):
        """Test that signal creation imports are no longer needed for journal generation."""
        # Setup mocks
        mock_path_exists.return_value = True  # Simulate we're in a git repo
        mock_setup_logging.return_value = None  # No-op for logging setup
        mock_daily_check.return_value = None
        mock_period_check.return_value = {
            'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False
        }
        mock_extract_metadata.return_value = {'commit_hash': 'abc123', 'author': 'test'}
        mock_generate_journal.return_value = True
        mock_signal_create.return_value = "/path/to/signal.json"
        
        # Call main function
        git_hook_worker.main()
        
        # Verify the generate_journal_entry_safe function exists and is callable
        assert hasattr(git_hook_worker, 'generate_journal_entry_safe')
        assert callable(git_hook_worker.generate_journal_entry_safe)
        
        # Verify it was called correctly
        mock_generate_journal.assert_called_once_with('/fake/repo') 