import os
import pytest
from unittest import mock
from pathlib import Path
from mcp_commit_story import journal_generate as journal

# Assume these will be imported from the journal module
# from mcp_commit_story.journal import get_journal_file_path, append_to_journal_file, create_journal_directories

@pytest.mark.parametrize("date, entry_type, expected_path", [
    ("2025-05-14", "daily", "journal/daily/2025-05-14-journal.md"),
    ("2025-05-14", "daily_summary", "journal/summaries/daily/2025-05-14-summary.md"),
    ("2025-05-01_07", "weekly_summary", "journal/summaries/weekly/2025-05-01_07-weekly.md"),
    ("2025-05", "monthly_summary", "journal/summaries/monthly/2025-05-monthly.md"),
    ("2025", "yearly_summary", "journal/summaries/yearly/2025-yearly.md"),
])
def test_get_journal_file_path(date, entry_type, expected_path):
    path = journal.get_journal_file_path(date=date, entry_type=entry_type)
    assert str(path) == expected_path

def test_append_to_journal_file_creates_and_appends(tmp_path):
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
    file_path = tmp_path / "journal" / "daily" / "2025-05-14-journal.md"
    entry = "### 2025-05-14 09:00 — Commit abc123\n\nFirst entry."
    # Simulate permission error
    with mock.patch("builtins.open", side_effect=PermissionError):
        with pytest.raises(ValueError):
            journal.append_to_journal_file(entry, file_path) 