import os
import shutil
import stat
import pytest
from pathlib import Path
import subprocess
import time

from mcp_commit_story.journal_init import generate_default_config, validate_git_repository, initialize_journal


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
    # Store original permissions
    original_mode = os.stat(tmp_path).st_mode
    try:
        # Make directory read-only
        os.chmod(tmp_path, stat.S_IREAD)
        with pytest.raises(PermissionError):
            generate_default_config(config_path, "journal/")
    finally:
        # Restore original permissions for cleanup
        os.chmod(tmp_path, original_mode)


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
    # Store original permissions
    original_mode = tmp_path.stat().st_mode
    try:
        # Make directory read-only
        tmp_path.chmod(stat.S_IREAD)
        # On some platforms, unreadable dirs may raise FileNotFoundError instead of PermissionError
        with pytest.raises((PermissionError, FileNotFoundError)):
            validate_git_repository(tmp_path)
    finally:
        # Restore original permissions for cleanup
        tmp_path.chmod(original_mode)


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