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


class TestWorkspacePathMismatch:
    """Test for the workspace path mismatch bug."""
    
    def test_workspace_match_does_not_have_workspace_hash_attribute(self):
        """Verify that WorkspaceMatch class doesn't have workspace_hash attribute."""
        workspace_match = WorkspaceMatch(
            path=Path("/Users/test/Library/Application Support/Cursor/User/workspaceStorage/abc123hash/state.vscdb"),
            confidence=0.85,
            match_type="folder_path",
            workspace_folder="file:///Users/test/project",
            git_remote=None
        )
        
        # Verify the object doesn't have workspace_hash attribute
        assert not hasattr(workspace_match, 'workspace_hash')
        
        # Verify it does have the correct attributes
        assert hasattr(workspace_match, 'path')
        assert workspace_match.path.parent.name == 'abc123hash'

    @patch('src.mcp_commit_story.cursor_db.composer_integration.detect_workspace_for_repo')
    def test_path_mismatch_between_detection_and_construction(self, mock_detect_workspace):
        """Test that demonstrates the path mismatch problem."""
        # Workspace detection finds the CORRECT macOS path
        correct_workspace_path = Path("/Users/test/Library/Application Support/Cursor/User/workspaceStorage/abc123hash/state.vscdb")
        workspace_match = WorkspaceMatch(
            path=correct_workspace_path,
            confidence=0.85,
            match_type="folder_path", 
            workspace_folder="file:///Users/test/project",
            git_remote=None
        )
        
        mock_detect_workspace.return_value = workspace_match
        
        # The function should FAIL because it constructs the wrong path
        # It tries to access ~/.cursor/workspaceStorage/abc123hash/state.vscdb
        # instead of using the correct path from workspace detection
        with pytest.raises(Exception) as exc_info:
            find_workspace_composer_databases("/Users/test/project")
        
        # Should fail because it's looking in the wrong location
        assert "Workspace database not found" in str(exc_info.value)
        
        # The error should show it's trying to access the wrong path (~/.cursor)
        # instead of the correct path found by workspace detection
        
    @patch('src.mcp_commit_story.cursor_db.composer_integration.detect_workspace_for_repo')
    def test_should_use_actual_workspace_path_found_by_detection(self, mock_detect_workspace):
        """Test that the function should use the actual workspace path found by detection."""
        # Setup: workspace detection finds the correct macOS path
        correct_workspace_path = Path("/Users/test/Library/Application Support/Cursor/User/workspaceStorage/abc123hash/state.vscdb")
        correct_global_path = Path("/Users/test/Library/Application Support/Cursor/User/globalStorage/state.vscdb")
        
        workspace_match = WorkspaceMatch(
            path=correct_workspace_path,
            confidence=0.85,
            match_type="folder_path",
            workspace_folder="file:///Users/test/project", 
            git_remote=None
        )
        
        mock_detect_workspace.return_value = workspace_match
        
        # Mock that all database files exist
        with patch('pathlib.Path.exists', return_value=True):
            
            # This should work - use the actual paths found by workspace detection
            workspace_db_path, global_db_path = find_workspace_composer_databases("/Users/test/project")
            
            # Should return the correct paths that were actually found
            assert workspace_db_path == str(correct_workspace_path)
            assert global_db_path == str(correct_global_path)


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


 