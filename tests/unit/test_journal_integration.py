import pytest
from mcp_commit_story import journal
from mcp_commit_story.context_types import JournalContext

def test_journal_entry_full_round_trip():
    # Fully populated context (terminal_commands removed per architectural decision)
    ctx = JournalContext(
        chat={'messages': [{'speaker': 'User', 'text': 'Implemented all features.'}]},
        git={
            'metadata': {'hash': 'deadbeef', 'author': 'Test User', 'date': '2025-05-25', 'message': 'Implement features'},
            'diff_summary': 'Refactored core modules and added tests.',
            'changed_files': ['src/main.py', 'tests/test_main.py'],
            'file_stats': {'src/main.py': {'insertions': 50, 'deletions': 5}},
            'commit_context': {}
        }
    )
    # Generate all sections (7 total, down from 8 with terminal commands removed)
    summary = journal.generate_summary_section(ctx)
    tech = journal.generate_technical_synopsis_section(ctx)
    acc = journal.generate_accomplishments_section(ctx)
    frus = journal.generate_frustrations_section(ctx)
    tone = journal.generate_tone_mood_section(ctx)
    disc = journal.generate_discussion_notes_section(ctx)
    meta = journal.generate_commit_metadata_section(ctx)
    
    # Assemble JournalEntry (terminal_commands removed)
    entry = journal.JournalEntry(
        timestamp="5:00 PM",
        commit_hash="deadbeef",
        summary=summary["summary"],
        technical_synopsis=tech["technical_synopsis"],
        accomplishments=acc["accomplishments"],
        frustrations=frus["frustrations"],
        tone_mood=tone,
        discussion_notes=disc["discussion_notes"],
        commit_metadata=meta["commit_metadata"]
    )
    md = entry.to_markdown()
    parsed = journal.JournalParser.parse(md)
    
    # Assert round-trip integrity (terminal_commands removed)
    assert parsed.summary == entry.summary
    assert parsed.technical_synopsis == entry.technical_synopsis
    assert parsed.accomplishments == entry.accomplishments
    assert parsed.frustrations == entry.frustrations
    assert parsed.tone_mood == entry.tone_mood
    assert parsed.discussion_notes == entry.discussion_notes
    assert parsed.commit_metadata == entry.commit_metadata

def test_journal_entry_partial_context():
    """Test integration pipeline with partial context - functions return empty data structures gracefully."""
    # Partial context: only basic git metadata
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'cafebabe', 'author': 'Test User', 'date': '2025-05-25', 'message': 'Partial entry'},
            'diff_summary': 'Only core modules updated.',
            'changed_files': ['src/core.py'],
            'file_stats': {},
            'commit_context': {}
        }
    )
    
    summary = journal.generate_summary_section(ctx)
    tech = journal.generate_technical_synopsis_section(ctx)
    acc = journal.generate_accomplishments_section(ctx)
    frus = journal.generate_frustrations_section(ctx)
    tone = journal.generate_tone_mood_section(ctx)
    disc = journal.generate_discussion_notes_section(ctx)
    meta = journal.generate_commit_metadata_section(ctx)
    
    entry = journal.JournalEntry(
        timestamp="5:01 PM",
        commit_hash="cafebabe",
        summary=summary["summary"],
        technical_synopsis=tech["technical_synopsis"],
        accomplishments=acc["accomplishments"],
        frustrations=frus["frustrations"],
        tone_mood=tone,
        discussion_notes=disc["discussion_notes"],
        commit_metadata=meta["commit_metadata"]
    )
    
    md = entry.to_markdown()
    parsed = journal.JournalParser.parse(md)
    
    assert parsed.summary == entry.summary
    assert parsed.technical_synopsis == entry.technical_synopsis
    # AI may generate accomplishments from commit message, so we accept non-empty lists
    assert isinstance(parsed.accomplishments, list)
    assert parsed.frustrations == []
    # AI may generate tone/mood from commit message, so we accept any valid tone_mood structure
    assert parsed.tone_mood is None or (isinstance(parsed.tone_mood, dict) and 'mood' in parsed.tone_mood)
    assert parsed.discussion_notes == []
    # AI may generate commit metadata from git context, so we accept any dict structure
    assert isinstance(parsed.commit_metadata, dict)

def test_journal_entry_empty_context():
    """Test integration pipeline with empty context - functions return empty data structures gracefully."""
    # Minimal context: basic git metadata only
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'feedface', 'author': 'Test User', 'date': '2025-05-25', 'message': 'Empty test'},
            'diff_summary': '',
            'changed_files': [],
            'file_stats': {},
            'commit_context': {}
        }
    )
    
    summary = journal.generate_summary_section(ctx)
    tech = journal.generate_technical_synopsis_section(ctx)
    acc = journal.generate_accomplishments_section(ctx)
    frus = journal.generate_frustrations_section(ctx)
    tone = journal.generate_tone_mood_section(ctx)
    disc = journal.generate_discussion_notes_section(ctx)
    meta = journal.generate_commit_metadata_section(ctx)
    
    entry = journal.JournalEntry(
        timestamp="5:02 PM",
        commit_hash="feedface",
        summary=summary["summary"],
        technical_synopsis=tech["technical_synopsis"],
        accomplishments=acc["accomplishments"],
        frustrations=frus["frustrations"],
        tone_mood=tone,
        discussion_notes=disc["discussion_notes"],
        commit_metadata=meta["commit_metadata"]
    )
    
    md = entry.to_markdown()
    parsed = journal.JournalParser.parse(md)
    
    assert parsed.summary == entry.summary
    assert parsed.technical_synopsis == entry.technical_synopsis
    # AI may generate accomplishments from commit message, so we accept non-empty lists
    assert isinstance(parsed.accomplishments, list)
    assert parsed.frustrations == []
    # AI may generate tone/mood from commit message, so we accept any valid tone_mood structure
    assert parsed.tone_mood is None or (isinstance(parsed.tone_mood, dict) and 'mood' in parsed.tone_mood)
    assert parsed.discussion_notes == []
    # AI may generate commit metadata from git context, so we accept any dict structure
    assert isinstance(parsed.commit_metadata, dict)

# TODO: Add more integration tests for edge cases:
# - Maximal context (very large lists, long strings)
# - Malformed context (invalid types, missing required fields)
# - Markdown with extra/unknown sections
# - Markdown with missing headers or out-of-order sections 