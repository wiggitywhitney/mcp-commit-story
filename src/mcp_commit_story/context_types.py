from typing import TypedDict, List, Optional

class ChatMessage(TypedDict):
    speaker: str
    text: str

class ChatHistory(TypedDict):
    messages: List[ChatMessage]

class TerminalCommand(TypedDict):
    command: str
    executed_by: str  # "user" or "ai"

class TerminalContext(TypedDict):
    commands: List[TerminalCommand]

class GitMetadata(TypedDict):
    hash: str
    author: str
    date: str
    message: str

class GitContext(TypedDict):
    metadata: GitMetadata
    diff_summary: str
    changed_files: List[str]
    file_stats: dict
    commit_context: dict

class JournalContext(TypedDict):
    chat: Optional[ChatHistory]
    terminal: Optional[TerminalContext]
    git: GitContext

class SummarySection(TypedDict):
    summary: str  # The finished summary paragraph for the journal entry 