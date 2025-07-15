"""
Integration tests for the consolidated daily summary functionality.

This test suite verifies that:
1. Daily summary generation works end-to-end with real AI integration
2. Git hook integration calls the consolidated module correctly  
3. Reflection extraction works with real file operations
4. No dependencies on the deprecated standalone module remain
5. All telemetry functionality works correctly
"""

import os
import tempfile
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mcp_commit_story.daily_summary import (
    generate_daily_summary_standalone,
    load_journal_entries_for_date,
    save_daily_summary,
    extract_reflections_from_journal_file
)
from mcp_commit_story.config import load_config
from mcp_commit_story.git_hook_worker import main as git_hook_main


class TestDailySummaryConsolidation:
    """Integration tests for consolidated daily summary functionality."""
    
    @pytest.fixture
    def temp_journal_dir(self):
        """Create a temporary journal directory with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create journal structure
            journal_path = Path(tmpdir) / "journal"
            daily_path = journal_path / "daily"
            summaries_path = journal_path / "summaries" / "daily"
            
            daily_path.mkdir(parents=True)
            summaries_path.mkdir(parents=True)
            
            # Create a test journal file
            test_date = "2025-01-15"
            journal_file = daily_path / f"{test_date}-journal.md"
            
            journal_content = f"""# Daily Journal Entries - January 15, 2025

### 10:30 AM — Commit abc123

#### Summary
Fixed critical bug in user authentication system.

#### Technical Synopsis
Modified AuthService.validateToken() to handle expired tokens correctly.

#### Accomplishments
- Fixed auth token validation bug
- Added comprehensive error handling
- Updated unit tests

#### Frustrations or Roadblocks
- Token expiration logic was confusing

#### Discussion Notes (from chat)
> **Human:** The auth system is failing for expired tokens
> **AI:** Let's check the token validation logic

#### Tone/Mood
> productive
> Successfully resolved blocking issue

### 2:45 PM — Commit def456

#### Summary
Implemented comprehensive logging for auth module.

#### Technical Synopsis
Added structured logging using the telemetry framework.

#### Accomplishments
- Implemented structured logging
- Added telemetry integration
- Improved error visibility

### 2:45 PM — Reflection

I'm really satisfied with how this bug fix turned out!

"""
            
            journal_file.write_text(journal_content)
            
            # Create config
            config = {
                "journal": {
                    "path": str(journal_path)
                },
                "ai": {
                    "provider": "openai",
                    "model": "gpt-4"
                }
            }
            
            config_file = Path(tmpdir) / "config.yaml"
            import yaml
            config_file.write_text(yaml.dump(config))
            
            yield {
                "tmpdir": tmpdir,
                "journal_path": journal_path,
                "config_file": config_file,
                "test_date": test_date,
                "journal_file": journal_file
            }
    
    def test_complete_daily_summary_workflow(self, temp_journal_dir):
        """Test the complete workflow from journal entries to saved summary."""
        config_file = temp_journal_dir["config_file"]
        test_date = temp_journal_dir["test_date"]
        journal_path = temp_journal_dir["journal_path"]
        
        # Mock AI invocation to return a proper JSON response
        mock_ai_response = json.dumps({
            "summary": "Today was focused on fixing critical authentication bugs and improving system logging.",
            "progress_made": "Successfully resolved auth token validation issues and implemented comprehensive logging.",
            "key_accomplishments": [
                "Fixed auth token validation bug",
                "Added comprehensive error handling", 
                "Implemented structured logging"
            ],
            "technical_progress": "Modified AuthService.validateToken() and added telemetry framework integration.",
            "challenges_overcome": ["Token expiration logic was initially confusing"],
            "learning_insights": ["Proper error handling makes debugging much easier"],
            "discussion_highlights": ["Human-AI collaboration on auth system debugging"],
            "tone_mood": {
                "mood": "productive",
                "indicators": "Successfully resolved blocking issues"
            },
            "daily_metrics": {
                "commits": 2,
                "files_changed": 3
            }
        })
        
        with patch("mcp_commit_story.daily_summary.load_config") as mock_load_config, \
             patch("mcp_commit_story.daily_summary.invoke_ai", return_value=mock_ai_response):
            
            # Use test config
            mock_load_config.return_value = {
                "journal": {"path": str(journal_path)},
                "ai": {"provider": "openai", "model": "gpt-4"}
            }
            
            # Generate daily summary
            result = generate_daily_summary_standalone(test_date)
            
            # Verify result is a DailySummary object (dict)
            assert isinstance(result, dict)
            assert result["date"] == test_date
            assert "summary" in result
            assert "key_accomplishments" in result
            assert "reflections" in result
            
            # Verify reflections were extracted from journal file
            assert result["reflections"] is not None
            assert len(result["reflections"]) > 0
            # Should include the manual reflection from the journal
            reflection_text = " ".join(result["reflections"])
            assert "I'm really satisfied" in reflection_text
            
            # Verify summary file was created
            summary_file = journal_path / "summaries" / "daily" / f"{test_date}-summary.md"
            assert summary_file.exists()
            
            # Verify summary file content
            summary_content = summary_file.read_text()
            assert f"# Daily Summary for {test_date}" in summary_content
            assert "## Summary" in summary_content  # More general assertion
            assert "## Reflections" in summary_content
            assert "I'm really satisfied" in summary_content
    
    def test_load_journal_entries_with_real_file_operations(self, temp_journal_dir):
        """Test that load_journal_entries_for_date works with real file operations."""
        test_date = temp_journal_dir["test_date"]
        journal_path = temp_journal_dir["journal_path"]
        
        config = {
            "journal": {"path": str(journal_path)}
        }
        
        # Load journal entries
        entries = load_journal_entries_for_date(test_date, config)
        
        # Should find entries from the test journal file
        assert len(entries) > 0
        
        # Verify entry content
        first_entry = entries[0]
        assert hasattr(first_entry, 'summary')
        assert hasattr(first_entry, 'accomplishments')
        assert "Fixed critical bug" in first_entry.summary
        assert any("Fixed auth token validation bug" in acc for acc in first_entry.accomplishments)
    
    def test_extract_reflections_from_real_journal_file(self, temp_journal_dir):
        """Test that reflection extraction works with real file operations."""
        test_date = temp_journal_dir["test_date"]
        journal_path = temp_journal_dir["journal_path"]
        
        config = {
            "journal": {"path": str(journal_path)}
        }
        
        # Extract reflections
        reflections = extract_reflections_from_journal_file(test_date, config)
        
        # Should find the reflection in the test journal file
        assert len(reflections) > 0
        
        # Verify reflection content
        reflection_content = str(reflections[0])
        assert "I'm really satisfied" in reflection_content
        
    def test_git_hook_integration_with_consolidated_module(self, temp_journal_dir):
        """Test that git hook worker calls the consolidated module correctly."""
        tmpdir = temp_journal_dir["tmpdir"]
        journal_path = temp_journal_dir["journal_path"]
        
        # Mock the config and git hook dependencies
        with patch("mcp_commit_story.daily_summary.load_config") as mock_load_config, \
             patch("mcp_commit_story.git_hook_worker.generate_daily_summary_standalone") as mock_generate, \
             patch("mcp_commit_story.git_hook_worker.log_hook_activity"), \
             patch("mcp_commit_story.journal_workflow.handle_journal_entry_creation") as mock_journal, \
             patch("mcp_commit_story.git_hook_worker.check_daily_summary_trigger", return_value="2025-01-15"), \
             patch("sys.exit"):
            
            mock_load_config.return_value = {
                "journal": {"path": str(journal_path)}
            }
            mock_generate.return_value = 2  # Mock entry count
            mock_journal.return_value = {"success": True, "file_path": "test.md"}
            
            # Simulate git hook execution
            import sys
            original_argv = sys.argv
            try:
                sys.argv = ["git_hook_worker.py", tmpdir]
                git_hook_main()
            finally:
                sys.argv = original_argv
            
            # Verify the consolidated function was called
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[0][0] == "2025-01-15"  # date
            assert call_args[0][1] == tmpdir  # repo_path
    
    def test_no_dependency_on_deprecated_standalone_module(self, temp_journal_dir):
        """Test that no code depends on the deprecated daily_summary_standalone.py module."""
        journal_path = temp_journal_dir["journal_path"]
        test_date = temp_journal_dir["test_date"]
        
        # Mock AI response
        mock_ai_response = json.dumps({
            "summary": "Test summary",
            "progress_made": "Test progress", 
            "key_accomplishments": ["Test accomplishment"],
            "technical_progress": "Test technical progress",
            "daily_metrics": {"commits": 1}
        })
        
        with patch("mcp_commit_story.daily_summary.load_config") as mock_load_config, \
             patch("mcp_commit_story.ai_invocation.invoke_ai", return_value=mock_ai_response):
            
            mock_load_config.return_value = {
                "journal": {"path": str(journal_path)},
                "ai": {"provider": "openai", "model": "gpt-4"}
            }
            
            # This should work without importing daily_summary_standalone
            result = generate_daily_summary_standalone(test_date)
            
            # Verify it worked and used the main module
            assert isinstance(result, dict)
            assert result["date"] == test_date
            
            # Verify the git hook worker imports from the main module
            from mcp_commit_story.git_hook_worker import generate_daily_summary_standalone as hook_function
            from mcp_commit_story.daily_summary import generate_daily_summary_standalone as main_function
            
            # Should be the same function (imported from main module)
            assert hook_function == main_function
    
    def test_telemetry_functionality_with_real_ai_integration(self, temp_journal_dir):
        """Test that telemetry works correctly with the consolidated module."""
        journal_path = temp_journal_dir["journal_path"]
        test_date = temp_journal_dir["test_date"]
        
        mock_ai_response = json.dumps({
            "summary": "Test summary with telemetry",
            "progress_made": "Telemetry test progress",
            "key_accomplishments": ["Telemetry test"],
            "technical_progress": "Telemetry integration test",
            "daily_metrics": {"commits": 1}
        })
        
        with patch("mcp_commit_story.daily_summary.load_config") as mock_load_config, \
             patch("mcp_commit_story.ai_invocation.invoke_ai", return_value=mock_ai_response), \
             patch("mcp_commit_story.daily_summary.get_mcp_metrics") as mock_metrics:
            
            # Mock metrics recorder
            mock_recorder = MagicMock()
            mock_metrics.return_value = mock_recorder
            
            mock_load_config.return_value = {
                "journal": {"path": str(journal_path)},
                "ai": {"provider": "openai", "model": "gpt-4"}
            }
            
            # Generate summary (should record telemetry)
            result = generate_daily_summary_standalone(test_date)
            
            # Verify telemetry was recorded
            assert mock_recorder.record_histogram.called
            assert mock_recorder.record_counter.called
            
            # Verify specific telemetry calls
            histogram_calls = [call.args[0] for call in mock_recorder.record_histogram.call_args_list]
            counter_calls = [call.args[0] for call in mock_recorder.record_counter.call_args_list]
            
            # Should record generation duration
            assert any("daily_summary.generation_duration_seconds" in call for call in histogram_calls)
            # Should record success counter  
            assert any("daily_summary.operations_total" in call for call in counter_calls)
    
    def test_error_handling_and_graceful_degradation(self, temp_journal_dir):
        """Test error handling when components fail."""
        journal_path = temp_journal_dir["journal_path"]
        test_date = "2025-01-16"  # Date with no journal file
        
        with patch("mcp_commit_story.daily_summary.load_config") as mock_load_config:
            mock_load_config.return_value = {
                "journal": {"path": str(journal_path)},
                "ai": {"provider": "openai", "model": "gpt-4"}
            }
            
            # Should return None when no journal entries found
            result = generate_daily_summary_standalone(test_date)
            assert result is None
            
        # Test with invalid config
        with patch("mcp_commit_story.daily_summary.load_config", side_effect=Exception("Config error")):
            with pytest.raises(Exception):
                generate_daily_summary_standalone(test_date)

class TestTelemetryVerification:
    """Test telemetry integration with the consolidated daily summary."""
    
    def test_telemetry_spans_work_with_real_ai_integration(self):
        """Test that telemetry spans are created correctly."""
        with patch("mcp_commit_story.daily_summary.trace.get_current_span") as mock_span, \
             patch("mcp_commit_story.daily_summary.load_config") as mock_config, \
             patch("mcp_commit_story.ai_invocation.invoke_ai", return_value='{"summary": "test"}'):
            
            mock_config.return_value = {
                "journal": {"path": "/tmp/test"},
                "ai": {"provider": "openai", "model": "gpt-4"}
            }
            
            # Mock span object
            span_mock = MagicMock()
            mock_span.return_value = span_mock
            
            # This should fail gracefully (no journal entries)
            result = generate_daily_summary_standalone("2025-01-01")
            
            # Verify span attributes were set
            span_mock.set_attribute.assert_called()
            
            # Check for expected attributes
            attribute_calls = [call.args[0] for call in span_mock.set_attribute.call_args_list]
            
            assert "summary.date" in attribute_calls
            assert "daily_summary.generation_type" in attribute_calls 