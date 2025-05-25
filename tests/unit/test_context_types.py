import pytest
from mcp_commit_story.context_types import ChatMessage, ChatHistory, TerminalCommand, TerminalContext, GitMetadata, GitContext, JournalContext, AccomplishmentsSection
from mcp_commit_story import journal, git_utils
from typing import get_type_hints
from mcp_commit_story.context_collection import collect_chat_history, collect_ai_terminal_commands

def test_chat_history_type():
    # Mocked chat history
    chat = {'messages': [{'speaker': 'user', 'text': 'Hello'}]}
    assert set(chat.keys()) == set(ChatHistory.__annotations__.keys())
    for msg in chat['messages']:
        assert set(msg.keys()) == set(ChatMessage.__annotations__.keys())

def test_terminal_context_type():
    terminal = {'commands': [{'command': 'ls', 'executed_by': 'user'}]}
    assert set(terminal.keys()) == set(TerminalContext.__annotations__.keys())
    for cmd in terminal['commands']:
        assert set(cmd.keys()) == set(TerminalCommand.__annotations__.keys())

def test_git_context_type():
    git = {
        'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
        'diff_summary': 'diff',
        'changed_files': ['file.py'],
        'file_stats': {},
        'commit_context': {}
    }
    assert set(git.keys()) == set(GitContext.__annotations__.keys())
    assert set(git['metadata'].keys()) == set(GitMetadata.__annotations__.keys())

def test_journal_context_type():
    ctx = {
        'chat': {'messages': [{'speaker': 'user', 'text': 'hi'}]},
        'terminal': {'commands': [{'command': 'ls', 'executed_by': 'user'}]},
        'git': {
            'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
            'diff_summary': 'diff',
            'changed_files': ['file.py'],
            'file_stats': {},
            'commit_context': {}
        }
    }
    assert set(ctx.keys()) == set(JournalContext.__annotations__.keys())
    assert set(ctx['chat'].keys()) == set(ChatHistory.__annotations__.keys())
    assert set(ctx['terminal'].keys()) == set(TerminalContext.__annotations__.keys())
    assert set(ctx['git'].keys()) == set(GitContext.__annotations__.keys())

def test_accomplishments_section_type():
    accomplishments = {'accomplishments': ['Implemented X', 'Refactored Y']}
    assert set(accomplishments.keys()) == set(AccomplishmentsSection.__annotations__.keys())
    assert isinstance(accomplishments['accomplishments'], list)
    for item in accomplishments['accomplishments']:
        assert isinstance(item, str)

def test_summary_section_type():
    section = {'summary': 'A summary.'}
    from mcp_commit_story.context_types import SummarySection
    assert set(section.keys()) == set(SummarySection.__annotations__.keys())
    assert isinstance(section['summary'], str)

def test_technical_synopsis_section_type():
    section = {'technical_synopsis': 'Technical details.'}
    from mcp_commit_story.context_types import TechnicalSynopsisSection
    assert set(section.keys()) == set(TechnicalSynopsisSection.__annotations__.keys())
    assert isinstance(section['technical_synopsis'], str)

def test_frustrations_section_type():
    section = {'frustrations': ['Bug', 'Slow tests']}
    from mcp_commit_story.context_types import FrustrationsSection
    assert set(section.keys()) == set(FrustrationsSection.__annotations__.keys())
    assert isinstance(section['frustrations'], list)
    for item in section['frustrations']:
        assert isinstance(item, str)

def test_tone_mood_section_type():
    section = {'mood': 'Happy', 'indicators': 'All tests passed.'}
    from mcp_commit_story.context_types import ToneMoodSection
    assert set(section.keys()) == set(ToneMoodSection.__annotations__.keys())
    assert isinstance(section['mood'], str)
    assert isinstance(section['indicators'], str)

def test_discussion_notes_section_type():
    section = {'discussion_notes': [
        {'speaker': 'Human', 'text': 'Should we use X?'},
        {'speaker': 'Agent', 'text': 'Yes.'},
        'Unattributed note.'
    ]}
    from mcp_commit_story.context_types import DiscussionNotesSection
    assert set(section.keys()) == set(DiscussionNotesSection.__annotations__.keys())
    for note in section['discussion_notes']:
        assert isinstance(note, (str, dict))

def test_terminal_commands_section_type():
    section = {'terminal_commands': ['pytest', 'git status']}
    from mcp_commit_story.context_types import TerminalCommandsSection
    assert set(section.keys()) == set(TerminalCommandsSection.__annotations__.keys())
    for cmd in section['terminal_commands']:
        assert isinstance(cmd, str)

def test_commit_metadata_section_type():
    section = {'commit_metadata': {'hash': 'abc', 'author': 'me'}}
    from mcp_commit_story.context_types import CommitMetadataSection
    assert set(section.keys()) == set(CommitMetadataSection.__annotations__.keys())
    assert isinstance(section['commit_metadata'], dict)

def test_edge_cases_empty_and_none():
    from mcp_commit_story.context_types import ChatHistory, JournalContext, AccomplishmentsSection, FrustrationsSection, DiscussionNotesSection
    # Empty lists
    assert ChatHistory(messages=[])['messages'] == []
    assert AccomplishmentsSection(accomplishments=[])['accomplishments'] == []
    assert FrustrationsSection(frustrations=[])['frustrations'] == []
    assert DiscussionNotesSection(discussion_notes=[])['discussion_notes'] == []
    # None values in JournalContext
    ctx = JournalContext(chat=None, terminal=None, git={
        'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
        'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
    })
    assert ctx['chat'] is None
    assert ctx['terminal'] is None

def test_section_generators_accept_journal_context():
    from mcp_commit_story import journal
    from mcp_commit_story.context_types import JournalContext
    ctx = JournalContext(
        chat={'messages': [{'speaker': 'user', 'text': 'hi'}]},
        terminal={'commands': [{'command': 'ls', 'executed_by': 'user'}]},
        git={
            'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
            'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
        }
    )
    # All section generators should accept JournalContext and return correct TypedDict
    section_fns = [
        journal.generate_summary_section,
        journal.generate_technical_synopsis_section,
        journal.generate_accomplishments_section,
        journal.generate_frustrations_section,
        journal.generate_tone_mood_section,
        journal.generate_discussion_notes_section,
        journal.generate_terminal_commands_section,
        journal.generate_commit_metadata_section,
    ]
    for fn in section_fns:
        result = fn(ctx)
        assert isinstance(result, dict)
        # Should have all required keys
        for key in fn.__annotations__['return'].__annotations__.keys():
            assert key in result

def test_type_safety_enforcement():
    from mcp_commit_story import journal
    # Invalid JournalContext structure
    invalid_ctx = {'chat': 'not_a_dict', 'git': None}
    # Should raise or handle gracefully
    for fn in [
        journal.generate_accomplishments_section,
        journal.generate_frustrations_section,
        journal.generate_tone_mood_section,
        journal.generate_discussion_notes_section,
    ]:
        try:
            fn(invalid_ctx)  # type: ignore
        except Exception as e:
            assert isinstance(e, (TypeError, KeyError, AttributeError)) 