import os
import shutil
import tempfile
import pytest
from pathlib import Path

from mcp_commit_story.journal_generate import ensure_journal_directory

def setup_temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_path():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)

def test_creates_missing_directories(temp_path):
    file_path = temp_path / "nested/dir/journal.md"
    assert not file_path.parent.exists()
    ensure_journal_directory(file_path)
    assert file_path.parent.exists()
    assert file_path.parent.is_dir()

def test_handles_existing_directories(temp_path):
    dir_path = temp_path / "existing/dir"
    dir_path.mkdir(parents=True)
    file_path = dir_path / "journal.md"
    ensure_journal_directory(file_path)
    assert dir_path.exists()
    assert dir_path.is_dir()

import builtins
from unittest import mock

def test_permission_error(monkeypatch, temp_path):
    file_path = temp_path / "no_permission/journal.md"
    # Simulate permission error on mkdir
    with mock.patch.object(Path, "mkdir", side_effect=PermissionError("No permission")):
        with pytest.raises(PermissionError):
            ensure_journal_directory(file_path)

def test_creates_nested_paths(temp_path):
    file_path = temp_path / "deep/nested/structure/journal.md"
    assert not file_path.parent.exists()
    ensure_journal_directory(file_path)
    assert file_path.parent.exists()
    assert file_path.parent.is_dir() 