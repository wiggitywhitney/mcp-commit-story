import pytest
import os
import shutil
import tempfile
import git

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