"""
TypedDict definitions for journal workflow operations.

This module provides structured type definitions for journal entry generation,
file operations, and workflow coordination to ensure type safety and clear
API contracts across the journal workflow functions.
"""

import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# Import existing context types for reference
from .context_types import GitContext, ChatHistory, TerminalContext


# =============================================================================
# Subtask 9.1: Journal Entry Generation
# =============================================================================

class GenerateJournalEntryInput(TypedDict):
    """Input parameters for generate_journal_entry function."""
    commit: Any  # git.Commit object (avoiding import due to optional dependency)
    config: Dict[str, Any]  # Config object or dict representation
    debug: bool

class GenerateJournalEntryResult(TypedDict):
    """Result from generate_journal_entry function."""
    entry: Optional[Any]  # JournalEntry object or None if skipped
    skipped: bool
    skip_reason: Optional[str]  # Only present if skipped=True


# =============================================================================
# Helper Types for Journal Operations
# =============================================================================

class JournalOnlyCommitCheck(TypedDict):
    """Input for is_journal_only_commit validation."""
    commit: Any  # git.Commit object
    journal_path: str

class JournalOnlyCommitResult(TypedDict):
    """Result from is_journal_only_commit check."""
    is_journal_only: bool
    changed_files: List[str]  # For debugging/telemetry purposes


# =============================================================================
# Subtask 9.2: File Operations
# =============================================================================

class SaveJournalEntryInput(TypedDict):
    """Input parameters for save_journal_entry function."""
    entry: Any  # JournalEntry object
    config: Dict[str, Any]  # Config object or dict representation

class SaveJournalEntryResult(TypedDict):
    """Result from save_journal_entry function."""
    file_path: str  # Absolute path to saved journal file
    success: bool
    created_new_file: bool  # Whether a new file was created vs appended


# =============================================================================
# Context Collection Types
# =============================================================================

class CollectedJournalContext(TypedDict):
    """Fully assembled context data for journal generation."""
    git_context: GitContext
    chat_context: Optional[ChatHistory]
    terminal_context: Optional[TerminalContext]
    config: Dict[str, Any]
    collection_timestamp: str  # ISO timestamp when context was collected

class ContextCollectionResult(TypedDict):
    """Result from context collection operations."""
    context: CollectedJournalContext
    collection_success: bool
    failed_sources: List[str]  # Sources that failed to collect (e.g., ['chat', 'terminal'])
    warnings: List[str]  # Non-fatal issues during collection 