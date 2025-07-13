"""Journal module for engineering journal entry generation and management."""

# Re-export classes for backward compatibility
from .models import JournalParser, JournalParseError
from ..journal_generate import JournalEntry

# Re-export functions from telemetry_utils module
from .telemetry_utils import (
    _add_ai_generation_telemetry,
    _record_ai_generation_metrics,
    log_ai_agent_interaction,
    _get_size_bucket,
)

# Re-export utility functions and AI generators from journal_generate.py
from ..journal_generate import (
    ensure_journal_directory,
    get_journal_file_path,
    append_to_journal_file,
    load_journal_context,
    generate_summary_section,
    generate_technical_synopsis_section,
    generate_accomplishments_section,
    generate_frustrations_section,
    generate_tone_mood_section,
    generate_discussion_notes_section,
    generate_commit_metadata_section,
)

__all__ = [
    'JournalEntry', 'JournalParser', 'JournalParseError',
    '_add_ai_generation_telemetry', '_record_ai_generation_metrics',
    'log_ai_agent_interaction', '_get_size_bucket',
    'ensure_journal_directory', 'get_journal_file_path', 
    'append_to_journal_file', 'load_journal_context',
    'generate_summary_section', 'generate_technical_synopsis_section',
    'generate_accomplishments_section', 'generate_frustrations_section',
    'generate_tone_mood_section', 'generate_discussion_notes_section',
    'generate_commit_metadata_section',
] 