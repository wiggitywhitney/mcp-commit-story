import pytest
import os
import shutil
import tempfile
import git
from unittest.mock import Mock, patch

@pytest.fixture
def git_repo():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize a new git repo (no commits by default)
        repo = git.Repo.init(temp_dir)
        # Yield the repo object for use in tests
        yield repo
    finally:
        # Cleanup: remove the temp directory
        shutil.rmtree(temp_dir)

@pytest.fixture
def mock_query_cursor_chat_database():
    """Mock fixture for query_cursor_chat_database function."""
    with patch('mcp_commit_story.context_collection.query_cursor_chat_database') as mock:
        yield mock

@pytest.fixture
def mock_filter_chat_for_commit():
    """Mock fixture for filter_chat_for_commit function."""
    with patch('mcp_commit_story.context_collection.filter_chat_for_commit') as mock:
        yield mock

@pytest.fixture
def mock_collect_git_context():
    """Mock fixture for collect_git_context function."""
    with patch('mcp_commit_story.context_collection.collect_git_context') as mock:
        yield mock 