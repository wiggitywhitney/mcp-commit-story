"""
Test suite for signal file replacement functionality.

Tests for replacing call_mcp_tool() placeholder with generic tool signal creation
using create_tool_signal() while maintaining all existing behavior and 
comprehensive telemetry.

Part of subtask 37.3: Replace call_mcp_tool Placeholder with Generic Tool Signal Creation
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any

import pytest

from mcp_commit_story.signal_management import SignalFileError, SignalDirectoryError


class TestCreateToolSignal:
    """Test the create_tool_signal() function for generic MCP tool signal creation."""
    
    def test_successful_signal_creation_journal_new_entry(self):
        """Test successful signal creation for journal_new_entry tool."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "journal_new_entry"
            parameters = {"repo_path": repo_path}
            commit_metadata = {
                "hash": "abc123def456",
                "author": "Test User <test@example.com>",
                "date": "2025-06-11T12:00:00-04:00",
                "message": "Test commit message",
                "files_changed": ["file1.py", "file2.md"],
                "stats": {"insertions": 10, "deletions": 2}
            }
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            # Verify signal file was created
            assert os.path.exists(signal_file_path)
            
            # Verify signal content
            with open(signal_file_path, 'r') as f:
                signal_data = json.load(f)
            
            assert signal_data["tool"] == tool_name
            assert signal_data["params"] == parameters
            assert signal_data["metadata"] == commit_metadata
            assert "created_at" in signal_data
            assert "signal_id" in signal_data
            
            # Verify timestamp format
            created_at = datetime.fromisoformat(signal_data["created_at"].replace('Z', '+00:00'))
            assert isinstance(created_at, datetime)
    
    def test_successful_signal_creation_generate_daily_summary(self):
        """Test successful signal creation for generate_daily_summary tool."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "generate_daily_summary"
            parameters = {"date": "2025-06-11"}
            commit_metadata = {
                "hash": "xyz789abc123",
                "author": "Another User <another@example.com>",
                "date": "2025-06-11T15:30:00-04:00",
                "message": "Daily summary trigger commit"
            }
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            # Verify signal file created with correct naming convention
            filename = os.path.basename(signal_file_path)
            assert "generate_daily_summary" in filename
            assert "xyz789ab" in filename  # short hash prefix
            assert filename.endswith(".json")
            
            # Verify signal directory structure
            signal_dir = os.path.dirname(signal_file_path)
            assert signal_dir.endswith(".mcp-commit-story/signals")
    
    def test_successful_signal_creation_generate_weekly_summary(self):
        """Test successful signal creation for generate_weekly_summary tool."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "generate_weekly_summary"
            parameters = {"date": "2025-06-08"}
            commit_metadata = {
                "hash": "weekly123",
                "author": "Weekly User <weekly@example.com>",
                "date": "2025-06-08T23:59:59-04:00",
                "message": "End of week commit"
            }
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            # Verify content structure
            with open(signal_file_path, 'r') as f:
                signal_data = json.load(f)
            
            assert signal_data["tool"] == "generate_weekly_summary"
            assert signal_data["params"]["date"] == "2025-06-08"
            assert signal_data["metadata"]["hash"] == "weekly123"
    
    def test_signal_creation_with_empty_parameters(self):
        """Test signal creation handles empty parameters gracefully."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "test_tool"
            parameters = {}
            commit_metadata = {"hash": "empty123", "author": "Empty <empty@test.com>"}
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            with open(signal_file_path, 'r') as f:
                signal_data = json.load(f)
            
            assert signal_data["params"] == {}
            assert signal_data["tool"] == "test_tool"
    
    def test_signal_creation_with_missing_metadata_fields(self):
        """Test signal creation handles missing metadata fields gracefully."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "test_tool"
            parameters = {"param1": "value1"}
            commit_metadata = {"hash": "minimal123"}  # Minimal metadata
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            with open(signal_file_path, 'r') as f:
                signal_data = json.load(f)
            
            assert signal_data["metadata"]["hash"] == "minimal123"
            assert signal_data["tool"] == "test_tool"
    
    def test_signal_file_naming_convention(self):
        """Test that signal files follow the approved naming convention."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "journal_new_entry"
            parameters = {"test": "value"}
            commit_metadata = {"hash": "abcdef123456789"}
            
            # Create multiple signals to test uniqueness
            signal_paths = []
            for i in range(3):
                signal_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
                signal_paths.append(signal_path)
                time.sleep(0.001)  # Small delay to ensure different timestamps
            
            # Verify all files have unique names
            filenames = [os.path.basename(path) for path in signal_paths]
            assert len(set(filenames)) == len(filenames)  # All unique
            
            # Verify naming pattern: {timestamp}_{tool_name}_{hash_prefix}.json
            for filename in filenames:
                parts = filename.replace('.json', '').split('_')
                assert len(parts) >= 3
                assert 'journal' in filename and 'new' in filename and 'entry' in filename
                assert 'abcdef12' in filename  # 8-char hash prefix
    
    def test_concurrent_signal_creation_thread_safety(self):
        """Test that concurrent signal creation is thread-safe."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "concurrent_test"
            
            signal_paths = []
            errors = []
            
            def create_signal(thread_id):
                try:
                    parameters = {"thread_id": thread_id}
                    commit_metadata = {"hash": f"thread{thread_id:03d}"}
                    path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
                    signal_paths.append(path)
                except Exception as e:
                    errors.append(e)
            
            # Create signals concurrently
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_signal, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # Verify no errors and all signals created
            assert len(errors) == 0
            assert len(signal_paths) == 5
            assert len(set(signal_paths)) == 5  # All unique paths


class TestSignalCreationTelemetry:
    """Test the signal_creation_telemetry() function for metrics recording."""
    
    @patch('mcp_commit_story.telemetry.get_mcp_metrics')
    def test_successful_signal_telemetry_recording(self, mock_get_metrics):
        """Test telemetry recording for successful signal creation."""
        from mcp_commit_story.git_hook_worker import signal_creation_telemetry
        
        mock_metrics = MagicMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Test successful signal creation telemetry
        signal_creation_telemetry("journal_new_entry", success=True)
        
        # Verify success metrics recorded
        mock_metrics.record_counter.assert_any_call("signal_creation_success", 1)
        mock_metrics.record_counter.assert_any_call("signal_creation_success_journal_new_entry", 1)
        # record_histogram should not be called without duration_ms parameter
        mock_metrics.record_histogram.assert_not_called()
    
    @patch('mcp_commit_story.telemetry.get_mcp_metrics')
    def test_failed_signal_telemetry_recording(self, mock_get_metrics):
        """Test telemetry recording for failed signal creation."""
        from mcp_commit_story.git_hook_worker import signal_creation_telemetry
        
        mock_metrics = MagicMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Test failed signal creation telemetry
        signal_creation_telemetry("generate_daily_summary", success=False, error_type="permission_error")
        
        # Verify failure metrics recorded
        mock_metrics.record_counter.assert_any_call("signal_creation_failure", 1)
        mock_metrics.record_counter.assert_any_call("signal_creation_failure_generate_daily_summary", 1)
        mock_metrics.record_counter.assert_any_call("signal_creation_error_permission_error", 1)
    
    @patch('mcp_commit_story.telemetry.get_mcp_metrics')
    def test_telemetry_with_performance_metrics(self, mock_get_metrics):
        """Test telemetry recording with performance metrics."""
        from mcp_commit_story.git_hook_worker import signal_creation_telemetry
        
        mock_metrics = MagicMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Test telemetry with timing information
        signal_creation_telemetry("generate_weekly_summary", success=True, duration_ms=150.5)
        
        # Verify performance metrics recorded
        mock_metrics.record_histogram.assert_any_call("signal_creation_duration_ms", 150.5)
        mock_metrics.record_counter.assert_any_call("signal_creation_success", 1)
    
    @patch('mcp_commit_story.telemetry.get_mcp_metrics')
    def test_telemetry_integration_with_existing_pipeline(self, mock_get_metrics):
        """Test telemetry integrates with existing telemetry pipeline."""
        from mcp_commit_story.git_hook_worker import signal_creation_telemetry
        
        mock_metrics = MagicMock()
        mock_get_metrics.return_value = mock_metrics
        
        # Test different tool types with telemetry
        tools = ["journal_new_entry", "generate_daily_summary", "generate_weekly_summary"]
        
        for tool in tools:
            signal_creation_telemetry(tool, success=True)
        
        # Verify all tool types tracked
        assert mock_metrics.record_counter.call_count >= len(tools) * 2  # At least 2 calls per tool
        
        # Verify tool-specific metrics
        for tool in tools:
            mock_metrics.record_counter.assert_any_call(f"signal_creation_success_{tool}", 1)


class TestErrorHandlingAndGracefulDegradation:
    """Test error handling and graceful degradation behavior."""
    
    @patch('mcp_commit_story.signal_management.ensure_signal_directory')
    def test_permission_error_graceful_degradation(self, mock_ensure_dir):
        """Test graceful handling of permission errors."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        # Mock permission error
        mock_ensure_dir.side_effect = SignalDirectoryError("Permission denied", graceful_degradation=True)
        
        tool_name = "test_tool"
        parameters = {"test": "value"}
        commit_metadata = {"hash": "test123"}
        repo_path = "/tmp/test"
        
        # Should not raise exception - graceful degradation
        result = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
        
        # Should return None or handle gracefully
        assert result is None or isinstance(result, str)
    
    @patch('mcp_commit_story.signal_management.create_signal_file')
    def test_disk_space_error_graceful_degradation(self, mock_create_file):
        """Test graceful handling of disk space errors."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        # Mock disk space error
        mock_create_file.side_effect = SignalFileError("No space left on device", graceful_degradation=True)
        
        tool_name = "test_tool"
        parameters = {"test": "value"}
        commit_metadata = {"hash": "test123"}
        repo_path = "/tmp/test"
        
        # Should handle gracefully and not block git operations
        result = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
        assert result is None  # Graceful failure
    
    def test_invalid_parameter_validation(self):
        """Test validation of invalid parameters."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            
            # Test with invalid tool name
            with pytest.raises(ValueError, match="tool_name must be a non-empty string"):
                create_tool_signal("", {"test": "value"}, {"hash": "test"}, repo_path)
            
            # Test with None parameters
            with pytest.raises(ValueError, match="parameters must be a dictionary"):
                create_tool_signal("test_tool", None, {"hash": "test"}, repo_path)
            
            # Test with None metadata
            with pytest.raises(ValueError, match="commit_metadata must be a dictionary"):
                create_tool_signal("test_tool", {"test": "value"}, None, repo_path)
    
    @patch('mcp_commit_story.telemetry.get_mcp_metrics')
    def test_telemetry_failure_does_not_block_operation(self, mock_get_metrics):
        """Test that telemetry failures don't block signal creation."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        # Mock telemetry failure
        mock_get_metrics.side_effect = Exception("Telemetry service unavailable")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "test_tool"
            parameters = {"test": "value"}
            commit_metadata = {"hash": "test123"}
            
            # Should still create signal despite telemetry failure
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            # Verify signal was created
            assert signal_file_path is not None
            assert os.path.exists(signal_file_path)


class TestSignalContentValidation:
    """Test signal content validation and format compliance."""
    
    def test_signal_format_validation_success(self):
        """Test validation of properly formatted signal data."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "test_tool"
            parameters = {"param1": "value1", "param2": {"nested": "value"}}
            commit_metadata = {
                "hash": "abc123",
                "author": "Test <test@example.com>",
                "date": "2025-06-11T12:00:00Z",
                "message": "Test commit"
            }
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            # Verify JSON is valid and properly formatted
            with open(signal_file_path, 'r') as f:
                content = f.read()
                signal_data = json.loads(content)
            
            # Verify required fields
            required_fields = ["tool", "params", "metadata", "created_at", "signal_id"]
            for field in required_fields:
                assert field in signal_data
            
            # Verify JSON is pretty-printed (indented)
            assert "\n" in content  # Multi-line formatting
            assert "  " in content or "\t" in content  # Indentation
    
    def test_signal_content_structure_compliance(self):
        """Test that signal content follows approved structure."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = temp_dir
            tool_name = "journal_new_entry"
            parameters = {"repo_path": repo_path}
            commit_metadata = {
                "hash": "structure123",
                "author": "Structure Test <structure@test.com>",
                "date": "2025-06-11T14:30:00Z",
                "message": "Structure test commit",
                "files_changed": ["test.py"],
                "stats": {"insertions": 5, "deletions": 1}
            }
            
            signal_file_path = create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
            
            with open(signal_file_path, 'r') as f:
                signal_data = json.load(f)
            
            # Verify exact structure from approved design
            expected_structure = {
                "tool": str,
                "params": dict,
                "metadata": dict,
                "created_at": str,
                "signal_id": str
            }
            
            for field, expected_type in expected_structure.items():
                assert field in signal_data
                assert isinstance(signal_data[field], expected_type)
            
            # Verify ISO timestamp format
            created_at = signal_data["created_at"]
            # Should be parseable as ISO format
            datetime.fromisoformat(created_at.replace('Z', '+00:00')) 