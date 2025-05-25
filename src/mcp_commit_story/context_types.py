from typing import TypedDict, List, Optional, Union, Dict

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

class TechnicalSynopsisSection(TypedDict):
    technical_synopsis: str  # The finished technical synopsis paragraph for the journal entry

class AccomplishmentsSection(TypedDict):
    accomplishments: List[str]  # List of accomplishment bullet points for the journal entry

class FrustrationsSection(TypedDict):
    frustrations: List[str]  # List of frustration/roadblock bullet points for the journal entry

class ToneMoodSection(TypedDict):
    mood: str  # The inferred mood
    indicators: str  # Evidence supporting the mood inference

class DiscussionNotesSection(TypedDict):
    discussion_notes: List[Union[str, Dict[str, str]]]  # Discussion points, with optional speaker attribution

class TerminalCommandsSection(TypedDict):
    terminal_commands: List[str]  # List of terminal commands executed during the session

class CommitMetadataSection(TypedDict):
    commit_metadata: Dict[str, str]  # Key-value pairs of commit statistics and metadata 