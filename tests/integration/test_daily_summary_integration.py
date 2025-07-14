"""Integration tests for standalone daily summary generation workflow.

Tests the complete workflow: git hook trigger → standalone generation → file saving.
Validates integration between git_hook_worker.py and daily_summary_standalone.py.
"""

import os
import shutil
import subprocess
import tempfile
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, call, MagicMock
import pytest
import sys

from mcp_commit_story.config import load_config
from mcp_commit_story.daily_summary import should_generate_daily_summary
from mcp_commit_story.daily_summary_standalone import generate_daily_summary_standalone
from mcp_commit_story.git_hook_worker import check_daily_summary_trigger, main
from mcp_commit_story.git_utils import generate_hook_content
from mcp_commit_story.journal_workflow_types import DailySummary


@pytest.fixture
def temp_git_repo_with_journal(tmp_path):
    """Create a temporary git repository with journal structure for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    
    # Create journal directory structure
    journal_dir = repo_dir / "journal" / "daily"
    journal_dir.mkdir(parents=True)
    
    summaries_dir = repo_dir / "journal" / "summaries" / "daily"
    summaries_dir.mkdir(parents=True)
    
    # Create initial commit
    (repo_dir / "README.md").write_text("# Test Repository for Daily Summary Integration\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    
    return repo_dir


@pytest.fixture
def mock_config(tmp_path):
    """Mock configuration with correct paths."""
    config_data = {
        "journal": {
            "path": str(tmp_path / "journal")
        },
        "ai_provider": "openai",
        "openai_api_key": "test-key"
    }
    
    # Mock both the standalone module and the config module used by git_hook_worker
    with patch('mcp_commit_story.daily_summary_standalone.load_config') as mock_load_standalone:
        with patch('mcp_commit_story.config.load_config') as mock_load_config:
            mock_load_standalone.return_value = config_data
            mock_load_config.return_value = config_data
            yield config_data


@pytest.fixture
def sample_journal_entries():
    """Sample journal entries for testing."""
    return {
        "2025-01-05": """### 2025-01-05T10:00:00-05:00 — Commit abc123

#### Summary
Implemented user authentication system with JWT tokens.

#### Technical Synopsis
Added login endpoint, JWT generation, and middleware for token validation.

#### Accomplishments
- Created secure login system
- Implemented JWT token generation
- Added authentication middleware

#### Tone and Mood
Productive and focused session.
""",
        "2025-01-06": """### 2025-01-06T09:00:00-05:00 — Commit def456

#### Summary
Fixed authentication bug and improved error handling.

#### Technical Synopsis
Resolved JWT expiration edge case and added proper error responses.

#### Accomplishments
- Fixed JWT expiration bug
- Improved error handling
- Added comprehensive tests

#### Tone and Mood
Debugging session with good progress.
"""
    }


class TestDailySummaryStandaloneIntegration:
    """Test the complete standalone daily summary workflow integration."""
    
    def test_complete_workflow_successful_generation(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test complete workflow: journal entries → git hook → standalone generation → file saving."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Step 1: Create journal entries for multiple days
        for date_str, content in sample_journal_entries.items():
            journal_file = journal_dir / f"{date_str}-journal.md"
            journal_file.write_text(content)
        
        # Step 2: Mock AI generation to return predictable results
        mock_summary = DailySummary(
            date="2025-01-05",
            summary="Implemented authentication system with JWT tokens.",
            accomplishments=["Created secure login system", "Implemented JWT token generation"],
            technical_synopsis="Added login endpoint, JWT generation, and middleware for token validation.",
            tone_and_mood="Productive and focused session."
        )
        
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            mock_generate.return_value = mock_summary
            
            # Step 3: Test standalone generation directly
            result = generate_daily_summary_standalone("2025-01-05")
            
            # Verify generation succeeded
            assert result is not None
            assert result["date"] == "2025-01-05"
            assert "authentication system" in result["summary"]
            
            # Verify file was saved
            summary_file = summaries_dir / "2025-01-05-summary.md"
            assert summary_file.exists()
            
            content = summary_file.read_text()
            assert "authentication system" in content
            assert "Daily Summary for 2025-01-05" in content
    
    def test_git_hook_integration_calls_standalone(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test git hook integration calls standalone daily summary correctly."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Create journal entries for yesterday and today
        yesterday_journal = journal_dir / "2025-01-05-journal.md"
        yesterday_journal.write_text(sample_journal_entries["2025-01-05"])
        
        today_journal = journal_dir / "2025-01-06-journal.md"
        today_journal.write_text(sample_journal_entries["2025-01-06"])
        
        # Mock the standalone generation function
        with patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone') as mock_standalone:
            mock_standalone.return_value = DailySummary(
                date="2025-01-05",
                summary="Test summary",
                accomplishments=["Test accomplishment"],
                technical_synopsis="Test synopsis",
                tone_and_mood="Test mood"
            )
            
            # Test the daily summary trigger check function
            trigger_date = check_daily_summary_trigger(str(repo_dir))
            
            # Verify trigger detects the need for yesterday's summary
            assert trigger_date == "2025-01-05"
            
            # Test the main hook processing through subprocess simulation
            with patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger') as mock_check:
                mock_check.return_value = "2025-01-05"
                
                # Mock sys.argv for the main function
                with patch('sys.argv', ['git_hook_worker.py', str(repo_dir)]):
                    # Mock journal generation to avoid complications
                    with patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe') as mock_journal:
                        mock_journal.return_value = True
                        
                        # Call main function (expect SystemExit)
                        try:
                            main()
                        except SystemExit as e:
                            # SystemExit(0) is expected from the main function
                            assert e.code == 0
                        
                        # Verify standalone function was called with correct date
                        mock_standalone.assert_called_once_with("2025-01-05")
    
    def test_trigger_logic_preservation(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test trigger logic preservation: file-creation-based detection, period boundaries."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Test case 1: Should trigger when today's journal exists but yesterday's summary doesn't
        yesterday_journal = journal_dir / "2025-01-05-journal.md"
        yesterday_journal.write_text(sample_journal_entries["2025-01-05"])
        
        today_journal = journal_dir / "2025-01-06-journal.md"
        today_journal.write_text(sample_journal_entries["2025-01-06"])
        
        # Verify trigger logic detects the need for yesterday's summary
        trigger_date = should_generate_daily_summary(str(today_journal), str(summaries_dir))
        assert trigger_date == "2025-01-05"
        
        # Test case 2: Should not trigger when summary already exists
        yesterday_summary = summaries_dir / "2025-01-05-summary.md"
        yesterday_summary.write_text("# Daily Summary for 2025-01-05\n\nExisting summary")
        
        trigger_date = should_generate_daily_summary(str(today_journal), str(summaries_dir))
        assert trigger_date is None
        
        # Test case 3: Should not trigger on first day (no previous journal)
        first_day_journal = journal_dir / "2025-01-01-journal.md"
        first_day_journal.write_text(sample_journal_entries["2025-01-05"])
        
        trigger_date = should_generate_daily_summary(str(first_day_journal), str(summaries_dir))
        assert trigger_date is None
    
    def test_error_scenarios_graceful_degradation(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test error scenarios with graceful degradation."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Create journal entry
        yesterday_journal = journal_dir / "2025-01-05-journal.md"
        yesterday_journal.write_text(sample_journal_entries["2025-01-05"])
        
        # Test case 1: AI generation failure
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            mock_generate.side_effect = Exception("AI service unavailable")
            
            with pytest.raises(Exception, match="AI service unavailable"):
                generate_daily_summary_standalone("2025-01-05")
            
            # Should not create summary file
            summary_file = summaries_dir / "2025-01-05-summary.md"
            assert not summary_file.exists()
        
        # Test case 2: File permission error
        with patch('mcp_commit_story.daily_summary_standalone.save_daily_summary') as mock_save:
            mock_save.side_effect = PermissionError("Cannot write to file")
            
            with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
                mock_generate.return_value = DailySummary(
                    date="2025-01-05",
                    summary="Test summary",
                    accomplishments=["Test"],
                    technical_synopsis="Test",
                    tone_and_mood="Test"
                )
                
                with pytest.raises(PermissionError, match="Cannot write to file"):
                    generate_daily_summary_standalone("2025-01-05")
        
        # Test case 3: Configuration loading failure
        with patch('mcp_commit_story.daily_summary_standalone.load_config') as mock_load:
            mock_load.side_effect = Exception("Config not found")
            
            with pytest.raises(Exception, match="Config not found"):
                generate_daily_summary_standalone("2025-01-05")
    
    def test_file_outputs_generated_correctly(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test that file outputs are generated correctly."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Create journal entry
        yesterday_journal = journal_dir / "2025-01-05-journal.md"
        yesterday_journal.write_text(sample_journal_entries["2025-01-05"])
        
        # Mock AI generation
        mock_summary = DailySummary(
            date="2025-01-05",
            summary="Implemented authentication system with JWT tokens.",
            accomplishments=["Created secure login system", "Implemented JWT token generation"],
            technical_synopsis="Added login endpoint, JWT generation, and middleware for token validation.",
            tone_and_mood="Productive and focused session."
        )
        
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            mock_generate.return_value = mock_summary
            
            # Generate summary
            result = generate_daily_summary_standalone("2025-01-05")
            
            # Verify result
            assert result is not None
            assert result["date"] == "2025-01-05"
            
            # Verify file was created
            summary_file = summaries_dir / "2025-01-05-summary.md"
            assert summary_file.exists()
            
            # Verify file content format
            content = summary_file.read_text()
            assert "# Daily Summary for 2025-01-05" in content
            assert "## Summary" in content
            assert "Implemented authentication system" in content
            assert "Daily Summary for 2025-01-05" in content
    
    def test_performance_verification(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test generation completes within acceptable time bounds."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Create multiple journal entries to test performance
        for i in range(5):
            date_str = f"2025-01-{i+1:02d}"
            journal_file = journal_dir / f"{date_str}-journal.md"
            journal_file.write_text(sample_journal_entries["2025-01-05"].replace("2025-01-05", date_str))
        
        # Mock AI generation with slight delay to simulate real conditions
        mock_summary = DailySummary(
            date="2025-01-05",
            summary="Test summary",
            accomplishments=["Test"],
            technical_synopsis="Test",
            tone_and_mood="Test"
        )
        
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            def slow_generate(*args, **kwargs):
                time.sleep(0.1)  # Simulate AI processing time
                return mock_summary
            
            mock_generate.side_effect = slow_generate
            
            # Test generation time
            start_time = time.time()
            result = generate_daily_summary_standalone("2025-01-05")
            end_time = time.time()
            
            # Should complete within reasonable time (2 seconds with AI delay)
            assert end_time - start_time < 2.0
            assert result is not None
    
    def test_various_journal_entry_scenarios(self, temp_git_repo_with_journal, mock_config):
        """Test with various journal entry counts and scenarios."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Test case 1: Empty journal file
        empty_journal = journal_dir / "2025-01-05-journal.md"
        empty_journal.write_text("")
        
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            mock_generate.return_value = None  # No summary for empty journal
            
            result = generate_daily_summary_standalone("2025-01-05")
            assert result is None
        
        # Test case 2: Journal with single entry
        single_entry_journal = journal_dir / "2025-01-06-journal.md"
        single_entry_journal.write_text("""### 2025-01-06T10:00:00-05:00 — Commit abc123

#### Summary
Single commit today.

#### Accomplishments
- Made one commit
""")
        
        mock_summary = DailySummary(
            date="2025-01-06",
            summary="Single commit today.",
            accomplishments=["Made one commit"],
            technical_synopsis="Single commit work",
            tone_and_mood="Brief session"
        )
        
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            mock_generate.return_value = mock_summary
            
            result = generate_daily_summary_standalone("2025-01-06")
            assert result is not None
            assert result["date"] == "2025-01-06"
            assert "Single commit today" in result["summary"]
        
        # Test case 3: Journal with multiple entries
        multi_entry_journal = journal_dir / "2025-01-07-journal.md"
        multi_entry_content = ""
        for i in range(5):
            multi_entry_content += f"""### 2025-01-07T{10+i:02d}:00:00-05:00 — Commit {i+1}

#### Summary
Multiple commits - Entry {i+1}

#### Accomplishments
- Made commit {i+1}

"""
        
        multi_entry_journal.write_text(multi_entry_content)
        
        mock_summary = DailySummary(
            date="2025-01-07",
            summary="Completed multiple work items.",
            accomplishments=[f"Finished task {i+1}" for i in range(5)],
            technical_synopsis="Multiple commits throughout day",
            tone_and_mood="Productive day"
        )
        
        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary') as mock_generate:
            mock_generate.return_value = mock_summary
            
            result = generate_daily_summary_standalone("2025-01-07")
            assert result is not None
            assert result["date"] == "2025-01-07"
            assert "Completed multiple work items" in result["summary"]
            assert len(result["accomplishments"]) == 5
    
    def test_git_hook_performance_no_regression(self, temp_git_repo_with_journal, mock_config, sample_journal_entries):
        """Test that git hook performance has no regression with standalone approach."""
        repo_dir = temp_git_repo_with_journal
        journal_dir = repo_dir / "journal" / "daily"
        summaries_dir = repo_dir / "journal" / "summaries" / "daily"
        
        # Update config to use correct paths
        mock_config["journal"]["path"] = str(repo_dir / "journal")
        
        # Create journal entries
        yesterday_journal = journal_dir / "2025-01-05-journal.md"
        yesterday_journal.write_text(sample_journal_entries["2025-01-05"])
        
        today_journal = journal_dir / "2025-01-06-journal.md"
        today_journal.write_text(sample_journal_entries["2025-01-06"])
        
        # Mock standalone generation to be fast
        with patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone') as mock_standalone:
            mock_standalone.return_value = DailySummary(
                date="2025-01-05",
                summary="Fast summary",
                accomplishments=["Fast work"],
                technical_synopsis="Fast synopsis",
                tone_and_mood="Fast mood"
            )
            
            # Test git hook processing performance by testing the trigger function
            start_time = time.time()
            trigger_date = check_daily_summary_trigger(str(repo_dir))
            end_time = time.time()
            
            # Should complete quickly (under 1 second for git hook processing)
            assert end_time - start_time < 1.0
            
            # Verify trigger worked correctly
            assert trigger_date == "2025-01-05" 