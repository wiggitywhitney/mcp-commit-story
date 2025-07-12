import pytest
import subprocess
from pathlib import Path
from mcp_commit_story.journal_init import initialize_journal
from mcp_commit_story.journal_generate import append_to_journal_file, get_journal_file_path


def test_journal_clean_init(tmp_path):
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    config_path = tmp_path / ".mcp-commit-storyrc.yaml"
    journal_path = tmp_path / "journal"
    result = initialize_journal(repo_path=tmp_path, config_path=config_path, journal_path=journal_path)
    assert result["status"] == "success"
    assert config_path.exists()
    assert journal_path.exists() and journal_path.is_dir()
    # On-demand pattern: only base journal/ directory should exist after init
    assert (journal_path / "daily").exists() is False
    assert (journal_path / "summaries").exists() is False
    assert "config" in result["paths"]
    assert "journal" in result["paths"]
    assert "successfully" in result["message"]


def test_journal_file_operation_creates_needed_dirs(tmp_path):
    """
    Test that writing a journal entry creates the required subdirectories on demand.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    journal_path = tmp_path / "journal"
    initialize_journal(repo_path=tmp_path, journal_path=journal_path)
    file_path = journal_path / "daily" / "2025-05-28-journal.md"
    entry = "### 2025-05-28 — Commit abcdef\n\nTest entry."
    append_to_journal_file(entry, file_path)
    # The parent directory should now exist
    assert (journal_path / "daily").exists()
    assert file_path.exists()
    # Other subdirectories should not exist yet
    assert (journal_path / "summaries").exists() is False


def test_journal_file_operation_deeply_nested(tmp_path):
    """
    Test that writing to a deeply nested summary file creates only the needed directories.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    journal_path = tmp_path / "journal"
    initialize_journal(repo_path=tmp_path, journal_path=journal_path)
    file_path = journal_path / "summaries" / "monthly" / "2025-05-monthly.md"
    entry = "## Monthly Summary\nDid a lot."
    append_to_journal_file(entry, file_path)
    # Only the required nested directories should exist
    assert (journal_path / "summaries").exists()
    assert (journal_path / "summaries" / "monthly").exists()
    assert file_path.exists()
    # Unrelated directories should not exist
    assert (journal_path / "daily").exists() is False
    assert (journal_path / "summaries" / "weekly").exists() is False
    assert (journal_path / "summaries" / "yearly").exists() is False


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