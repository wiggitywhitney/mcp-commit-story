from mcp_commit_story.context_types import JournalContext, GitContext, ChatHistory

def mock_context_with_explicit_purpose():
    return JournalContext(
        git=GitContext(
            metadata={"hash": "abc123", "author": "Dev", "date": "2025-05-24", "message": "refactor: improve auth because it's messy"},
            diff_summary="Refactored authentication logic in auth.py.",
            changed_files=["auth.py"],
            file_stats={},
            commit_context={}
        ),
        chat=ChatHistory(messages=[
            {"speaker": "Human", "text": "Refactoring auth because it's messy"}
        ]),
        terminal=None
    )

def mock_context_evolution_thinking():
    return JournalContext(
        git=GitContext(
            metadata={"hash": "def456", "author": "Dev", "date": "2025-05-24", "message": "fix: resolve auth timeout"},
            diff_summary="Fixed timeout in authentication, improved connection pooling.",
            changed_files=["auth.py", "db.py"],
            file_stats={},
            commit_context={}
        ),
        chat=ChatHistory(messages=[
            {"speaker": "Human", "text": "Started fixing auth timeout"},
            {"speaker": "Human", "text": "Actually the real problem is connection pooling"}
        ]),
        terminal=None
    )

def mock_context_unkind_language():
    return JournalContext(
        git=GitContext(
            metadata={"hash": "ghi789", "author": "Dev", "date": "2025-05-24", "message": "fix: build"},
            diff_summary="Fixed build error in ci.yml.",
            changed_files=["ci.yml"],
            file_stats={},
            commit_context={}
        ),
        chat=ChatHistory(messages=[
            {"speaker": "Human", "text": "I'm such an idiot, I broke the build again. Fixing it now."}
        ]),
        terminal=None
    )

def mock_context_no_chat():
    return JournalContext(
        git=GitContext(
            metadata={"hash": "jkl012", "author": "Dev", "date": "2025-05-24", "message": "update: renamed variables"},
            diff_summary="Renamed variables in utils.py.",
            changed_files=["utils.py"],
            file_stats={},
            commit_context={}
        ),
        chat=None,
        terminal=None
    ) 