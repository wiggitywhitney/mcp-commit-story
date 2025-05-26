import os
import shutil
import stat
import pytest
from pathlib import Path
import subprocess
import time

from mcp_commit_story.journal_init import create_journal_directories, generate_default_config, validate_git_repository, initialize_journal


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
    time.sleep(0.01)  # Ensure timestamp changes for backup file
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


def test_validate_git_repository_valid(tmp_path):
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    # Should not raise
    validate_git_repository(tmp_path)


def test_validate_git_repository_not_a_repo(tmp_path):
    # Not a git repo
    with pytest.raises(Exception):
        validate_git_repository(tmp_path)


def test_validate_git_repository_bare_repo(tmp_path):
    # Create a bare repo
    subprocess.run(["git", "init", "--bare"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    with pytest.raises(Exception):
        validate_git_repository(tmp_path)


def test_validate_git_repository_permission_error(tmp_path):
    # Make directory read-only
    tmp_path.chmod(stat.S_IREAD)
    try:
        # On some platforms, unreadable dirs may raise FileNotFoundError instead of PermissionError
        with pytest.raises((PermissionError, FileNotFoundError)):
            validate_git_repository(tmp_path)
    finally:
        tmp_path.chmod(stat.S_IWRITE)


def test_initialize_journal_success(tmp_path):
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    result = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result["status"] == "success"
    assert config_path.exists()
    assert journal_path.exists() and journal_path.is_dir()
    assert "config" in result["paths"]
    assert "journal" in result["paths"]
    assert "successfully" in result["message"]


def test_initialize_journal_already_initialized(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    config_path.write_text("journal: {}\n")
    journal_path.mkdir()
    result = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result["status"] == "error"
    assert "already initialized" in result["message"]
    assert result["paths"]["config"] == str(config_path)
    assert result["paths"]["journal"] == str(journal_path)


def test_initialize_journal_partial_failure_and_rollback(tmp_path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    # Simulate failure in create_journal_directories
    def fail_create_journal_directories(path):
        raise OSError("Simulated failure")
    monkeypatch.setattr("mcp_commit_story.journal_init.create_journal_directories", fail_create_journal_directories)
    result = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    # Config should be created, journal should not
    assert result["status"] == "error"
    assert "Failed to create journal directory" in result["message"]
    assert config_path.exists()
    assert not journal_path.exists()
    assert result["paths"].get("config") == str(config_path)


def test_initialize_journal_not_a_git_repo(tmp_path):
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    result = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result["status"] == "error"
    assert "git repository" in result["message"].lower()
    assert not config_path.exists()
    assert not journal_path.exists()


def test_initialize_journal_handles_exceptions(tmp_path, monkeypatch):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    # Simulate unexpected exception in validate_git_repository
    def fail_validate_git_repository(path):
        raise RuntimeError("Unexpected error")
    monkeypatch.setattr("mcp_commit_story.journal_init.validate_git_repository", fail_validate_git_repository)
    result = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result["status"] == "error"
    assert "unexpected error" in result["message"].lower()
    assert not config_path.exists()
    assert not journal_path.exists() 