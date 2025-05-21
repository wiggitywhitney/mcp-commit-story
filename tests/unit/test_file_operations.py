import os
import pytest
from unittest import mock
from pathlib import Path

# Assume these will be imported from the journal module
# from mcp_commit_story.journal import get_journal_file_path, append_to_journal_file, create_journal_directories

@pytest.mark.parametrize("date, entry_type, expected_path", [
    ("2025-05-14", "daily", "journal/daily/2025-05-14-journal.md"),
    ("2025-05-14", "daily_summary", "journal/summaries/daily/2025-05-14-daily.md"),
    ("2025-05-01_07", "weekly_summary", "journal/summaries/weekly/2025-05-01_07-weekly.md"),
    ("2025-05", "monthly_summary", "journal/summaries/monthly/2025-05-monthly.md"),
    ("2025", "yearly_summary", "journal/summaries/yearly/2025-yearly.md"),
])
def test_get_journal_file_path(date, entry_type, expected_path):
    from mcp_commit_story import journal
    path = journal.get_journal_file_path(date=date, entry_type=entry_type)
    assert str(path) == expected_path

def test_create_journal_directories_creates_all_needed_dirs(tmp_path):
    from mcp_commit_story import journal
    base_dir = tmp_path / "journal"
    # Remove if exists
    if base_dir.exists():
        for sub in base_dir.iterdir():
            if sub.is_dir():
                for f in sub.iterdir():
                    f.unlink()
                sub.rmdir()
        base_dir.rmdir()
    # Should create all subdirs
    journal.create_journal_directories(base_dir)
    assert (base_dir / "daily").exists()
    assert (base_dir / "summaries" / "daily").exists()
    assert (base_dir / "summaries" / "weekly").exists()
    assert (base_dir / "summaries" / "monthly").exists()
    assert (base_dir / "summaries" / "yearly").exists()

def test_append_to_journal_file_creates_and_appends(tmp_path):
    from mcp_commit_story import journal
    file_path = tmp_path / "journal" / "daily" / "2025-05-14-journal.md"
    entry1 = "### 2025-05-14 09:00 — Commit abc123\n\nFirst entry."
    entry2 = "### 2025-05-14 10:00 — Commit def456\n\nSecond entry."
    # File does not exist yet
    journal.append_to_journal_file(entry1, file_path)
    with open(file_path) as f:
        content = f.read()
    assert entry1 in content
    # Append second entry
    journal.append_to_journal_file(entry2, file_path)
    with open(file_path) as f:
        content = f.read()
    assert entry1 in content and entry2 in content
    # Should separate entries with a horizontal rule
    assert "\n---\n" in content

def test_append_to_journal_file_handles_filesystem_errors(tmp_path):
    from mcp_commit_story import journal
    file_path = tmp_path / "journal" / "daily" / "2025-05-14-journal.md"
    entry = "### 2025-05-14 09:00 — Commit abc123\n\nFirst entry."
    # Simulate permission error
    with mock.patch("builtins.open", side_effect=PermissionError):
        with pytest.raises(PermissionError):
            journal.append_to_journal_file(entry, file_path) 