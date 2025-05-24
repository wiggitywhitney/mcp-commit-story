import pytest
from mcp_commit_story.context_types import ChatMessage, ChatHistory, TerminalCommand, TerminalContext, GitMetadata, GitContext, JournalContext
from mcp_commit_story import journal, git_utils
from typing import get_type_hints

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