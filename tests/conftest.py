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
        # Initialize a new git repo
        repo = git.Repo.init(temp_dir)
        # Create a file and commit it
        file_path = os.path.join(temp_dir, 'file1.txt')
        with open(file_path, 'w') as f:
            f.write('hello world\n')
        repo.index.add(['file1.txt'])
        repo.index.commit('initial commit')
        # Yield the repo object for use in tests
        yield repo
    finally:
        # Cleanup: remove the temp directory
        shutil.rmtree(temp_dir) 