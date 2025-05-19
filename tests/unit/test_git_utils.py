import pytest
import os
from unittest.mock import Mock, patch
from pathlib import Path
from mcp_journal.git_utils import (
    is_git_repo, 
    get_repo, 
    get_current_commit, 
    is_journal_only_commit,
    get_commit_details
)

# TDD: Test that GitPython is installed and can instantiate a Repo object
# This test should fail if GitPython is missing or misconfigured

def test_gitpython_import_and_repo_instantiation():
    try:
        import git
        repo = git.Repo(os.getcwd())
        assert repo is not None
    except ImportError:
        pytest.fail("GitPython is not installed. Run: pip install gitpython")
    except git.InvalidGitRepositoryError:
        # Acceptable if not in a git repo, but the import should still succeed
        pass

def test_is_git_repo_valid():
    """Test detection of valid Git repository"""
    with patch('os.path.exists') as mock_exists:
        # Mock .git directory exists
        mock_exists.return_value = True
        
        result = is_git_repo('/fake/repo/path')
        assert result is True
        mock_exists.assert_called_with(os.path.join('/fake/repo/path', '.git'))

def test_is_git_repo_invalid():
    """Test detection of invalid Git repository"""
    with patch('os.path.exists') as mock_exists:
        # Mock .git directory doesn't exist
        mock_exists.return_value = False
        
        result = is_git_repo('/fake/repo/path')
        assert result is False
        mock_exists.assert_called_with(os.path.join('/fake/repo/path', '.git'))

def test_get_repo_with_path():
    """Test getting repo with specific path"""
    with patch('mcp_journal.git_utils.git.Repo') as mock_repo:
        # Setup
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        
        # Call
        result = get_repo('/fake/repo/path')
        
        # Assert
        assert result == mock_repo_instance
        mock_repo.assert_called_with('/fake/repo/path')

def test_get_repo_with_default_path():
    """Test getting repo with default path (current dir)"""
    with patch('mcp_journal.git_utils.git.Repo') as mock_repo, \
         patch('os.getcwd') as mock_getcwd:
        # Setup
        mock_repo_instance = Mock()
        mock_repo.return_value = mock_repo_instance
        mock_getcwd.return_value = '/default/path'
        
        # Call
        result = get_repo()
        
        # Assert
        assert result == mock_repo_instance
        mock_repo.assert_called_with('/default/path')

def test_get_current_commit():
    """Test getting current commit from repo"""
    # Setup mock repo
    mock_repo = Mock()
    mock_commit = Mock()
    mock_repo.head.commit = mock_commit
    
    # Call
    result = get_current_commit(mock_repo)
    
    # Assert
    assert result == mock_commit

def test_is_journal_only_commit_true():
    """Test detecting commit that only modifies journal files"""
    # Setup
    mock_commit = Mock()
    mock_file1 = Mock()
    mock_file1.a_path = 'journal/2023-05-20.md'
    mock_file2 = Mock()
    mock_file2.a_path = 'journal/summaries/weekly.md'
    
    # Mock the diff to return journal files only
    mock_commit.diff.return_value = [mock_file1, mock_file2]
    
    # Call
    result = is_journal_only_commit(mock_commit, 'journal/')
    
    # Assert
    assert result is True

def test_is_journal_only_commit_false():
    """Test detecting commit that modifies non-journal files"""
    # Setup
    mock_commit = Mock()
    mock_file1 = Mock()
    mock_file1.a_path = 'journal/2023-05-20.md'
    mock_file2 = Mock()
    mock_file2.a_path = 'src/main.py'
    
    # Mock the diff to return mixed files
    mock_commit.diff.return_value = [mock_file1, mock_file2]
    
    # Call
    result = is_journal_only_commit(mock_commit, 'journal/')
    
    # Assert
    assert result is False

def test_get_commit_details():
    """Test extracting relevant details from a commit"""
    # Setup
    mock_commit = Mock()
    mock_commit.hexsha = 'abcdef123456'
    mock_commit.message = 'Test commit message'
    mock_commit.committed_date = 1621512345
    mock_commit.author.name = 'Test Author'
    mock_commit.author.email = 'test@example.com'
    
    # Mock the diff stats
    mock_stats = Mock()
    mock_stats.files = {
        'file1.py': {'insertions': 10, 'deletions': 5},
        'file2.py': {'insertions': 3, 'deletions': 2}
    }
    mock_commit.stats = mock_stats
    
    # Call
    result = get_commit_details(mock_commit)
    
    # Assert
    assert result['hash'] == 'abcdef123456'
    assert result['message'] == 'Test commit message'
    assert 'timestamp' in result
    assert result['author'] == 'Test Author <test@example.com>'
    assert result['stats']['files'] == 2
    assert result['stats']['insertions'] == 13
    assert result['stats']['deletions'] == 7 