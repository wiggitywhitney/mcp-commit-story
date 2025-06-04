"""Tests for core reflection functionality.

This module tests the core components for manual reflection addition:
- ensure_journal_directory utility (existing)
- format_reflection function  
- add_reflection_to_journal function
"""

import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch, mock_open
import pytest

# Import existing function from journal.py
from src.mcp_commit_story.journal import ensure_journal_directory

# Import new functions from reflection_core (to be created)
from src.mcp_commit_story.reflection_core import (
    format_reflection,
    add_reflection_to_journal
)


class TestEnsureJournalDirectory:
    """Test the ensure_journal_directory utility function."""
    
    def test_ensure_directory_creates_missing_directory(self):
        """Test that ensure_journal_directory creates missing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "sandbox-journal", "daily", "2025-06-02-journal.md")
            
            # Ensure directory doesn't exist initially
            directory = os.path.dirname(journal_path)
            assert not os.path.exists(directory)
            
            # Call function
            ensure_journal_directory(journal_path)
            
            # Verify directory was created
            assert os.path.exists(directory)
    
    def test_ensure_directory_handles_existing_directory(self):
        """Test that ensure_journal_directory works when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure first
            journal_dir = os.path.join(temp_dir, "sandbox-journal", "daily")
            os.makedirs(journal_dir)
            journal_path = os.path.join(journal_dir, "2025-06-02-journal.md")
            
            # Should not raise error when directory exists
            ensure_journal_directory(journal_path)
            
            # Directory should still exist
            assert os.path.exists(journal_dir)
    
    def test_ensure_directory_handles_file_in_current_directory(self):
        """Test that ensure_journal_directory handles files in current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save current directory
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                journal_path = "journal.md"  # No directory component
                
                # Should not raise error
                ensure_journal_directory(journal_path)
            finally:
                # Always restore original directory
                os.chdir(original_cwd)
    
    def test_ensure_directory_creates_nested_directories(self):
        """Test that ensure_journal_directory creates deeply nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "a", "b", "c", "d", "journal.md")
            
            ensure_journal_directory(journal_path)
            
            assert os.path.exists(os.path.dirname(journal_path))


class TestFormatReflection:
    """Test the format_reflection function."""
    
    @patch('src.mcp_commit_story.reflection_core.datetime')
    def test_format_reflection_basic(self, mock_datetime):
        """Test basic reflection formatting with timestamp."""
        # Mock datetime - simulate 3:30 PM
        mock_datetime.now.return_value.strftime.return_value = "3:30 PM"

        reflection_text = "This is a test reflection about my coding progress."

        result = format_reflection(reflection_text)

        expected = "\n\n### 3:30 PM — Reflection\n\nThis is a test reflection about my coding progress."
        assert result == expected
    
    @patch('src.mcp_commit_story.reflection_core.datetime')
    def test_format_reflection_multiline(self, mock_datetime):
        """Test reflection formatting with multiline text."""
        mock_datetime.now.return_value.strftime.return_value = "3:30 PM"

        reflection_text = """This is a multiline reflection.
It spans multiple lines.
And contains various thoughts."""

        result = format_reflection(reflection_text)

        expected = """\n\n### 3:30 PM — Reflection\n\nThis is a multiline reflection.
It spans multiple lines.
And contains various thoughts."""
        assert result == expected
    
    @patch('src.mcp_commit_story.reflection_core.datetime')
    def test_format_reflection_empty_text(self, mock_datetime):
        """Test reflection formatting with empty text."""
        mock_datetime.now.return_value.strftime.return_value = "3:30 PM"

        result = format_reflection("")

        expected = "\n\n### 3:30 PM — Reflection\n\n"
        assert result == expected
    
    @patch('src.mcp_commit_story.reflection_core.datetime')
    def test_format_reflection_timestamp_format(self, mock_datetime):
        """Test that reflection uses correct timestamp format."""
        mock_now = mock_datetime.now.return_value

        format_reflection("test")

        # Verify strftime was called with correct format and lstrip was applied
        mock_now.strftime.assert_called_once_with("%I:%M %p")
        mock_now.strftime.return_value.lstrip.assert_called_once_with('0')


class TestAddReflectionToJournal:
    """Test the add_reflection_to_journal function."""
    
    @patch('src.mcp_commit_story.reflection_core.append_to_journal_file')
    @patch('src.mcp_commit_story.reflection_core.format_reflection')
    def test_add_reflection_creates_new_file(self, mock_format, mock_append):
        """Test adding reflection to a new journal file."""
        mock_format.return_value = "\n\n### 3:30 PM — Reflection\n\nTest reflection"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "test-journal.md")
            
            result = add_reflection_to_journal(journal_path, "Test reflection")
            
            # Verify append_to_journal_file was called (which handles directory creation)
            mock_append.assert_called_once_with(
                "\n\n### 3:30 PM — Reflection\n\nTest reflection",
                journal_path
            )
            
            # Verify formatting was called
            mock_format.assert_called_once_with("Test reflection")
            
            # Verify return value
            assert result is True
    
    @patch('src.mcp_commit_story.reflection_core.append_to_journal_file')
    @patch('src.mcp_commit_story.reflection_core.format_reflection')
    def test_add_reflection_appends_to_existing_file(self, mock_format, mock_append):
        """Test adding reflection to an existing journal file."""
        mock_format.return_value = "\n\n### 3:30 PM — Reflection\n\nNew reflection"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "existing-journal.md")
            
            result = add_reflection_to_journal(journal_path, "New reflection")
            
            # Verify append_to_journal_file was called
            mock_append.assert_called_once_with(
                "\n\n### 3:30 PM — Reflection\n\nNew reflection",
                journal_path
            )
            
            assert result is True
    
    @patch('src.mcp_commit_story.reflection_core.append_to_journal_file')
    @patch('src.mcp_commit_story.reflection_core.format_reflection')
    def test_add_reflection_handles_unicode(self, mock_format, mock_append):
        """Test adding reflection with unicode characters."""
        mock_format.return_value = "\n\n### 3:30 PM — Reflection\n\nUnicode: 🎉 café naïve"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "unicode-journal.md")
            
            result = add_reflection_to_journal(journal_path, "Unicode: 🎉 café naïve")
            
            # Verify append_to_journal_file was called
            mock_append.assert_called_once_with(
                "\n\n### 3:30 PM — Reflection\n\nUnicode: 🎉 café naïve",
                journal_path
            )
            
            assert result is True
    
    @patch('src.mcp_commit_story.reflection_core.append_to_journal_file')
    @patch('src.mcp_commit_story.reflection_core.format_reflection')
    def test_add_reflection_error_handling(self, mock_format, mock_append):
        """Test error handling in add_reflection_to_journal."""
        mock_format.return_value = "\n\n### 3:30 PM — Reflection\n\nTest"
        mock_append.side_effect = OSError("Permission denied")
        
        with pytest.raises(OSError):
            add_reflection_to_journal("/invalid/path/journal.md", "Test reflection")


class TestReflectionCoreIntegration:
    """Integration tests for the complete reflection core workflow."""
    
    def test_end_to_end_reflection_workflow(self):
        """Test the complete workflow from directory creation to reflection addition."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = os.path.join(temp_dir, "sandbox-journal", "daily", "2025-06-02-journal.md")
            reflection_text = "This is an end-to-end test reflection."
            
            # Ensure directory doesn't exist initially
            assert not os.path.exists(os.path.dirname(journal_path))
            
            # Add reflection (should create directory and file)
            result = add_reflection_to_journal(journal_path, reflection_text)
            
            # Verify everything worked
            assert result is True
            assert os.path.exists(journal_path)
            
            with open(journal_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "### " in content and "— Reflection" in content
            assert reflection_text in content
            
            # Add another reflection to the same file
            second_reflection = "This is a second reflection."
            result2 = add_reflection_to_journal(journal_path, second_reflection)
            
            assert result2 is True
            
            with open(journal_path, 'r', encoding='utf-8') as f:
                final_content = f.read()
            
            # Both reflections should be present
            assert reflection_text in final_content
            assert second_reflection in final_content
            assert final_content.count("### ") == 2 