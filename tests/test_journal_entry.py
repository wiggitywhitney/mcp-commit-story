import pytest
from mcp_commit_story.journal import JournalEntry


def test_header_includes_timestamp_and_commit_hash():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="2cc11c5"
    )
    md = entry.to_markdown()
    assert md.startswith("### 2025-05-20 08:10 — Commit 2cc11c5")


def test_terminal_commands_rendered_as_code_block():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        terminal_commands=["pytest tests/", "git status"]
    )
    md = entry.to_markdown()
    assert "```bash" in md
    assert "pytest tests/" in md
    assert "git status" in md
    assert "Commands executed by AI during this work session:" in md


def test_discussion_notes_with_speaker_attribution():
    notes = [
        {"speaker": "Human", "text": "Should we simplify the process?"},
        {"speaker": "Agent", "text": "Yes, you can skip team steps."}
    ]
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        discussion_notes=notes
    )
    md = entry.to_markdown()
    assert "> **Human:** Should we simplify the process?" in md
    assert "> **Agent:** Yes, you can skip team steps." in md


def test_discussion_notes_plain_string_fallback():
    notes = [
        "This is a plain note."
    ]
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        discussion_notes=notes
    )
    md = entry.to_markdown()
    assert "> This is a plain note." in md


def test_multiline_summary_and_discussion_notes():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Line one.\nLine two.",
        discussion_notes=[
            {"speaker": "Human", "text": "First line.\nSecond line."}
        ]
    )
    md = entry.to_markdown()
    assert "Line one.\nLine two." in md
    assert "> **Human:** First line.\n> Second line." in md


def test_very_long_entry_formatting():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="A" * 1000,
        accomplishments=[f"Accomplishment {i}" for i in range(50)],
        frustrations=[f"Frustration {i}" for i in range(50)],
        terminal_commands=[f"cmd_{i}" for i in range(50)],
        discussion_notes=[{"speaker": "Human", "text": f"Note {i}"} for i in range(50)],
        tone_mood={"mood": "Relieved", "indicators": "All tests passed."},
        behind_the_commit={"files_changed": "10", "insertions": "100", "deletions": "5"}
    )
    md = entry.to_markdown()
    assert "A" * 1000 in md
    assert "- Accomplishment 0" in md
    assert "- Frustration 0" in md
    assert "cmd_0" in md
    assert "> **Human:** Note 0" in md
    assert "> Relieved" in md
    assert "> All tests passed." in md
    assert "- **files_changed:** 10" in md


def test_mood_inference_omitted_if_no_evidence():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123"
    )
    md = entry.to_markdown()
    assert "Tone/Mood" not in md


def test_tone_mood_blockquote_formatting():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        tone_mood={"mood": "Relieved", "indicators": "All tests passed."}
    )
    md = entry.to_markdown()
    assert "> Relieved" in md
    assert "> All tests passed." in md


def test_omit_empty_sections():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Only summary"
    )
    md = entry.to_markdown()
    assert "## Summary" in md
    assert "Only summary" in md
    assert "Accomplishments" not in md
    assert "Frustrations" not in md
    assert "Terminal Commands" not in md
    assert "Discussion Notes" not in md
    assert "Tone/Mood" not in md
    assert "Behind the Commit" not in md 