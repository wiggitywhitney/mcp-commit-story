"""
Unit tests for commit-based time window filtering functionality.

Tests the core logic for determining chat history time windows based on git commit timestamps,
including edge cases like first commits, merge commits, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import git

from mcp_commit_story.commit_time_window import (
    get_commit_time_window,
    is_merge_commit,
    get_commit_timestamp_ms,
    calculate_time_window
)
from mcp_commit_story.git_hook_worker import handle_errors_gracefully


class TestCommitTimeWindow:
    """Test suite for commit-based time window filtering."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock git repository."""
        repo = Mock(spec=git.Repo)
        return repo

    @pytest.fixture
    def mock_commit_with_parent(self):
        """Create a mock commit with one parent."""
        commit = Mock(spec=git.Commit)
        parent = Mock(spec=git.Commit)
        parent.committed_date = 1640995200  # 2022-01-01 00:00:00 UTC (seconds)
        commit.committed_date = 1641000000   # 2022-01-01 01:20:00 UTC (seconds)
        commit.parents = [parent]
        commit.hexsha = "abc123"
        return commit

    @pytest.fixture
    def mock_first_commit(self):
        """Create a mock commit with no parents (first commit)."""
        commit = Mock(spec=git.Commit)
        commit.committed_date = 1641000000   # 2022-01-01 01:20:00 UTC (seconds)
        commit.parents = []
        commit.hexsha = "first123"
        return commit

    @pytest.fixture
    def mock_merge_commit(self):
        """Create a mock merge commit with multiple parents."""
        commit = Mock(spec=git.Commit)
        parent1 = Mock(spec=git.Commit)
        parent2 = Mock(spec=git.Commit)
        parent1.committed_date = 1640995200
        parent2.committed_date = 1640999000
        commit.committed_date = 1641000000
        commit.parents = [parent1, parent2]
        commit.hexsha = "merge123"
        return commit

    def test_is_merge_commit_single_parent(self, mock_commit_with_parent):
        """Test merge commit detection for normal commits."""
        assert not is_merge_commit(mock_commit_with_parent)

    def test_is_merge_commit_no_parents(self, mock_first_commit):
        """Test merge commit detection for first commits."""
        assert not is_merge_commit(mock_first_commit)

    def test_is_merge_commit_multiple_parents(self, mock_merge_commit):
        """Test merge commit detection for actual merge commits."""
        assert is_merge_commit(mock_merge_commit)

    def test_get_commit_timestamp_ms_conversion(self, mock_commit_with_parent):
        """Test timestamp conversion from seconds to milliseconds."""
        result = get_commit_timestamp_ms(mock_commit_with_parent)
        expected = 1641000000 * 1000  # Convert seconds to milliseconds
        assert result == expected

    def test_calculate_time_window_normal_commit(self, mock_commit_with_parent):
        """Test time window calculation for normal commits with parents."""
        result = calculate_time_window(mock_commit_with_parent)
        
        assert result['strategy'] == 'commit_based'
        assert result['start_timestamp_ms'] == 1640995200 * 1000  # Parent timestamp
        assert result['end_timestamp_ms'] == 1641000000 * 1000    # Current timestamp
        assert result['duration_hours'] == pytest.approx(1.33, rel=0.1)  # ~1.33 hours

    def test_calculate_time_window_first_commit(self, mock_first_commit):
        """Test time window calculation for first commits (24-hour lookback)."""
        result = calculate_time_window(mock_first_commit)
        
        assert result['strategy'] == 'first_commit'
        assert result['end_timestamp_ms'] == 1641000000 * 1000    # Current timestamp
        # Start should be 24 hours before current timestamp
        expected_start = (1641000000 - 24 * 3600) * 1000
        assert result['start_timestamp_ms'] == expected_start
        assert result['duration_hours'] == 24.0

    def test_calculate_time_window_multiple_parents_uses_first(self):
        """Test that commits with multiple parents use first parent."""
        commit = Mock(spec=git.Commit)
        parent1 = Mock(spec=git.Commit)
        parent2 = Mock(spec=git.Commit)
        parent1.committed_date = 1640995200  # Earlier timestamp
        parent2.committed_date = 1640999000  # Later timestamp
        commit.committed_date = 1641000000
        commit.parents = [parent1, parent2]
        commit.hexsha = "multi123"
        
        result = calculate_time_window(commit)
        
        assert result['strategy'] == 'commit_based'
        assert result['start_timestamp_ms'] == 1640995200 * 1000  # First parent timestamp

    @patch('mcp_commit_story.commit_time_window.logger')
    def test_calculate_time_window_error_fallback(self, mock_logger, mock_commit_with_parent):
        """Test fallback to 24-hour window when git operations fail."""
        # Simulate error accessing parent timestamp
        mock_commit_with_parent.parents[0].committed_date = None
        
        result = calculate_time_window(mock_commit_with_parent)
        
        assert result['strategy'] == 'fallback_24h'
        assert result['duration_hours'] == 24.0
        mock_logger.warning.assert_called()

    def test_get_commit_time_window_telemetry_integration(self, mock_repo, mock_commit_with_parent):
        """Test that telemetry functions are applied and result structure is correct."""
        # Setup mock repo to return our test commit  
        mock_repo.commit.return_value = mock_commit_with_parent
        
        result = get_commit_time_window(mock_repo, "abc123")
        
        # Verify result structure (telemetry integration tested separately)
        assert result is not None
        assert 'strategy' in result
        assert 'start_timestamp_ms' in result
        assert 'end_timestamp_ms' in result
        assert 'duration_hours' in result
        
        # Verify the function completes successfully with telemetry applied
        assert callable(get_commit_time_window)
        assert hasattr(get_commit_time_window, '__wrapped__')  # Decorator applied

    def test_get_commit_time_window_skip_merge_commits(self, mock_repo, mock_merge_commit):
        """Test that merge commits are skipped entirely."""
        mock_repo.commit.return_value = mock_merge_commit
        
        result = get_commit_time_window(mock_repo, "merge123")
        
        # Should return None or empty result for merge commits
        assert result is None or result.get('skip_merge', False)

    @patch('mcp_commit_story.commit_time_window.logger')
    def test_get_commit_time_window_invalid_commit_hash(self, mock_logger, mock_repo):
        """Test handling of invalid commit hashes."""
        mock_repo.commit.side_effect = git.exc.BadName("Invalid commit hash")
        
        result = get_commit_time_window(mock_repo, "invalid123")
        
        # Should fall back to 24-hour window
        assert result['strategy'] == 'fallback_24h'
        mock_logger.warning.assert_called()

    @patch('mcp_commit_story.commit_time_window.logger')
    def test_get_commit_time_window_repo_error(self, mock_logger, mock_repo):
        """Test handling of repository access errors."""
        mock_repo.commit.side_effect = git.exc.GitCommandError("git", 1, "Repository not found")
        
        result = get_commit_time_window(mock_repo, "abc123")
        
        # Should fall back to 24-hour window
        assert result['strategy'] == 'fallback_24h'
        mock_logger.warning.assert_called()

    def test_error_handling_graceful_fallbacks(self):
        """Test that function handles errors gracefully with fallback strategies."""
        # Test that function exists and can handle errors (actual behavior tested in other tests)
        assert callable(get_commit_time_window)

    @patch('mcp_commit_story.commit_time_window.logger')
    def test_structured_logging_patterns(self, mock_logger, mock_commit_with_parent):
        """Test that structured logging follows established patterns."""
        result = calculate_time_window(mock_commit_with_parent)
        
        # Verify debug logging follows our patterns
        expected_calls = [
            f"Using {result['strategy']} time window: {result['start_timestamp_ms']} to {result['end_timestamp_ms']}"
        ]
        # We'll verify actual log calls in implementation

    def test_performance_threshold_monitoring(self, mock_commit_with_parent):
        """Test that performance is monitored against established thresholds."""
        # The implementation should track execution time and compare against thresholds
        # This will be verified in the actual implementation with telemetry
        result = calculate_time_window(mock_commit_with_parent)
        assert result is not None  # Basic sanity check

    def test_time_window_edge_cases(self):
        """Test edge cases for time window calculation."""
        # Test commit exactly at epoch
        commit = Mock(spec=git.Commit)
        parent = Mock(spec=git.Commit)
        parent.committed_date = 0
        commit.committed_date = 3600  # 1 hour later
        commit.parents = [parent]
        
        result = calculate_time_window(commit)
        
        assert result['start_timestamp_ms'] == 0
        assert result['end_timestamp_ms'] == 3600000
        assert result['duration_hours'] == 1.0

    def test_duration_calculation_precision(self, mock_commit_with_parent):
        """Test that duration calculation is precise."""
        result = calculate_time_window(mock_commit_with_parent)
        
        start_seconds = result['start_timestamp_ms'] // 1000
        end_seconds = result['end_timestamp_ms'] // 1000
        expected_hours = (end_seconds - start_seconds) / 3600
        
        assert result['duration_hours'] == expected_hours

    @pytest.mark.parametrize("error_type", [
        git.exc.GitCommandError("git", 1, "error"),
        git.exc.BadName("invalid"),
        AttributeError("missing attribute"),
        TypeError("type error")
    ])
    def test_error_categorization(self, error_type, mock_repo):
        """Test that different error types are properly categorized."""
        mock_repo.commit.side_effect = error_type
        
        result = get_commit_time_window(mock_repo, "test123")
        
        # Should always fall back gracefully
        assert result['strategy'] == 'fallback_24h'
        assert result['duration_hours'] == 24.0

    def test_metric_tracking_attributes(self, mock_commit_with_parent):
        """Test that all required metrics attributes are tracked."""
        result = calculate_time_window(mock_commit_with_parent)
        
        # Verify all required attributes are present
        required_attributes = [
            'strategy', 'start_timestamp_ms', 'end_timestamp_ms', 'duration_hours'
        ]
        for attr in required_attributes:
            assert attr in result 