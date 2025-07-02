"""
Tests for composer integration functionality.

Tests the integration between workspace detection and Composer database access,
focusing on workspace hash extraction and database path construction.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.mcp_commit_story.cursor_db.composer_integration import find_workspace_composer_databases
from src.mcp_commit_story.cursor_db.workspace_detection import WorkspaceMatch


class TestWorkspaceHashRegression:
    """Test for the workspace_hash attribute regression bug."""
    

    def test_workspace_match_does_not_have_workspace_hash_attribute(self):
        """Verify that WorkspaceMatch class doesn't have workspace_hash attribute."""
        workspace_match = WorkspaceMatch(
            path=Path("/Users/test/.cursor/workspaceStorage/abc123hash/state.vscdb"),
            confidence=0.85,
            match_type="folder_path",
            workspace_folder="file:///Users/test/project",
            git_remote=None
        )
        
        # Verify the object doesn't have workspace_hash attribute
        assert not hasattr(workspace_match, 'workspace_hash')
        
        # Verify it does have the path attribute (which contains the hash)
        assert hasattr(workspace_match, 'path')
        assert workspace_match.path.parent.name == "abc123hash"  # This should be the workspace hash


class TestWorkspaceHashFix:
    """Test that the workspace hash extraction fix works correctly."""
    
    @patch('src.mcp_commit_story.cursor_db.composer_integration.detect_workspace_for_repo')
    @patch('pathlib.Path.exists')
    def test_find_workspace_composer_databases_extracts_hash_from_path(self, mock_exists, mock_detect_workspace):
        """Test that find_workspace_composer_databases can extract workspace hash from path."""
        # Create a WorkspaceMatch object with a realistic path
        workspace_match = WorkspaceMatch(
            path=Path("/Users/test/.cursor/workspaceStorage/abc123hash/state.vscdb"),
            confidence=0.85,
            match_type="folder_path",
            workspace_folder="file:///Users/test/project",
            git_remote=None
        )
        
        mock_detect_workspace.return_value = workspace_match
        
        # Mock that the database files exist
        mock_exists.return_value = True
        
        # This should now work and return the correct paths
        workspace_db_path, global_db_path = find_workspace_composer_databases("/test/repo")
        
        # Verify the paths are constructed correctly
        expected_workspace_path = str(Path.home() / ".cursor" / "workspaceStorage" / "abc123hash" / "state.vscdb")
        expected_global_path = str(Path.home() / ".cursor" / "globalStorage" / "state.vscdb")
        
        assert workspace_db_path == expected_workspace_path
        assert global_db_path == expected_global_path
        
        # Verify detect_workspace_for_repo was called with correct repo path
        mock_detect_workspace.assert_called_once_with("/test/repo")
    
    @patch('src.mcp_commit_story.cursor_db.composer_integration.detect_workspace_for_repo')
    def test_find_workspace_composer_databases_handles_empty_hash(self, mock_detect_workspace):
        """Test that find_workspace_composer_databases handles case where workspace hash is empty."""
        # Create a WorkspaceMatch object with a path that would result in empty hash
        workspace_match = WorkspaceMatch(
            path=Path("/state.vscdb"),  # No parent directory, so parent.name would be empty
            confidence=0.85,
            match_type="folder_path",
            workspace_folder="file:///Users/test/project",
            git_remote=None
        )
        
        mock_detect_workspace.return_value = workspace_match
        
        # This should fail with a meaningful error about missing workspace hash
        with pytest.raises(Exception, match="No workspace hash found for repository"):
            find_workspace_composer_databases("/test/repo") 