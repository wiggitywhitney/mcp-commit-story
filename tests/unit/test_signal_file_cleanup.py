"""
Test suite for signal file cleanup and maintenance functionality.

This test suite covers the commit-based cleanup approach where signals are cleared
completely with each new commit, ensuring AI only sees current commit signals.
"""

import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY

import pytest


class TestCommitBasedCleanup:
    """Test commit-based signal cleanup (clear all signals)."""

    def test_cleanup_old_signals_removes_all_files(self, tmp_path):
        """Test that cleanup_old_signals removes all signal files (commit-based)."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        # Setup: Create signal directory with multiple files
        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal files with different ages (all should be removed)
        signal_files = []
        for i in range(5):
            signal_file = signal_dir / f"signal_{i}_123456.json"
            signal_file.write_text(f'{{"tool": "journal_new_entry", "params": {{}}, "created_at": "2025-06-11T1{i}:00:00Z"}}')
            signal_files.append(signal_file)

        # Execute: Cleanup (should remove all signals)
        result = cleanup_old_signals(str(signal_dir))

        # Verify: All signal files removed
        for signal_file in signal_files:
            assert not signal_file.exists(), f"Signal file {signal_file.name} should be removed"
        
        assert result["success"] is True
        assert result["files_removed"] == 5
        assert result["files_preserved"] == 0
        assert result["errors"] == 0

    def test_cleanup_old_signals_empty_directory(self, tmp_path):
        """Test cleanup on empty signal directory."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Execute cleanup on empty directory
        result = cleanup_old_signals(str(signal_dir))

        # Verify: Successful with no files processed
        assert result["success"] is True
        assert result["files_removed"] == 0
        assert result["files_preserved"] == 0

    def test_cleanup_old_signals_nonexistent_directory(self, tmp_path):
        """Test cleanup on non-existent directory."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        non_existent_dir = tmp_path / ".mcp-commit-story" / "signals"
        # Don't create the directory

        # Execute cleanup
        result = cleanup_old_signals(str(non_existent_dir))

        # Verify: Success (no directory = already clean)
        assert result["success"] is True
        assert result["files_removed"] == 0

    def test_cleanup_old_signals_safety_validation(self, tmp_path):
        """Test safety validation prevents cleanup of wrong directories."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        # Create wrong directory structure
        wrong_dir = tmp_path / "not-signal-directory"
        wrong_dir.mkdir(parents=True)

        # Execute cleanup (should be rejected by safety validation)
        result = cleanup_old_signals(str(wrong_dir))

        # Verify: Safety validation prevents cleanup
        assert result["success"] is False
        assert "safety validation failed" in result.get("error", "").lower()


class TestInMemoryProcessedTracking:
    """Test in-memory processed signal tracking."""

    def test_mark_and_check_processed_signals(self, tmp_path):
        """Test marking and checking processed signals."""
        from mcp_commit_story.signal_management import mark_signal_processed, is_signal_processed

        signal_path = "/path/to/signal_123456.json"

        # Initially not processed
        assert not is_signal_processed(signal_path)

        # Mark as processed
        mark_signal_processed(signal_path)

        # Should now be processed
        assert is_signal_processed(signal_path)

    def test_remove_processed_signals_by_processing_marker(self, tmp_path):
        """Test removal of signals marked as processed."""
        from mcp_commit_story.signal_management import (
            remove_processed_signals, mark_signal_processed
        )

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal files
        processed_signal = signal_dir / "processed_signal_123456.json"
        processed_signal.write_text('{"tool": "test", "params": {}, "created_at": "2025-06-11T12:00:00Z"}')
        
        unprocessed_signal = signal_dir / "unprocessed_signal_789012.json"
        unprocessed_signal.write_text('{"tool": "test", "params": {}, "created_at": "2025-06-11T12:00:00Z"}')

        # Mark one as processed
        mark_signal_processed(str(processed_signal))

        # Execute removal
        result = remove_processed_signals(str(signal_dir))

        # Verify: Processed signal removed, unprocessed preserved
        assert not processed_signal.exists(), "Processed signal should be removed"
        assert unprocessed_signal.exists(), "Unprocessed signal should be preserved"
        assert result["processed_removed"] == 1
        assert result["unprocessed_preserved"] == 1

    def test_remove_processed_signals_concurrent_processing(self, tmp_path):
        """Test processed signal removal during concurrent processing."""
        from mcp_commit_story.signal_management import (
            remove_processed_signals, mark_signal_processed
        )

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create multiple signal files
        signal_files = []
        for i in range(10):
            signal_file = signal_dir / f"signal_{i}_123456.json"
            signal_file.write_text(f'{{"tool": "test_{i}", "params": {{}}, "created_at": "2025-06-11T12:00:00Z"}}')
            signal_files.append(signal_file)

        # Mark half as processed
        for i in range(0, 10, 2):  # Even indices
            mark_signal_processed(str(signal_files[i]))

        # Execute removal
        result = remove_processed_signals(str(signal_dir))

        # Verify: Correct files removed/preserved
        assert result["processed_removed"] == 5
        assert result["unprocessed_preserved"] == 5


class TestValidateCleanupSafety:
    """Test cleanup safety validation."""

    def test_validate_cleanup_safety_prevents_wrong_directory(self, tmp_path):
        """Test safety validation prevents cleanup of non-signal directories."""
        from mcp_commit_story.signal_management import validate_cleanup_safety

        # Test various wrong directory structures
        wrong_dirs = [
            tmp_path / "random-directory",
            tmp_path / ".mcp-commit-story" / "not-signals",
            tmp_path / "signals",  # Not in .mcp-commit-story
        ]

        for wrong_dir in wrong_dirs:
            wrong_dir.mkdir(parents=True)
            is_safe, reason = validate_cleanup_safety(str(wrong_dir))
            assert not is_safe, f"Directory {wrong_dir} should not be safe for cleanup"
            assert "not a signal directory" in reason.lower()

    def test_validate_cleanup_safety_allows_signal_directories(self, tmp_path):
        """Test safety validation allows legitimate signal directories."""
        from mcp_commit_story.signal_management import validate_cleanup_safety

        # Create proper signal directory
        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Should be safe for cleanup
        is_safe, reason = validate_cleanup_safety(str(signal_dir))
        assert is_safe, f"Proper signal directory should be safe for cleanup: {reason}"


class TestDiskSpaceMonitoring:
    """Test disk space monitoring and triggered cleanup."""

    def test_disk_space_monitoring_triggers_cleanup(self, tmp_path):
        """Test that low disk space triggers signal cleanup."""
        from mcp_commit_story.signal_management import monitor_disk_space_and_cleanup

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal files for cleanup
        for i in range(5):
            signal_file = signal_dir / f"signal_{i}_123456.json"
            signal_file.write_text(f'{{"tool": "test_{i}", "params": {{}}, "created_at": "2025-06-11T10:00:00Z"}}')

        # Set very high minimum space to trigger cleanup (larger than available)
        result = monitor_disk_space_and_cleanup(str(signal_dir), min_free_mb=999999999)

        # Verify: Cleanup was triggered
        assert result["cleanup_triggered"] is True
        assert result["files_cleaned"] == 5  # All signals should be cleaned

    def test_disk_space_monitoring_skips_cleanup_when_sufficient(self, tmp_path):
        """Test that sufficient disk space skips cleanup."""
        from mcp_commit_story.signal_management import monitor_disk_space_and_cleanup

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal file
        signal_file = signal_dir / "signal_123456.json"
        signal_file.write_text('{"tool": "test", "params": {}, "created_at": "2025-06-11T10:00:00Z"}')

        # Use very low minimum space (won't trigger cleanup)
        result = monitor_disk_space_and_cleanup(str(signal_dir), min_free_mb=1)

        # Verify: Cleanup was not triggered
        assert result["cleanup_triggered"] is False
        assert result["files_cleaned"] == 0
        assert signal_file.exists()  # File should still exist


class TestCleanupTelemetry:
    """Test telemetry recording for cleanup operations."""

    @patch('mcp_commit_story.signal_management.get_mcp_metrics')
    def test_cleanup_telemetry_success_metrics(self, mock_get_metrics, tmp_path):
        """Test telemetry recording for successful cleanup operations."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        # Setup mock metrics
        mock_metrics = MagicMock()
        mock_get_metrics.return_value = mock_metrics

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal file
        signal_file = signal_dir / "signal_123456.json"
        signal_file.write_text('{"tool": "test", "params": {}, "created_at": "2025-06-11T10:00:00Z"}')

        # Execute cleanup
        cleanup_old_signals(str(signal_dir))

        # Verify telemetry calls
        mock_metrics.record_counter.assert_any_call("signal_cleanup_started", 1)
        mock_metrics.record_counter.assert_any_call("signal_cleanup_files_removed", 1)
        mock_metrics.record_counter.assert_any_call("signal_cleanup_completed", 1)

    @patch('mcp_commit_story.signal_management.get_mcp_metrics')
    def test_cleanup_telemetry_error_metrics(self, mock_get_metrics, tmp_path):
        """Test telemetry recording for cleanup errors."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        # Setup mock metrics
        mock_metrics = MagicMock()
        mock_get_metrics.return_value = mock_metrics

        # Use non-signal directory to trigger safety rejection
        wrong_dir = tmp_path / "wrong-directory"
        wrong_dir.mkdir(parents=True)

        # Execute cleanup (should be rejected by safety validation)
        result = cleanup_old_signals(str(wrong_dir))

        # Verify error telemetry
        assert result["success"] is False
        mock_metrics.record_counter.assert_any_call("signal_cleanup_safety_rejected", 1)


class TestConcurrentCleanupOperations:
    """Test cleanup operations under concurrent access."""

    def test_concurrent_cleanup_thread_safety(self, tmp_path):
        """Test cleanup operations are thread-safe."""
        from mcp_commit_story.signal_management import cleanup_old_signals

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal files
        for i in range(20):
            signal_file = signal_dir / f"signal_{i}_123456.json"
            signal_file.write_text(f'{{"tool": "test_{i}", "params": {{}}, "created_at": "2025-06-11T10:00:00Z"}}')

        cleanup_results = []
        errors = []

        def run_cleanup():
            try:
                result = cleanup_old_signals(str(signal_dir))
                cleanup_results.append(result)
            except Exception as e:
                errors.append(str(e))

        # Start multiple cleanup threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_cleanup)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify: All operations completed without errors
        assert len(errors) == 0, f"Concurrent cleanup should be safe: {errors}"
        assert len(cleanup_results) == 3, "All cleanup operations should complete"

        # Verify: All files are cleaned up
        remaining_files = list(signal_dir.glob("*.json"))
        assert len(remaining_files) == 0, "All signal files should be cleaned up"

    def test_cleanup_during_signal_creation(self, tmp_path):
        """Test cleanup operation during concurrent signal creation."""
        from mcp_commit_story.signal_management import cleanup_old_signals, create_signal_file

        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create some initial signals
        for i in range(3):
            signal_file = signal_dir / f"initial_signal_{i}_123456.json"
            signal_file.write_text(f'{{"tool": "test_{i}", "params": {{}}, "created_at": "2025-06-11T10:00:00Z"}}')

        results = {"cleanup": None, "creation": []}
        errors = []

        def run_cleanup():
            try:
                time.sleep(0.1)  # Let signal creation start first
                result = cleanup_old_signals(str(signal_dir))
                results["cleanup"] = result
            except Exception as e:
                errors.append(f"Cleanup error: {e}")

        def create_signals():
            try:
                for i in range(3):
                    commit_metadata = {
                        "hash": f"abcdef{i:06d}",
                        "author": "Test User",
                        "date": "2025-06-11T12:00:00Z",
                        "message": f"Test commit {i}"
                    }
                    signal_path = create_signal_file(
                        str(signal_dir),
                        "journal_new_entry",
                        {},
                        commit_metadata
                    )
                    results["creation"].append(signal_path)
                    time.sleep(0.05)  # Small delay between creations
            except Exception as e:
                errors.append(f"Signal creation error: {e}")

        # Start concurrent operations
        cleanup_thread = threading.Thread(target=run_cleanup)
        creation_thread = threading.Thread(target=create_signals)

        creation_thread.start()
        cleanup_thread.start()

        creation_thread.join()
        cleanup_thread.join()

        # Verify: Both operations completed successfully
        assert len(errors) == 0, f"Concurrent operations should be safe: {errors}"
        assert results["cleanup"] is not None, "Cleanup should complete"
        assert len(results["creation"]) == 3, "Signal creation should complete"

        # Note: In commit-based cleanup, new signals created after cleanup starts
        # may or may not survive depending on timing. This is acceptable since
        # the next commit will clear them anyway.


class TestCommitBasedCleanupMain:
    """Test main commit-based cleanup functions."""

    def test_cleanup_signals_for_new_commit(self, tmp_path):
        """Test main cleanup function for new commits."""
        from mcp_commit_story.signal_management import cleanup_signals_for_new_commit

        # Create fake git repo structure
        repo_path = tmp_path
        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal files
        for i in range(5):
            signal_file = signal_dir / f"signal_{i}_123456.json"
            signal_file.write_text(f'{{"tool": "test_{i}", "params": {{}}, "created_at": "2025-06-11T10:00:00Z"}}')

        # Execute commit-based cleanup
        result = cleanup_signals_for_new_commit(str(repo_path))

        # Verify: All previous signals cleared
        assert result["success"] is True
        assert result["previous_signals_cleared"] == 5

        # Verify: Signal directory is empty
        remaining_files = list(signal_dir.glob("*.json"))
        assert len(remaining_files) == 0

    def test_cleanup_signals_post_commit_legacy(self, tmp_path):
        """Test legacy cleanup function still works."""
        from mcp_commit_story.signal_management import cleanup_signals_post_commit

        # Create fake git repo structure
        repo_path = tmp_path
        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)

        # Create signal file
        signal_file = signal_dir / "signal_123456.json"
        signal_file.write_text('{"tool": "test", "params": {}, "created_at": "2025-06-11T10:00:00Z"}')

        # Execute legacy cleanup (should work same as new function)
        result = cleanup_signals_post_commit(str(repo_path))

        # Verify: Works like new function
        assert result["success"] is True
        assert result["previous_signals_cleared"] == 1


if __name__ == "__main__":
    pytest.main([__file__]) 