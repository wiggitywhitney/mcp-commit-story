import pytest
from mcp_commit_story import context_collection, journal
from mcp_commit_story.context_types import ChatHistory, GitContext, JournalContext
from unittest.mock import patch

# --- Context Collection Edge Cases ---
def test_collect_chat_history_none():
    # Should handle None gracefully (return empty ChatHistory or raise ValueError)
    with pytest.raises(Exception):
        context_collection.collect_chat_history(since_commit=None, max_messages_back=None)

# Terminal command collection removed per architectural decision
# See Task 56: Remove Terminal Command Collection Infrastructure

def test_collect_git_context_invalid_commit():
    # Should raise on invalid commit hash
    with pytest.raises(Exception):
        context_collection.collect_git_context(commit_hash="notarealhash")

# --- Journal Section Generators Edge Cases ---
def test_generate_summary_section_empty():
    # Should not raise, should return valid SummarySection even with empty context
    ctx = JournalContext()
    result = journal.generate_summary_section(ctx)
    assert isinstance(result, dict)
    assert 'summary' in result

def test_generate_technical_synopsis_section_none():
    # Should not raise, should return valid TechnicalSynopsisSection
    result = journal.generate_technical_synopsis_section(None)
    assert isinstance(result, dict)
    assert 'technical_synopsis' in result

# --- File Operations Edge Cases ---
def test_append_to_journal_file_permission_error(tmp_path):
    """append_to_journal_file should raise ValueError if file cannot be written due to permissions."""
    file_path = tmp_path / "file.md"
    with patch("mcp_commit_story.journal_generate.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(ValueError) as excinfo:
            journal.append_to_journal_file("entry", file_path)

# --- JournalEntry/Parser Edge Cases ---
def test_journal_entry_to_markdown_missing_fields():
    # Should not raise, should handle missing optional fields
    entry = journal.JournalEntry(timestamp="now", commit_hash="abc123")
    md = entry.to_markdown()
    assert isinstance(md, str)
    assert "### now" in md

def test_journal_parser_malformed_markdown():
    # Should raise JournalParseError on malformed markdown
    with pytest.raises(journal.JournalParseError):
        journal.JournalParser.parse("not a real journal entry")

# --- TODO: Add more tests for each function in context_collection.py and journal.py ---
# - Test partial/invalid TypedDicts
# - Test boundary conditions (empty lists, large data)
# - Test file permission errors
# - Test error logging/fallbacks 