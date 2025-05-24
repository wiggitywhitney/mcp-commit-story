import pytest
from mcp_commit_story.journal import JournalEntry, generate_summary_section
from mcp_commit_story.context_types import SummarySection


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


def test_technical_synopsis_section_rendering():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Summary text",
        technical_synopsis="Technical details about code changes.",
        accomplishments=["Did something"],
    )
    md = entry.to_markdown()
    # Technical Synopsis should appear after Summary and before Accomplishments
    summary_idx = md.find("#### Summary")
    tech_idx = md.find("#### Technical Synopsis")
    acc_idx = md.find("#### Accomplishments")
    assert summary_idx != -1
    assert tech_idx != -1
    assert acc_idx != -1
    assert summary_idx < tech_idx < acc_idx
    assert "Technical details about code changes." in md


def test_omit_technical_synopsis_if_empty():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Summary text",
        technical_synopsis=None,
        accomplishments=["Did something"]
    )
    md = entry.to_markdown()
    assert "Technical Synopsis" not in md

    entry2 = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Summary text",
        technical_synopsis="",
        accomplishments=["Did something"]
    )
    md2 = entry2.to_markdown()
    assert "Technical Synopsis" not in md2


def test_very_long_entry_formatting():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="A" * 1000,
        technical_synopsis="B" * 500,
        accomplishments=[f"Accomplishment {i}" for i in range(50)],
        frustrations=[f"Frustration {i}" for i in range(50)],
        terminal_commands=[f"cmd_{i}" for i in range(50)],
        discussion_notes=[{"speaker": "Human", "text": f"Note {i}"} for i in range(50)],
        tone_mood={"mood": "Relieved", "indicators": "All tests passed."},
        behind_the_commit={"files_changed": "10", "insertions": "100", "deletions": "5"}
    )
    md = entry.to_markdown()
    assert "A" * 1000 in md
    assert "B" * 500 in md
    assert "#### Technical Synopsis" in md
    assert "#### Summary" in md
    assert "#### Accomplishments" in md
    assert "#### Frustrations or Roadblocks" in md
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
    assert "#### Summary" in md
    assert "Only summary" in md
    assert "Accomplishments" not in md
    assert "Frustrations" not in md
    assert "Terminal Commands" not in md
    assert "Discussion Notes" not in md
    assert "Tone/Mood" not in md
    assert "Behind the Commit" not in md
    assert "Technical Synopsis" not in md


# --- Journal Entry Format Improvements (Subtask 5.9) ---

def test_horizontal_rule_between_entries():
    entry1 = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Entry 1"
    )
    entry2 = JournalEntry(
        timestamp="2025-05-20 09:00",
        commit_hash="def456",
        summary="Entry 2"
    )
    combined = f"{entry1.to_markdown()}\n---\n{entry2.to_markdown()}"
    assert "\n---\n" in combined
    # Split on the horizontal rule and check that each part starts with the correct header
    parts = combined.split("\n---\n")
    assert parts[0].startswith("### ")
    assert parts[1].startswith("### ")


def test_header_hierarchy():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Test summary",
        accomplishments=["Did something"],
        frustrations=["Hit a bug"]
    )
    md = entry.to_markdown()
    assert md.startswith("### ")
    assert "#### Summary" in md
    assert "#### Accomplishments" in md
    assert "#### Frustrations or Roadblocks" in md


def test_blank_line_on_speaker_change_in_discussion_notes():
    notes = [
        {"speaker": "Human", "text": "First."},
        {"speaker": "Agent", "text": "Second."},
        {"speaker": "Human", "text": "Third."}
    ]
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        discussion_notes=notes
    )
    md = entry.to_markdown()
    # There should be a blank line between speaker changes
    assert "> **Human:** First.\n\n> **Agent:** Second.\n\n> **Human:** Third." in md


def test_spacing_after_section_headers():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Test summary",
        accomplishments=["A"],
        frustrations=["B"]
    )
    md = entry.to_markdown()
    # Each section header should be followed by exactly one blank line
    assert "#### Summary\n\nTest summary" in md
    assert "#### Accomplishments\n\n- A" in md
    assert "#### Frustrations or Roadblocks\n\n- B" in md


def test_terminal_commands_as_code_block():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        terminal_commands=["ls", "pwd"]
    )
    md = entry.to_markdown()
    assert "```bash" in md
    assert "ls" in md
    assert "pwd" in md
    assert md.count("```bash") == 1
    # There should be one opening and one closing code block (total 2)
    assert md.count("```") == 2  # One opening, one closing


def test_spacing_between_bullet_points():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        accomplishments=["A", "B", "C"]
    )
    md = entry.to_markdown()
    # There should be a blank line between bullet points
    assert "- A\n\n- B\n\n- C" in md


def test_blockquote_styling_and_indentation():
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        discussion_notes=[{"speaker": "Human", "text": "Note 1"}, {"speaker": "Agent", "text": "Note 2"}],
        tone_mood={"mood": "Happy", "indicators": "All good."}
    )
    md = entry.to_markdown()
    # Blockquotes should be visually distinct and properly indented
    assert md.count("> ") >= 3
    assert "> **Human:** Note 1" in md
    assert "> **Agent:** Note 2" in md
    assert "> Happy" in md
    assert "> All good." in md


def test_integration_multiple_formatting_rules():
    notes = [
        {"speaker": "Human", "text": "First."},
        {"speaker": "Agent", "text": "Second."},
        {"speaker": "Human", "text": "Third."}
    ]
    entry = JournalEntry(
        timestamp="2025-05-20 08:10",
        commit_hash="abc123",
        summary="Integration summary",
        accomplishments=["A", "B"],
        frustrations=["C"],
        terminal_commands=["ls", "pwd"],
        discussion_notes=notes,
        tone_mood={"mood": "Happy", "indicators": "All good."},
        behind_the_commit={"files_changed": "2", "insertions": "10", "deletions": "1"}
    )
    md = entry.to_markdown()
    # Check for all formatting features
    assert md.startswith("### ")
    assert "#### Summary" in md
    assert "#### Accomplishments" in md
    assert "#### Frustrations or Roadblocks" in md
    assert "```bash" in md
    assert "- A\n\n- B" in md
    assert "> **Human:** First.\n\n> **Agent:** Second.\n\n> **Human:** Third." in md
    assert "> Happy" in md
    assert "> All good." in md
    assert "#### Behind the Commit" in md
    assert "- **files_changed:** 2" in md
    assert "- **insertions:** 10" in md
    assert "- **deletions:** 1" in md


def minimal_context_with_purpose():
    return {
        "chat": {"messages": [
            {"speaker": "Human", "text": "Refactoring because the old code was too slow."}
        ]},
        "git": {"metadata": {"message": "refactor: improve speed"}, "diff_summary": "Refactored foo.py for performance."}
    }

def empty_context():
    return {"chat": {"messages": []}, "git": {"metadata": {"message": ""}, "diff_summary": ""}}

# Pattern 1: In local/dev runs, AI-driven functions return only the placeholder.
# Only test that the placeholder is returned. Full content tests should be run in an AI-invoked or integration environment.

def test_generate_summary_section_returns_placeholder():
    ctx = {"chat": None, "git": None, "terminal": None}
    result = generate_summary_section(ctx)
    assert isinstance(result, dict)
    assert "summary" in result
    assert result["summary"] == ""

# ---
# The following tests are for AI-integration environments only.
# They are skipped in local/dev runs because the function returns only the placeholder.
# Uncomment and use in an environment where the AI agent executes the docstring prompt.
#
# @pytest.mark.skip(reason="Requires AI agent execution")
# def test_generate_summary_section_ai_content():
#     ctx = { ... }  # Provide realistic context
#     result = generate_summary_section(ctx)
#     assert result["summary"]  # Should be non-empty and meaningful
#     # Additional assertions for anti-hallucination, content, etc. 