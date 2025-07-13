"""
Test for the PosixPath bug in git context collection.

This test reproduces the issue where collect_git_context() fails when passed
a pathlib.Path object instead of a string for the repo parameter.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import git

from mcp_commit_story.context_collection import collect_git_context


def test_collect_git_context_with_posixpath_object():
    """Test that collect_git_context() properly handles pathlib.Path objects for repo parameter."""
    
    # Create a mock repo object
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc123"
    mock_commit.parents = [MagicMock()]  # Has parent commits
    mock_commit.diff.return_value = []  # Empty diff for simplicity
    mock_repo.commit.return_value = mock_commit
    mock_repo.working_tree_dir = "/fake/repo"
    
    # Mock the get_repo function to return our mock repo
    with patch('mcp_commit_story.context_collection.get_repo') as mock_get_repo:
        mock_get_repo.return_value = mock_repo
        
        # Mock other functions called by collect_git_context
        with patch('mcp_commit_story.context_collection.get_commit_details') as mock_details:
            mock_details.return_value = {
                'hash': 'abc123',
                'author': 'Test Author',
                'datetime': '2025-01-15T10:00:00',
                'message': 'Test commit',
                'stats': {'insertions': 10, 'deletions': 5}
            }
            
            with patch('mcp_commit_story.context_collection.get_commit_diff_summary') as mock_diff:
                mock_diff.return_value = "Test diff summary"
                
                with patch('mcp_commit_story.context_collection.classify_file_type') as mock_classify:
                    mock_classify.return_value = 'source'
                    
                    with patch('mcp_commit_story.context_collection.classify_commit_size') as mock_size:
                        mock_size.return_value = 'medium'
                        
                        # Test with Path object - this should work without errors
                        repo_path = Path("/fake/repo/path")
                        
                        try:
                            result = collect_git_context(
                                commit_hash="abc123",
                                repo=repo_path,  # Pass Path object, not string
                                journal_path=None
                            )
                            
                            # Verify get_repo was called with string conversion of Path
                            mock_get_repo.assert_called_once_with(str(repo_path))
                            
                            # Verify we got a proper result structure
                            assert isinstance(result, dict)
                            assert 'metadata' in result
                            assert 'diff_summary' in result
                            assert 'changed_files' in result
                            assert 'file_stats' in result
                            assert 'commit_context' in result
                            
                        except AttributeError as e:
                            # This is the bug we're testing for - Path objects don't have commit() method
                            if "'PosixPath' object has no attribute 'commit'" in str(e):
                                pytest.fail(f"PosixPath bug reproduced: {e}")
                            else:
                                raise


def test_collect_git_context_with_string_path():
    """Test that collect_git_context() works correctly with string paths (baseline)."""
    
    # Create a mock repo object
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc123"
    mock_commit.parents = [MagicMock()]  # Has parent commits
    mock_commit.diff.return_value = []  # Empty diff for simplicity
    mock_repo.commit.return_value = mock_commit
    mock_repo.working_tree_dir = "/fake/repo"
    
    # Mock the get_repo function to return our mock repo
    with patch('mcp_commit_story.context_collection.get_repo') as mock_get_repo:
        mock_get_repo.return_value = mock_repo
        
        # Mock other functions called by collect_git_context
        with patch('mcp_commit_story.context_collection.get_commit_details') as mock_details:
            mock_details.return_value = {
                'hash': 'abc123',
                'author': 'Test Author',
                'datetime': '2025-01-15T10:00:00',
                'message': 'Test commit',
                'stats': {'insertions': 10, 'deletions': 5}
            }
            
            with patch('mcp_commit_story.context_collection.get_commit_diff_summary') as mock_diff:
                mock_diff.return_value = "Test diff summary"
                
                with patch('mcp_commit_story.context_collection.classify_file_type') as mock_classify:
                    mock_classify.return_value = 'source'
                    
                    with patch('mcp_commit_story.context_collection.classify_commit_size') as mock_size:
                        mock_size.return_value = 'medium'
                        
                        # Test with string path - this should work
                        repo_path = "/fake/repo/path"
                        
                        result = collect_git_context(
                            commit_hash="abc123",
                            repo=repo_path,  # Pass string path
                            journal_path=None
                        )
                        
                        # Verify get_repo was called with the string path
                        mock_get_repo.assert_called_once_with(repo_path)
                        
                        # Verify we got a proper result structure
                        assert isinstance(result, dict)
                        assert 'metadata' in result
                        assert 'diff_summary' in result
                        assert 'changed_files' in result
                        assert 'file_stats' in result
                        assert 'commit_context' in result


def test_collect_git_context_with_git_repo_object():
    """Test that collect_git_context() works correctly with git.Repo objects."""
    
    # Create a mock repo object
    mock_repo = MagicMock(spec=git.Repo)
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc123"
    mock_commit.parents = [MagicMock()]  # Has parent commits
    mock_commit.diff.return_value = []  # Empty diff for simplicity
    mock_repo.commit.return_value = mock_commit
    mock_repo.working_tree_dir = "/fake/repo"
    
    # Mock other functions called by collect_git_context
    with patch('mcp_commit_story.context_collection.get_commit_details') as mock_details:
        mock_details.return_value = {
            'hash': 'abc123',
            'author': 'Test Author',
            'datetime': '2025-01-15T10:00:00',
            'message': 'Test commit',
            'stats': {'insertions': 10, 'deletions': 5}
        }
        
        with patch('mcp_commit_story.context_collection.get_commit_diff_summary') as mock_diff:
            mock_diff.return_value = "Test diff summary"
            
            with patch('mcp_commit_story.context_collection.classify_file_type') as mock_classify:
                mock_classify.return_value = 'source'
                
                with patch('mcp_commit_story.context_collection.classify_commit_size') as mock_size:
                    mock_size.return_value = 'medium'
                    
                    # Test with git.Repo object - this should work
                    result = collect_git_context(
                        commit_hash="abc123",
                        repo=mock_repo,  # Pass git.Repo object directly
                        journal_path=None
                    )
                    
                    # Verify we got a proper result structure
                    assert isinstance(result, dict)
                    assert 'metadata' in result
                    assert 'diff_summary' in result
                    assert 'changed_files' in result
                    assert 'file_stats' in result
                    assert 'commit_context' in result 