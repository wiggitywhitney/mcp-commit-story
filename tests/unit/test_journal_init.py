import os
import shutil
import stat
import pytest
from pathlib import Path

from mcp_commit_story.journal_init import create_journal_directories, generate_default_config


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


def test_generate_default_config_creates_new(tmp_path):
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    assert not config_path.exists()
    generate_default_config(config_path, "journal/")
    assert config_path.exists()
    content = config_path.read_text()
    assert "journal:" in content
    assert "path:" in content


def test_generate_default_config_backs_up_existing(tmp_path):
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal: {}\n")
    generate_default_config(config_path, "journal/")
    # Old file should be backed up
    backups = list(tmp_path.glob(".mcp-commit-storyrc.yaml.bak*"))
    assert backups, "Backup file not created"
    assert config_path.exists()
    content = config_path.read_text()
    assert "journal:" in content
    assert "path:" in content


def test_generate_default_config_malformed_file(tmp_path):
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal: [unclosed_list\n")
    generate_default_config(config_path, "journal/")
    backups = list(tmp_path.glob(".mcp-commit-storyrc.yaml.bak*"))
    assert backups, "Backup file not created for malformed config"
    assert config_path.exists()
    content = config_path.read_text()
    assert "journal:" in content
    assert "path:" in content


def test_generate_default_config_backup_naming(tmp_path):
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    config_path.write_text("journal: {}\n")
    generate_default_config(config_path, "journal/")
    # Create again to force multiple backups
    generate_default_config(config_path, "journal/")
    backups = list(tmp_path.glob(".mcp-commit-storyrc.yaml.bak*"))
    assert len(backups) >= 2, "Multiple backups should be created with unique names"


def test_generate_default_config_permission_error(tmp_path):
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    # Make directory read-only
    os.chmod(tmp_path, stat.S_IREAD)
    with pytest.raises(PermissionError):
        generate_default_config(config_path, "journal/")
    # Restore permissions for cleanup
    os.chmod(tmp_path, stat.S_IWRITE) 