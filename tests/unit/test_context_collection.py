import pytest
import git
import os
from pathlib import Path
from typing import get_type_hints
from mcp_commit_story.context_types import ChatMessage, ChatHistory, TerminalCommand, TerminalContext
from mcp_commit_story.context_collection import collect_chat_history, collect_ai_terminal_commands, collect_git_context

# Assume these will be imported from the journal module
# from mcp_commit_story.journal import collect_commit_metadata, extract_code_diff, gather_discussion_notes, capture_file_changes, collect_chat_history, collect_ai_terminal_commands

def setup_temp_repo_with_commit(tmp_path):
    repo = git.Repo.init(tmp_path)
    file_path = Path(tmp_path) / "file.txt"
    file_path.write_text("hello")
    repo.index.add([str(file_path)])
    commit = repo.index.commit("test commit")
    return repo, commit

def test_collect_git_context_metadata_fields(tmp_path):
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    assert isinstance(ctx, dict)
    assert 'metadata' in ctx
    meta = ctx['metadata']
    for field in ['hash', 'author', 'date', 'message']:
        assert field in meta

def test_collect_git_context_diff_summary(tmp_path):
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    assert 'diff_summary' in ctx
    assert isinstance(ctx['diff_summary'], str)

def test_collect_git_context_changed_files_and_stats(tmp_path):
    repo, commit = setup_temp_repo_with_commit(tmp_path)
    ctx = collect_git_context(commit.hexsha, repo=repo)
    assert 'changed_files' in ctx
    assert isinstance(ctx['changed_files'], list)
    assert 'file_stats' in ctx
    for key in ['source', 'config', 'docs', 'tests']:
        assert key in ctx['file_stats']
        assert isinstance(ctx['file_stats'][key], int)

def test_collect_chat_history_thoroughness_and_boundary():
    """
    collect_chat_history should:
    - Search backward for the last mcp-commit-story new-entry command (or similar)
    - If not found, review all available conversation history
    - Review ALL chat messages and terminal commands within this boundary
    - Be thorough and not skip or summarize large portions
    - Exclude sensitive data and ambiguous notes
    - Format output as a list of dicts with 'speaker' and 'text' or just 'text'
    """
    # This test would mock a conversation and check that only the correct boundary is used,
    # all relevant notes are included, and filtering/formatting is correct.
    pass

def test_collect_ai_terminal_commands_thoroughness_and_boundary():
    """
    collect_ai_terminal_commands should:
    - Search backward for the last mcp-commit-story new-entry command (or similar)
    - If not found, review all available terminal command history
    - Review ALL terminal commands within this boundary
    - Be thorough and not skip or summarize large portions
    - Exclude routine git commands, journal creation commands, and sensitive data
    - Format output as a chronological list of commands
    """
    # This test would mock a terminal history and check that only the correct boundary is used,
    # all relevant commands are included, and filtering/formatting is correct.
    pass

def test_collect_chat_history_structure():
    result = collect_chat_history()
    # Should be a dict with 'messages' key
    assert isinstance(result, dict)
    assert set(result.keys()) == set(ChatHistory.__annotations__.keys())
    for msg in result['messages']:
        assert set(msg.keys()) == set(ChatMessage.__annotations__.keys())

def test_collect_chat_history_type_hint():
    hints = get_type_hints(collect_chat_history)
    assert 'return' in hints
    assert hints['return'].__name__ == 'ChatHistory'

def test_collect_ai_terminal_commands_structure():
    result = collect_ai_terminal_commands()
    assert isinstance(result, dict)
    assert set(result.keys()) == set(TerminalContext.__annotations__.keys())
    for cmd in result['commands']:
        assert set(cmd.keys()) == set(TerminalCommand.__annotations__.keys())

def test_collect_ai_terminal_commands_type_hint():
    hints = get_type_hints(collect_ai_terminal_commands)
    assert 'return' in hints
    assert hints['return'].__name__ == 'TerminalContext'

def test_collect_git_context_invalid_repo(tmp_path):
    # Create a directory that is not a git repo
    non_repo_path = tmp_path / "not_a_repo"
    non_repo_path.mkdir()
    with pytest.raises(git.InvalidGitRepositoryError):
        collect_git_context("HEAD", repo=git.Repo(str(non_repo_path)))

def test_collect_git_context_bad_commit_hash(tmp_path):
    repo = git.Repo.init(tmp_path)
    # No commits yet, so any hash is bad
    with pytest.raises(git.BadName):
        collect_git_context("deadbeef", repo=repo) 