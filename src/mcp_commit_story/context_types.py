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
    """Chat message with optional enhanced metadata for improved context.
    
    Represents a single chat exchange with core required fields (speaker, text)
    and optional enhanced metadata fields (timestamp, bubbleId) that provide
    additional context when available from the chat system integration.
    
    Args:
        speaker: The role of the message sender - "Human" or "Assistant" 
        text: The content of the chat message
        timestamp: Optional Unix timestamp in milliseconds when message was sent
                 bubbleId: Unique identifier for AI filtering and conversation boundaries
         composerId: Cursor composer session identifier
    """
    speaker: str
    text: str
    # Optional enhanced metadata from Composer integration  
    timestamp: Optional[int]  # Unix timestamp in milliseconds

    bubbleId: Optional[str]  # Unique identifier for AI filtering
    composerId: Optional[str]  # Cursor composer session identifier

class ChatHistory(TypedDict):
    messages: List[ChatMessage]

class TimeWindow(TypedDict):
    """Time window information for chat context collection.
    
    Represents the time range for collecting chat messages during journal generation,
    including strategy used and calculated duration.
    """
    start_timestamp_ms: int  # Unix timestamp in milliseconds for window start
    end_timestamp_ms: int    # Unix timestamp in milliseconds for window end  
    strategy: str           # Strategy used: "commit_based", "fallback", etc.
    duration_hours: float   # Calculated duration in hours

class ChatContextData(TypedDict):
    """Enhanced chat context data with metadata for journal generation.
    
    Contains processed chat messages with time window information, unique session names,
    and additional metadata for comprehensive journal context.
    """
    messages: List[ChatMessage]      # Chat messages with enhanced metadata
    time_window: TimeWindow          # Time window information for the collection
    session_names: List[str]         # Unique session names found in messages  
    metadata: Dict[str, Union[str, int, float]]  # Additional context metadata

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
    file_diffs: Dict[str, str]  # Mapping of file paths to their diffs

class RecentJournalContext(TypedDict):
    """Recent journal context for enriching commit journal generation.
    
    Contains the most recent journal entry plus any AI captures or reflections
    added after that entry to avoid duplication while ensuring new insights
    are available for journal generation.
    
    Args:
        latest_entry: Most recent journal entry content (None if no entries found)
        additional_context: List of AI captures/reflections added after latest entry
        metadata: File information, timestamps, and collection statistics
    """
    latest_entry: Optional[str]  # Most recent journal entry content
    additional_context: List[str]  # AI captures/reflections after latest entry
    metadata: Dict[str, Union[str, int, bool]]  # File info, timestamps, statistics

class JournalContext(TypedDict):
    chat: Optional[ChatHistory]
    git: GitContext
    journal: Optional[RecentJournalContext]

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