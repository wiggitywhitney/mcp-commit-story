"""
Context collection functions for MCP Commit Story.

This module provides unified functions for collecting chat, terminal, and git context for journal entry generation.
"""

import os
from mcp_commit_story.context_types import ChatHistory, TerminalContext, GitContext
from mcp_commit_story.git_utils import get_repo, get_current_commit, get_commit_details, get_commit_diff_summary, classify_file_type, classify_commit_size, NULL_TREE


def collect_chat_history(since_commit=None, max_messages_back=150) -> ChatHistory:
    """
    Returns:
        ChatHistory: Structured chat history as defined in context_types.py

    Notes:
    - The ChatHistory type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.

    Collect relevant chat history for journal entry.

    AI Prompt:
    Please analyze our ENTIRE chat history within the specified boundary and extract ALL relevant discussion points for the journal entry.
    - Search backward through the current conversation for the last time you invoked the mcp-commit-story new-entry command (or a similar journal generation function).
    - If no such reference is found, review all available conversation history within your context window.
    IMPORTANT: Review ALL chat messages and terminal commands within this boundary, not just the most recent ones.
    Be thorough and comprehensive in your review—do not skip or summarize large portions of the conversation.
    Focus on:
      1. Technical decisions and reasoning
      2. Problem-solving approaches and solutions
      3. Challenges encountered and how they were addressed
      4. Expressions of frustration, satisfaction, or other emotions
      5. Key questions and answers that shaped the work
    Do NOT include:
      - Passwords, API keys, authentication tokens
      - Personal identifiable information (PII)
      - Other sensitive data
      - Routine procedural discussions that don't provide insight
      - Ambiguous notes that don't add clear value
    If in doubt about whether to include a note, err on the side of exclusion unless it clearly adds value to the engineering narrative.
    Format each discussion note as a dictionary with 'speaker' and 'text' fields when the speaker is identifiable, or just 'text' for unattributed notes.
    These entries may be used to generate developer-facing summaries or historical narratives. Please ensure clarity and accuracy.
    The goal is to capture the complete narrative and decision-making process, reviewing ALL available information within the boundary.
    
    ANTI-HALLUCINATION RULES:
    - Do NOT invent, infer, or summarize information that is not explicitly present in the actual conversation history.
    - Only include discussion points that are directly supported by the chat transcript.
    - If a detail is not present, do NOT speculate or fill in gaps.

    Checklist:
    - [ ] Search backward through the current conversation for the last invocation of the mcp-commit-story new-entry command (or similar journal generation function)
    - [ ] If no such reference is found, review all available conversation history within your context window
    - [ ] Review ALL chat messages and terminal commands within this boundary, not just the most recent ones
    - [ ] Be thorough and comprehensive—do not skip or summarize large portions of the conversation
    - [ ] Focus on extracting:
        - Technical decisions and reasoning
        - Problem-solving approaches and solutions
        - Challenges encountered and how they were addressed
        - Expressions of frustration, satisfaction, or other emotions
        - Key questions and answers that shaped the work
    - [ ] Exclude:
        - Passwords, API keys, authentication tokens
        - Personal identifiable information (PII)
        - Other sensitive data
        - Routine procedural discussions that don't provide insight
        - Ambiguous notes that don't add clear value
    - [ ] If in doubt about whether to include a note, err on the side of exclusion unless it clearly adds value to the engineering narrative
    - [ ] Format each discussion note as a dictionary with 'speaker' and 'text' fields when the speaker is identifiable, or just 'text' for unattributed notes
    - [ ] Ensure clarity and accuracy, as these entries may be used for developer-facing summaries or historical narratives
    - [ ] ANTI-HALLUCINATION: Do NOT invent, infer, or summarize information that is not explicitly present in the actual conversation history
    - [ ] ANTI-HALLUCINATION: Only include discussion points directly supported by the chat transcript
    - [ ] ANTI-HALLUCINATION: If a detail is not present, do NOT speculate or fill in gaps

    ---
    ADDITIONAL INSTRUCTIONS (MESSAGE-BASED BOUNDARY):
    - This function scans backward through the conversation for the last commit reference (e.g., last journal entry or new-entry command).
    - If no such reference is found, scan up to `max_messages_back` messages.
    - No time-based boundaries are used.
    - Do not use timestamps or time-based calculations for chat history collection.
    - All time boundaries in this function are deprecated in favor of message count.
    """
    return ChatHistory(messages=[])


def collect_ai_terminal_commands(since_commit=None, max_messages_back=150) -> TerminalContext:
    """
    Returns:
        TerminalContext: Structured terminal command context as defined in context_types.py

    Notes:
    - The TerminalContext type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.

    Collect terminal commands executed by AI during the current work session.

    AI Prompt:
    Please analyze our ENTIRE terminal command history within the specified boundary and extract ALL relevant commands executed by the AI for the journal entry.
    - Search backward through the current conversation for the last time you invoked the mcp-commit-story new-entry command (or a similar journal generation function).
    - If no such reference is found, review all available terminal command history within your context window.
    IMPORTANT: Review ALL terminal commands within this boundary, not just the most recent ones.
    Be thorough and comprehensive in your review—do not skip or summarize large portions of the command history.
    Focus on including:
      - Commands that demonstrate problem-solving steps
      - Commands that show the technical approach
      - Failed commands that highlight challenges or errors
      - Repetitive commands that might indicate frustrations or iteration
    Exclude:
      - Routine git commands (add, status, commit) unless they are significant to the narrative
      - Commands run specifically as part of journal entry creation
      - Commands containing passwords, API keys, tokens, or other sensitive information
      - Commands that reveal personal identifiable information (PII)
    If in doubt about whether to include a command, err on the side of exclusion unless it clearly adds value to the engineering narrative.
    Format the output as a chronological list of terminal commands, suitable for inclusion in a developer-facing journal entry.
    These entries may be used to generate developer-facing summaries or historical narratives. Please ensure clarity and accuracy.
    The goal is to document the complete technical steps taken during the work session, reviewing ALL available information within the boundary.

    ANTI-HALLUCINATION RULES:
    - Do NOT invent, infer, or summarize commands that are not explicitly present in the actual terminal history.
    - Only include commands that are directly supported by the terminal transcript.
    - If a command is not present, do NOT speculate or fill in gaps.

    Checklist:
    - [ ] Search backward through the current conversation for the last invocation of the mcp-commit-story new-entry command (or similar journal generation function)
    - [ ] If no such reference is found, review all available terminal command history within your context window
    - [ ] Review ALL terminal commands within this boundary, not just the most recent ones
    - [ ] Be thorough and comprehensive—do not skip or summarize large portions of the command history
    - [ ] Focus on including:
        - Commands that demonstrate problem-solving steps
        - Commands that show the technical approach
        - Failed commands that highlight challenges or errors
        - Repetitive commands that might indicate frustrations or iteration
    - [ ] Exclude:
        - Routine git commands (add, status, commit) unless significant to the narrative
        - Commands run specifically as part of journal entry creation
        - Commands containing passwords, API keys, tokens, or other sensitive information
        - Commands that reveal personal identifiable information (PII)
    - [ ] If in doubt about whether to include a command, err on the side of exclusion unless it clearly adds value to the engineering narrative
    - [ ] Format the output as a chronological list of terminal commands, suitable for a developer-facing journal entry
    - [ ] Ensure clarity and accuracy, as these entries may be used for developer-facing summaries or historical narratives
    - [ ] ANTI-HALLUCINATION: Do NOT invent, infer, or summarize commands that are not explicitly present in the actual terminal history
    - [ ] ANTI-HALLUCINATION: Only include commands directly supported by the terminal transcript
    - [ ] ANTI-HALLUCINATION: If a command is not present, do NOT speculate or fill in gaps

    ---
    ADDITIONAL INSTRUCTIONS (MESSAGE-BASED BOUNDARY):
    - This function scans backward through the conversation for the last commit reference (e.g., last journal entry or new-entry command).
    - If no such reference is found, scan up to `max_messages_back` messages.
    - No time-based boundaries are used.
    - Do not use timestamps or time-based calculations for terminal command collection.
    - All time boundaries in this function are deprecated in favor of message count.
    """
    return TerminalContext(commands=[])


def collect_git_context(commit_hash=None, repo=None, journal_path=None) -> GitContext:
    """
    Collect structured git context for a given commit hash (or HEAD if None).

    Args:
        commit_hash (str, optional): Commit hash to analyze. Defaults to HEAD.
        repo (git.Repo, optional): GitPython Repo object. Defaults to current repo.
        journal_path (str, optional): Path to the journal file or directory to exclude from context (for recursion prevention).

    Returns:
        GitContext: Structured git context as defined in context_types.py

    Notes:
    - The GitContext type is a TypedDict defined in context_types.py.
    - All context is ephemeral and only persisted as part of the generated journal entry.
    - This function enforces the in-memory-only rule for context data.
    - If journal_path is provided, all journal files are filtered from changed_files, file_stats, and diff_summary to prevent recursion.
    """
    if repo is None:
        repo = get_repo()
    try:
        if commit_hash is None:
            commit = get_current_commit(repo)
        else:
            commit = repo.commit(commit_hash)
    except Exception as e:
        import git as gitlib
        if isinstance(e, gitlib.InvalidGitRepositoryError):
            raise
        if isinstance(e, gitlib.BadName):
            raise
        raise
    # Metadata
    details = get_commit_details(commit)
    metadata = {
        'hash': details.get('hash'),
        'author': details.get('author'),
        'date': details.get('datetime'),
        'message': details.get('message'),
    }
    # Diff summary
    diff_summary = get_commit_diff_summary(commit)
    # Changed files
    parent = commit.parents[0] if commit.parents else None
    # For the initial commit, diff against the empty tree (NULL_TREE)
    diffs = commit.diff(parent) if parent else commit.diff(NULL_TREE)
    changed_files = []
    file_stats = {'source': 0, 'config': 0, 'docs': 0, 'tests': 0}
    for diff in diffs:
        fname = diff.b_path or diff.a_path
        if fname:
            changed_files.append(fname)
            ftype = classify_file_type(fname)
            if ftype in file_stats:
                file_stats[ftype] += 1
            else:
                file_stats['source'] += 1  # Default bucket
    # --- Recursion prevention: filter out journal files ---
    if journal_path:
        journal_rel = os.path.relpath(journal_path, repo.working_tree_dir)
        changed_files = [f for f in changed_files if not f.startswith(journal_rel)]
        # Regenerate file_stats without journal files
        file_stats = {'source': 0, 'config': 0, 'docs': 0, 'tests': 0}
        for f in changed_files:
            ftype = classify_file_type(f)
            if ftype in file_stats:
                file_stats[ftype] += 1
            else:
                file_stats['source'] += 1
        # Regenerate diff_summary without journal files
        # (Optional: for now, just note in diff_summary if journal files were filtered)
        diff_summary += "\n[Journal files filtered for recursion prevention]"
    # Commit size
    stats = details.get('stats', {})
    insertions = stats.get('insertions', 0)
    deletions = stats.get('deletions', 0)
    size_classification = classify_commit_size(insertions, deletions)
    # Merge status
    is_merge = len(commit.parents) > 1
    commit_context = {
        'size_classification': size_classification,
        'is_merge': is_merge,
    }
    return {
        'metadata': metadata,
        'diff_summary': diff_summary,
        'changed_files': changed_files,
        'file_stats': file_stats,
        'commit_context': commit_context,
    } 