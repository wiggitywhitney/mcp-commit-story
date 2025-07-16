"""
Tests for summary source file linking functionality.

This module tests the capability to generate markdown links to source files
that each summary type was built from, creating a navigable hierarchy.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, date
from unittest.mock import patch, MagicMock

# Import the functions we'll be testing (these will initially fail - that's expected in TDD)
from src.mcp_commit_story.daily_summary import (
    generate_daily_summary, 
    load_journal_entries_for_date
)


class TestDailySummarySourceLinks:
    """Test source file linking for daily summaries."""
    
    def test_daily_summary_includes_source_journal_file_link(self, tmp_path):
        """Test that daily summary includes link to the source journal file."""
        # Setup: Create a journal file
        journal_dir = tmp_path / "journal" / "daily"
        journal_dir.mkdir(parents=True)
        journal_file = journal_dir / "2025-06-06-journal.md"
        journal_file.write_text("### 9:00 AM — Commit abc123\n\nTest journal entry")
        
        # Create a proper mock entry
        mock_entry = MagicMock()
        mock_entry.summary = "Test journal entry"
        mock_entry.reflections = ""
        mock_entry.technical_details = ""
        mock_entry.progress_notes = ""
        mock_entry.discussion_highlights = ""
        mock_entry.challenges = ""
        
        mock_entries = [mock_entry]
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        
        # Mock the AI call to avoid the formatting error
        mock_ai_response = {
            "summary": "Test daily summary",
            "progress_made": "Made progress on testing",
            "key_accomplishments": ["Created test"],
            "technical_synopsis": "Technical work done",
            "daily_metrics": {"commits": 1}
        }
        
        with patch('src.mcp_commit_story.daily_summary.load_journal_entries_for_date', return_value=mock_entries), \
             patch('src.mcp_commit_story.daily_summary._call_ai_for_daily_summary', return_value=mock_ai_response):
            summary = generate_daily_summary(mock_entries, "2025-06-06", mock_config)
        
        # The summary should include a source files section
        assert 'source_files' in summary
        assert summary['source_files'] is not None
        assert len(summary['source_files']) == 1
        
        # Should contain a link to the journal file
        source_file = summary['source_files'][0]
        assert source_file['path'] == "daily/2025-06-06-journal.md"
        assert source_file['exists'] is True
        assert source_file['type'] == "journal_entry"
    
    def test_daily_summary_handles_missing_journal_file(self, tmp_path):
        """Test daily summary gracefully handles missing source journal file."""
        # Setup: No journal file created
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        
        # Mock AI response with minimal valid structure
        mock_ai_response = '{"summary": "No journal entries found for this date.", "source_files": []}'
        
        with patch('src.mcp_commit_story.daily_summary.load_journal_entries_for_date', return_value=[]), \
             patch('src.mcp_commit_story.daily_summary.invoke_ai', return_value=mock_ai_response):
            summary = generate_daily_summary([], "2025-06-06", mock_config)
        
        # Should still track that we looked for a source file
        assert 'source_files' in summary
        assert len(summary['source_files']) == 1
        
        source_file = summary['source_files'][0]
        assert source_file['path'] == "daily/2025-06-06-journal.md"
        assert source_file['exists'] is False
        assert source_file['type'] == "journal_entry"


class TestWeeklySummarySourceLinks:
    """Test source file linking for weekly summaries."""
    
    def test_weekly_summary_links_to_daily_summaries(self, tmp_path):
        """Test that weekly summary includes links to daily summary files."""
        # Setup: Create daily summary files for a week
        daily_summaries_dir = tmp_path / "journal" / "summaries" / "daily"
        daily_summaries_dir.mkdir(parents=True)
        
        # Week of June 2-8, 2025 (Monday to Sunday)
        week_dates = ["2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06", "2025-06-07", "2025-06-08"]
        
        # Create some daily summaries (not all days need summaries)
        for date_str in week_dates[:5]:  # Only create 5 of 7 days
            summary_file = daily_summaries_dir / f"{date_str}-summary.md"
            summary_file.write_text(f"# Daily Summary for {date_str}\n\nTest summary")
        
        # This function doesn't exist yet - we'll implement it
        from src.mcp_commit_story.weekly_summary import generate_weekly_summary
        
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        weekly_summary = generate_weekly_summary("2025-06-02", mock_config)  # Start of week
        
        # Should link to daily summaries for that week
        assert 'source_files' in weekly_summary
        assert len(weekly_summary['source_files']) == 7  # All 7 days checked
        
        # First 5 should exist, last 2 should not
        for i, source_file in enumerate(weekly_summary['source_files']):
            expected_date = week_dates[i]
            assert source_file['path'] == f"summaries/daily/{expected_date}-summary.md"
            assert source_file['type'] == "daily_summary"
            if i < 5:
                assert source_file['exists'] is True
            else:
                assert source_file['exists'] is False


class TestMonthlySummarySourceLinks:
    """Test source file linking for monthly summaries."""
    
    def test_monthly_summary_links_to_weekly_summaries(self, tmp_path):
        """Test that monthly summary includes links to weekly summary files."""
        # Setup: Create weekly summary files for June 2025
        weekly_summaries_dir = tmp_path / "journal" / "summaries" / "weekly"
        weekly_summaries_dir.mkdir(parents=True)
        
        # June 2025 has weeks starting: June 2, June 9, June 16, June 23, June 30
        june_weeks = [
            "2025-06-week23.md",  # Week 23
            "2025-06-week24.md",  # Week 24  
            "2025-06-week25.md",  # Week 25
            "2025-06-week26.md",  # Week 26
            "2025-06-week27.md",  # Week 27 (partial)
        ]
        
        # Create some weekly summaries
        for week_file in june_weeks[:4]:  # Create 4 of 5 weeks
            (weekly_summaries_dir / week_file).write_text(f"# Weekly Summary\n\nTest content")
        
        from src.mcp_commit_story.monthly_summary import generate_monthly_summary
        
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        monthly_summary = generate_monthly_summary("2025-06", mock_config)
        
        # Should link to weekly summaries for June
        assert 'source_files' in monthly_summary
        assert len(monthly_summary['source_files']) == 5  # 5 weeks in June 2025
        
        for i, source_file in enumerate(monthly_summary['source_files']):
            assert source_file['path'] == f"summaries/weekly/{june_weeks[i]}"
            assert source_file['type'] == "weekly_summary"
            if i < 4:
                assert source_file['exists'] is True
            else:
                assert source_file['exists'] is False


class TestQuarterlySummarySourceLinks:
    """Test source file linking for quarterly summaries."""
    
    def test_quarterly_summary_links_to_monthly_summaries(self, tmp_path):
        """Test that quarterly summary includes links to monthly summary files."""
        # Setup: Create monthly summary files for Q2 2025
        monthly_summaries_dir = tmp_path / "journal" / "summaries" / "monthly"
        monthly_summaries_dir.mkdir(parents=True)
        
        # Q2 2025: April, May, June
        q2_months = ["2025-04.md", "2025-05.md", "2025-06.md"]
        
        # Create monthly summaries
        for month_file in q2_months[:2]:  # Create 2 of 3 months
            (monthly_summaries_dir / month_file).write_text(f"# Monthly Summary\n\nTest content")
        
        from src.mcp_commit_story.quarterly_summary import generate_quarterly_summary
        
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        quarterly_summary = generate_quarterly_summary("2025,2", mock_config)  # Q2 2025
        
        # Should link to monthly summaries for Q2
        assert 'source_files' in quarterly_summary
        assert len(quarterly_summary['source_files']) == 3  # 3 months in Q2
        
        for i, source_file in enumerate(quarterly_summary['source_files']):
            assert source_file['path'] == f"summaries/monthly/{q2_months[i]}"
            assert source_file['type'] == "monthly_summary"
            if i < 2:
                assert source_file['exists'] is True
            else:
                assert source_file['exists'] is False


class TestYearlySummarySourceLinks:
    """Test source file linking for yearly summaries."""
    
    def test_yearly_summary_links_to_quarterly_summaries(self, tmp_path):
        """Test that yearly summary includes links to quarterly summary files."""
        # Setup: Create quarterly summary files for 2025
        quarterly_summaries_dir = tmp_path / "journal" / "summaries" / "quarterly"
        quarterly_summaries_dir.mkdir(parents=True)
        
        # 2025: Q1, Q2, Q3, Q4
        quarters_2025 = ["2025-Q1.md", "2025-Q2.md", "2025-Q3.md", "2025-Q4.md"]
        
        # Create quarterly summaries
        for quarter_file in quarters_2025[:3]:  # Create 3 of 4 quarters
            (quarterly_summaries_dir / quarter_file).write_text(f"# Quarterly Summary\n\nTest content")
        
        from src.mcp_commit_story.yearly_summary import generate_yearly_summary
        
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        yearly_summary = generate_yearly_summary("2025", mock_config)
        
        # Should link to quarterly summaries for 2025
        assert 'source_files' in yearly_summary
        assert len(yearly_summary['source_files']) == 4  # 4 quarters in 2025
        
        for i, source_file in enumerate(yearly_summary['source_files']):
            assert source_file['path'] == f"summaries/quarterly/{quarters_2025[i]}"
            assert source_file['type'] == "quarterly_summary"
            if i < 3:
                assert source_file['exists'] is True
            else:
                assert source_file['exists'] is False


class TestSourceFileLinkGeneration:
    """Test the generic source file link generation logic."""
    
    def test_generate_source_links_section_markdown(self):
        """Test that source file data is properly formatted as markdown."""
        from src.mcp_commit_story.summary_utils import generate_source_links_section
        
        source_files = [
            {'path': 'daily/2025-06-06-journal.md', 'exists': True, 'type': 'journal_entry'},
            {'path': 'daily/2025-06-05-journal.md', 'exists': False, 'type': 'journal_entry'},
        ]
        
        markdown = generate_source_links_section(source_files, "June 5-6, 2025")
        
        # Should contain proper markdown links
        assert "#### Source Files" in markdown
        assert "[2025-06-06-journal.md](daily/2025-06-06-journal.md)" in markdown
        assert "[2025-06-05-journal.md](daily/2025-06-05-journal.md) *(file not found)*" in markdown
        assert "**Coverage**: June 5-6, 2025" in markdown
    
    def test_determine_source_file_type_and_pattern(self):
        """Test logic for determining what type of files each summary should link to."""
        from src.mcp_commit_story.summary_utils import determine_source_files_for_summary
        
        # Daily summary should link to journal entries
        source_files = determine_source_files_for_summary("daily", "2025-06-06", "/journal")
        assert len(source_files) == 1
        assert source_files[0]['type'] == 'journal_entry'
        assert 'daily/2025-06-06-journal.md' in source_files[0]['path']
        
        # Weekly summary should link to daily summaries
        source_files = determine_source_files_for_summary("weekly", "2025-06-02", "/journal")  # Monday
        assert len(source_files) == 7  # 7 days in week
        assert all(sf['type'] == 'daily_summary' for sf in source_files)
        
        # Monthly summary should link to weekly summaries  
        source_files = determine_source_files_for_summary("monthly", "2025-06", "/journal")
        assert len(source_files) >= 4  # At least 4 weeks in any month
        assert all(sf['type'] == 'weekly_summary' for sf in source_files)


class TestSourceLinksIntegration:
    """Test integration of source links with existing summary functionality."""
    
    def test_daily_summary_with_source_links_end_to_end(self, tmp_path):
        """Test complete daily summary generation including source links."""
        # Setup complete environment
        journal_dir = tmp_path / "journal" / "daily"
        journal_dir.mkdir(parents=True)
        
        # Create journal file
        journal_file = journal_dir / "2025-06-06-journal.md"
        journal_file.write_text("""# Daily Journal Entries - June 6, 2025

### 9:00 AM — Commit abc123

#### Summary
Test journal entry content.
""")
        
        # Generate daily summary
        mock_config = {"journal": {"path": str(tmp_path / "journal")}}
        
        # Create a proper mock entry
        mock_entry = MagicMock()
        mock_entry.summary = "Test journal entry content"
        mock_entry.reflections = ""
        mock_entry.technical_details = ""
        mock_entry.progress_notes = ""
        mock_entry.discussion_highlights = ""
        mock_entry.challenges = ""
        
        mock_entries = [mock_entry]
        
        # Mock the AI call to avoid the formatting error
        mock_ai_response = {
            "summary": "Test daily summary",
            "progress_made": "Made progress on testing",
            "key_accomplishments": ["Created test"],
            "technical_synopsis": "Technical work done",
            "daily_metrics": {"commits": 1}
        }
        
        with patch('src.mcp_commit_story.daily_summary.load_journal_entries_for_date', return_value=mock_entries), \
             patch('src.mcp_commit_story.daily_summary._call_ai_for_daily_summary', return_value=mock_ai_response):
            summary = generate_daily_summary(mock_entries, "2025-06-06", mock_config)
        
        # Verify source links are included
        assert 'source_files' in summary
        assert len(summary['source_files']) == 1
        
        # Verify markdown serialization includes source links
        from src.mcp_commit_story.daily_summary import _format_summary_as_markdown
        summary_markdown = _format_summary_as_markdown(summary)
        assert "#### Source Files" in summary_markdown
        assert "[2025-06-06-journal.md]" in summary_markdown 