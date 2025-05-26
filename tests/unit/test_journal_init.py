import os
import shutil
import stat
import pytest
from pathlib import Path

from mcp_commit_story.journal_init import create_journal_directories


def test_create_journal_directories_success(tmp_path):
    base = tmp_path / "journal"
    # Should create daily/ and summaries/ with subdirs
    create_journal_directories(base)
    assert (base / "daily").is_dir()
    assert (base / "summaries" / "daily").is_dir()
    assert (base / "summaries" / "weekly").is_dir()
    assert (base / "summaries" / "monthly").is_dir()
    assert (base / "summaries" / "yearly").is_dir()


def test_create_journal_directories_already_exists(tmp_path):
    base = tmp_path / "journal"
    (base / "daily").mkdir(parents=True)
    (base / "summaries" / "daily").mkdir(parents=True)
    (base / "summaries" / "weekly").mkdir(parents=True)
    (base / "summaries" / "monthly").mkdir(parents=True)
    (base / "summaries" / "yearly").mkdir(parents=True)
    # Should not raise
    create_journal_directories(base)
    # All dirs still exist
    assert (base / "daily").is_dir()
    assert (base / "summaries" / "daily").is_dir()
    assert (base / "summaries" / "weekly").is_dir()
    assert (base / "summaries" / "monthly").is_dir()
    assert (base / "summaries" / "yearly").is_dir()


def test_create_journal_directories_permission_error(tmp_path):
    base = tmp_path / "journal"
    base.mkdir()
    # Remove write permission
    base.chmod(stat.S_IREAD)
    try:
        with pytest.raises(PermissionError):
            create_journal_directories(base)
    finally:
        base.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_create_journal_directories_invalid_path(tmp_path):
    # Use a file instead of a directory
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("not a dir")
    with pytest.raises(Exception):
        create_journal_directories(file_path) 