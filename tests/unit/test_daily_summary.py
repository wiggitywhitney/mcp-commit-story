"""Tests for daily summary file-creation-based trigger system."""

import pytest
import tempfile
import os
from datetime import datetime, date
from pathlib import Path
from unittest.mock import patch, mock_open

from src.mcp_commit_story.daily_summary import (
    extract_date_from_journal_path,
    daily_summary_exists,
    should_generate_daily_summary,
    should_generate_period_summaries
)


class TestExtractDateFromJournalPath:
    """Test extracting date from journal file paths."""
    
    def test_extract_date_valid_journal_path(self):
        """Test extracting date from valid journal file path."""
        path = "/path/to/daily/2025-01-06-journal.md"
        result = extract_date_from_journal_path(path)
        assert result == "2025-01-06"
    
    def test_extract_date_different_formats(self):
        """Test extracting date from different valid formats."""
        paths_and_expected = [
            ("2025-01-06-journal.md", "2025-01-06"),
            ("/full/path/2025-12-25-journal.md", "2025-12-25"),
            ("./relative/2025-06-15-journal.md", "2025-06-15"),
        ]
        
        for path, expected in paths_and_expected:
            result = extract_date_from_journal_path(path)
            assert result == expected, f"Failed for path: {path}"
    
    def test_extract_date_invalid_paths(self):
        """Test handling invalid journal file paths."""
        invalid_paths = [
            "not-a-journal-file.txt",
            "2025-13-40-journal.md",  # Invalid date
            "invalid-date-format.md",
            "",
            None
        ]
        
        for invalid_path in invalid_paths:
            result = extract_date_from_journal_path(invalid_path)
            assert result is None, f"Should return None for: {invalid_path}"
    
    def test_extract_date_edge_cases(self):
        """Test edge cases in date extraction."""
        # Valid edge cases
        assert extract_date_from_journal_path("2025-02-29-journal.md") is None  # Invalid leap year
        assert extract_date_from_journal_path("2024-02-29-journal.md") == "2024-02-29"  # Valid leap year


class TestDailySummaryExists:
    """Test checking if daily summary files exist."""
    
    def test_daily_summary_exists_true(self):
        """Test returns True when summary file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a summary file
            summary_file = os.path.join(temp_dir, "2025-01-05-summary.md")
            with open(summary_file, 'w') as f:
                f.write("Summary content")
            
            result = daily_summary_exists("2025-01-05", temp_dir)
            assert result is True
    
    def test_daily_summary_exists_false(self):
        """Test returns False when summary file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = daily_summary_exists("2025-01-05", temp_dir)
            assert result is False
    
    def test_daily_summary_exists_missing_directory(self):
        """Test handling missing summary directory."""
        non_existent_dir = "/tmp/definitely_does_not_exist_12345"
        result = daily_summary_exists("2025-01-05", non_existent_dir)
        assert result is False
    
    def test_daily_summary_exists_multiple_formats(self):
        """Test checking different summary file formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test different potential summary file names
            formats_to_test = [
                "2025-01-05-summary.md",
                "2025-01-05-daily-summary.md", 
                "daily-2025-01-05.md"
            ]
            
            for filename in formats_to_test:
                summary_file = os.path.join(temp_dir, filename)
                with open(summary_file, 'w') as f:
                    f.write("Summary")
                
                # This test will need to be updated based on actual implementation
                # For now, assume it checks for standard format
                if filename == "2025-01-05-summary.md":
                    result = daily_summary_exists("2025-01-05", temp_dir)
                    assert result is True
                    
                os.unlink(summary_file)


class TestShouldGenerateDailySummary:
    """Test the main daily summary trigger logic."""
    
    def test_should_generate_daily_summary_valid_case(self):
        """Test generating summary for valid previous date."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = os.path.join(temp_dir, "daily")
            summary_dir = os.path.join(temp_dir, "summaries")
            os.makedirs(journal_dir)
            os.makedirs(summary_dir)
            
            # Create previous journal file
            prev_journal = os.path.join(journal_dir, "2025-01-05-journal.md")
            with open(prev_journal, 'w') as f:
                f.write("Previous day's journal")
            
            # Current journal being created
            new_journal = os.path.join(journal_dir, "2025-01-06-journal.md")
            
            result = should_generate_daily_summary(new_journal, summary_dir)
            assert result == "2025-01-05"
    
    def test_should_generate_daily_summary_no_previous_entries(self):
        """Test when there are no previous journal entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = os.path.join(temp_dir, "daily")
            summary_dir = os.path.join(temp_dir, "summaries")
            os.makedirs(journal_dir)
            os.makedirs(summary_dir)
            
            # Only current journal, no previous entries
            new_journal = os.path.join(journal_dir, "2025-01-06-journal.md")
            
            result = should_generate_daily_summary(new_journal, summary_dir)
            assert result is None
    
    def test_should_generate_daily_summary_already_exists(self):
        """Test when summary already exists for previous date."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = os.path.join(temp_dir, "daily")
            summary_dir = os.path.join(temp_dir, "summaries")
            os.makedirs(journal_dir)
            os.makedirs(summary_dir)
            
            # Create previous journal file
            prev_journal = os.path.join(journal_dir, "2025-01-05-journal.md")
            with open(prev_journal, 'w') as f:
                f.write("Previous day's journal")
            
            # Create existing summary
            existing_summary = os.path.join(summary_dir, "2025-01-05-summary.md")
            with open(existing_summary, 'w') as f:
                f.write("Existing summary")
            
            # Current journal being created
            new_journal = os.path.join(journal_dir, "2025-01-06-journal.md")
            
            result = should_generate_daily_summary(new_journal, summary_dir)
            assert result is None
    
    def test_should_generate_daily_summary_invalid_input(self):
        """Test handling invalid input paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Invalid journal path
            result = should_generate_daily_summary("invalid-path.txt", temp_dir)
            assert result is None
            
            # None input
            result = should_generate_daily_summary(None, temp_dir)
            assert result is None
    
    def test_should_generate_daily_summary_multiple_previous_files(self):
        """Test when multiple previous journal files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_dir = os.path.join(temp_dir, "daily")
            summary_dir = os.path.join(temp_dir, "summaries")
            os.makedirs(journal_dir)
            os.makedirs(summary_dir)
            
            # Create multiple previous journal files
            dates = ["2025-01-03", "2025-01-04", "2025-01-05"]
            for date_str in dates:
                journal_file = os.path.join(journal_dir, f"{date_str}-journal.md")
                with open(journal_file, 'w') as f:
                    f.write(f"Journal for {date_str}")
            
            # Current journal being created
            new_journal = os.path.join(journal_dir, "2025-01-06-journal.md")
            
            result = should_generate_daily_summary(new_journal, summary_dir)
            # Should return the most recent previous date
            assert result == "2025-01-05"


class TestShouldGeneratePeriodSummaries:
    """Test period summary trigger logic (weekly, monthly, etc.)."""
    
    def test_should_generate_period_summaries_weekly_monday(self):
        """Test weekly summary trigger on Monday."""
        # Monday January 6, 2025
        monday_date = "2025-01-06"
        
        result = should_generate_period_summaries(monday_date)
        
        # Should indicate weekly summary needed
        assert "weekly" in result
        assert result["weekly"] is True
    
    def test_should_generate_period_summaries_not_monday(self):
        """Test no weekly summary on non-Monday."""
        # Tuesday January 7, 2025
        tuesday_date = "2025-01-07"
        
        result = should_generate_period_summaries(tuesday_date)
        
        # Should not indicate weekly summary needed
        assert result.get("weekly", False) is False
    
    def test_should_generate_period_summaries_monthly_first(self):
        """Test monthly summary trigger on first of month."""
        # February 1, 2025
        first_of_month = "2025-02-01"
        
        result = should_generate_period_summaries(first_of_month)
        
        # Should indicate monthly summary needed
        assert "monthly" in result
        assert result["monthly"] is True
    
    def test_should_generate_period_summaries_not_first(self):
        """Test no monthly summary on non-first day."""
        # January 15, 2025
        mid_month = "2025-01-15"
        
        result = should_generate_period_summaries(mid_month)
        
        # Should not indicate monthly summary needed
        assert result.get("monthly", False) is False
    
    def test_should_generate_period_summaries_quarterly(self):
        """Test quarterly summary triggers."""
        quarterly_dates = ["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]
        
        for quarter_date in quarterly_dates:
            result = should_generate_period_summaries(quarter_date)
            assert result.get("quarterly", False) is True, f"Failed for {quarter_date}"
    
    def test_should_generate_period_summaries_yearly(self):
        """Test yearly summary trigger on January 1st."""
        new_years = "2025-01-01"
        
        result = should_generate_period_summaries(new_years)
        
        # Should indicate yearly summary needed
        assert "yearly" in result
        assert result["yearly"] is True
    
    def test_should_generate_period_summaries_invalid_date(self):
        """Test handling invalid date input."""
        invalid_dates = ["invalid-date", "2025-13-40", None, ""]
        
        for invalid_date in invalid_dates:
            result = should_generate_period_summaries(invalid_date)
            # Should return empty dict or all False values
            assert isinstance(result, dict)
            assert all(v is False for v in result.values()) or len(result) == 0 