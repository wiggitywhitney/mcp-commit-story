"""Tests for journal file operations functionality.

This module tests the file operations components for journal entry saving:
- save_journal_entry function for writing entries to daily files
- File path generation and directory handling
- Error handling for file operations
- Integration with existing append_to_journal_file utility
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from src.mcp_commit_story.journal_workflow import save_journal_entry
from src.mcp_commit_story.journal import JournalEntry


class TestSaveJournalEntry:
    """Test the save_journal_entry function for writing journal entries to daily files."""
    
    @patch('src.mcp_commit_story.journal_workflow.datetime')
    @patch('src.mcp_commit_story.journal.append_to_journal_file')
    @patch('src.mcp_commit_story.journal.ensure_journal_directory')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_new_daily_file_with_header(self, mock_file, mock_ensure_dir, mock_append, mock_datetime):
        """Test saving journal entry to a new daily file with proper header."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y-%m-%d": "2025-06-03",
            "%B %d, %Y": "June 3, 2025"
        }[fmt]
        mock_datetime.now.return_value = mock_now
        
        # Create test journal entry
        journal_entry = MagicMock()
        journal_entry.to_markdown.return_value = "### 2:34 PM — Commit abc123\n\n#### Summary\nTest entry"
        
        # Create test config (dict format)
        config = {'journal': {'path': 'test-journal'}}
        
        # Mock Path.exists to return False (new file)
        with patch('pathlib.Path.exists', return_value=False):
            # Call function
            result = save_journal_entry(journal_entry, config, debug=True)
        
        # Verify directory creation
        mock_ensure_dir.assert_called_once()
        
        # Verify file creation with header (should use open for new files)
        expected_content = "# Daily Journal Entries - June 3, 2025\n\n### 2:34 PM — Commit abc123\n\n#### Summary\nTest entry"
        # For new files, it writes directly with open()
        mock_file.assert_called_once()
        mock_file().write.assert_called_once_with(expected_content)
        
        # Verify return path contains expected components
        assert "test-journal" in result
        assert "daily/2025-06-03-journal.md" in result
    
    @patch('src.mcp_commit_story.journal_workflow.datetime')
    @patch('src.mcp_commit_story.journal.append_to_journal_file')
    @patch('src.mcp_commit_story.journal.ensure_journal_directory')
    def test_save_to_existing_daily_file(self, mock_ensure_dir, mock_append, mock_datetime):
        """Test appending journal entry to existing daily file."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-06-03"
        mock_datetime.now.return_value = mock_now
        
        # Create test journal entry
        journal_entry = MagicMock()
        journal_entry.to_markdown.return_value = "### 3:45 PM — Commit def456\n\n#### Summary\nAnother entry"
        
        # Create test config (Config object format)
        config = MagicMock()
        config.journal_path = 'test-journal'
        
        # Mock Path.exists to return True (existing file)
        with patch('pathlib.Path.exists', return_value=True):
            # Call function
            result = save_journal_entry(journal_entry, config, debug=False)
        
        # Verify directory creation
        mock_ensure_dir.assert_called_once()
        
        # Verify append to existing file (should use append_to_journal_file)
        mock_append.assert_called_once()
        args = mock_append.call_args[0]
        assert args[0] == "### 3:45 PM — Commit def456\n\n#### Summary\nAnother entry"
        assert "test-journal" in args[1]
        assert "daily/2025-06-03-journal.md" in args[1]
        
        # Verify return path contains expected components
        assert "test-journal" in result
        assert "daily/2025-06-03-journal.md" in result
    
    @patch('src.mcp_commit_story.journal_workflow.datetime')
    @patch('src.mcp_commit_story.journal.ensure_journal_directory')
    def test_config_object_vs_dict_handling(self, mock_ensure_dir, mock_datetime):
        """Test that both Config objects and dict configurations work."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-06-03"
        mock_datetime.now.return_value = mock_now
        
        journal_entry = MagicMock()
        journal_entry.to_markdown.return_value = "test entry"
        
        # Test with Config object
        config_obj = MagicMock()
        config_obj.journal_path = 'config-obj-path'
        
        with patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file:
            save_journal_entry(journal_entry, config_obj)
            # Verify file was opened for writing (new file)
            mock_file.assert_called()
        
        # Test with dict config
        config_dict = {'journal': {'path': 'dict-config-path'}}
        
        with patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.open', mock_open()) as mock_file:
            save_journal_entry(journal_entry, config_dict)
            # Verify file was opened for writing (new file)
            mock_file.assert_called()
    
    @patch('src.mcp_commit_story.journal_workflow.datetime')
    @patch('src.mcp_commit_story.journal.ensure_journal_directory')
    def test_file_permission_error_handling(self, mock_ensure_dir, mock_datetime):
        """Test error handling for file permission issues."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-06-03"
        mock_datetime.now.return_value = mock_now
        
        # Create test data
        journal_entry = MagicMock()
        journal_entry.to_markdown.return_value = "test entry"
        config = {'journal': {'path': 'test-journal'}}
        
        # Mock file operations to raise PermissionError
        with patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.open', side_effect=PermissionError("Access denied")):
            
            # The function actually catches PermissionError and may convert it
            # Let's test that some kind of error is raised (PermissionError or ValueError)
            with pytest.raises((PermissionError, ValueError)):
                save_journal_entry(journal_entry, config)
    
    @patch('src.mcp_commit_story.journal_workflow.datetime')
    @patch('src.mcp_commit_story.journal.append_to_journal_file')
    @patch('src.mcp_commit_story.journal.ensure_journal_directory')
    def test_debug_mode_behavior(self, mock_ensure_dir, mock_append, mock_datetime):
        """Test debug mode logging behavior."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "2025-06-03"
        mock_datetime.now.return_value = mock_now
        
        journal_entry = MagicMock()
        journal_entry.to_markdown.return_value = "test entry"
        config = {'journal': {'path': 'test-journal'}}
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('src.mcp_commit_story.journal_workflow.logger') as mock_logger:
            
            # Call with debug=True
            save_journal_entry(journal_entry, config, debug=True)
            
            # Verify debug logging was called
            mock_logger.debug.assert_called()
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any("Appending to existing file" in call for call in debug_calls)
    
    def test_daily_file_naming_convention(self):
        """Test that daily files follow YYYY-MM-DD.md naming convention."""
        with patch('src.mcp_commit_story.journal_workflow.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "2025-12-31"
            mock_datetime.now.return_value = mock_now
            
            journal_entry = MagicMock()
            journal_entry.to_markdown.return_value = "test"
            config = {'journal': {'path': 'test'}}
            
            with patch('pathlib.Path.exists', return_value=False), \
                 patch('src.mcp_commit_story.journal.ensure_journal_directory'), \
                 patch('builtins.open', mock_open()):
                
                result = save_journal_entry(journal_entry, config)
                
                # Verify the returned path follows the expected pattern
                assert "daily/2025-12-31-journal.md" in result


class TestJournalFileOperationsIntegration:
    """Integration tests for journal file operations."""
    
    def test_end_to_end_file_saving(self):
        """Test complete file saving workflow with real file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test journal entry
            journal_entry = JournalEntry(
                timestamp="2:34 PM",
                commit_hash="abc123",
                summary="Test summary",
                technical_synopsis="Test technical details",
                accomplishments="Test accomplishments",
                frustrations="Test frustrations",
                tone_mood={"mood": "positive", "indicators": "good progress"},
                discussion_notes=["Test discussion"],
                terminal_commands=["test command"],
                commit_metadata={"author": "test", "files": 2}
            )
            
            # Create test config
            config = {'journal': {'path': temp_dir}}
            
            # Use a single datetime mock that covers both save_journal_entry calls
            with patch('src.mcp_commit_story.journal_workflow.datetime') as mock_datetime:
                mock_now = MagicMock()
                mock_now.strftime.side_effect = lambda fmt: {
                    "%Y-%m-%d": "2025-06-03",
                    "%B %d, %Y": "June 3, 2025"
                }[fmt]
                mock_datetime.now.return_value = mock_now
                
                # Save first journal entry
                result_path = save_journal_entry(journal_entry, config)
                
                # Save another entry to same file (within same datetime mock context)
                journal_entry2 = JournalEntry(
                    timestamp="3:45 PM",
                    commit_hash="def456",
                    summary="Second entry"
                )
                
                result_path2 = save_journal_entry(journal_entry2, config)
            
            # Verify file was created
            expected_path = Path(temp_dir) / "daily" / "2025-06-03-journal.md"
            assert expected_path.exists()
            assert result_path == str(expected_path)
            
            # Verify same file path for both entries
            assert result_path2 == result_path
            
            # Verify file content
            content = expected_path.read_text()
            assert "# Daily Journal Entries - June 3, 2025" in content
            assert "### 2:34 PM — Commit abc123" in content
            assert "Test summary" in content
            
            # Verify both entries in file
            final_content = expected_path.read_text()
            assert "### 2:34 PM — Commit abc123" in final_content
            assert "### 3:45 PM — Commit def456" in final_content
            assert "Second entry" in final_content


class TestQuarterlyFilePathSupport:
    """Test quarterly file path generation in get_journal_file_path function."""
    
    def test_quarterly_file_path_q1(self):
        """Test quarterly file path generation for Q1 (Jan-Mar)."""
        from src.mcp_commit_story.journal import get_journal_file_path
        
        # Test February (Q1)
        result = get_journal_file_path("2025-02-15", "quarterly_summary")
        expected_path = "journal/summaries/quarterly/2025-Q1.md"
        assert result == expected_path
    
    def test_quarterly_file_path_q2(self):
        """Test quarterly file path generation for Q2 (Apr-Jun)."""
        from src.mcp_commit_story.journal import get_journal_file_path
        
        # Test May (Q2)
        result = get_journal_file_path("2025-05-20", "quarterly_summary")
        expected_path = "journal/summaries/quarterly/2025-Q2.md"
        assert result == expected_path
    
    def test_quarterly_file_path_q3(self):
        """Test quarterly file path generation for Q3 (Jul-Sep)."""
        from src.mcp_commit_story.journal import get_journal_file_path
        
        # Test August (Q3)
        result = get_journal_file_path("2025-08-10", "quarterly_summary")
        expected_path = "journal/summaries/quarterly/2025-Q3.md"
        assert result == expected_path
    
    def test_quarterly_file_path_q4(self):
        """Test quarterly file path generation for Q4 (Oct-Dec)."""
        from src.mcp_commit_story.journal import get_journal_file_path
        
        # Test December (Q4)
        result = get_journal_file_path("2025-12-31", "quarterly_summary")
        expected_path = "journal/summaries/quarterly/2025-Q4.md"
        assert result == expected_path
    
    def test_quarterly_file_path_all_quarters(self):
        """Test quarterly file path generation for all quarter boundaries."""
        from src.mcp_commit_story.journal import get_journal_file_path
        
        # Test all quarter boundary months
        test_cases = [
            ("2025-01-01", "2025-Q1.md"),  # January - Q1
            ("2025-03-31", "2025-Q1.md"),  # March - Q1
            ("2025-04-01", "2025-Q2.md"),  # April - Q2
            ("2025-06-30", "2025-Q2.md"),  # June - Q2
            ("2025-07-01", "2025-Q3.md"),  # July - Q3
            ("2025-09-30", "2025-Q3.md"),  # September - Q3
            ("2025-10-01", "2025-Q4.md"),  # October - Q4
            ("2025-12-31", "2025-Q4.md"),  # December - Q4
        ]
        
        for date, expected_filename in test_cases:
            result = get_journal_file_path(date, "quarterly_summary")
            expected_path = f"journal/summaries/quarterly/{expected_filename}"
            assert result == expected_path, f"Failed for date {date}: expected {expected_path}, got {result}"