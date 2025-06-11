"""
Unit tests for signal file management functionality.

Tests signal directory creation, file-based signaling mechanism, 
and generic create_tool_signal() function for MCP tools.

Part of subtask 37.2: Implement Signal Directory Management and File Creation
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

# Import the functions we'll be testing (they don't exist yet - TDD approach)
# These will be implemented after the tests are written
try:
    from mcp_commit_story.signal_management import (
        ensure_signal_directory,
        create_signal_file,
        validate_signal_format,
        SignalDirectoryError,
        SignalFileError,
        SignalValidationError
    )
except ImportError:
    # Expected during TDD - functions don't exist yet
    pass


class TestEnsureSignalDirectory:
    """Test signal directory creation and validation."""
    
    def test_successful_directory_creation(self, tmp_path):
        """Test successful creation of signal directory."""
        signal_path = tmp_path / ".mcp-commit-story" / "signals"
        
        # Directory should not exist initially
        assert not signal_path.exists()
        
        # Function should create directory and return path
        result_path = ensure_signal_directory(str(tmp_path))
        
        assert signal_path.exists()
        assert signal_path.is_dir()
        assert str(signal_path) == result_path
    
    def test_existing_directory_validation(self, tmp_path):
        """Test validation when signal directory already exists."""
        signal_path = tmp_path / ".mcp-commit-story" / "signals"
        signal_path.mkdir(parents=True)
        
        # Function should validate existing directory
        result_path = ensure_signal_directory(str(tmp_path))
        
        assert signal_path.exists()
        assert str(signal_path) == result_path
    
    def test_permission_error_graceful_degradation(self, tmp_path):
        """Test graceful handling of permission errors."""
        # Make parent directory read-only to simulate permission error
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(SignalDirectoryError) as exc_info:
                ensure_signal_directory(str(tmp_path))
            
            assert "Permission denied" in str(exc_info.value)
            assert exc_info.value.graceful_degradation is True
    
    def test_invalid_repo_path(self):
        """Test handling of invalid repository path."""
        with pytest.raises(SignalDirectoryError) as exc_info:
            ensure_signal_directory("/nonexistent/path")
        
        assert "Invalid repository path" in str(exc_info.value)
    
    def test_nested_directory_creation(self, tmp_path):
        """Test creation of nested signal directory structure."""
        # Test that both .mcp-commit-story and signals directories are created
        result_path = ensure_signal_directory(str(tmp_path))
        
        mcp_dir = tmp_path / ".mcp-commit-story"
        signal_dir = mcp_dir / "signals"
        
        assert mcp_dir.exists()
        assert signal_dir.exists()
        assert str(signal_dir) == result_path


class TestCreateSignalFile:
    """Test generic signal file generation."""
    
    @pytest.fixture
    def signal_directory(self, tmp_path):
        """Create a temporary signal directory for testing."""
        signal_dir = tmp_path / ".mcp-commit-story" / "signals"
        signal_dir.mkdir(parents=True)
        return str(signal_dir)
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample commit metadata for testing."""
        return {
            "hash": "abc123def456",
            "author": "Test Author",
            "email": "test@example.com",
            "date": "2025-06-11T07:36:12-04:00",
            "message": "Test commit message",
            "files_changed": ["test.py", "README.md"],
            "insertions": 15,
            "deletions": 3
        }
    
    def test_successful_signal_file_creation(self, signal_directory, sample_metadata):
        """Test successful creation of signal file with proper format."""
        tool_name = "journal_new_entry"
        parameters = {"date": "2025-06-11", "auto_summary": True}
        
        file_path = create_signal_file(
            signal_directory=signal_directory,
            tool_name=tool_name,
            parameters=parameters,
            commit_metadata=sample_metadata
        )
        
        # Verify file was created
        assert os.path.exists(file_path)
        
        # Verify file content
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        assert signal_data["tool"] == tool_name
        assert signal_data["params"] == parameters
        assert signal_data["metadata"] == sample_metadata
        assert "created_at" in signal_data
        assert "signal_id" in signal_data
    
    def test_unique_file_naming(self, signal_directory, sample_metadata):
        """Test that signal files have unique names for proper ordering."""
        import time
        
        # Create multiple signal files with small delays to ensure unique timestamps
        file_paths = []
        for i in range(3):
            file_path = create_signal_file(
                signal_directory=signal_directory,
                tool_name="test_tool",
                parameters={"iteration": i},
                commit_metadata=sample_metadata
            )
            file_paths.append(file_path)
            # Small delay to ensure microsecond differences in timestamp
            time.sleep(0.001)
        
        # Verify all files have unique names
        assert len(set(file_paths)) == 3
        
        # Verify files are ordered by creation time (filename should be sortable)
        filenames = [os.path.basename(path) for path in file_paths]
        assert filenames == sorted(filenames)
    
    def test_json_format_validation(self, signal_directory, sample_metadata):
        """Test that signal files contain valid JSON in expected format."""
        file_path = create_signal_file(
            signal_directory=signal_directory,
            tool_name="generate_daily_summary",
            parameters={"date": "2025-06-11"},
            commit_metadata=sample_metadata
        )
        
        # Verify JSON is valid and parseable
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        # Verify required fields are present
        required_fields = ["tool", "params", "metadata", "created_at", "signal_id"]
        for field in required_fields:
            assert field in signal_data
        
        # Verify field types
        assert isinstance(signal_data["tool"], str)
        assert isinstance(signal_data["params"], dict)
        assert isinstance(signal_data["metadata"], dict)
        assert isinstance(signal_data["created_at"], str)
        assert isinstance(signal_data["signal_id"], str)
    
    def test_disk_space_error_handling(self, signal_directory, sample_metadata):
        """Test graceful handling of disk space errors."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = OSError("No space left on device")
            
            with pytest.raises(SignalFileError) as exc_info:
                create_signal_file(
                    signal_directory=signal_directory,
                    tool_name="test_tool",
                    parameters={},
                    commit_metadata=sample_metadata
                )
            
            assert "No space left on device" in str(exc_info.value)
            assert exc_info.value.graceful_degradation is True
    
    def test_permission_error_handling(self, signal_directory, sample_metadata):
        """Test graceful handling of permission errors during file creation."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(SignalFileError) as exc_info:
                create_signal_file(
                    signal_directory=signal_directory,
                    tool_name="test_tool",
                    parameters={},
                    commit_metadata=sample_metadata
                )
            
            assert "Permission denied" in str(exc_info.value)
            assert exc_info.value.graceful_degradation is True
    
    def test_generic_tool_support(self, signal_directory, sample_metadata):
        """Test that function works with any MCP tool name."""
        tools_to_test = [
            "journal_new_entry",
            "generate_daily_summary", 
            "generate_weekly_summary",
            "custom_tool_name",
            "another.tool.with.dots"
        ]
        
        for tool_name in tools_to_test:
            file_path = create_signal_file(
                signal_directory=signal_directory,
                tool_name=tool_name,
                parameters={"test": True},
                commit_metadata=sample_metadata
            )
            
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            
            assert signal_data["tool"] == tool_name
    
    def test_empty_parameters_handling(self, signal_directory, sample_metadata):
        """Test handling of empty parameters."""
        file_path = create_signal_file(
            signal_directory=signal_directory,
            tool_name="test_tool",
            parameters={},
            commit_metadata=sample_metadata
        )
        
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        assert signal_data["params"] == {}
        assert "created_at" in signal_data
    
    def test_large_metadata_handling(self, signal_directory):
        """Test handling of large commit metadata."""
        large_metadata = {
            "hash": "abc123def456",
            "message": "A" * 10000,  # Large commit message
            "files_changed": [f"file_{i}.py" for i in range(1000)],  # Many files
            "diff": "+" * 50000  # Large diff content
        }
        
        file_path = create_signal_file(
            signal_directory=signal_directory,
            tool_name="test_tool",
            parameters={"test": True},
            commit_metadata=large_metadata
        )
        
        # File should be created successfully
        assert os.path.exists(file_path)
        
        # Content should be preserved
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        assert len(signal_data["metadata"]["message"]) == 10000
        assert len(signal_data["metadata"]["files_changed"]) == 1000


class TestValidateSignalFormat:
    """Test JSON structure validation for signal files."""
    
    def test_valid_signal_format(self):
        """Test validation of correctly formatted signal."""
        valid_signal = {
            "tool": "journal_new_entry",
            "params": {"date": "2025-06-11"},
            "metadata": {"hash": "abc123", "author": "Test"},
            "created_at": "2025-06-11T07:36:12Z",
            "signal_id": "signal_123"
        }
        
        # Should not raise any exception
        result = validate_signal_format(valid_signal)
        assert result is True
    
    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        invalid_signals = [
            # Missing tool
            {
                "params": {},
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            },
            # Missing params
            {
                "tool": "test_tool",
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            },
            # Missing metadata
            {
                "tool": "test_tool",
                "params": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            },
            # Missing created_at
            {
                "tool": "test_tool",
                "params": {},
                "metadata": {},
                "signal_id": "signal_123"
            },
            # Missing signal_id
            {
                "tool": "test_tool",
                "params": {},
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z"
            }
        ]
        
        for invalid_signal in invalid_signals:
            with pytest.raises(SignalValidationError):
                validate_signal_format(invalid_signal)
    
    def test_invalid_field_types(self):
        """Test validation fails when field types are incorrect."""
        invalid_signals = [
            # tool should be string
            {
                "tool": 123,
                "params": {},
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            },
            # params should be dict
            {
                "tool": "test_tool",
                "params": "invalid",
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            },
            # metadata should be dict
            {
                "tool": "test_tool",
                "params": {},
                "metadata": "invalid",
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            },
            # created_at should be string
            {
                "tool": "test_tool", 
                "params": {},
                "metadata": {},
                "created_at": 123,
                "signal_id": "signal_123"
            },
            # signal_id should be string
            {
                "tool": "test_tool",
                "params": {},
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": 123
            }
        ]
        
        for invalid_signal in invalid_signals:
            with pytest.raises(SignalValidationError):
                validate_signal_format(invalid_signal)
    
    def test_empty_string_validation(self):
        """Test validation handles empty strings appropriately."""
        # Empty tool name should be invalid
        with pytest.raises(SignalValidationError):
            validate_signal_format({
                "tool": "",
                "params": {},
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": "signal_123"
            })
        
        # Empty signal_id should be invalid
        with pytest.raises(SignalValidationError):
            validate_signal_format({
                "tool": "test_tool",
                "params": {},
                "metadata": {},
                "created_at": "2025-06-11T07:36:12Z",
                "signal_id": ""
            })
    
    def test_additional_fields_allowed(self):
        """Test that additional fields are allowed in signal format."""
        signal_with_extra_fields = {
            "tool": "journal_new_entry",
            "params": {"date": "2025-06-11"},
            "metadata": {"hash": "abc123"},
            "created_at": "2025-06-11T07:36:12Z",
            "signal_id": "signal_123",
            "extra_field": "allowed",
            "version": "1.0"
        }
        
        # Should not raise any exception
        result = validate_signal_format(signal_with_extra_fields)
        assert result is True
    
    def test_non_dict_input(self):
        """Test validation fails for non-dict input."""
        invalid_inputs = [
            "string",
            123,
            [],
            None,
            True
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(SignalValidationError):
                validate_signal_format(invalid_input)


class TestSignalFileManagementIntegration:
    """Integration tests for signal file management workflow."""
    
    def test_complete_workflow(self, tmp_path):
        """Test complete workflow from directory creation to signal validation."""
        # 1. Ensure signal directory
        signal_dir = ensure_signal_directory(str(tmp_path))
        assert os.path.exists(signal_dir)
        
        # 2. Create signal file
        metadata = {
            "hash": "abc123",
            "author": "Test Author",
            "message": "Test commit"
        }
        
        file_path = create_signal_file(
            signal_directory=signal_dir,
            tool_name="journal_new_entry",
            parameters={"test": True},
            commit_metadata=metadata
        )
        
        # 3. Validate signal format
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        result = validate_signal_format(signal_data)
        assert result is True
    
    def test_concurrent_signal_creation(self, tmp_path):
        """Test thread safety for concurrent signal creation."""
        import threading
        import time
        
        signal_dir = ensure_signal_directory(str(tmp_path))
        
        def create_signal(thread_id):
            """Create a signal in a separate thread."""
            return create_signal_file(
                signal_directory=signal_dir,
                tool_name=f"tool_{thread_id}",
                parameters={"thread_id": thread_id},
                commit_metadata={"hash": f"commit_{thread_id}"}
            )
        
        # Create signals concurrently
        threads = []
        results = {}
        
        for i in range(5):
            def worker(tid=i):
                results[tid] = create_signal(tid)
            
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all signals were created with unique names
        assert len(results) == 5
        file_paths = list(results.values())
        assert len(set(file_paths)) == 5  # All unique
        
        # Verify all files exist and contain valid data
        for file_path in file_paths:
            assert os.path.exists(file_path)
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            assert validate_signal_format(signal_data) is True


class TestSignalManagementErrors:
    """Test custom exception classes for signal management."""
    
    def test_signal_directory_error(self):
        """Test SignalDirectoryError exception."""
        error = SignalDirectoryError("Test error", graceful_degradation=True)
        assert str(error) == "Test error"
        assert error.graceful_degradation is True
    
    def test_signal_file_error(self):
        """Test SignalFileError exception."""
        error = SignalFileError("Test error", graceful_degradation=True)
        assert str(error) == "Test error"
        assert error.graceful_degradation is True
    
    def test_signal_validation_error(self):
        """Test SignalValidationError exception."""
        error = SignalValidationError("Test error")
        assert str(error) == "Test error"


if __name__ == "__main__":
    pytest.main([__file__]) 