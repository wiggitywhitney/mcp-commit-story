"""
Tests for daily summary standalone functionality.

This module tests the standalone daily summary generation that doesn't require MCP server,
including the main entry point, core functions, and error handling.
"""

import pytest
import tempfile
import os
from datetime import datetime, date
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import the functions we'll be testing (these don't exist yet)
try:
    from mcp_commit_story.daily_summary_standalone import (
        generate_daily_summary_standalone,
        load_journal_entries_for_date,
        save_daily_summary,
        should_generate_daily_summary,
        should_generate_period_summaries,
        generate_daily_summary
    )
except ImportError:
    # These imports will fail until we implement them
    pass

from mcp_commit_story.journal import JournalEntry


def create_test_config():
    """Create a test Config object with all required fields."""
    from mcp_commit_story.config import Config
    return Config({
        "journal": {"path": "/test/journal"},
        "git": {"exclude_patterns": []},
        "telemetry": {"enabled": False}
    })


class TestGenerateDailySummaryStandalone:
    """Test the main entry point for standalone daily summary generation."""
    
    @patch('mcp_commit_story.daily_summary_standalone.load_journal_entries_for_date')
    @patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary')
    @patch('mcp_commit_story.daily_summary_standalone.save_daily_summary')
    @patch('mcp_commit_story.daily_summary_standalone.should_generate_daily_summary')
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_successful_generation_with_entries(self, mock_load_config, mock_should_generate, 
                                               mock_save, mock_generate, mock_load_entries):
        """Test successful daily summary generation with journal entries."""
        # Setup mocks - use actual Config object
        mock_config = create_test_config()
        mock_load_config.return_value = mock_config
        mock_should_generate.return_value = "2025-01-06"
        
        mock_entries = [
            Mock(spec=JournalEntry, commit_hash="abc123"),
            Mock(spec=JournalEntry, commit_hash="def456")
        ]
        mock_load_entries.return_value = mock_entries
        
        mock_summary = {
            "date": "2025-01-06",
            "summary": "Test summary",
            "key_accomplishments": ["Test accomplishment"]
        }
        mock_generate.return_value = mock_summary
        mock_save.return_value = "/test/journal/summaries/daily/2025-01-06-summary.md"
        
        # Call function
        result = generate_daily_summary_standalone("2025-01-06")
        
        # Verify calls
        mock_load_config.assert_called_once()
        mock_load_entries.assert_called_once_with("2025-01-06", mock_config)
        mock_generate.assert_called_once_with(mock_entries, "2025-01-06", mock_config)
        mock_save.assert_called_once_with(mock_summary, mock_config)
        
        # Verify result
        assert result == mock_summary
        assert result["date"] == "2025-01-06"
    
    @patch('mcp_commit_story.daily_summary_standalone.load_journal_entries_for_date')
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_successful_generation_with_no_entries(self, mock_load_config, mock_load_entries):
        """Test successful handling when no journal entries exist for date."""
        # Setup mocks - use actual Config object
        mock_config = create_test_config()
        mock_load_config.return_value = mock_config
        mock_load_entries.return_value = []
        
        # Call function
        result = generate_daily_summary_standalone("2025-01-06")
        
        # Verify result
        assert result is None
        mock_load_entries.assert_called_once_with("2025-01-06", mock_config)
    
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_date_parameter_handling(self, mock_load_config):
        """Test date parameter handling including default to today."""
        mock_config = create_test_config()
        mock_load_config.return_value = mock_config
        
        with patch('mcp_commit_story.daily_summary_standalone.load_journal_entries_for_date') as mock_load_entries:
            mock_load_entries.return_value = []
            
            # Test with explicit date
            generate_daily_summary_standalone("2025-01-06")
            mock_load_entries.assert_called_with("2025-01-06", mock_config)
            
            # Test with None date (should default to today)
            with patch('mcp_commit_story.daily_summary_standalone.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "2025-01-07"
                generate_daily_summary_standalone(None)
                mock_load_entries.assert_called_with("2025-01-07", mock_config)
    
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_configuration_loading_failure(self, mock_load_config):
        """Test handling of configuration loading failure."""
        mock_load_config.side_effect = Exception("Config loading failed")
        
        with pytest.raises(Exception) as exc_info:
            generate_daily_summary_standalone("2025-01-06")
        
        assert "Config loading failed" in str(exc_info.value)
    
    @patch('mcp_commit_story.daily_summary_standalone.load_journal_entries_for_date')
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_journal_entry_loading_failure(self, mock_load_config, mock_load_entries):
        """Test handling of journal entry loading failure."""
        mock_config = create_test_config()
        mock_load_config.return_value = mock_config
        mock_load_entries.side_effect = Exception("Journal loading failed")
        
        with pytest.raises(Exception) as exc_info:
            generate_daily_summary_standalone("2025-01-06")
        
        assert "Journal loading failed" in str(exc_info.value)
    
    @patch('mcp_commit_story.daily_summary_standalone.load_journal_entries_for_date')
    @patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary')
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_ai_generation_failure(self, mock_load_config, mock_generate, mock_load_entries):
        """Test handling of AI generation failure."""
        mock_config = create_test_config()
        mock_load_config.return_value = mock_config
        mock_entries = [Mock(spec=JournalEntry)]
        mock_load_entries.return_value = mock_entries
        mock_generate.side_effect = Exception("AI generation failed")
        
        with pytest.raises(Exception) as exc_info:
            generate_daily_summary_standalone("2025-01-06")
        
        assert "AI generation failed" in str(exc_info.value)
    
    @patch('mcp_commit_story.daily_summary_standalone.load_journal_entries_for_date')
    @patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary')
    @patch('mcp_commit_story.daily_summary_standalone.save_daily_summary')
    @patch('mcp_commit_story.daily_summary_standalone.load_config')
    def test_file_saving_failure(self, mock_load_config, mock_save, mock_generate, mock_load_entries):
        """Test handling of file saving failure."""
        mock_config = create_test_config()
        mock_load_config.return_value = mock_config
        mock_entries = [Mock(spec=JournalEntry)]
        mock_load_entries.return_value = mock_entries
        mock_summary = {"date": "2025-01-06", "summary": "Test"}
        mock_generate.return_value = mock_summary
        mock_save.side_effect = Exception("File saving failed")
        
        with pytest.raises(Exception) as exc_info:
            generate_daily_summary_standalone("2025-01-06")
        
        assert "File saving failed" in str(exc_info.value)


class TestLoadJournalEntriesForDate:
    """Test the load_journal_entries_for_date function in standalone context."""
    
    @patch('mcp_commit_story.daily_summary_standalone.get_journal_file_path')
    @patch('os.path.exists')
    def test_load_entries_with_existing_file(self, mock_exists, mock_get_path):
        """Test loading journal entries when file exists."""
        mock_get_path.return_value = "/test/journal/daily/2025-01-06-journal.md"
        mock_exists.return_value = True
        
        mock_file_content = """### 2025-01-06 10:00:00 — Commit abc123
Test journal entry content

---

### 2025-01-06 11:00:00 — Commit def456
Another journal entry

---
"""
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('mcp_commit_story.daily_summary_standalone.JournalParser') as mock_parser:
                mock_entry1 = Mock(spec=JournalEntry)
                mock_entry2 = Mock(spec=JournalEntry)
                mock_parser.parse.side_effect = [mock_entry1, mock_entry2]
                
                config = create_test_config()
                entries = load_journal_entries_for_date("2025-01-06", config)
                
                assert len(entries) == 2
                assert entries[0] == mock_entry1
                assert entries[1] == mock_entry2
    
    @patch('mcp_commit_story.daily_summary_standalone.get_journal_file_path')
    @patch('os.path.exists')
    def test_load_entries_with_nonexistent_file(self, mock_exists, mock_get_path):
        """Test loading journal entries when file doesn't exist."""
        mock_get_path.return_value = "/test/journal/daily/2025-01-06-journal.md"
        mock_exists.return_value = False
        
        config = create_test_config()
        entries = load_journal_entries_for_date("2025-01-06", config)
        
        assert entries == []
    
    @patch('mcp_commit_story.daily_summary_standalone.get_journal_file_path')
    @patch('os.path.exists')
    def test_load_entries_with_parse_error(self, mock_exists, mock_get_path):
        """Test handling of journal parsing errors."""
        mock_get_path.return_value = "/test/journal/daily/2025-01-06-journal.md"
        mock_exists.return_value = True
        
        mock_file_content = "Invalid journal content"
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('mcp_commit_story.daily_summary_standalone.JournalParser') as mock_parser:
                mock_parser.parse.side_effect = Exception("Parse error")
                
                config = create_test_config()
                entries = load_journal_entries_for_date("2025-01-06", config)
                
                # Should return empty list on parse error
                assert entries == []


class TestShouldGenerateDailySummary:
    """Test the should_generate_daily_summary function in standalone context."""
    
    @patch('mcp_commit_story.daily_summary_standalone.extract_date_from_journal_path')
    @patch('mcp_commit_story.daily_summary_standalone.daily_summary_exists')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_should_generate_with_previous_entries(self, mock_listdir, mock_exists, 
                                                  mock_summary_exists, mock_extract_date):
        """Test should generate daily summary with previous journal entries."""
        mock_extract_date.side_effect = ["2025-01-06", "2025-01-05", "2025-01-04"]
        mock_exists.return_value = True
        mock_listdir.return_value = ["2025-01-05-journal.md", "2025-01-04-journal.md"]
        mock_summary_exists.return_value = False
        
        result = should_generate_daily_summary("/test/journal/daily/2025-01-06-journal.md", 
                                              "/test/journal/summaries/daily")
        
        assert result == "2025-01-05"
        mock_summary_exists.assert_called_once_with("2025-01-05", "/test/journal/summaries/daily")
    
    @patch('mcp_commit_story.daily_summary_standalone.extract_date_from_journal_path')
    @patch('mcp_commit_story.daily_summary_standalone.daily_summary_exists')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_should_not_generate_with_existing_summary(self, mock_listdir, mock_exists, 
                                                      mock_summary_exists, mock_extract_date):
        """Test should not generate when summary already exists."""
        mock_extract_date.side_effect = ["2025-01-06", "2025-01-05"]
        mock_exists.return_value = True
        mock_listdir.return_value = ["2025-01-05-journal.md"]
        mock_summary_exists.return_value = True
        
        result = should_generate_daily_summary("/test/journal/daily/2025-01-06-journal.md", 
                                              "/test/journal/summaries/daily")
        
        assert result is None
    
    def test_should_not_generate_with_invalid_path(self):
        """Test should not generate with invalid file path."""
        result = should_generate_daily_summary(None, "/test/journal/summaries/daily")
        assert result is None
        
        result = should_generate_daily_summary("", "/test/journal/summaries/daily")
        assert result is None


class TestShouldGeneratePeriodSummaries:
    """Test the should_generate_period_summaries function in standalone context."""
    
    @patch('mcp_commit_story.daily_summary_standalone._weekly_summary_exists')
    @patch('mcp_commit_story.daily_summary_standalone._monthly_summary_exists')
    @patch('mcp_commit_story.daily_summary_standalone._quarterly_summary_exists')
    @patch('mcp_commit_story.daily_summary_standalone._yearly_summary_exists')
    def test_period_summaries_with_boundaries(self, mock_yearly_exists, mock_quarterly_exists,
                                            mock_monthly_exists, mock_weekly_exists):
        """Test period summary generation with boundary conditions."""
        mock_weekly_exists.return_value = False
        mock_monthly_exists.return_value = False
        mock_quarterly_exists.return_value = False
        mock_yearly_exists.return_value = False
        
        # Test Monday (weekly boundary)
        result = should_generate_period_summaries("2025-01-06")  # Monday
        assert result["weekly"] == True
        
        # Test first of month (monthly boundary)
        result = should_generate_period_summaries("2025-01-01")  # First of month
        assert result["monthly"] == True
        
        # Test quarter boundary
        result = should_generate_period_summaries("2025-04-01")  # Quarter start
        assert result["quarterly"] == True
        
        # Test year boundary
        result = should_generate_period_summaries("2025-01-01")  # Year start
        assert result["yearly"] == True
    
    def test_period_summaries_with_invalid_date(self):
        """Test period summary generation with invalid date."""
        result = should_generate_period_summaries("invalid-date")
        expected = {"weekly": False, "monthly": False, "quarterly": False, "yearly": False}
        assert result == expected
        
        result = should_generate_period_summaries(None)
        assert result == expected


class TestGenerateDailySummary:
    """Test the generate_daily_summary function in standalone context."""
    
    @patch('mcp_commit_story.daily_summary_standalone._extract_manual_reflections')
    @patch('mcp_commit_story.daily_summary_standalone._call_ai_for_daily_summary')
    def test_generate_summary_with_entries(self, mock_call_ai, mock_extract_reflections):
        """Test daily summary generation with journal entries."""
        mock_entries = [
            Mock(spec=JournalEntry, commit_hash="abc123"),
            Mock(spec=JournalEntry, commit_hash="def456")
        ]
        mock_extract_reflections.return_value = ["Test reflection"]
        mock_call_ai.return_value = {
            "summary": "Test AI summary",
            "key_accomplishments": ["Test accomplishment"],
            "daily_metrics": {"commits": 2}
        }
        
        config = create_test_config()
        result = generate_daily_summary(mock_entries, "2025-01-06", config)
        
        assert result["date"] == "2025-01-06"
        assert result["summary"] == "Test AI summary"
        assert result["key_accomplishments"] == ["Test accomplishment"]
        assert result["reflections"] == ["Test reflection"]
        assert result["daily_metrics"] == {"commits": 2}
    
    @patch('mcp_commit_story.daily_summary_standalone._extract_manual_reflections')
    @patch('mcp_commit_story.daily_summary_standalone._call_ai_for_daily_summary')
    def test_generate_summary_without_reflections(self, mock_call_ai, mock_extract_reflections):
        """Test daily summary generation without manual reflections."""
        mock_entries = [Mock(spec=JournalEntry)]
        mock_extract_reflections.return_value = []
        mock_call_ai.return_value = {
            "summary": "Test AI summary",
            "key_accomplishments": ["Test accomplishment"],
            "daily_metrics": {"commits": 1}
        }
        
        config = create_test_config()
        result = generate_daily_summary(mock_entries, "2025-01-06", config)
        
        assert result["date"] == "2025-01-06"
        assert result["reflections"] is None
    
    @patch('mcp_commit_story.daily_summary_standalone._extract_manual_reflections')
    @patch('mcp_commit_story.daily_summary_standalone._call_ai_for_daily_summary')
    def test_generate_summary_with_ai_failure(self, mock_call_ai, mock_extract_reflections):
        """Test daily summary generation with AI failure."""
        mock_entries = [Mock(spec=JournalEntry)]
        mock_extract_reflections.return_value = []
        mock_call_ai.side_effect = Exception("AI generation failed")
        
        config = create_test_config()
        
        with pytest.raises(Exception) as exc_info:
            generate_daily_summary(mock_entries, "2025-01-06", config)
        
        assert "AI generation failed" in str(exc_info.value)


class TestSaveDailySummary:
    """Test the save_daily_summary function in standalone context."""
    
    @patch('mcp_commit_story.daily_summary_standalone.get_journal_file_path')
    @patch('mcp_commit_story.daily_summary_standalone.ensure_journal_directory')
    @patch('mcp_commit_story.daily_summary_standalone._format_summary_as_markdown')
    def test_save_summary_success(self, mock_format, mock_ensure_dir, mock_get_path):
        """Test successful summary saving."""
        mock_get_path.return_value = "journal/summaries/daily/2025-01-06-summary.md"
        mock_format.return_value = "# Daily Summary\n\nTest content"
    
        summary = {"date": "2025-01-06", "summary": "Test summary"}
        config = create_test_config()
    
        with patch('builtins.open', mock_open()) as mock_file:
            result = save_daily_summary(summary, config)
    
            assert result == "/test/journal/summaries/daily/2025-01-06-summary.md"
            mock_ensure_dir.assert_called_once()
            mock_file.assert_called_once_with("/test/journal/summaries/daily/2025-01-06-summary.md", 
                                             'w', encoding='utf-8')
    
    @patch('mcp_commit_story.daily_summary_standalone.get_journal_file_path')
    @patch('mcp_commit_story.daily_summary_standalone.ensure_journal_directory')
    def test_save_summary_with_file_error(self, mock_ensure_dir, mock_get_path):
        """Test summary saving with file error."""
        mock_get_path.return_value = "/test/journal/summaries/daily/2025-01-06-summary.md"
        
        summary = {"date": "2025-01-06", "summary": "Test summary"}
        config = create_test_config()
        
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = IOError("File write failed")
            
            with pytest.raises(IOError) as exc_info:
                save_daily_summary(summary, config)
            
            assert "File write failed" in str(exc_info.value) 