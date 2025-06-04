"""
Tests for journal workflow TypedDict definitions.

Validates that all TypedDict structures work correctly, provide proper
type checking, and maintain compatibility with the existing codebase.
"""

import pytest
from typing import get_type_hints
from unittest.mock import MagicMock
from pathlib import Path

from mcp_commit_story.journal_workflow_types import (
    GenerateJournalEntryInput,
    GenerateJournalEntryResult,
    SaveJournalEntryInput,
    SaveJournalEntryResult,
    JournalOnlyCommitCheck,
    JournalOnlyCommitResult,
    CollectedJournalContext,
    ContextCollectionResult
)
from mcp_commit_story.context_types import GitContext, ChatHistory, TerminalContext


class TestGenerateJournalEntryTypes:
    """Test TypedDicts for journal entry generation (Subtask 9.1)."""

    def test_generate_journal_entry_input_structure(self):
        """Test GenerateJournalEntryInput TypedDict structure."""
        # Valid input data
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        
        input_data: GenerateJournalEntryInput = {
            "commit": mock_commit,
            "config": {"journal": {"path": "journal/"}},
            "debug": False
        }
        
        # Verify all required fields are present
        assert "commit" in input_data
        assert "config" in input_data
        assert "debug" in input_data
        assert input_data["debug"] is False

    def test_generate_journal_entry_input_type_annotations(self):
        """Test that type annotations are correct."""
        hints = get_type_hints(GenerateJournalEntryInput)
        
        assert "commit" in hints
        assert "config" in hints  
        assert "debug" in hints
        # debug should be bool type
        assert hints["debug"] == bool

    def test_generate_journal_entry_result_success(self):
        """Test GenerateJournalEntryResult for successful generation."""
        mock_entry = MagicMock()
        mock_entry.to_markdown.return_value = "# Test Entry"
        
        result: GenerateJournalEntryResult = {
            "entry": mock_entry,
            "skipped": False,
            "skip_reason": None
        }
        
        assert result["entry"] is not None
        assert result["skipped"] is False
        assert result["skip_reason"] is None

    def test_generate_journal_entry_result_skipped(self):
        """Test GenerateJournalEntryResult for skipped generation."""
        result: GenerateJournalEntryResult = {
            "entry": None,
            "skipped": True,
            "skip_reason": "journal_only_commit"
        }
        
        assert result["entry"] is None
        assert result["skipped"] is True
        assert result["skip_reason"] == "journal_only_commit"


class TestJournalOnlyCommitTypes:
    """Test TypedDicts for journal-only commit checking."""

    def test_journal_only_commit_check_structure(self):
        """Test JournalOnlyCommitCheck TypedDict structure."""
        mock_commit = MagicMock()
        
        check_data: JournalOnlyCommitCheck = {
            "commit": mock_commit,
            "journal_path": "journal/"
        }
        
        assert "commit" in check_data
        assert "journal_path" in check_data
        assert check_data["journal_path"] == "journal/"

    def test_journal_only_commit_result_structure(self):
        """Test JournalOnlyCommitResult TypedDict structure."""
        result: JournalOnlyCommitResult = {
            "is_journal_only": True,
            "changed_files": ["journal/daily/2025-06-04.md"]
        }
        
        assert "is_journal_only" in result
        assert "changed_files" in result
        assert isinstance(result["changed_files"], list)
        assert result["is_journal_only"] is True


class TestSaveJournalEntryTypes:
    """Test TypedDicts for journal entry file operations (Subtask 9.2)."""

    def test_save_journal_entry_input_structure(self):
        """Test SaveJournalEntryInput TypedDict structure."""
        mock_entry = MagicMock()
        mock_config = {"journal": {"path": "journal/"}}
        
        input_data: SaveJournalEntryInput = {
            "entry": mock_entry,
            "config": mock_config
        }
        
        assert "entry" in input_data
        assert "config" in input_data
        assert input_data["config"]["journal"]["path"] == "journal/"

    def test_save_journal_entry_result_structure(self):
        """Test SaveJournalEntryResult TypedDict structure."""
        result: SaveJournalEntryResult = {
            "file_path": "/path/to/journal/daily/2025-06-04.md",
            "success": True,
            "created_new_file": False
        }
        
        assert "file_path" in result
        assert "success" in result
        assert "created_new_file" in result
        assert result["success"] is True
        assert result["created_new_file"] is False

    def test_save_journal_entry_result_failure(self):
        """Test SaveJournalEntryResult for failure case."""
        result: SaveJournalEntryResult = {
            "file_path": "",
            "success": False,
            "created_new_file": False
        }
        
        assert result["success"] is False
        assert result["file_path"] == ""


class TestContextCollectionTypes:
    """Test TypedDicts for context collection operations."""

    def test_collected_journal_context_structure(self):
        """Test CollectedJournalContext TypedDict structure."""
        git_context: GitContext = {
            "metadata": {
                "hash": "abc123",
                "author": "Test Author",
                "date": "2025-06-04",
                "message": "Test commit"
            },
            "diff_summary": "Test changes",
            "changed_files": ["test.py"],
            "file_stats": {"source": 1},
            "commit_context": {"size_classification": "small"}
        }
        
        chat_context: ChatHistory = {
            "messages": [{"speaker": "Human", "text": "Test message"}]
        }
        
        context: CollectedJournalContext = {
            "git_context": git_context,
            "chat_context": chat_context,
            "terminal_context": None,
            "config": {"journal": {"path": "journal/"}},
            "collection_timestamp": "2025-06-04T10:00:00Z"
        }
        
        assert "git_context" in context
        assert "chat_context" in context
        assert "terminal_context" in context
        assert "config" in context
        assert "collection_timestamp" in context
        assert context["terminal_context"] is None

    def test_context_collection_result_success(self):
        """Test ContextCollectionResult for successful collection."""
        # Create minimal valid context
        context: CollectedJournalContext = {
            "git_context": {
                "metadata": {"hash": "abc", "author": "test", "date": "2025-06-04", "message": "test"},
                "diff_summary": "test",
                "changed_files": [],
                "file_stats": {},
                "commit_context": {}
            },
            "chat_context": None,
            "terminal_context": None,
            "config": {},
            "collection_timestamp": "2025-06-04T10:00:00Z"
        }
        
        result: ContextCollectionResult = {
            "context": context,
            "collection_success": True,
            "failed_sources": [],
            "warnings": []
        }
        
        assert result["collection_success"] is True
        assert len(result["failed_sources"]) == 0
        assert len(result["warnings"]) == 0

    def test_context_collection_result_partial_failure(self):
        """Test ContextCollectionResult for partial failure."""
        # Create minimal valid context
        context: CollectedJournalContext = {
            "git_context": {
                "metadata": {"hash": "abc", "author": "test", "date": "2025-06-04", "message": "test"},
                "diff_summary": "test", 
                "changed_files": [],
                "file_stats": {},
                "commit_context": {}
            },
            "chat_context": None,
            "terminal_context": None,
            "config": {},
            "collection_timestamp": "2025-06-04T10:00:00Z"
        }
        
        result: ContextCollectionResult = {
            "context": context,
            "collection_success": True,  # Still successful even with some failures
            "failed_sources": ["chat", "terminal"],
            "warnings": ["Chat history unavailable", "Terminal context failed"]
        }
        
        assert result["collection_success"] is True
        assert "chat" in result["failed_sources"]
        assert "terminal" in result["failed_sources"]
        assert len(result["warnings"]) == 2


class TestTypeCompatibility:
    """Test compatibility with existing context types."""

    def test_git_context_compatibility(self):
        """Test that GitContext from context_types works with workflow types."""
        from mcp_commit_story.context_types import GitContext
        
        git_context: GitContext = {
            "metadata": {
                "hash": "test123",
                "author": "Test User", 
                "date": "2025-06-04",
                "message": "Test commit message"
            },
            "diff_summary": "Added test file",
            "changed_files": ["test.py"],
            "file_stats": {"source": 1, "tests": 0},
            "commit_context": {"size_classification": "small", "is_merge": False}
        }
        
        # Should be usable in CollectedJournalContext
        context: CollectedJournalContext = {
            "git_context": git_context,
            "chat_context": None,
            "terminal_context": None,
            "config": {"journal": {"path": "journal/"}},
            "collection_timestamp": "2025-06-04T10:00:00Z"
        }
        
        assert context["git_context"]["metadata"]["hash"] == "test123"

    def test_optional_context_fields(self):
        """Test that optional context fields work correctly."""
        context: CollectedJournalContext = {
            "git_context": {
                "metadata": {"hash": "abc", "author": "test", "date": "2025-06-04", "message": "test"},
                "diff_summary": "test",
                "changed_files": [],
                "file_stats": {},
                "commit_context": {}
            },
            "chat_context": None,  # Optional field
            "terminal_context": None,  # Optional field  
            "config": {},
            "collection_timestamp": "2025-06-04T10:00:00Z"
        }
        
        # Should work with None values
        assert context["chat_context"] is None
        assert context["terminal_context"] is None


class TestTypeValidation:
    """Test type validation and error cases."""

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields cause issues (when using type checker)."""
        # This test documents expected behavior rather than runtime validation
        # since TypedDict doesn't enforce at runtime
        
        # This would fail type checking:
        # incomplete_input: GenerateJournalEntryInput = {
        #     "commit": mock_commit
        #     # Missing "config" and "debug"
        # }
        
        # For runtime testing, we verify the structure expectations
        with pytest.raises(KeyError):
            incomplete_data = {"commit": "test"}
            # Accessing missing key should raise KeyError
            _ = incomplete_data["config"]

    def test_type_hints_accessibility(self):
        """Test that all TypedDict classes have accessible type hints."""
        from typing import get_type_hints
        
        # All workflow types should have accessible type hints
        workflow_types = [
            GenerateJournalEntryInput,
            GenerateJournalEntryResult, 
            SaveJournalEntryInput,
            SaveJournalEntryResult,
            JournalOnlyCommitCheck,
            JournalOnlyCommitResult,
            CollectedJournalContext,
            ContextCollectionResult
        ]
        
        for typed_dict_class in workflow_types:
            hints = get_type_hints(typed_dict_class)
            assert isinstance(hints, dict)
            assert len(hints) > 0  # Should have at least one field


# Integration test
class TestWorkflowTypeIntegration:
    """Test integration between different workflow types."""

    def test_end_to_end_type_flow(self):
        """Test that types work together in a complete workflow."""
        # Simulate the data flow through the types
        
        # 1. Input for journal entry generation
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        
        generate_input: GenerateJournalEntryInput = {
            "commit": mock_commit,
            "config": {"journal": {"path": "journal/"}},
            "debug": False
        }
        
        # 2. Result from journal entry generation
        mock_entry = MagicMock()
        generate_result: GenerateJournalEntryResult = {
            "entry": mock_entry,
            "skipped": False,
            "skip_reason": None
        }
        
        # 3. Input for saving journal entry
        save_input: SaveJournalEntryInput = {
            "entry": generate_result["entry"],
            "config": generate_input["config"]
        }
        
        # 4. Result from saving
        save_result: SaveJournalEntryResult = {
            "file_path": "journal/daily/2025-06-04.md",
            "success": True,
            "created_new_file": True
        }
        
        # Verify the flow works
        assert generate_input["commit"] == mock_commit
        assert save_input["entry"] == mock_entry
        assert save_result["success"] is True 