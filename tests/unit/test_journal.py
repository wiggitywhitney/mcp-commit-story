import sys
import os
import pytest
from mcp_commit_story import journal_generate as journal
from mcp_commit_story.context_types import JournalContext, AccomplishmentsSection, FrustrationsSection, ToneMoodSection, DiscussionNotesSection
from mcp_commit_story.context_collection import collect_chat_history
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
import json

# Sample markdown for a daily note entry
DAILY_NOTE_MD = '''
### 2:17 PM — Commit def456

#### Summary
A friendly, succinct summary that captures what was accomplished.

#### Accomplishments
- Implemented feature X
- Fixed bug Y

#### Frustrations or Roadblocks
- Spent hours debugging config

#### Terminal Commands (AI Session)
```bash
git status
pytest
```

#### Discussion Notes (from chat)
> Should we use PostgreSQL or MongoDB? I'm leaning toward PostgreSQL because we need ACID compliance for financial data...

#### Tone/Mood
> Focused and energized

#### Commit Metadata
- Commit hash: def456
- Message: "feat: add feature X"
- Files touched: src/feature_x.py
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

# Test data for diff information tests
SAMPLE_FILE_DIFFS = {
    "src/auth.py": """@@ -0,0 +1,15 @@
+class UserAuthentication:
+    def __init__(self, secret_key):
+        self.secret_key = secret_key
+    
+    def authenticate(self, token):
+        # Validate JWT token
+        return self._validate_jwt(token)
+    
+    def _validate_jwt(self, token):
+        # Implementation details
+        return True
""",
    "src/user.py": """@@ -10,3 +10,8 @@ class User:
     def __init__(self, username):
         self.username = username
+    
+    def set_auth_token(self, token):
+        self.auth_token = token
+        return True
"""
}

EMPTY_FILE_DIFFS = {}


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


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_generate_summary_section_basic_commit(mock_invoke_ai):
    # Mock AI response
    mock_invoke_ai.return_value = "Added user authentication feature to auth.py because security is important for protecting user data"
    
    ctx = JournalContext(
        chat=None,
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


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_generate_summary_section_with_chat_reasoning(mock_invoke_ai):
    # Mock AI response
    mock_invoke_ai.return_value = "Added user authentication feature because security discussion indicated need to protect user data"
    
    ctx = JournalContext(
        chat={'messages': [
            {'speaker': 'Human', 'text': 'We need to add authentication to protect user data.'},
            {'speaker': 'Agent', 'text': 'Agreed, this will improve security.'},
        ]},
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
    ctx = JournalContext(chat=None, git=None)  # type: ignore
    result = journal.generate_summary_section(ctx)
    assert isinstance(result, dict)
    assert 'summary' in result
    assert result['summary'] == ""


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


def test_generate_accomplishments_section_none_found():
    """Test accomplishments section generation when no accomplishments are found."""
    context = {'git': {'diff_summary': 'No meaningful changes'}, 'chat': {'messages': []}}
    result = journal.generate_accomplishments_section(context)
    assert isinstance(result, dict)
    assert 'accomplishments' in result


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


def test_generate_frustrations_section_empty_context():
    """Test frustrations section generation with empty context."""
    empty_context = {'git': {'diff_summary': ''}, 'chat': {'messages': []}}
    result = journal.generate_frustrations_section(empty_context)
    assert isinstance(result, dict)
    assert 'frustrations' in result


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


def test_generate_tone_mood_section_empty_context():
    """Test tone and mood section generation with empty context."""
    empty_context = {'git': {'diff_summary': ''}, 'chat': {'messages': []}}
    result = journal.generate_tone_mood_section(empty_context)
    assert isinstance(result, dict)
    assert 'mood' in result


def test_generate_tone_mood_section_conflicting_signals():
    """Test tone and mood section generation with conflicting emotional signals."""
    context = {
        'git': {'diff_summary': 'Fixed critical bug'}, 
        'chat': {'messages': [
            {'speaker': 'Human', 'text': 'This is so frustrating!'},
            {'speaker': 'Human', 'text': 'Finally got it working!'}
        ]}
    }
    result = journal.generate_tone_mood_section(context)
    assert isinstance(result, dict)
    assert 'mood' in result


def test_generate_tone_mood_section_format():
    """Test that tone and mood section returns the expected format."""
    context = {'git': {'diff_summary': 'Made changes'}, 'chat': {'messages': []}}
    result = journal.generate_tone_mood_section(context)
    assert isinstance(result, dict)
    assert 'mood' in result
    assert 'indicators' in result


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


def test_generate_discussion_notes_section_empty_context():
    """Test discussion notes section generation with empty context."""
    empty_context = {'chat': {'messages': []}}
    result = journal.generate_discussion_notes_section(empty_context)
    assert isinstance(result, dict)
    assert 'discussion_notes' in result


def test_generate_discussion_notes_section_malformed_chat():
    """Test discussion notes section generation with malformed chat context."""
    malformed_context = {'chat': None}
    result = journal.generate_discussion_notes_section(malformed_context)
    assert isinstance(result, dict)
    assert 'discussion_notes' in result


@pytest.mark.xfail(reason="Requires AI agent or mock AI")
def test_generate_discussion_notes_section_format():
    ctx = JournalContext(chat={'messages': [
        {'speaker': 'Human', 'text': 'First line.'},
        {'speaker': 'Agent', 'text': 'Second line.'}
    ]}, git=None)
    result = journal.generate_discussion_notes_section(ctx)
    notes = result['discussion_notes']
    assert isinstance(notes, list)
    assert any(isinstance(n, dict) and n.get('speaker') == 'Human' for n in notes)
    assert any(isinstance(n, dict) and n.get('speaker') == 'Agent' for n in notes)


# Terminal commands section tests removed per architectural decision
# See Task 56: Remove Terminal Command Collection Infrastructure


def test_append_to_journal_file_creates_directories(tmp_path):
    from mcp_commit_story.journal import append_to_journal_file
    file_path = tmp_path / "nested/dir/journal.md"
    entry = "Test entry"
    assert not file_path.parent.exists()
    append_to_journal_file(entry, file_path)
    assert file_path.exists()
    assert file_path.read_text().startswith(entry)


def test_append_to_journal_file_existing_directories(tmp_path):
    from mcp_commit_story.journal import append_to_journal_file
    file_path = tmp_path / "existing/dir/journal.md"
    file_path.parent.mkdir(parents=True)
    entry = "Another test entry"
    append_to_journal_file(entry, file_path)
    assert file_path.exists()
    assert file_path.read_text().startswith(entry)


def test_append_to_journal_file_permission_error(monkeypatch, tmp_path):
    from mcp_commit_story.journal import append_to_journal_file
    file_path = tmp_path / "protected/dir/journal.md"
    entry = "Should fail"
    # Patch ensure_journal_directory to raise PermissionError
    import mcp_commit_story.journal_generate as journal_generate_mod
    def raise_permission_error(fp):
        raise PermissionError("No permission to create directory")
    monkeypatch.setattr(journal_generate_mod, "ensure_journal_directory", raise_permission_error)
    with pytest.raises(ValueError):
        append_to_journal_file(entry, file_path) 


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_generate_summary_section_with_file_diffs(mock_invoke_ai):
    """Test that summary section can access and utilize file_diffs from GitContext."""
    # Mock AI response
    mock_invoke_ai.return_value = "Added user authentication feature with JWT validation in auth.py and token support in user.py"
    
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add user authentication feature',
            },
            'diff_summary': 'auth.py: added, user.py: modified',
            'changed_files': ['src/auth.py', 'src/user.py'],
            'file_stats': {'source': 2, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'medium', 'is_merge': False},
            'file_diffs': SAMPLE_FILE_DIFFS
        },
        journal=None
    )
    
    result = journal.generate_summary_section(ctx)
    
    # Verify AI was called with context including file_diffs
    assert mock_invoke_ai.called
    args, kwargs = mock_invoke_ai.call_args
    prompt_with_context = args[0]
    
    # Check that file_diffs are included in the JSON context
    assert '"file_diffs"' in prompt_with_context
    assert 'class UserAuthentication' in prompt_with_context
    assert 'set_auth_token' in prompt_with_context
    
    # Verify return format
    assert 'summary' in result
    assert isinstance(result['summary'], str)


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_generate_summary_section_empty_diffs_vs_populated_diffs(mock_invoke_ai):
    """Test that summary section produces different output when diffs are available vs empty."""
    
    # Test with empty diffs
    mock_invoke_ai.return_value = "Added authentication feature"
    ctx_empty = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice', 'date': '2025-05-24', 'message': 'Add auth'},
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False},
            'file_diffs': EMPTY_FILE_DIFFS
        },
        journal=None
    )
    
    result_empty = journal.generate_summary_section(ctx_empty)
    
    # Test with populated diffs
    mock_invoke_ai.return_value = "Added comprehensive authentication feature with JWT validation and token management"
    ctx_with_diffs = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice', 'date': '2025-05-24', 'message': 'Add auth'},
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False},
            'file_diffs': SAMPLE_FILE_DIFFS
        },
        journal=None
    )
    
    result_with_diffs = journal.generate_summary_section(ctx_with_diffs)
    
    # Verify both calls were made
    assert mock_invoke_ai.call_count == 2
    
    # Verify the context sent to AI differs between calls
    call1_context = mock_invoke_ai.call_args_list[0][0][0]
    call2_context = mock_invoke_ai.call_args_list[1][0][0]
    
    # First call should have empty file_diffs
    assert '"file_diffs": {}' in call1_context
    
    # Second call should have populated file_diffs
    assert '"file_diffs": {' in call2_context
    assert 'class UserAuthentication' in call2_context


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_generate_technical_synopsis_section_with_file_diffs(mock_invoke_ai):
    """Test that technical synopsis section can access and utilize file_diffs from GitContext."""
    # Mock AI response
    mock_invoke_ai.return_value = "Implemented UserAuthentication class with JWT validation and User.set_auth_token method"
    
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add user authentication feature',
            },
            'diff_summary': 'auth.py: added, user.py: modified',
            'changed_files': ['src/auth.py', 'src/user.py'],
            'file_stats': {'source': 2, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'medium', 'is_merge': False},
            'file_diffs': SAMPLE_FILE_DIFFS
        },
        journal=None
    )
    
    result = journal.generate_technical_synopsis_section(ctx)
    
    # Verify AI was called with context including file_diffs
    assert mock_invoke_ai.called
    args, kwargs = mock_invoke_ai.call_args
    prompt_with_context = args[0]
    
    # Check that file_diffs are included in the JSON context
    assert '"file_diffs"' in prompt_with_context
    assert 'class UserAuthentication' in prompt_with_context
    assert '_validate_jwt' in prompt_with_context
    assert 'set_auth_token' in prompt_with_context
    
    # Verify return format
    assert 'technical_synopsis' in result
    assert isinstance(result['technical_synopsis'], str)


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_generate_technical_synopsis_section_empty_diffs_vs_populated_diffs(mock_invoke_ai):
    """Test that technical synopsis section produces different output when diffs are available vs empty."""
    
    # Test with empty diffs
    mock_invoke_ai.return_value = "Added authentication functionality"
    ctx_empty = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice', 'date': '2025-05-24', 'message': 'Add auth'},
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False},
            'file_diffs': EMPTY_FILE_DIFFS
        },
        journal=None
    )
    
    result_empty = journal.generate_technical_synopsis_section(ctx_empty)
    
    # Test with populated diffs
    mock_invoke_ai.return_value = "Created UserAuthentication class with JWT validation methods and added token support to User class"
    ctx_with_diffs = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice', 'date': '2025-05-24', 'message': 'Add auth'},
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False},
            'file_diffs': SAMPLE_FILE_DIFFS
        },
        journal=None
    )
    
    result_with_diffs = journal.generate_technical_synopsis_section(ctx_with_diffs)
    
    # Verify both calls were made
    assert mock_invoke_ai.call_count == 2
    
    # Verify the context sent to AI differs between calls
    call1_context = mock_invoke_ai.call_args_list[0][0][0]
    call2_context = mock_invoke_ai.call_args_list[1][0][0]
    
    # First call should have empty file_diffs
    assert '"file_diffs": {}' in call1_context
    
    # Second call should have populated file_diffs
    assert '"file_diffs": {' in call2_context
    assert 'UserAuthentication' in call2_context
    assert '_validate_jwt' in call2_context


def test_file_diffs_integration_with_all_generators():
    """Test that file_diffs field is accessible to all generator functions without errors."""
    
    ctx_with_diffs = JournalContext(
        chat=None,
        git={
            'metadata': {'hash': 'abc123', 'author': 'Alice', 'date': '2025-05-24', 'message': 'Add auth'},
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False},
            'file_diffs': SAMPLE_FILE_DIFFS
        },
        journal=None
    )
    
    # Test that all generator functions can handle file_diffs without errors
    with patch('mcp_commit_story.journal_generate.invoke_ai') as mock_ai:
        mock_ai.return_value = "Test response"
        
        # These should not raise exceptions
        result_summary = journal.generate_summary_section(ctx_with_diffs)
        result_tech = journal.generate_technical_synopsis_section(ctx_with_diffs)
        result_accomplishments = journal.generate_accomplishments_section(ctx_with_diffs)
        result_frustrations = journal.generate_frustrations_section(ctx_with_diffs)
        result_tone = journal.generate_tone_mood_section(ctx_with_diffs)
        result_discussion = journal.generate_discussion_notes_section(ctx_with_diffs)
        result_metadata = journal.generate_commit_metadata_section(ctx_with_diffs)
        
        # Verify all functions returned valid responses
        assert 'summary' in result_summary
        assert 'technical_synopsis' in result_tech
        assert 'accomplishments' in result_accomplishments
        assert 'frustrations' in result_frustrations
        assert 'mood' in result_tone
        assert 'discussion_notes' in result_discussion
        assert 'commit_metadata' in result_metadata 


# Tests for Technical Synopsis JSON Output Fix

@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_technical_synopsis_json_object_converted_to_readable_text(mock_invoke_ai):
    """Test that when AI returns JSON object with technical_synopsis structure, function returns readable text instead of JSON string."""
    # Mock AI returning structured JSON response
    structured_response = {
        "technical_synopsis": {
            "overview": "Implemented user authentication system with JWT validation",
            "implementation_details": [
                "Created UserAuthentication class with token validation methods",
                "Added JWT secret key configuration to environment variables",
                "Integrated bcrypt for password hashing"
            ],
            "impact": "Enhanced security by adding proper authentication flow"
        }
    }
    mock_invoke_ai.return_value = json.dumps(structured_response)
    
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {
                'hash': 'abc123',
                'author': 'Alice <alice@example.com>',
                'date': '2025-05-24 12:00:00',
                'message': 'Add user authentication',
            },
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False}
        },
        journal=None
    )
    
    result = journal.generate_technical_synopsis_section(ctx)
    
    # Should return readable text, not JSON string
    technical_synopsis = result['technical_synopsis']
    assert isinstance(technical_synopsis, str)
    
    # Should NOT contain JSON artifacts like curly braces, square brackets, or quotes around keys
    assert not technical_synopsis.startswith('{')
    assert not technical_synopsis.endswith('}')
    assert '"overview"' not in technical_synopsis
    assert '"implementation_details"' not in technical_synopsis
    assert '"impact"' not in technical_synopsis
    
    # Should contain the actual content in readable form
    assert "user authentication system" in technical_synopsis.lower()
    assert "jwt validation" in technical_synopsis.lower()


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_technical_synopsis_plain_text_response_unchanged(mock_invoke_ai):
    """Test that plain text responses still work unchanged."""
    # Mock AI returning plain text response
    plain_text_response = "Implemented comprehensive user authentication with JWT tokens and bcrypt password hashing."
    mock_invoke_ai.return_value = plain_text_response
    
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {
                'hash': 'def456',
                'author': 'Bob <bob@example.com>',
                'date': '2025-05-24 14:00:00',
                'message': 'Add authentication',
            },
            'diff_summary': 'auth.py: added',
            'changed_files': ['src/auth.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False}
        },
        journal=None
    )
    
    result = journal.generate_technical_synopsis_section(ctx)
    
    # Should return the same plain text
    assert result['technical_synopsis'] == plain_text_response


@patch('mcp_commit_story.journal_generate.invoke_ai')
def test_technical_synopsis_malformed_json_fallback(mock_invoke_ai):
    """Test edge case: malformed JSON still gets reasonable fallback."""
    # Mock AI returning malformed JSON
    malformed_response = '{"technical_synopsis": {"overview": "Fixed bug", "implementation_details": [incomplete'
    mock_invoke_ai.return_value = malformed_response
    
    ctx = JournalContext(
        chat=None,
        git={
            'metadata': {
                'hash': 'ghi789',
                'author': 'Charlie <charlie@example.com>',
                'date': '2025-05-24 16:00:00',
                'message': 'Fix bug',
            },
            'diff_summary': 'bug.py: modified',
            'changed_files': ['src/bug.py'],
            'file_stats': {'source': 1, 'config': 0, 'docs': 0, 'tests': 0},
            'commit_context': {'size_classification': 'small', 'is_merge': False}
        },
        journal=None
    )
    
    result = journal.generate_technical_synopsis_section(ctx)
    
    # Should return some reasonable fallback text instead of crashing
    technical_synopsis = result['technical_synopsis']
    assert isinstance(technical_synopsis, str)
    assert len(technical_synopsis) > 0  # Should not be empty
    # Should contain the original malformed response as fallback
    assert malformed_response in technical_synopsis 