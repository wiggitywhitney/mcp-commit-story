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
    
    def test_extract_date_legitimate_relative_paths(self):
        """Test that legitimate relative paths with .. work correctly."""
        # These should work since os.path.basename() safely extracts just the filename
        assert extract_date_from_journal_path("../2025-01-06-journal.md") == "2025-01-06"
        assert extract_date_from_journal_path("subdir/../2025-01-06-journal.md") == "2025-01-06"
        assert extract_date_from_journal_path("/home/user/project/../backup/2025-01-06-journal.md") == "2025-01-06"
    
    def test_extract_date_non_journal_files(self):
        """Test early exit for non-journal files."""
        assert extract_date_from_journal_path("2025-01-06-notes.txt") is None
        assert extract_date_from_journal_path("2025-01-06.md") is None
        assert extract_date_from_journal_path("readme.md") is None
        assert extract_date_from_journal_path("2025-01-06-journal.txt") is None
    
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
    """Test period summary trigger logic (lookback approach)."""
    
    def test_should_generate_period_summaries_weekly_boundary_no_summary(self, tmp_path):
        """Test weekly summary trigger on Monday when no previous weekly summary exists."""
        # Monday January 6, 2025
        monday_date = "2025-01-06"
        
        # Create summaries directory structure
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "weekly").mkdir()
        
        result = should_generate_period_summaries(monday_date, str(summaries_dir))
        
        # Should indicate weekly summary needed
        assert result["weekly"] is True
        assert result["monthly"] is False  # Not first of month
        assert result["quarterly"] is False  # Not quarter boundary
        assert result["yearly"] is False  # Not new year
    
    def test_should_generate_period_summaries_weekly_boundary_summary_exists(self, tmp_path):
        """Test no weekly summary generation when summary already exists."""
        # Monday January 6, 2025
        monday_date = "2025-01-06"
        
        # Create summaries directory with existing weekly summary
        summaries_dir = tmp_path / "summaries"
        weekly_dir = summaries_dir / "weekly"
        weekly_dir.mkdir(parents=True)
        
        # Create a weekly summary for the previous week (ending Jan 5) 
        # Jan 5 is Sunday, previous Monday was Dec 30, 2024
        # Use one of the expected filename formats
        (weekly_dir / "2024-12-week1.md").write_text("Previous week summary")
        
        result = should_generate_period_summaries(monday_date, str(summaries_dir))
        
        # Should not generate weekly summary since it exists
        assert result["weekly"] is False
    
    def test_should_generate_period_summaries_monthly_boundary_no_summary(self, tmp_path):
        """Test monthly summary trigger on first of month when no previous summary exists."""
        # February 1, 2025
        first_of_month = "2025-02-01"
        
        # Create summaries directory structure
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "monthly").mkdir()
        
        result = should_generate_period_summaries(first_of_month, str(summaries_dir))
        
        # Should indicate monthly summary needed
        assert result["monthly"] is True
        assert result["weekly"] is False  # Not Monday
        assert result["quarterly"] is False  # Not quarter boundary
        assert result["yearly"] is False  # Not new year
    
    def test_should_generate_period_summaries_quarterly_boundary(self, tmp_path):
        """Test quarterly summary trigger on quarter boundaries."""
        quarterly_dates = ["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]
        
        for quarter_date in quarterly_dates:
            # Create fresh summaries directory for each test
            summaries_dir = tmp_path / f"summaries_{quarter_date.replace('-', '_')}"
            summaries_dir.mkdir()
            (summaries_dir / "quarterly").mkdir()
            
            result = should_generate_period_summaries(quarter_date, str(summaries_dir))
            assert result["quarterly"] is True, f"Quarterly should be True for {quarter_date}"
    
    def test_should_generate_period_summaries_yearly_boundary(self, tmp_path):
        """Test yearly summary trigger on January 1st."""
        new_years = "2025-01-01"
        
        # Create summaries directory structure
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "yearly").mkdir()
        
        result = should_generate_period_summaries(new_years, str(summaries_dir))
        
        # Should indicate yearly, quarterly, and monthly summaries needed
        assert result["yearly"] is True
        assert result["quarterly"] is True  # Jan 1 is also quarter boundary
        assert result["monthly"] is True   # Jan 1 is also month boundary
        assert result["weekly"] is False   # Jan 1, 2025 is not a Monday
    
    def test_should_generate_period_summaries_non_boundary_dates(self, tmp_path):
        """Test no summary generation on non-boundary dates."""
        non_boundary_dates = [
            "2025-01-07",  # Tuesday, not Monday
            "2025-01-15",  # Mid-month
            "2025-06-15",  # Mid-year, mid-month
        ]
        
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        
        for date_str in non_boundary_dates:
            result = should_generate_period_summaries(date_str, str(summaries_dir))
            
            # All should be False for non-boundary dates
            assert result["weekly"] is False, f"Weekly should be False for {date_str}"
            assert result["monthly"] is False, f"Monthly should be False for {date_str}"
            assert result["quarterly"] is False, f"Quarterly should be False for {date_str}"
            assert result["yearly"] is False, f"Yearly should be False for {date_str}"
    
    def test_should_generate_period_summaries_invalid_date(self):
        """Test handling invalid date input."""
        invalid_dates = ["invalid-date", "2025-13-40", None, ""]
        
        for invalid_date in invalid_dates:
            result = should_generate_period_summaries(invalid_date)
            
            # Should return dict with all False values for invalid input
            assert isinstance(result, dict)
            assert result["weekly"] is False
            assert result["monthly"] is False
            assert result["quarterly"] is False
            assert result["yearly"] is False
    
    def test_should_generate_period_summaries_structure(self):
        """Test that the return structure is consistent."""
        result = should_generate_period_summaries("2025-06-15")
        
        # Verify expected keys exist
        expected_keys = {"weekly", "monthly", "quarterly", "yearly"}
        assert set(result.keys()) == expected_keys
        
        # Verify all values are boolean
        assert all(isinstance(v, bool) for v in result.values())
    
    def test_should_generate_period_summaries_default_directory(self):
        """Test that function works with default summaries directory."""
        # Test with None summaries_dir (should use default)
        result = should_generate_period_summaries("2025-01-06", None)
        
        # Should not crash and return valid structure
        assert isinstance(result, dict)
        expected_keys = {"weekly", "monthly", "quarterly", "yearly"}
        assert set(result.keys()) == expected_keys


class TestEnhancedBoundaryDetection:
    """Test enhanced boundary detection for delayed commits and gap scenarios."""
    
    def test_delayed_weekly_commit_after_monday(self, tmp_path):
        """Test weekly summary generation when committing on Wednesday after Monday boundary."""
        # Scenario: Last commit was Friday Jan 3, current commit is Wednesday Jan 8
        # Monday Jan 6 boundary was missed, should generate summary for week ending Jan 5
        
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "weekly").mkdir()
        
        last_commit = "2025-01-03"  # Friday
        current_commit = "2025-01-08"  # Wednesday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should detect missed Monday boundary and generate weekly summary
        assert result["weekly"] is True
        assert result["monthly"] is False
        assert result["quarterly"] is False
        assert result["yearly"] is False
    
    def test_delayed_weekly_commit_summary_exists(self, tmp_path):
        """Test no weekly summary when delayed commit but summary already exists."""
        summaries_dir = tmp_path / "summaries"
        weekly_dir = summaries_dir / "weekly"
        weekly_dir.mkdir(parents=True)
        
        # Create existing weekly summary for the week ending Jan 5 
        # The week ending Jan 5 starts on Monday Dec 30, 2024 which is week 1
        (weekly_dir / "2024-12-week1.md").write_text("Existing summary")
        
        last_commit = "2025-01-03"  # Friday
        current_commit = "2025-01-08"  # Wednesday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should not generate since summary exists
        assert result["weekly"] is False
    
    def test_multiple_weekly_boundaries_crossed(self, tmp_path):
        """Test multiple weekly boundaries crossed in long gap."""
        # Scenario: Last commit Dec 27, 2024 (Friday), current commit Jan 20, 2025 (Monday)
        # Should detect boundaries: Jan 6 (Monday), Jan 13 (Monday), Jan 20 (Monday)
        # Should generate summary for weeks ending Jan 5, Jan 12 (but not Jan 19 since that's current week)
        
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "weekly").mkdir()
        
        last_commit = "2024-12-27"  # Friday
        current_commit = "2025-01-20"   # Monday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should detect multiple missed weekly boundaries
        assert result["weekly"] is True
    
    def test_delayed_monthly_boundary(self, tmp_path):
        """Test monthly summary generation when committing days after 1st of month."""
        # Scenario: Last commit Jan 30, current commit Feb 5
        # Feb 1 boundary was missed (monthly), Feb 3 was Monday (weekly)
        
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "monthly").mkdir()
        (summaries_dir / "weekly").mkdir()
        
        last_commit = "2025-01-30"  # Thursday
        current_commit = "2025-02-05"  # Wednesday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should detect missed monthly boundary (Feb 1) AND weekly boundary (Feb 3 Monday)
        assert result["monthly"] is True
        assert result["weekly"] is True  # Feb 3 (Monday) was crossed
    
    def test_multiple_period_boundaries_crossed(self, tmp_path):
        """Test crossing multiple different period boundaries in one gap."""
        # Scenario: Last commit Dec 20, 2024, current commit Jan 15, 2025
        # Boundaries crossed: Dec 23 (Monday), Dec 30 (Monday), Jan 1 (yearly/quarterly/monthly), Jan 6 (Monday), Jan 13 (Monday)
        
        summaries_dir = tmp_path / "summaries"
        for period in ["weekly", "monthly", "quarterly", "yearly"]:
            (summaries_dir / period).mkdir(parents=True)
        
        last_commit = "2024-12-20"  # Friday
        current_commit = "2025-01-15"   # Wednesday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should detect all types of boundaries
        assert result["weekly"] is True    # Multiple Mondays crossed
        assert result["monthly"] is True   # Jan 1 crossed
        assert result["quarterly"] is True # Jan 1 crossed
        assert result["yearly"] is True    # Jan 1 crossed
    
    def test_no_boundaries_crossed_same_period(self, tmp_path):
        """Test no summary generation when commits are in same period."""
        # Scenario: Both commits in same week
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        
        last_commit = "2025-01-07"  # Tuesday
        current_commit = "2025-01-09"  # Thursday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # No boundaries crossed
        assert result["weekly"] is False
        assert result["monthly"] is False
        assert result["quarterly"] is False
        assert result["yearly"] is False
    
    def test_exact_boundary_day_with_gap_detection(self, tmp_path):
        """Test gap detection when current commit is on exact boundary day."""
        # Scenario: Last commit Jan 3, current commit Jan 6 (Monday)
        # Should detect the immediate boundary AND check for any missed ones
        
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "weekly").mkdir()
        
        last_commit = "2025-01-03"  # Friday
        current_commit = "2025-01-06"  # Monday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should detect the Monday boundary
        assert result["weekly"] is True
    
    def test_fallback_to_original_logic_without_last_commit(self, tmp_path):
        """Test fallback to original boundary detection when last_commit_date not provided."""
        # When last_commit_date is None, should use original logic
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "weekly").mkdir()
        
        # Monday boundary
        monday_date = "2025-01-06"
        
        result = should_generate_period_summaries(
            monday_date, 
            str(summaries_dir), 
            last_commit_date=None  # Explicitly None
        )
        
        # Should use original logic - detect Monday boundary
        assert result["weekly"] is True
    
    def test_edge_case_consecutive_boundaries(self, tmp_path):
        """Test consecutive boundary days (like Jan 1 with multiple period types)."""
        # Jan 1 is yearly, quarterly, and monthly boundary
        summaries_dir = tmp_path / "summaries"
        for period in ["weekly", "monthly", "quarterly", "yearly"]:
            (summaries_dir / period).mkdir(parents=True)
        
        last_commit = "2024-12-31"  # Tuesday  
        current_commit = "2025-01-01"  # Wednesday
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        # Should detect all applicable boundaries
        assert result["monthly"] is True
        assert result["quarterly"] is True
        assert result["yearly"] is True
        assert result["weekly"] is False  # Jan 1, 2025 is Wednesday, not Monday
    
    def test_performance_large_gap(self, tmp_path):
        """Test performance with very large gaps (should still be reasonable)."""
        # Test 1 year gap - should not hang or be excessively slow
        summaries_dir = tmp_path / "summaries"
        summaries_dir.mkdir()
        (summaries_dir / "weekly").mkdir()
        
        last_commit = "2024-01-01"  
        current_commit = "2025-01-01" 
        
        import time
        start_time = time.time()
        
        result = should_generate_period_summaries(
            current_commit, 
            str(summaries_dir), 
            last_commit_date=last_commit
        )
        
        duration = time.time() - start_time
        
        # Should complete within reasonable time (< 1 second for 1 year gap)
        assert duration < 1.0
        
        # Should detect boundaries (multiple of each type in 1 year)
        assert result["weekly"] is True
        assert result["monthly"] is True  
        assert result["quarterly"] is True
        assert result["yearly"] is True 


class TestExtractAllReflections:
    """Test extracting all full reflections from journal markdown content."""
    
    def test_extract_single_reflection_from_markdown(self):
        """Test extracting a single reflection from markdown content."""
        markdown_content = """
# Daily Journal - 2025-01-15

### 7:30 AM — Reflection

This is a test reflection about my work today.
I'm feeling good about the progress.

### 8:00 AM — Commit abc123

#### Summary
Did some work on the project.
"""
        
        from src.mcp_commit_story.daily_summary import extract_all_reflections_from_markdown
        
        reflections = extract_all_reflections_from_markdown(markdown_content)
        
        assert len(reflections) == 1
        assert reflections[0]['timestamp'] == '7:30 AM'
        assert reflections[0]['content'] == 'This is a test reflection about my work today.\nI\'m feeling good about the progress.'
    
    def test_extract_multiple_reflections_from_markdown(self):
        """Test extracting multiple reflections from markdown content."""
        markdown_content = """
# Daily Journal - 2025-01-15

### 7:30 AM — Reflection

First reflection of the day.

### 8:00 AM — Commit abc123

#### Summary
Did some work.

### 2:30 PM — Reflection

Second reflection after lunch.
This one has multiple lines.

### 3:00 PM — Commit def456

#### Summary  
More work done.
"""
        
        from src.mcp_commit_story.daily_summary import extract_all_reflections_from_markdown
        
        reflections = extract_all_reflections_from_markdown(markdown_content)
        
        assert len(reflections) == 2
        assert reflections[0]['timestamp'] == '7:30 AM'
        assert reflections[0]['content'] == 'First reflection of the day.'
        assert reflections[1]['timestamp'] == '2:30 PM'
        assert reflections[1]['content'] == 'Second reflection after lunch.\nThis one has multiple lines.'
    
    def test_extract_no_reflections_from_markdown(self):
        """Test extracting reflections when there are none."""
        markdown_content = """
# Daily Journal - 2025-01-15

### 8:00 AM — Commit abc123

#### Summary
Did some work on the project.

### 9:00 AM — Commit def456

#### Summary
More work done.
"""
        
        from src.mcp_commit_story.daily_summary import extract_all_reflections_from_markdown
        
        reflections = extract_all_reflections_from_markdown(markdown_content)
        
        assert len(reflections) == 0
    
    def test_extract_reflections_with_complex_content(self):
        """Test extracting reflections with complex content including code blocks."""
        markdown_content = """
# Daily Journal - 2025-01-15

### 7:30 AM — Reflection

I'm thinking about the architecture:

```python
def some_function():
    return "test"
```

This approach might work better.

### 8:00 AM — Commit abc123

#### Summary
Did some work.
"""
        
        from src.mcp_commit_story.daily_summary import extract_all_reflections_from_markdown
        
        reflections = extract_all_reflections_from_markdown(markdown_content)
        
        assert len(reflections) == 1
        assert reflections[0]['timestamp'] == '7:30 AM'
        assert '```python' in reflections[0]['content']
        assert 'def some_function():' in reflections[0]['content']
        assert 'This approach might work better.' in reflections[0]['content']


class TestDailySummaryReflectionSection:
    """Test that daily summaries include all reflections in REFLECTIONS section."""
    
    @patch('src.mcp_commit_story.daily_summary.extract_reflections_from_journal_file')
    @patch('src.mcp_commit_story.daily_summary._call_ai_for_daily_summary')
    def test_daily_summary_includes_reflections_section(self, mock_call_ai, mock_extract_full):
        """Test that daily summary includes REFLECTIONS section when reflections exist."""
        # Mock markdown reflections from journal file
        mock_extract_full.return_value = [
            {'timestamp': '7:30 AM', 'content': 'First reflection about the work'},
            {'timestamp': '2:30 PM', 'content': 'Second reflection\nwith multiple lines'}
        ]
        
        # Mock AI response
        mock_call_ai.return_value = {
            "summary": "Test summary",
            "progress_made": "Test progress",
            "key_accomplishments": ["Test accomplishment"],
            "technical_progress": "Test technical progress",
            "daily_metrics": {"commits": 2}
        }
        
        from src.mcp_commit_story.daily_summary import generate_daily_summary
        from mcp_commit_story.summary_utils import add_source_links_to_summary
        
        # Mock the source links function
        with patch('mcp_commit_story.summary_utils.add_source_links_to_summary') as mock_add_links:
            mock_add_links.return_value = {
                "date": "2025-01-15",
                "summary": "Test summary",
                "reflections": [
                    '[7:30 AM] First reflection about the work',
                    '[2:30 PM] Second reflection\nwith multiple lines'
                ]
            }
            
            result = generate_daily_summary([], "2025-01-15", {"journal": {"path": "test"}})
            
            # Verify the function was called to extract reflections from journal file
            mock_extract_full.assert_called_once_with("2025-01-15", {"journal": {"path": "test"}})
            
            # Verify the result includes reflections in consolidated format
            assert "reflections" in result
            assert len(result["reflections"]) == 2
            assert '[7:30 AM] First reflection about the work' in result["reflections"]
            assert '[2:30 PM] Second reflection\nwith multiple lines' in result["reflections"]
    
    @patch('src.mcp_commit_story.daily_summary.extract_reflections_from_journal_file')
    @patch('src.mcp_commit_story.daily_summary._call_ai_for_daily_summary')
    def test_daily_summary_omits_reflections_section_when_none_exist(self, mock_call_ai, mock_extract_full):
        """Test that daily summary omits REFLECTIONS section when no reflections exist."""
        # Mock no reflections found from journal file
        mock_extract_full.return_value = []
        
        # Mock AI response
        mock_call_ai.return_value = {
            "summary": "Test summary",
            "progress_made": "Test progress",
            "key_accomplishments": ["Test accomplishment"],
            "technical_progress": "Test technical progress",
            "daily_metrics": {"commits": 0}
        }
        
        from src.mcp_commit_story.daily_summary import generate_daily_summary
        
        # Mock the source links function
        with patch('mcp_commit_story.summary_utils.add_source_links_to_summary') as mock_add_links:
            mock_add_links.return_value = {
                "date": "2025-01-15",
                "summary": "Test summary",
                "full_reflections": None
            }
            
            result = generate_daily_summary([], "2025-01-15", {"journal": {"path": "test"}})
            
            # Verify no full reflections in result
            assert result.get("full_reflections") is None


class TestReflectionSectionFormatting:
    """Test formatting of the REFLECTIONS section in daily summaries."""
    
    def test_format_reflections_section_with_multiple_reflections(self):
        """Test formatting multiple reflections into markdown section."""
        reflections = [
            {'timestamp': '7:30 AM', 'content': 'First reflection about the work'},
            {'timestamp': '2:30 PM', 'content': 'Second reflection\nwith multiple lines'}
        ]
        
        from src.mcp_commit_story.daily_summary import format_reflections_section
        
        result = format_reflections_section(reflections)
        
        assert result.startswith('## REFLECTIONS')
        assert '### 7:30 AM' in result
        assert '### 2:30 PM' in result
        assert 'First reflection about the work' in result
        assert 'Second reflection\nwith multiple lines' in result
    
    def test_format_reflections_section_with_single_reflection(self):
        """Test formatting single reflection into markdown section."""
        reflections = [
            {'timestamp': '7:30 AM', 'content': 'Single reflection'}
        ]
        
        from src.mcp_commit_story.daily_summary import format_reflections_section
        
        result = format_reflections_section(reflections)
        
        assert result.startswith('## REFLECTIONS')
        assert '### 7:30 AM' in result
        assert 'Single reflection' in result
    
    def test_format_reflections_section_with_empty_list(self):
        """Test formatting empty reflections list."""
        reflections = []
        
        from src.mcp_commit_story.daily_summary import format_reflections_section
        
        result = format_reflections_section(reflections)
        
        assert result == ""


class TestReflectionExtraction:
    """Test the complete reflection extraction workflow."""
    
    def test_extract_reflections_from_journal_file(self):
        """Test extracting reflections from actual journal file for date."""
        date_str = "2025-01-15"
        config = {"journal": {"path": "test-journal"}}
        
        # Mock file content
        mock_content = """
### 7:30 AM — Reflection

Test reflection content.

### 8:00 AM — Commit abc123

#### Summary
Some work done.
"""
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            with patch('os.path.exists', return_value=True):
                from src.mcp_commit_story.daily_summary import extract_reflections_from_journal_file
                
                reflections = extract_reflections_from_journal_file(date_str, config)
                
                assert len(reflections) == 1
                assert reflections[0]['timestamp'] == '7:30 AM'
                assert reflections[0]['content'] == 'Test reflection content.'
    
    def test_extract_reflections_from_nonexistent_file(self):
        """Test extracting reflections from non-existent journal file."""
        date_str = "2025-01-15"
        config = {"journal": {"path": "test-journal"}}
        
        with patch('os.path.exists', return_value=False):
            from src.mcp_commit_story.daily_summary import extract_reflections_from_journal_file
            
            reflections = extract_reflections_from_journal_file(date_str, config)
            
            assert len(reflections) == 0 