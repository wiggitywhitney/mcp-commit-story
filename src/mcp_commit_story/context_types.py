import sys
from typing import List, Optional, Union, Dict

if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# Architecture Decision: Terminal Command Collection Removed (2025-06-27)
# Terminal commands were originally designed to be collected by Cursor's AI with
# access to its execution context. With the shift to external journal generation,
# we no longer have access. Git diffs and chat context provide sufficient narrative.

class ChatMessage(TypedDict):
    speaker: str
    text: str

class ChatHistory(TypedDict):
    messages: List[ChatMessage]

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

class CommitMetadataSection(TypedDict):
    commit_metadata: Dict[str, str]  # Key-value pairs of commit statistics and metadata 