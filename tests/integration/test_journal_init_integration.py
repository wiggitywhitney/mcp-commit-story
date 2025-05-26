import pytest
import subprocess
from pathlib import Path
from mcp_commit_story.journal_init import initialize_journal, create_journal_directories


def test_journal_clean_init(tmp_path):
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


def test_journal_reinit_already_initialized(tmp_path):
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


def test_journal_init_with_existing_files(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    # Only config exists
    config_path.write_text("journal: {}\n")
    result1 = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result1["status"] == "success"
    assert config_path.exists()
    assert journal_path.exists() and journal_path.is_dir()
    # Only journal dir exists
    config_path.unlink()
    if not journal_path.exists():
        journal_path.mkdir()
    result2 = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result2["status"] == "success"
    assert config_path.exists()
    assert journal_path.exists() and journal_path.is_dir()


def test_journal_failure_recovery(tmp_path, monkeypatch):
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