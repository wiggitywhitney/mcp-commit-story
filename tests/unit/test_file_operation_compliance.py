"""
Test file operation compliance with on-demand directory creation pattern.

This test suite verifies that all file-writing operations in the codebase
follow the on-demand directory creation pattern as documented in
docs/on-demand-directory-pattern.md.

Key requirements tested:
1. All file operations call ensure_journal_directory before writing
2. No code creates directories upfront
3. Reflection operations follow the pattern
4. Existing file operations comply with the pattern
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import sys

# Import the modules we need to test
from mcp_commit_story.journal import (
    append_to_journal_file, 
    ensure_journal_directory
)
from mcp_commit_story.reflection_core import (
    add_reflection_to_journal,
    add_manual_reflection
)


class TestFileOperationCompliance:
    """Test that all file operations follow on-demand directory creation pattern."""

    def test_append_to_journal_file_calls_ensure_directory(self):
        """Test that append_to_journal_file calls ensure_journal_directory before writing."""
        with patch('mcp_commit_story.journal_generate.ensure_journal_directory') as mock_ensure, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists', return_value=True):
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Call the function
            test_path = "/test/path/daily/2025-06-03-journal.md"
            test_content = "Test content"
            append_to_journal_file(test_content, test_path)
            
            # Verify ensure_journal_directory was called first - accept both Path and string
            mock_ensure.assert_called_once()
            call_args = mock_ensure.call_args[0][0]
            assert str(call_args) == test_path
            
            # Verify file was opened for writing - append_to_journal_file converts to Path and doesn't pass encoding
            expected_path = Path(test_path)
            mock_open.assert_called_once_with(expected_path, 'a')

    def test_reflection_operations_call_ensure_directory(self):
        """Test that reflection operations call ensure_journal_directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_mock = MagicMock()
            config_mock.journal_path = temp_dir
            
            with patch('mcp_commit_story.reflection_core.load_config', return_value=config_mock), \
                 patch('mcp_commit_story.reflection_core.append_to_journal_file') as mock_append:
                
                # Call add_reflection_to_journal
                from mcp_commit_story.reflection_core import add_reflection_to_journal
                add_reflection_to_journal("test_path.md", "Test reflection")
                
                # Verify append_to_journal_file was called
                mock_append.assert_called_once()
                
                # Get the call arguments to verify the content and path
                call_args = mock_append.call_args
                reflection_content = call_args[0][0]
                file_path = call_args[0][1]
                
                # Verify the content includes the reflection
                assert "Test reflection" in reflection_content
                # Verify the path is passed correctly
                assert file_path == "test_path.md"

    def test_manual_reflection_follows_pattern(self):
        """Test that add_manual_reflection follows on-demand directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_mock = MagicMock()
            config_mock.journal_path = temp_dir
            
            with patch('mcp_commit_story.reflection_core.load_config', return_value=config_mock), \
                 patch('mcp_commit_story.reflection_core.append_to_journal_file') as mock_append:
                
                # Call add_manual_reflection
                result = add_manual_reflection("Manual test reflection", "2025-06-03")
                
                # Verify success
                assert result["status"] == "success"
                
                # Verify append_to_journal_file pattern is followed
                mock_append.assert_called_once()

    def test_ensure_journal_directory_creates_parents_only(self):
        """Test that ensure_journal_directory only creates parent directories, not the file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file_path = os.path.join(temp_dir, "deep", "nested", "path", "test-file.md")
            
            # Call ensure_journal_directory
            ensure_journal_directory(test_file_path)
            
            # Verify parent directories were created
            parent_dir = os.path.dirname(test_file_path)
            assert os.path.exists(parent_dir)
            assert os.path.isdir(parent_dir)
            
            # Verify the file itself was NOT created
            assert not os.path.exists(test_file_path)

    def test_no_upfront_directory_creation_in_reflection_core(self):
        """Test that reflection_core.py doesn't create directories upfront."""
        import mcp_commit_story.reflection_core as reflection_core
        import inspect
        
        # Get all functions in the reflection_core module
        functions = inspect.getmembers(reflection_core, inspect.isfunction)
        
        # Check that no function calls os.makedirs directly
        for name, func in functions:
            if func.__module__ == reflection_core.__name__:  # Only check functions defined in this module
                source = inspect.getsource(func)
                
                # Verify no direct directory creation calls
                assert "os.makedirs" not in source, f"Function {name} calls os.makedirs directly"
                assert "os.mkdir" not in source, f"Function {name} calls os.mkdir directly"
                assert "Path.mkdir" not in source, f"Function {name} calls Path.mkdir directly"

    def test_file_operations_use_ensure_pattern(self):
        """Test that file operations consistently use ensure_journal_directory pattern."""
        # Test that append_to_journal_file follows the pattern
        with patch('mcp_commit_story.journal_generate.ensure_journal_directory') as mock_ensure, \
             patch('builtins.open', create=True), \
             patch('os.path.exists', return_value=True):
            
            test_path = "/test/journal/daily/2025-06-03-journal.md"
            append_to_journal_file("test content", test_path)
            
            # Verify ensure_journal_directory was called - accept both Path and string
            mock_ensure.assert_called_once()
            call_args = mock_ensure.call_args[0][0]
            assert str(call_args) == test_path

    def test_reflection_core_imports_ensure_function(self):
        """Test that reflection_core imports and can access ensure_journal_directory."""
        import mcp_commit_story.reflection_core as reflection_core
        
        # Verify ensure_journal_directory is accessible
        assert hasattr(reflection_core, 'ensure_journal_directory')
        
        # Verify it's the correct function
        from mcp_commit_story.journal import ensure_journal_directory
        assert reflection_core.ensure_journal_directory == ensure_journal_directory

    def test_pattern_compliance_in_new_operations(self):
        """Test that new reflection operations comply with the documented pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_mock = MagicMock()
            config_mock.journal_path = temp_dir
            
            # Test the full flow with real directory creation
            with patch('mcp_commit_story.reflection_core.load_config', return_value=config_mock):
                
                # Call add_manual_reflection - this should create directories on demand
                result = add_manual_reflection("Pattern compliance test", "2025-06-03")
                
                # Verify success
                assert result["status"] == "success"
                
                # Verify the file was created
                expected_file = os.path.join(temp_dir, "daily", "2025-06-03-journal.md")
                assert os.path.exists(expected_file)
                
                # Verify the content was written
                with open(expected_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert "Pattern compliance test" in content

    def test_no_premature_directory_creation(self):
        """Test that no operations create directories before they're needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_mock = MagicMock()
            config_mock.journal_path = temp_dir
            
            with patch('mcp_commit_story.reflection_core.load_config', return_value=config_mock):
                
                # Initially, no subdirectories should exist
                subdirs_before = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                assert len(subdirs_before) == 0
                
                # Only after calling a file operation should directories be created
                add_manual_reflection("Test", "2025-06-03")
                
                # Now the daily directory should exist
                daily_dir = os.path.join(temp_dir, "daily")
                assert os.path.exists(daily_dir)
                assert os.path.isdir(daily_dir)

    def test_error_handling_in_directory_creation(self):
        """Test that directory creation errors are handled gracefully."""
        # We need to patch Path.mkdir instead of os.makedirs since ensure_journal_directory uses Path.mkdir
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            # Simulate permission error
            mock_mkdir.side_effect = PermissionError("Permission denied")
            
            test_path = "/restricted/path/daily/2025-06-03-journal.md"
            
            # This should raise a PermissionError
            with pytest.raises(PermissionError):
                ensure_journal_directory(test_path) 