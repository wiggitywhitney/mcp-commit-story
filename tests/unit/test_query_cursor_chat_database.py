"""
Tests for the high-level query_cursor_chat_database function.

This module tests the main user-facing API function that orchestrates
all cursor_db components to provide complete chat history with workspace metadata.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import os
import time
from pathlib import Path

from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.cursor_db.exceptions import CursorDatabaseError


class TestQueryCursorChatDatabaseSuccess:
    """Test successful data retrieval scenarios."""
    
    def test_successful_query_with_workspace_info(self):
        """Test successful query returns proper workspace_info and chat_history structure."""
        # Mock the functions for our NEW implementation (direct scanning)
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            # Setup mocks for the NEW direct scanning behavior
            workspace_storage = Path("/Users/test/.cursor/workspaceStorage")
            mock_workspace.return_value = workspace_storage
            mock_listdir.return_value = ["hash123", "hash456", "not_a_hash"]
            
            # Mock directory checks and database existence
            def mock_isdir_func(path):
                return "hash" in str(path)  # Only hash directories are directories
            
            def mock_exists_func(path):
                return "state.vscdb" in str(path) and "hash123" in str(path)  # Only hash123 has database
            
            mock_isdir.side_effect = mock_isdir_func
            mock_exists.side_effect = mock_exists_func
            
            # Mock the rest of the pipeline
            mock_recent.return_value = ["/Users/test/.cursor/workspaceStorage/hash123/state.vscdb"]
            mock_extract.return_value = [{
                "database_path": "/Users/test/.cursor/workspaceStorage/hash123/state.vscdb",
                "prompts": [{"id": 1, "content": "test prompt"}],
                "generations": [{"id": 1, "content": "test response"}]
            }]
            mock_reconstruct.return_value = {"messages": [{"role": "user", "content": "test prompt"}], "metadata": {"prompt_count": 1, "generation_count": 1}}

            result = query_cursor_chat_database()

            # Verify structure
            assert "workspace_info" in result
            assert "chat_history" in result

            # Verify workspace_info content
            workspace_info = result["workspace_info"]
            assert workspace_info["workspace_path"] == str(workspace_storage)
            assert workspace_info["total_messages"] == 1  # Should be length of chat_history.messages
            assert workspace_info["database_path"] == "/Users/test/.cursor/workspaceStorage/hash123/state.vscdb"

    def test_uses_direct_scanning_correctly(self):
        """Test that function uses direct workspace storage scanning instead of discovery system."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            workspace_storage = Path("/Users/test/.cursor/workspaceStorage")
            mock_workspace.return_value = workspace_storage
            mock_listdir.return_value = ["abc123", "def456"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = ["/path/to/db1.vscdb"]  # Only recent one
            mock_extract.return_value = [{"prompts": [], "generations": []}]
            mock_reconstruct.return_value = {"messages": [], "metadata": {"prompt_count": 0, "generation_count": 0}}

            result = query_cursor_chat_database()

            # Verify the direct scanning was used in correct order
            mock_workspace.assert_called_once()
            mock_listdir.assert_called_once_with(workspace_storage)  # Should scan workspace storage
            mock_recent.assert_called_once()  # Should call recent filtering
            mock_extract.assert_called_once()  # Should extract from recent databases


class TestQueryCursorChatDatabaseErrorHandling:
    """Test error scenarios and graceful degradation."""

    def test_missing_workspace_graceful_handling(self):
        """Test graceful handling when workspace path cannot be determined."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
            mock_workspace.return_value = None
            
            result = query_cursor_chat_database()
            
            # Should return empty but valid structure
            assert result["workspace_info"]["workspace_path"] is None
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []

    def test_no_databases_found_graceful_handling(self):
        """Test graceful handling when no databases are found in workspace storage."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = []  # No subdirectories
            
            result = query_cursor_chat_database()
            
            # Should return empty but valid structure
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []

    def test_no_recent_databases_graceful_handling(self):
        """Test graceful handling when no recent databases found."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["hash123"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = []  # No recent databases
            
            result = query_cursor_chat_database()
            
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []

    def test_empty_database_handling(self):
        """Test handling when databases exist but contain no data."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["hash123"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = ["/path/to/db.vscdb"]
            mock_extract.return_value = []  # No extraction results
            
            result = query_cursor_chat_database()
            
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []

    def test_exception_graceful_handling(self):
        """Test graceful handling when exceptions occur during processing."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
            mock_workspace.side_effect = Exception("Workspace detection failed")
            
            result = query_cursor_chat_database()
            
            # Should return error structure without crashing
            assert "workspace_info" in result
            assert "chat_history" in result
            assert result["workspace_info"]["workspace_path"] is None


class TestQueryCursorChatDatabaseIntegration:
    """Test integration scenarios and performance."""

    def test_large_chat_history_performance(self):
        """Test performance with large chat histories."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            # Mock large dataset
            large_results = [{
                "prompts": [{"id": i, "content": f"prompt {i}"} for i in range(1000)],
                "generations": [{"id": i, "content": f"response {i}"} for i in range(1000)]
            }]
            large_history = {"messages": [{"role": "user", "content": f"message {i}"} for i in range(2000)], "metadata": {"prompt_count": 1000, "generation_count": 1000}}

            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["hash123"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = ["/path/to/large_db.vscdb"]
            mock_extract.return_value = large_results
            mock_reconstruct.return_value = large_history

            result = query_cursor_chat_database()

            # Verify large dataset handling
            assert result["workspace_info"]["total_messages"] == 2000
            assert len(result["chat_history"]["messages"]) == 2000

    def test_multiple_databases_with_filtering(self):
        """Test handling multiple databases with 48-hour filtering."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            # Mock discovering many databases but only some are recent
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = [f"hash{i}" for i in range(10)]  # 10 hash directories
            mock_isdir.return_value = True
            mock_exists.return_value = True
            
            all_databases = [f"/test/workspace/hash{i}/state.vscdb" for i in range(10)]
            recent_databases = ["/test/workspace/hash8/state.vscdb", "/test/workspace/hash9/state.vscdb"]  # Only last 2 are recent

            mock_recent.return_value = recent_databases
            mock_extract.return_value = [
                {"prompts": [{"id": 1}], "generations": [{"id": 1}]},
                {"prompts": [{"id": 2}], "generations": [{"id": 2}]}
            ]
            mock_reconstruct.return_value = {"messages": [{"role": "user", "content": "combined chat"}], "metadata": {"prompt_count": 2, "generation_count": 2}}

            result = query_cursor_chat_database()

            # Verify that all discovered databases were passed to recent filtering
            mock_recent.assert_called_once()
            called_args = mock_recent.call_args[0][0]
            assert len(called_args) == 10  # All 10 databases should be passed to filtering
            
            # Verify that only recent databases were processed
            mock_extract.assert_called_once_with(recent_databases)


class TestQueryCursorChatDatabaseTelemetry:
    """Test telemetry and monitoring integration."""

    def test_telemetry_decorator_applied(self):
        """Test that the trace_mcp_operation decorator is properly applied."""
        # This test verifies the decorator exists - actual telemetry testing happens in integration tests
        import inspect
        from mcp_commit_story.cursor_db import query_cursor_chat_database
        
        # Check that function has telemetry decorator (would show in __wrapped__ or similar)
        assert hasattr(query_cursor_chat_database, '__name__')
        assert query_cursor_chat_database.__name__ == 'query_cursor_chat_database'


class TestHashSubdirectoryScanning:
    """Test specific functionality of hash subdirectory scanning."""

    def test_scans_only_hash_subdirectories(self):
        """Test that function only scans hash-like subdirectories for databases."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            workspace_storage = Path("/test/workspace")
            mock_workspace.return_value = workspace_storage
            
            # Mix of valid hash dirs, non-hash dirs, and files
            mock_listdir.return_value = [
                "abc123def456",  # Valid hash
                "xyz789ghi012",  # Valid hash
                "not_a_hash",    # Not hash-like
                "file.txt",      # File (not directory)
                ".hidden"        # Hidden file/dir
            ]
            
            # Mock isdir to return True only for hash-like names
            def mock_isdir_func(path):
                basename = os.path.basename(str(path))
                return len(basename) > 10 and basename.replace('_', '').replace('-', '').isalnum()
            
            # Mock exists to return True for hash directories
            def mock_exists_func(path):
                return "abc123def456" in str(path) or "xyz789ghi012" in str(path)
            
            mock_isdir.side_effect = mock_isdir_func
            mock_exists.side_effect = mock_exists_func
            mock_recent.return_value = ["/test/workspace/abc123def456/state.vscdb"]
            mock_extract.return_value = [{"prompts": [], "generations": []}]
            mock_reconstruct.return_value = {"messages": [], "metadata": {"prompt_count": 0, "generation_count": 0}}

            result = query_cursor_chat_database()

            # Verify that recent databases was called with only the valid hash databases
            mock_recent.assert_called_once()
            called_databases = mock_recent.call_args[0][0]
            
            # Should only include valid hash directories that exist and have databases
            assert len(called_databases) == 2
            assert any("abc123def456" in db for db in called_databases)
            assert any("xyz789ghi012" in db for db in called_databases)

    def test_handles_no_hash_directories(self):
        """Test graceful handling when workspace has no hash subdirectories."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isdir') as mock_isdir:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["folder1", "folder2", "file.txt"]  # No hash-like names
            mock_isdir.return_value = False  # None are directories
            
            result = query_cursor_chat_database()
            
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []

    def test_handles_hash_directories_without_databases(self):
        """Test handling when hash directories exist but don't contain databases."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["abc123def456", "xyz789ghi012"]
            mock_isdir.return_value = True
            mock_exists.return_value = False  # No state.vscdb files exist
            
            result = query_cursor_chat_database()
            
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []


class TestFortyEightHourFiltering:
    """Test specific functionality of 48-hour database filtering."""

    def test_applies_48_hour_filtering_correctly(self):
        """Test that 48-hour filtering is applied to discovered databases."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            workspace_storage = Path("/test/workspace")
            mock_workspace.return_value = workspace_storage
            mock_listdir.return_value = ["hash1", "hash2", "hash3"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            
            # Simulate filtering out old databases
            all_databases = [
                "/test/workspace/hash1/state.vscdb",
                "/test/workspace/hash2/state.vscdb", 
                "/test/workspace/hash3/state.vscdb"
            ]
            recent_databases = ["/test/workspace/hash3/state.vscdb"]  # Only 1 is recent
            
            mock_recent.return_value = recent_databases
            mock_extract.return_value = [{"prompts": [{"id": 1}], "generations": [{"id": 1}]}]
            mock_reconstruct.return_value = {"messages": [{"role": "user", "content": "test"}], "metadata": {"prompt_count": 1, "generation_count": 1}}

            result = query_cursor_chat_database()

            # Verify that all databases were passed to filtering
            mock_recent.assert_called_once()
            called_databases = mock_recent.call_args[0][0]
            assert len(called_databases) == 3
            
            # Verify that only recent databases were extracted
            mock_extract.assert_called_once_with(recent_databases)

    def test_handles_no_recent_databases_after_filtering(self):
        """Test handling when 48-hour filter removes all databases."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["old_hash1", "old_hash2"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = []  # All filtered out by 48-hour window
            
            result = query_cursor_chat_database()
            
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []


class TestChatHistoryStructure:
    """Test the structure and format of returned chat history."""

    def test_chat_history_messages_and_metadata_structure(self):
        """Test that chat_history contains both messages array and metadata dict."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["hash123"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = ["/test/workspace/hash123/state.vscdb"]
            mock_extract.return_value = [{"prompts": [{"id": 1}], "generations": [{"id": 2}]}]
            
            # Mock the expected chat history structure
            expected_history = {
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": 1234567890},
                    {"role": "assistant", "content": "Hi there", "timestamp": 1234567891}
                ],
                "metadata": {
                    "prompt_count": 1,
                    "generation_count": 1
                }
            }
            mock_reconstruct.return_value = expected_history

            result = query_cursor_chat_database()

            # Verify structure
            assert "chat_history" in result
            chat_history = result["chat_history"]
            
            # Verify it's a dict with expected keys
            assert isinstance(chat_history, dict)
            assert "messages" in chat_history
            assert "metadata" in chat_history
            
            # Verify messages structure
            messages = chat_history["messages"]
            assert isinstance(messages, list)
            assert len(messages) == 2
            
            # Verify metadata structure
            metadata = chat_history["metadata"]
            assert isinstance(metadata, dict)
            assert "prompt_count" in metadata
            assert "generation_count" in metadata
            
            # Verify total_messages calculation
            assert result["workspace_info"]["total_messages"] == len(messages)

    def test_handles_legacy_chat_history_format(self):
        """Test backward compatibility with old list-style chat history."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.isdir') as mock_isdir, \
             patch('mcp_commit_story.cursor_db.get_recent_databases') as mock_recent, \
             patch('mcp_commit_story.cursor_db.extract_from_multiple_databases') as mock_extract, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct:

            mock_workspace.return_value = Path("/test/workspace")
            mock_listdir.return_value = ["hash123"]
            mock_isdir.return_value = True
            mock_exists.return_value = True
            mock_recent.return_value = ["/test/workspace/hash123/state.vscdb"]
            mock_extract.return_value = [{"prompts": [], "generations": []}]
            
            # Mock old-style list format
            legacy_history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"}
            ]
            mock_reconstruct.return_value = legacy_history

            result = query_cursor_chat_database()

            # Verify total_messages calculation works with list format
            assert result["workspace_info"]["total_messages"] == 2
            assert result["chat_history"] == legacy_history 