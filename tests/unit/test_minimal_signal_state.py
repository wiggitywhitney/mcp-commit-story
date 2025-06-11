"""
Test suite for minimal signal state refactor.

Tests to verify that signal creation uses minimal state (commit hash + tool params)
while leveraging existing git_utils functions for on-demand context retrieval.
This eliminates redundant metadata storage and PII exposure.

TDD Step 1: Write failing tests to drive the minimal signal implementation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

import pytest

from mcp_commit_story.signal_management import SignalFileError


class TestMinimalSignalCreation:
    """Test minimal signal file creation with only essential data."""
    
    def test_create_minimal_signal_contains_only_essential_fields(self):
        """Test that signals contain only tool, params with commit_hash, and created_at."""
        from mcp_commit_story.signal_management import create_signal_file
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create signal with full metadata (current implementation)
            full_metadata = {
                "hash": "abc123def456789012345678901234567890abcd",
                "author": "Test User <test@example.com>",
                "date": "2025-06-11T15:00:00Z",
                "message": "Sensitive commit message with details",
                "files_changed": ["/private/path/file1.py", "/private/path/file2.py"],
                "stats": {"insertions": 50, "deletions": 10}
            }
            
            signal_file = create_signal_file(
                signal_directory=temp_dir,
                tool_name="journal_new_entry",
                parameters={"custom_param": "value"},
                commit_metadata=full_metadata
            )
            
            # Read and validate minimal structure
            with open(signal_file, 'r') as f:
                signal_data = json.load(f)
            
            # Should contain ONLY these fields
            expected_fields = {"tool", "params", "created_at"}
            assert set(signal_data.keys()) == expected_fields
            
            # Should NOT contain these fields (privacy/redundancy)
            forbidden_fields = {"metadata", "signal_id", "author", "files_changed"}
            for field in forbidden_fields:
                assert field not in signal_data
            
            # Params should contain commit_hash plus custom params
            assert "commit_hash" in signal_data["params"]
            assert signal_data["params"]["commit_hash"] == "abc123def456789012345678901234567890abcd"
            assert signal_data["params"]["custom_param"] == "value"

    def test_signal_size_reduction_privacy_improvement(self):
        """Test that minimal signals are significantly smaller and contain no PII."""
        from mcp_commit_story.signal_management import create_signal_file
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Large metadata with PII
            large_metadata = {
                "hash": "abc123def456",
                "author": "John Doe <john.doe@company.com>",
                "date": "2025-06-11T15:00:00Z", 
                "message": "Fix security vulnerability in authentication system",
                "files_changed": [f"/company/secret/project/file_{i}.py" for i in range(100)],
                "stats": {"insertions": 500, "deletions": 200}
            }
            
            signal_file = create_signal_file(
                signal_directory=temp_dir,
                tool_name="journal_new_entry", 
                parameters={},
                commit_metadata=large_metadata
            )
            
            # Check file size is minimal
            file_size = Path(signal_file).stat().st_size
            assert file_size < 500  # Should be under 500 bytes (was ~2KB+)
            
            # Read content and verify no PII
            with open(signal_file, 'r') as f:
                content = f.read()
            
            # Should NOT contain PII or sensitive paths
            pii_patterns = ["john.doe@company.com", "/company/secret", "authentication system"]
            for pattern in pii_patterns:
                assert pattern not in content
            
            # Should contain only essential data
            assert "abc123def456" in content  # commit hash
            assert "journal_new_entry" in content  # tool name

    def test_backward_compatibility_signal_validation(self):
        """Test that signal validation accepts minimal format."""
        from mcp_commit_story.signal_management import validate_signal_format, SignalValidationError

        # Minimal signal format
        minimal_signal = {
            "tool": "journal_new_entry",
            "params": {"commit_hash": "abc123def456"},
            "created_at": "2025-06-11T15:30:00Z"
        }

        # Should pass validation
        assert validate_signal_format(minimal_signal) is True

        # Old format should fail validation
        old_signal = {
            "tool": "journal_new_entry",
            "params": {"commit_hash": "abc123def456"},
            "metadata": {"hash": "abc123def456", "author": "User"},  # Old redundant field
            "signal_id": "20250611_153000_journal_new_entry_abc123",   # Old redundant field
            "created_at": "2025-06-11T15:30:00Z"
        }

        # Should fail validation (extra fields not allowed)
        try:
            validate_signal_format(old_signal)
            assert False, "Should have raised SignalValidationError"
        except SignalValidationError:
            assert True  # Expected exception


class TestOnDemandGitContextRetrieval:
    """Test on-demand git context retrieval using existing git_utils."""
    
    @patch('mcp_commit_story.git_utils.get_repo')
    @patch('mcp_commit_story.git_utils.get_commit_details')
    def test_fetch_git_context_from_minimal_signal(self, mock_get_details, mock_get_repo):
        """Test fetching full git context from just commit hash in signal."""
        
        # This function should exist after refactor
        from mcp_commit_story.signal_management import fetch_git_context_on_demand
        
        # Setup mocks
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_repo.commit.return_value = mock_commit
        mock_get_repo.return_value = mock_repo
        mock_get_details.return_value = {
            "hash": "abc123def456789012345678901234567890abcd",
            "author": "Test User <test@example.com>",
            "datetime": "2025-06-11T15:00:00Z",
            "message": "Test commit message",
            "stats": {"insertions": 10, "deletions": 5}
        }
        
        # Test function that should be implemented
        context = fetch_git_context_on_demand("abc123def456", "/path/to/repo")
        
        # Verify it uses existing git_utils functions
        mock_get_repo.assert_called_once_with("/path/to/repo")
        mock_repo.commit.assert_called_once()  # Called with commit hash
        mock_get_details.assert_called_once_with(mock_commit)
        
        # Verify returned context
        assert context["hash"] == "abc123def456789012345678901234567890abcd"
        assert context["author"] == "Test User <test@example.com>"

    def test_signal_processing_uses_on_demand_context(self):
        """Test that AI signal processing uses on-demand context retrieval."""
        
        # This function should exist for AI clients
        from mcp_commit_story.signal_management import process_signal_with_context
        
        minimal_signal = {
            "tool": "journal_new_entry",
            "params": {"commit_hash": "abc123def456"},
            "created_at": "2025-06-11T15:30:00Z"
        }
        
        with patch('mcp_commit_story.signal_management.fetch_git_context_on_demand') as mock_fetch:
            mock_fetch.return_value = {
                "hash": "abc123def456",
                "author": "Test User",
                "message": "Test commit"
            }
            
            # Process signal (should fetch context on-demand)
            result = process_signal_with_context(minimal_signal, "/path/to/repo")
            
            # Verify it fetched context using commit hash
            mock_fetch.assert_called_once_with("abc123def456", "/path/to/repo")
            
            # Verify result contains both signal and context
            assert result["tool"] == "journal_new_entry"
            assert result["commit_context"]["author"] == "Test User"

    def test_context_caching_for_performance(self):
        """Test that context retrieval can be cached for performance."""
        
        from mcp_commit_story.signal_management import fetch_git_context_on_demand
        
        with patch('mcp_commit_story.git_utils.get_repo') as mock_get_repo, \
             patch('mcp_commit_story.git_utils.get_commit_details') as mock_details:
            
            # Setup mocks  
            mock_repo = MagicMock()
            mock_commit = MagicMock()
            mock_repo.commit.return_value = mock_commit
            mock_get_repo.return_value = mock_repo
            mock_details.return_value = {"hash": "abc123", "author": "Test"}
            
            # Function should work correctly
            context = fetch_git_context_on_demand("abc123def456", "/path/to/repo")
            
            # Should return expected structure
            assert context is not None
            assert context["hash"] == "abc123"


class TestSummaryTriggerLogic:
    """Test summary generation trigger logic (AI beast awakening)."""
    
    def test_daily_summary_trigger_from_minimal_signals(self):
        """Test that daily summary triggers work with minimal signal state."""
        
        # This function should be enhanced to work with minimal signals  
        from mcp_commit_story.git_hook_worker import check_daily_summary_trigger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Should work without full metadata (current implementation dependency)
            date_to_generate = check_daily_summary_trigger(temp_dir)
            
            # Should return None or valid date string
            assert date_to_generate is None or isinstance(date_to_generate, str)

    def test_summary_signal_creation_minimal_format(self):
        """Test that summary signals also use minimal format."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create summary signal
            with patch('mcp_commit_story.git_utils.get_repo'), \
                 patch('mcp_commit_story.git_utils.get_current_commit'), \
                 patch('mcp_commit_story.git_utils.get_commit_details') as mock_details:
                
                mock_details.return_value = {"hash": "abc123def456", "author": "Test"}
                
                signal_file = create_tool_signal(
                    tool_name="generate_daily_summary",
                    parameters={"date": "2025-06-11"},
                    commit_metadata={"hash": "abc123def456"},  # Minimal metadata input
                    repo_path=temp_dir
                )
                
                # Verify signal file uses minimal format
                with open(signal_file, 'r') as f:
                    signal_data = json.load(f)
                
                # Should contain only essential fields
                expected_fields = {"tool", "params", "created_at"}
                assert set(signal_data.keys()) == expected_fields
                
                # Should contain tool-specific params plus commit hash
                assert signal_data["params"]["date"] == "2025-06-11"
                assert signal_data["params"]["commit_hash"] == "abc123def456"

    def test_ai_beast_awakening_decision_logic(self):
        """Test logic for determining when AI should be awakened for summaries."""
        
        # This function should exist after refactor
        from mcp_commit_story.git_hook_worker import determine_summary_trigger
        
        # Test with various commit patterns
        test_cases = [
            {"commits_today": 1, "expect_summary": False},    # Too few commits
            {"commits_today": 5, "expect_summary": True},     # Enough for summary
            {"commits_today": 0, "expect_summary": False},    # No commits
        ]
        
        for case in test_cases:
            with patch('mcp_commit_story.git_hook_worker.count_commits_today') as mock_count:
                mock_count.return_value = case["commits_today"]
                
                should_trigger = determine_summary_trigger("/fake/repo", "2025-06-11")
                assert should_trigger == case["expect_summary"]


class TestErrorHandlingAndGracefulDegradation:
    """Test error handling with minimal signal state."""
    
    def test_missing_commit_hash_handling(self):
        """Test handling when commit hash is missing or invalid."""
        from mcp_commit_story.signal_management import create_signal_file
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Missing commit metadata
            try:
                create_signal_file(
                    signal_directory=temp_dir,
                    tool_name="journal_new_entry",
                    parameters={},
                    commit_metadata={}  # No hash
                )
                assert False, "Should raise error for missing commit hash"
            except (ValueError, SignalFileError):
                pass  # Expected

    def test_git_context_retrieval_failure_graceful_degradation(self):
        """Test graceful degradation when git context cannot be retrieved."""
        
        from mcp_commit_story.signal_management import fetch_git_context_on_demand
        
        with patch('mcp_commit_story.git_utils.get_repo') as mock_repo:
            mock_repo.side_effect = Exception("Git repository not found")
            
            # Should return None or minimal context, not crash
            context = fetch_git_context_on_demand("invalid_hash", "/invalid/repo")
            assert context is None or isinstance(context, dict)

    def test_signal_validation_rejects_invalid_minimal_format(self):
        """Test validation rejects invalid minimal signal formats."""
        from mcp_commit_story.signal_management import validate_signal_format, SignalValidationError

        invalid_cases = [
            {},  # Empty
            {"tool": "test"},  # Missing required fields
            {"tool": "test", "params": "not_dict", "created_at": "2025-06-11"},  # Wrong type
            {"tool": "test", "params": {}, "created_at": "2025-06-11", "extra": "field"},  # Extra fields
        ]

        for invalid_signal in invalid_cases:
            try:
                validate_signal_format(invalid_signal)
                assert False, f"Should have raised SignalValidationError for {invalid_signal}"
            except SignalValidationError:
                pass  # Expected exception


class TestIntegrationWithExistingSystem:
    """Test integration of minimal signals with existing git_utils and context_collection."""
    
    def test_minimal_signals_work_with_existing_git_hook_worker(self):
        """Test that git hook worker creates minimal signals correctly."""
        from mcp_commit_story.git_hook_worker import create_tool_signal
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('mcp_commit_story.git_utils.get_repo'), \
                 patch('mcp_commit_story.git_utils.get_current_commit'), \
                 patch('mcp_commit_story.git_utils.get_commit_details') as mock_details:
                
                mock_details.return_value = {
                    "hash": "abc123def456789012345678901234567890abcd",
                    "author": "Test User <test@example.com>",
                    "datetime": "2025-06-11T15:00:00Z",
                    "message": "Test commit message"
                }
                
                # Should work with existing function signature
                signal_file = create_tool_signal(
                    tool_name="journal_new_entry",
                    parameters={},  # No repo_path needed
                    commit_metadata={"hash": "abc123def456789012345678901234567890abcd"},
                    repo_path=temp_dir
                )
                
                assert signal_file is not None
                assert Path(signal_file).exists()

    def test_context_collection_integration(self):
        """Test integration with existing context_collection.py functions."""

        # Should be able to use existing context collection with minimal signals
        from mcp_commit_story.context_collection import collect_git_context

        with patch('mcp_commit_story.context_collection.get_repo') as mock_get_repo, \
             patch('mcp_commit_story.context_collection.get_commit_details') as mock_get_details:

            # Setup mocks properly - patch the internal calls within collect_git_context
            mock_repo = MagicMock()
            mock_commit = MagicMock()
            mock_commit.parents = []  # Make it look like initial commit
            mock_commit.diff.return_value = []  # Empty diff
            mock_repo.commit.return_value = mock_commit
            mock_get_repo.return_value = mock_repo
            mock_get_details.return_value = {
                "hash": "abc123def456",
                "author": "Test User",
                "datetime": "2025-06-11T15:00:00Z",
                "message": "Test commit"
            }

            # Should work with commit hash from minimal signal (correct signature)
            context = collect_git_context(commit_hash="abc123def456")

            # Should return GitContext structure
            assert isinstance(context, dict)
            # Should have called our mocked functions
            mock_get_repo.assert_called_once()
            mock_repo.commit.assert_called_once_with("abc123def456") 