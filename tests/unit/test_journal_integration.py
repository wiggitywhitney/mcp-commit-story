import pytest
from mcp_commit_story import journal
from mcp_commit_story.context_types import JournalContext

def test_journal_entry_full_round_trip():
    # Fully populated context
    ctx = JournalContext(
        summary="Implemented all features.",
        technical_synopsis="Refactored core modules and added tests.",
        accomplishments=["All tests passing", "Full coverage achieved"],
        frustrations=["Mocking file system errors was tricky"],
        tone_mood={"mood": "Relieved", "indicators": "All edge cases handled."},
        discussion_notes=[{"speaker": "Dev", "text": "Should we use mock or patch?"}],
        terminal_commands=["pytest", "git commit -m 'done'"],
        commit_metadata={"files_changed": "5", "insertions": "100", "deletions": "10"}
    )
    # Generate all sections (except tone_mood, use actual context for integration)
    summary = journal.generate_summary_section(ctx)
    tech = journal.generate_technical_synopsis_section(ctx)
    acc = journal.generate_accomplishments_section(ctx)
    frus = journal.generate_frustrations_section(ctx)
    # PATCH: Use actual tone_mood from context
    tone = ctx["tone_mood"]
    disc = journal.generate_discussion_notes_section(ctx)
    term = journal.generate_terminal_commands_section(ctx)
    meta = journal.generate_commit_metadata_section(ctx)
    # Assemble JournalEntry
    entry = journal.JournalEntry(
        timestamp="2025-05-25 17:00",
        commit_hash="deadbeef",
        summary=summary["summary"],
        technical_synopsis=tech["technical_synopsis"],
        accomplishments=acc["accomplishments"],
        frustrations=frus["frustrations"],
        tone_mood=tone,
        discussion_notes=disc["discussion_notes"],
        terminal_commands=term["terminal_commands"],
        commit_metadata=meta["commit_metadata"]
    )
    md = entry.to_markdown()
    parsed = journal.JournalParser.parse(md)
    # Assert round-trip integrity
    assert parsed.summary == entry.summary
    assert parsed.technical_synopsis == entry.technical_synopsis
    assert parsed.accomplishments == entry.accomplishments
    assert parsed.frustrations == entry.frustrations
    assert parsed.tone_mood == entry.tone_mood
    assert parsed.discussion_notes == entry.discussion_notes
    assert parsed.terminal_commands == entry.terminal_commands
    assert parsed.commit_metadata == entry.commit_metadata

def test_journal_entry_partial_context():
    """Test integration pipeline with partial context - functions return empty data structures gracefully."""
    # Partial context: only summary and technical_synopsis
    ctx = JournalContext(
        summary="Partial entry.",
        technical_synopsis="Only core modules updated."
    )
    summary = journal.generate_summary_section(ctx)
    tech = journal.generate_technical_synopsis_section(ctx)
    acc = journal.generate_accomplishments_section(ctx)
    frus = journal.generate_frustrations_section(ctx)
    tone = journal.generate_tone_mood_section(ctx)
    disc = journal.generate_discussion_notes_section(ctx)
    term = journal.generate_terminal_commands_section(ctx)
    meta = journal.generate_commit_metadata_section(ctx)
    entry = journal.JournalEntry(
        timestamp="2025-05-25 17:01",
        commit_hash="cafebabe",
        summary=summary["summary"],
        technical_synopsis=tech["technical_synopsis"],
        accomplishments=acc["accomplishments"],
        frustrations=frus["frustrations"],
        tone_mood=tone,
        discussion_notes=disc["discussion_notes"],
        terminal_commands=term["terminal_commands"],
        commit_metadata=meta["commit_metadata"]
    )
    md = entry.to_markdown()
    parsed = journal.JournalParser.parse(md)
    assert parsed.summary == entry.summary
    assert parsed.technical_synopsis == entry.technical_synopsis
    # All other fields should be empty or omitted
    assert parsed.accomplishments == []
    assert parsed.frustrations == []
    assert parsed.tone_mood is None or parsed.tone_mood == {"mood": "", "indicators": ""}
    assert parsed.discussion_notes == []
    assert parsed.terminal_commands == []
    assert parsed.commit_metadata == {}

def test_journal_entry_empty_context():
    """Test integration pipeline with empty context - functions return empty data structures gracefully."""
    # Empty context: all fields missing
    ctx = JournalContext()
    summary = journal.generate_summary_section(ctx)
    tech = journal.generate_technical_synopsis_section(ctx)
    acc = journal.generate_accomplishments_section(ctx)
    frus = journal.generate_frustrations_section(ctx)
    tone = journal.generate_tone_mood_section(ctx)
    disc = journal.generate_discussion_notes_section(ctx)
    term = journal.generate_terminal_commands_section(ctx)
    meta = journal.generate_commit_metadata_section(ctx)
    entry = journal.JournalEntry(
        timestamp="2025-05-25 17:02",
        commit_hash="feedface",
        summary=summary["summary"],
        technical_synopsis=tech["technical_synopsis"],
        accomplishments=acc["accomplishments"],
        frustrations=frus["frustrations"],
        tone_mood=tone,
        discussion_notes=disc["discussion_notes"],
        terminal_commands=term["terminal_commands"],
        commit_metadata=meta["commit_metadata"]
    )
    md = entry.to_markdown()
    parsed = journal.JournalParser.parse(md)
    assert parsed.summary == entry.summary
    assert parsed.technical_synopsis == entry.technical_synopsis
    assert parsed.accomplishments == []
    assert parsed.frustrations == []
    assert parsed.tone_mood is None or parsed.tone_mood == {"mood": "", "indicators": ""}
    assert parsed.discussion_notes == []
    assert parsed.terminal_commands == []
    assert parsed.commit_metadata == {}

# TODO: Add more integration tests for edge cases:
# - Maximal context (very large lists, long strings)
# - Malformed context (invalid types, missing required fields)
# - Markdown with extra/unknown sections
# - Markdown with missing headers or out-of-order sections 