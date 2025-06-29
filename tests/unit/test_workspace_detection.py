"""
Unit tests for workspace detection functionality.

Tests the fuzzy matching workspace detection strategy that finds the correct
Cursor workspace database based on git repository path using git remote URL matching,
folder path matching, and folder name similarity with fallback to most recent.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import sqlite3
import tempfile
import os

# Import the module we're about to create (will fail initially - that's expected in TDD)
try:
    from mcp_commit_story.cursor_db.workspace_detection import (
        detect_workspace_for_repo,
        WorkspaceMatch,
        WorkspaceDetectionError,
        _scan_workspace_directories,
        _extract_workspace_info,
        _calculate_match_confidence,
        _get_git_remote_urls,
        _get_most_recent_workspace,
        CONFIDENCE_THRESHOLD
    )
except ImportError:
    # Expected to fail initially in TDD
    pytest.skip("Workspace detection module not yet implemented", allow_module_level=True)


class TestWorkspaceDetection:
    """Test core workspace detection functionality."""
    
    def test_detect_workspace_for_repo_git_remote_match(self, tmp_path):
        """Test workspace detection using git remote URL matching (highest confidence)."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Mock git remote URL
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = "https://github.com/user/test-repo.git\n"
            mock_run.return_value.returncode = 0
            
            # Mock workspace scanning
            with patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories') as mock_scan:
                mock_workspace = WorkspaceMatch(
                    path=Path("/cursor/workspace/abc123/state.vscdb"),
                    confidence=0.95,
                    match_type="git_remote",
                    workspace_folder="file:///Users/user/test_repo",
                    git_remote="https://github.com/user/test-repo.git"
                )
                mock_scan.return_value = [mock_workspace]
                
                result = detect_workspace_for_repo(str(repo_path))
                
                assert result.path == Path("/cursor/workspace/abc123/state.vscdb")
                assert result.confidence == 0.95
                assert result.match_type == "git_remote"
    
    def test_detect_workspace_for_repo_folder_path_match(self, tmp_path):
        """Test workspace detection using folder path matching (medium confidence)."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Mock git command failure (no remote)
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            
            # Mock workspace scanning
            with patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories') as mock_scan:
                mock_workspace = WorkspaceMatch(
                    path=Path("/cursor/workspace/def456/state.vscdb"),
                    confidence=0.85,
                    match_type="folder_path",
                    workspace_folder=f"file://{repo_path}",
                    git_remote=None
                )
                mock_scan.return_value = [mock_workspace]
                
                result = detect_workspace_for_repo(str(repo_path))
                
                assert result.path == Path("/cursor/workspace/def456/state.vscdb")
                assert result.confidence == 0.85
                assert result.match_type == "folder_path"
    
    def test_detect_workspace_for_repo_folder_name_similarity(self, tmp_path):
        """Test workspace detection using folder name similarity (low confidence)."""
        repo_path = tmp_path / "my-awesome-project"
        repo_path.mkdir()
        
        # Mock git command failure
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            
            # Mock workspace scanning
            with patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories') as mock_scan:
                mock_workspace = WorkspaceMatch(
                    path=Path("/cursor/workspace/ghi789/state.vscdb"),
                    confidence=0.82,
                    match_type="folder_name",
                    workspace_folder="file:///Users/user/my_awesome_project_backup",
                    git_remote=None
                )
                mock_scan.return_value = [mock_workspace]
                
                result = detect_workspace_for_repo(str(repo_path))
                
                assert result.path == Path("/cursor/workspace/ghi789/state.vscdb")
                assert result.confidence == 0.82
                assert result.match_type == "folder_name"
    
    def test_detect_workspace_for_repo_fallback_most_recent(self, tmp_path):
        """Test fallback to most recently modified workspace when no good matches."""
        repo_path = tmp_path / "unmatched_repo"
        repo_path.mkdir()
        
        # Mock git command failure
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            
            # Mock workspace scanning with low confidence matches
            with patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories') as mock_scan:
                low_confidence_workspace = WorkspaceMatch(
                    path=Path("/cursor/workspace/low123/state.vscdb"),
                    confidence=0.3,  # Below threshold
                    match_type="folder_name",
                    workspace_folder="file:///Users/user/different_project",
                    git_remote=None
                )
                mock_scan.return_value = [low_confidence_workspace]
                
                # Mock most recent workspace selection
                with patch('mcp_commit_story.cursor_db.workspace_detection._get_most_recent_workspace') as mock_recent:
                    recent_workspace = WorkspaceMatch(
                        path=Path("/cursor/workspace/recent999/state.vscdb"),
                        confidence=0.0,  # Fallback has no confidence
                        match_type="most_recent",
                        workspace_folder="file:///Users/user/some_other_project",
                        git_remote=None
                    )
                    mock_recent.return_value = recent_workspace
                    
                    result = detect_workspace_for_repo(str(repo_path))
                    
                    assert result.path == Path("/cursor/workspace/recent999/state.vscdb")
                    assert result.confidence == 0.0
                    assert result.match_type == "most_recent"
    
    def test_detect_workspace_for_repo_no_workspaces_found(self, tmp_path):
        """Test error handling when no workspaces are found at all."""
        repo_path = tmp_path / "empty_repo"
        repo_path.mkdir()
        
        # Mock empty workspace scanning
        with patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories') as mock_scan:
            mock_scan.return_value = []
            
            with patch('mcp_commit_story.cursor_db.workspace_detection._get_most_recent_workspace') as mock_recent:
                mock_recent.return_value = None
                
                with pytest.raises(WorkspaceDetectionError, match="No Cursor workspaces found"):
                    detect_workspace_for_repo(str(repo_path))
    
    def test_detect_workspace_for_repo_invalid_repo_path(self):
        """Test error handling for invalid repository path."""
        with pytest.raises(WorkspaceDetectionError, match="Repository path does not exist"):
            detect_workspace_for_repo("/nonexistent/repo/path")


class TestWorkspaceScanning:
    """Test workspace directory scanning functionality."""
    
    @patch('mcp_commit_story.cursor_db.platform.get_cursor_workspace_paths')
    def test_scan_workspace_directories(self, mock_get_workspace_paths, tmp_path):
        """Test scanning of workspace directories and workspace.json extraction."""
        # Setup mock workspace storage directory
        storage_path = tmp_path / "workspaceStorage"
        storage_path.mkdir()
        mock_get_workspace_paths.return_value = [storage_path]
        
        # Create mock workspace directories with workspace.json files
        workspace1 = storage_path / "abc123hash"
        workspace1.mkdir()
        workspace1_json = workspace1 / "workspace.json"
        workspace1_json.write_text(json.dumps({
            "folder": "file:///Users/user/project1"
        }))
        
        workspace2 = storage_path / "def456hash"
        workspace2.mkdir()
        workspace2_json = workspace2 / "workspace.json"
        workspace2_json.write_text(json.dumps({
            "folder": "file:///Users/user/project2"
        }))
        
        # Create state.vscdb files
        (workspace1 / "state.vscdb").touch()
        (workspace2 / "state.vscdb").touch()
        
        repo_path = "/Users/user/test_repo"
        
        # Mock git remote URLs
        with patch('mcp_commit_story.cursor_db.workspace_detection._get_git_remote_urls') as mock_git:
            mock_git.return_value = ["https://github.com/user/test-repo.git"]
            
            # Mock confidence calculation to ensure we only process our test data
            with patch('mcp_commit_story.cursor_db.workspace_detection._calculate_match_confidence') as mock_confidence:
                mock_confidence.side_effect = [(0.85, "git_remote"), (0.3, "folder_name")]  # First workspace matches better
                
                # Make sure we only scan the test directory, not real ones
                with patch('mcp_commit_story.cursor_db.workspace_detection.get_cursor_workspace_paths') as mock_paths:
                    mock_paths.return_value = [storage_path]
                    
                    result = _scan_workspace_directories(repo_path)
                    
                    assert len(result) == 2
                    assert result[0].confidence == 0.85  # Sorted by confidence
                    assert result[1].confidence == 0.3
                    assert all(isinstance(match, WorkspaceMatch) for match in result)
    
    def test_scan_workspace_directories_missing_workspace_json(self, tmp_path):
        """Test handling of workspace directories without workspace.json."""
        storage_path = tmp_path / "workspaceStorage"
        storage_path.mkdir()
        
        # Create workspace directory without workspace.json
        workspace1 = storage_path / "abc123hash"
        workspace1.mkdir()
        (workspace1 / "state.vscdb").touch()
        
        with patch('mcp_commit_story.cursor_db.workspace_detection._get_git_remote_urls', return_value=[]):
            with patch('mcp_commit_story.cursor_db.workspace_detection.get_cursor_workspace_paths', return_value=[storage_path]):
                result = _scan_workspace_directories("/test/repo")
                
                # Should handle missing workspace.json gracefully
                assert len(result) == 0
    
    def test_scan_workspace_directories_corrupted_json(self, tmp_path):
        """Test handling of corrupted workspace.json files."""
        storage_path = tmp_path / "workspaceStorage"
        storage_path.mkdir()
        
        workspace1 = storage_path / "abc123hash"
        workspace1.mkdir()
        workspace1_json = workspace1 / "workspace.json"
        workspace1_json.write_text("{ invalid json content")
        (workspace1 / "state.vscdb").touch()
        
        with patch('mcp_commit_story.cursor_db.workspace_detection._get_git_remote_urls', return_value=[]):
            with patch('mcp_commit_story.cursor_db.workspace_detection.get_cursor_workspace_paths', return_value=[storage_path]):
                result = _scan_workspace_directories("/test/repo")
                
                # Should handle corrupted JSON gracefully
                assert len(result) == 0


class TestMatchConfidenceCalculation:
    """Test workspace match confidence calculation logic."""
    
    def test_calculate_match_confidence_git_remote_exact_match(self):
        """Test confidence calculation for exact git remote URL match."""
        repo_git_remotes = ["https://github.com/user/test-repo.git"]
        workspace_info = {
            "folder": "file:///Users/user/test_repo",
            "git_remote": "https://github.com/user/test-repo.git"
        }
        
        confidence, match_type = _calculate_match_confidence(
            "/Users/user/test_repo", repo_git_remotes, workspace_info
        )
        
        assert confidence >= 0.95
        assert match_type == "git_remote"
    
    def test_calculate_match_confidence_folder_path_exact_match(self):
        """Test confidence calculation for exact folder path match."""
        repo_git_remotes = []
        workspace_info = {
            "folder": "file:///Users/user/test_repo"
        }
        
        confidence, match_type = _calculate_match_confidence(
            "/Users/user/test_repo", repo_git_remotes, workspace_info
        )
        
        assert 0.8 <= confidence < 0.9
        assert match_type == "folder_path"
    
    def test_calculate_match_confidence_folder_name_similarity(self):
        """Test confidence calculation for folder name similarity."""
        repo_git_remotes = []
        workspace_info = {
            "folder": "file:///Users/user/my_awesome_project_backup"
        }
        
        confidence, match_type = _calculate_match_confidence(
            "/Users/user/my-awesome-project", repo_git_remotes, workspace_info
        )
        
        assert 0.6 <= confidence < 0.9  # Should be decent similarity
        assert match_type == "folder_name"
    
    def test_calculate_match_confidence_no_match(self):
        """Test confidence calculation when there's no meaningful match."""
        repo_git_remotes = []
        workspace_info = {
            "folder": "file:///Users/user/completely_different_project"
        }
        
        confidence, match_type = _calculate_match_confidence(
            "/Users/user/my_project", repo_git_remotes, workspace_info
        )
        
        assert confidence < 0.6
        assert match_type == "folder_name"  # Still tries folder name as last resort


class TestGitOperations:
    """Test git-related utility functions."""
    
    @patch('subprocess.run')
    def test_get_git_remote_urls_success(self, mock_run):
        """Test successful extraction of git remote URLs."""
        mock_run.return_value.stdout = "origin\thttps://github.com/user/repo.git (fetch)\norigin\thttps://github.com/user/repo.git (push)\n"
        mock_run.return_value.returncode = 0
        
        result = _get_git_remote_urls("/test/repo")
        
        assert result == ["https://github.com/user/repo.git"]
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_git_remote_urls_multiple_remotes(self, mock_run):
        """Test extraction with multiple git remotes."""
        mock_run.return_value.stdout = (
            "origin\thttps://github.com/user/repo.git (fetch)\n"
            "upstream\thttps://github.com/original/repo.git (fetch)\n"
        )
        mock_run.return_value.returncode = 0
        
        result = _get_git_remote_urls("/test/repo")
        
        assert len(result) == 2
        assert "https://github.com/user/repo.git" in result
        assert "https://github.com/original/repo.git" in result
    
    @patch('subprocess.run')
    def test_get_git_remote_urls_no_remotes(self, mock_run):
        """Test handling when repository has no remotes."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 0
        
        result = _get_git_remote_urls("/test/repo")
        
        assert result == []
    
    @patch('subprocess.run')
    def test_get_git_remote_urls_git_command_failure(self, mock_run):
        """Test handling when git command fails."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Not a git repository"
        
        result = _get_git_remote_urls("/test/repo")
        
        assert result == []


class TestFallbackStrategies:
    """Test fallback workspace selection strategies."""
    
    @patch('mcp_commit_story.cursor_db.platform.get_cursor_workspace_paths')
    def test_get_most_recent_workspace(self, mock_get_workspace_paths, tmp_path):
        """Test selection of most recently modified workspace."""
        storage_path = tmp_path / "workspaceStorage"
        storage_path.mkdir()
        mock_get_workspace_paths.return_value = [storage_path]
        
        # Create workspaces with different modification times
        workspace1 = storage_path / "old_workspace"
        workspace1.mkdir()
        db1 = workspace1 / "state.vscdb"
        db1.touch()
        
        workspace2 = storage_path / "recent_workspace"  
        workspace2.mkdir()
        db2 = workspace2 / "state.vscdb"
        db2.touch()
        
        # Modify timestamps (recent_workspace is newer)
        old_time = time.time() - 3600  # 1 hour ago
        recent_time = time.time() - 60   # 1 minute ago
        
        os.utime(db1, (old_time, old_time))
        os.utime(db2, (recent_time, recent_time))
        
        # Mock inside the function to ensure only test paths are scanned
        with patch('mcp_commit_story.cursor_db.workspace_detection.get_cursor_workspace_paths', return_value=[storage_path]):
            result = _get_most_recent_workspace()
            
            assert result.path == db2
            assert result.match_type == "most_recent"
            assert result.confidence == 0.0  # Fallback has no confidence
    
    @patch('mcp_commit_story.cursor_db.platform.get_cursor_workspace_paths')
    def test_get_most_recent_workspace_no_databases(self, mock_get_workspace_paths, tmp_path):
        """Test handling when no workspace databases exist."""
        storage_path = tmp_path / "workspaceStorage"
        storage_path.mkdir()
        mock_get_workspace_paths.return_value = [storage_path]
        
        # Mock inside the function to ensure only test paths are scanned
        with patch('mcp_commit_story.cursor_db.workspace_detection.get_cursor_workspace_paths', return_value=[storage_path]):
            result = _get_most_recent_workspace()
            
            assert result is None


class TestWorkspaceDetectionTelemetry:
    """Test telemetry instrumentation for workspace detection."""
    
    def test_detect_workspace_for_repo_has_trace_decorator(self):
        """Test that main detection function has @trace_mcp_operation decorator."""
        assert hasattr(detect_workspace_for_repo, '__wrapped__'), \
            "detect_workspace_for_repo should have @trace_mcp_operation decorator"
    
    @patch('opentelemetry.trace.get_current_span')
    def test_detect_workspace_telemetry_attributes(self, mock_get_span, tmp_path):
        """Test that proper telemetry attributes are set during detection."""
        mock_span = MagicMock()
        mock_get_span.return_value = mock_span
        
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Mock successful detection
        with patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories') as mock_scan:
            mock_workspace = WorkspaceMatch(
                path=Path("/cursor/workspace/abc123/state.vscdb"),
                confidence=0.95,
                match_type="git_remote",
                workspace_folder="file:///Users/user/test_repo",
                git_remote="https://github.com/user/test-repo.git"
            )
            mock_scan.return_value = [mock_workspace]
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.stdout = "https://github.com/user/test-repo.git\n"
                mock_run.return_value.returncode = 0
                
                detect_workspace_for_repo(str(repo_path))
        
        # Verify telemetry attributes were set
        expected_calls = [
            call("repo_path", str(repo_path)),
            call("detection_strategy", "workspace_json_match"),
            call("candidates_found", 1),
            call("match_confidence", 0.95),
            call("match_type", "git_remote"),
            call("fallback_used", False),
        ]
        
        for expected_call in expected_calls:
            assert expected_call in mock_span.set_attribute.call_args_list


class TestDataStructures:
    """Test data structures and constants."""
    
    def test_workspace_match_dataclass_structure(self):
        """Test WorkspaceMatch dataclass has required fields."""
        match = WorkspaceMatch(
            path=Path("/test/path"),
            confidence=0.85,
            match_type="git_remote",
            workspace_folder="file:///test/folder",
            git_remote="https://github.com/user/repo.git"
        )
        
        assert match.path == Path("/test/path")
        assert match.confidence == 0.85
        assert match.match_type == "git_remote"
        assert match.workspace_folder == "file:///test/folder"
        assert match.git_remote == "https://github.com/user/repo.git"
    
    def test_confidence_threshold_constant(self):
        """Test that confidence threshold constant is properly defined."""
        assert CONFIDENCE_THRESHOLD == 0.8
        assert isinstance(CONFIDENCE_THRESHOLD, float)


class TestErrorHandling:
    """Test comprehensive error handling."""
    
    def test_workspace_detection_error_creation(self):
        """Test WorkspaceDetectionError can be created with context."""
        error = WorkspaceDetectionError(
            "Test error message",
            repo_path="/test/repo",
            candidates_scanned=5,
            fallback_attempted=True
        )
        
        assert str(error) == "Test error message"
        assert error.repo_path == "/test/repo"
        assert error.candidates_scanned == 5
        assert error.fallback_attempted is True
    
    @patch('mcp_commit_story.cursor_db.workspace_detection._scan_workspace_directories')
    def test_detect_workspace_handles_scanning_errors(self, mock_scan, tmp_path):
        """Test that detection gracefully handles scanning errors."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Mock scanning error
        mock_scan.side_effect = PermissionError("Access denied to workspace storage")
        
        with pytest.raises(WorkspaceDetectionError, match="Failed to scan workspace directories"):
            detect_workspace_for_repo(str(repo_path)) 