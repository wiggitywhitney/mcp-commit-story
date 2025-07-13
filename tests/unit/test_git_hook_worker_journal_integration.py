"""
Test git_hook_worker journal integration functionality.

This module tests the direct journal generation wrapper that replaces signal-based journal creation
in git_hook_worker.py.
"""

import pytest
from unittest.mock import patch, MagicMock
from git import InvalidGitRepositoryError

from mcp_commit_story.git_hook_worker import generate_journal_entry_safe


class TestGenerateJournalEntrySafe:
    """Test the generate_journal_entry_safe wrapper function."""

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.generate_journal_entry')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_successful_generation(self, mock_log, mock_get_repo, mock_get_commit, 
                                   mock_load_config, mock_generate):
        """Test successful journal entry generation."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = 'test123'
        mock_config = {'journal': {'path': '/tmp/journal'}}
        mock_journal_entry = MagicMock()
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = mock_config
        mock_generate.return_value = mock_journal_entry
        
        # Call the function
        result = generate_journal_entry_safe('/test/repo')
        
        # Verify dependencies were called correctly
        mock_get_repo.assert_called_once_with('/test/repo')
        mock_get_commit.assert_called_once_with(mock_repo)
        mock_load_config.assert_called_once()
        mock_generate.assert_called_once_with(mock_commit, mock_config)
        
        # Verify result
        assert result is True
        
        # Verify success logging
        mock_log.assert_called_with(
            f"Journal entry generated successfully for commit {mock_commit.hexsha}", 
            "info", 
            '/test/repo'
        )

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

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.generate_journal_entry')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_journal_generation_failure(self, mock_log, mock_get_repo, mock_get_commit, 
                                        mock_load_config, mock_generate):
        """Test handling of journal generation failure."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = 'test456'
        mock_config = {'journal': {'path': '/tmp/journal'}}
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = mock_config
        
        # Configure journal generation to fail
        mock_generate.side_effect = Exception('Journal generation error')
        
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

    @patch('mcp_commit_story.git_hook_worker.journal_workflow.generate_journal_entry')
    @patch('mcp_commit_story.git_hook_worker.config.load_config')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.signal_creation_telemetry')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_telemetry_success_recording(self, mock_log, mock_telemetry, mock_get_repo, 
                                         mock_get_commit, mock_load_config, mock_generate):
        """Test that telemetry is recorded for successful generation."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = 'test789'
        mock_config = {'journal': {'path': '/tmp/journal'}}
        mock_journal_entry = MagicMock()
        
        mock_get_repo.return_value = mock_repo
        mock_get_commit.return_value = mock_commit
        mock_load_config.return_value = mock_config
        mock_generate.return_value = mock_journal_entry
        
        # Call the function
        result = generate_journal_entry_safe('/test/repo')
        
        # Verify telemetry was recorded
        mock_telemetry.assert_called_once_with(
            "journal_generation_direct", 
            success=True
        )
        
        # Verify result
        assert result is True

    @patch('mcp_commit_story.git_hook_worker.git_utils.get_repo')
    @patch('mcp_commit_story.git_hook_worker.signal_creation_telemetry')
    @patch('mcp_commit_story.git_hook_worker.log_hook_activity')
    def test_telemetry_failure_recording(self, mock_log, mock_telemetry, mock_get_repo):
        """Test that telemetry is recorded for failed generation."""
        # Configure mock to raise InvalidGitRepositoryError
        mock_get_repo.side_effect = InvalidGitRepositoryError('Not a git repo')
        
        # Call the function
        result = generate_journal_entry_safe('/invalid/repo')
        
        # Verify telemetry was recorded with error
        mock_telemetry.assert_called_once_with(
            "journal_generation_direct", 
            success=False, 
            error_type="git_repo_detection_failed"
        )
        
        # Verify result
        assert result is False 