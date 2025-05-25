import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from mcp_commit_story import journal
from mcp_commit_story.context_types import JournalContext, AccomplishmentsSection, FrustrationsSection, ToneMoodSection, DiscussionNotesSection
from mcp_commit_story.context_collection import collect_chat_history, collect_ai_terminal_commands

# Sample markdown for a daily note entry
DAILY_NOTE_MD = '''
### 2:17 PM — Commit def456

## Summary
A friendly, succinct summary that captures what was accomplished.

## Accomplishments
- Implemented feature X
- Fixed bug Y

## Frustrations or Roadblocks
- Spent hours debugging config

## Terminal Commands (AI Session)
- `git status`
- `pytest`

## Discussion Notes (from chat)
> "Should we use PostgreSQL or MongoDB? I'm leaning toward PostgreSQL because we need ACID compliance for financial data..."

## Tone + Mood (inferred)
> Mood: Focused and energized

## Behind the Commit
- Commit hash: def456
- Message: "feat: add feature X"
- Files touched: src/feature_x.py

## Reflections
- This was a tough one!
'''

# Sample markdown for a manual reflection entry
REFLECTION_MD = '''
### 4:45 PM — Reflection

Today I learned about the importance of clear error messages.
'''

# Sample markdown for a summary entry (lengthy, human-readable)
SUMMARY_MD = '''
## Summary
Today was a productive day. I implemented feature X, fixed a long-standing bug in the config system, and learned a lot about error handling. The main challenge was tracking down a subtle bug that only appeared in certain edge cases. After several hours of debugging, I finally identified the root cause and fixed it. I also spent some time refactoring the codebase to improve readability and maintainability. Overall, I'm happy with the progress made today and look forward to tackling the next set of features tomorrow.
'''

# Edge case: empty entry
EMPTY_MD = ''

# Edge case: malformed entry (missing required sections)
MALFORMED_MD = '## Accomplishments\n- Did something\n'


def test_parse_daily_note_entry():
    entry = journal.JournalParser.parse(DAILY_NOTE_MD)
    assert entry.timestamp == '2:17 PM'
    assert entry.commit_hash == 'def456'
    assert 'Implemented feature X' in entry.accomplishments
    assert 'Spent hours debugging config' in entry.frustrations
    assert entry.summary.startswith('A friendly, succinct summary')


def test_handle_empty_entry():
    with pytest.raises(journal.JournalParseError):
        journal.JournalParser.parse(EMPTY_MD)


def test_handle_malformed_entry():
    with pytest.raises(journal.JournalParseError):
        journal.JournalParser.parse(MALFORMED_MD)


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_summary_section_basic_commit():
    ctx = JournalContext(
        chat=None,
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add user authentication feature',
            },
            'diff_summary': 'auth.py: added, user.py: modified',
            'changed_files': ['auth.py', 'user.py'],
            'file_stats': {'source': 2, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'medium', 'is_merge': False},
        },
    )
    result = journal.generate_summary_section(ctx)
    assert isinstance(result, dict)
    assert 'summary' in result
    summary = result['summary']
    assert isinstance(summary, str)
    assert 'user authentication' in summary.lower()
    assert 'auth.py' in summary
    assert any(word in summary.lower() for word in ['why', 'reason', 'intent', 'motivation', 'goal', 'purpose', 'because', 'to ', 'for '])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_summary_section_with_chat_reasoning():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'We need to add authentication to protect user data.'},
            {'speaker': 'Agent', 'text': 'Agreed, this will improve security.'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add user authentication feature',
            },
            'diff_summary': 'auth.py: added, user.py: modified',
            'changed_files': ['auth.py', 'user.py'],
            'file_stats': {'source': 2, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'medium', 'is_merge': False},
        },
    )
    result = journal.generate_summary_section(ctx)
    summary = result['summary']
    assert 'protect user data' in summary.lower() or 'security' in summary.lower()


def test_generate_summary_section_handles_missing_git():
    ctx = JournalContext(chat=None, terminal=None, git=None)  # type: ignore
    result = journal.generate_summary_section(ctx)
    assert isinstance(result, dict)
    assert 'summary' in result
    assert result['summary'] == ""


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_summary_section_ignores_how_and_errors():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'I fixed a bug in the login flow.'},
            {'speaker': 'Agent', 'text': 'The test failed because of a typo.'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Fix login bug',
            },
            'diff_summary': 'login.py: fixed bug',
            'changed_files': ['login.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False},
        },
    )
    result = journal.generate_summary_section(ctx)
    summary = result['summary']
    assert 'how' not in summary.lower()
    assert 'test failed' not in summary.lower()
    assert 'typo' not in summary.lower()
    assert 'fixed bug' in summary.lower() or 'login' in summary.lower()


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_happy_path():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Finally got the authentication working!'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Fix authentication bug',
            },
            'diff_summary': 'auth.py: fixed bug',
            'changed_files': ['auth.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert isinstance(result, dict)
    assert 'accomplishments' in result
    assert any('authentication' in a.lower() for a in result['accomplishments'])
    assert any('finally' in a.lower() or 'got' in a.lower() for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_pride_and_concern():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': "Finally got this working but it's probably terrible code."},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Refactor',
            },
            'diff_summary': 'refactor.py: refactored',
            'changed_files': ['refactor.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert any('despite' in a.lower() or 'concern' in a.lower() for a in result['accomplishments'])
    assert any('finally' in a.lower() or 'got' in a.lower() for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_git_only():
    ctx = JournalContext(
        chat=None,
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add feature X',
            },
            'diff_summary': 'feature_x.py: added',
            'changed_files': ['feature_x.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert any('feature' in a.lower() for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_none_found():
    ctx = JournalContext(chat=None, terminal=None, git=None)  # type: ignore
    result = journal.generate_accomplishments_section(ctx)
    assert isinstance(result, dict)
    assert 'accomplishments' in result
    assert result['accomplishments'] == []


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_high_energy():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Breakthrough! Finally fixed the deployment pipeline!'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Fix deployment pipeline',
            },
            'diff_summary': 'deploy.py: fixed pipeline',
            'changed_files': ['deploy.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert any('breakthrough' in a.lower() or 'finally' in a.lower() for a in result['accomplishments'])
    assert any('deployment' in a.lower() for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_matter_of_fact():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Fixed typo in documentation.'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Fix typo',
            },
            'diff_summary': 'README.md: fixed typo',
            'changed_files': ['README.md'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert any('typo' in a.lower() for a in result['accomplishments'])
    assert all('.' in a for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_relief():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Finally! That did it.'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Fix bug',
            },
            'diff_summary': 'bug.py: fixed',
            'changed_files': ['bug.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert any('finally' in a.lower() or 'did it' in a.lower() for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_accomplishments_section_achievement_and_criticism():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Got the tests passing, but the code is a mess.'},
        ]},
        terminal=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Test fixes',
            },
            'diff_summary': 'tests.py: fixed',
            'changed_files': ['tests.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_accomplishments_section(ctx)
    assert any('tests' in a.lower() for a in result['accomplishments'])
    assert any('mess' in a.lower() or 'criticism' in a.lower() or 'concern' in a.lower() for a in result['accomplishments'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_frustrations_section_happy_path():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Spent hours debugging config, so frustrating!'},
            {'speaker': 'Agent', 'text': 'That bug was a pain.'},
        ]},
        terminal=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice <alice@example.com>', 'date': '2025-05-24 12:00:00', 'message': 'Fix config bug'},
            'diff_summary': 'config.py: fixed bug',
            'changed_files': ['config.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_frustrations_section(ctx)
    assert isinstance(result, dict)
    assert 'frustrations' in result
    assert any('frustrat' in f.lower() or 'pain' in f.lower() for f in result['frustrations'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_frustrations_section_empty_context():
    ctx = JournalContext(chat=None, terminal=None, git=None)  # type: ignore
    result = journal.generate_frustrations_section(ctx)
    assert isinstance(result, dict)
    assert 'frustrations' in result
    assert result['frustrations'] == []


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_frustrations_section_conflicting_signals():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'This was easy.'},
            {'speaker': 'Human', 'text': 'Actually, the config bug was a nightmare.'},
        ]},
        terminal=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice <alice@example.com>', 'date': '2025-05-24 12:00:00', 'message': 'Fix config bug'},
            'diff_summary': 'config.py: fixed bug',
            'changed_files': ['config.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_frustrations_section(ctx)
    assert isinstance(result, dict)
    assert 'frustrations' in result
    assert any('nightmare' in f.lower() or 'easy' not in f.lower() for f in result['frustrations'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_frustrations_section_multiple_indicators():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Debugging was tedious.'},
            {'speaker': 'Human', 'text': 'Tests kept failing.'},
        ]},
        terminal=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice <alice@example.com>', 'date': '2025-05-24 12:00:00', 'message': 'Fix test bug'},
            'diff_summary': 'test.py: fixed bug',
            'changed_files': ['test.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_frustrations_section(ctx)
    assert isinstance(result, dict)
    assert 'frustrations' in result
    assert len(result['frustrations']) >= 2


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_tone_mood_section_happy_path():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Feeling pretty good about this commit.'},
            {'speaker': 'Agent', 'text': 'Nice work!'}
        ]},
        terminal={'commands': [
            {'command': 'pytest', 'executed_by': 'user'}
        ]},
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add tone section',
            },
            'diff_summary': 'tone.py: added',
            'changed_files': ['tone.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_tone_mood_section(ctx)
    assert isinstance(result, dict)
    assert 'mood' in result
    assert 'indicators' in result
    assert isinstance(result['mood'], str)
    assert isinstance(result['indicators'], str)
    assert result['mood'] != ""
    assert 'good' in result['mood'].lower() or 'positive' in result['mood'].lower()


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_tone_mood_section_empty_context():
    ctx = JournalContext(chat=None, terminal=None, git=None)  # type: ignore
    result = journal.generate_tone_mood_section(ctx)
    assert isinstance(result, dict)
    assert 'mood' in result
    assert 'indicators' in result
    assert result['mood'] == ""
    assert result['indicators'] == ""


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_tone_mood_section_conflicting_signals():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'This was easy.'},
            {'speaker': 'Human', 'text': 'Actually, the config bug was a nightmare.'},
        ]},
        terminal=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice <alice@example.com>', 'date': '2025-05-24 12:00:00', 'message': 'Fix config bug'},
            'diff_summary': 'config.py: fixed bug',
            'changed_files': ['config.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_tone_mood_section(ctx)
    assert isinstance(result, dict)
    assert 'mood' in result
    assert 'indicators' in result
    assert 'conflict' in result['indicators'].lower() or 'ambiguous' in result['indicators'].lower() or result['mood'] == ""


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_tone_mood_section_format():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Relieved to have this done.'},
        ]},
        terminal=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice <alice@example.com>', 'date': '2025-05-24 12:00:00', 'message': 'Finish tone section'},
            'diff_summary': 'tone.py: finished',
            'changed_files': ['tone.py'],
            'file_stats': {},
            'commit_context': {},
        },
    )
    result = journal.generate_tone_mood_section(ctx)
    assert isinstance(result, dict)
    assert set(result.keys()) == {'mood', 'indicators'}
    assert isinstance(result['mood'], str)
    assert isinstance(result['indicators'], str)


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_discussion_notes_section_happy_path():
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'Should we use PostgreSQL or MongoDB? I prefer PostgreSQL.'},
            {'speaker': 'Agent', 'text': 'PostgreSQL is a good choice for ACID compliance.'}
        ]},
        terminal=None,
        git=None,
    )
    result = journal.generate_discussion_notes_section(ctx)
    assert isinstance(result, dict)
    assert 'discussion_notes' in result
    notes = result['discussion_notes']
    assert isinstance(notes, list)
    assert any(isinstance(n, dict) and n.get('speaker') == 'Human' for n in notes)
    assert any(isinstance(n, dict) and n.get('speaker') == 'Agent' for n in notes)


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_discussion_notes_section_empty_context():
    ctx = JournalContext(chat=None, terminal=None, git=None)  # type: ignore
    result = journal.generate_discussion_notes_section(ctx)
    assert isinstance(result, dict)
    assert 'discussion_notes' in result
    assert result['discussion_notes'] == []


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_discussion_notes_section_malformed_chat():
    ctx = JournalContext(chat={'messages': [
        {'speaker': 'Human'},  # missing text
        {'text': 'No speaker here.'}  # missing speaker
    ]}, terminal=None, git=None)
    result = journal.generate_discussion_notes_section(ctx)
    assert isinstance(result, dict)
    assert 'discussion_notes' in result
    assert all(isinstance(n, (str, dict)) for n in result['discussion_notes'])


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_discussion_notes_section_format():
    ctx = JournalContext(chat={'messages': [
        {'speaker': 'Human', 'text': 'First line.'},
        {'speaker': 'Agent', 'text': 'Second line.'}
    ]}, terminal=None, git=None)
    result = journal.generate_discussion_notes_section(ctx)
    notes = result['discussion_notes']
    assert isinstance(notes, list)
    assert any(isinstance(n, dict) and n.get('speaker') == 'Human' for n in notes)
    assert any(isinstance(n, dict) and n.get('speaker') == 'Agent' for n in notes)


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_terminal_commands_section_happy_path():
    ctx = JournalContext(
        chat=None,
        terminal={
            'commands': [
                {'command': 'pytest', 'executed_by': 'ai'},
                {'command': 'git status', 'executed_by': 'ai'},
            ]
        },
        git={
            'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
            'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
        }
    )
    result = journal.generate_terminal_commands_section(ctx)
    assert isinstance(result, dict)
    assert 'terminal_commands' in result
    assert isinstance(result['terminal_commands'], list)
    assert all(isinstance(cmd, str) for cmd in result['terminal_commands'])
    assert 'pytest' in result['terminal_commands'][0]


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_terminal_commands_section_empty_context():
    ctx = JournalContext(chat=None, terminal=None, git={
        'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
        'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
    })
    result = journal.generate_terminal_commands_section(ctx)
    assert isinstance(result, dict)
    assert 'terminal_commands' in result
    assert result['terminal_commands'] == []


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_terminal_commands_section_malformed_terminal():
    ctx = JournalContext(chat=None, terminal={'commands': [123, None]}, git={
        'metadata': {'hash': 'abc', 'author': 'me', 'date': 'today', 'message': 'msg'},
        'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
    })
    result = journal.generate_terminal_commands_section(ctx)
    assert isinstance(result, dict)
    assert 'terminal_commands' in result
    assert isinstance(result['terminal_commands'], list)


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_terminal_commands_section_type_safety():
    ctx = None  # type: ignore
    result = journal.generate_terminal_commands_section(ctx)
    assert isinstance(result, dict)
    assert 'terminal_commands' in result
    assert isinstance(result['terminal_commands'], list) 