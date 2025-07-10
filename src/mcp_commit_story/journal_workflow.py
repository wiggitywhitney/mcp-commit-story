"""
Journal entry workflow orchestration for MCP Commit Story.

This module handles the high-level workflow of generating journal entries,
orchestrating context collection and section generation functions.
"""

import logging
from typing import Optional
from datetime import datetime

from .telemetry import trace_mcp_operation
from .journal import JournalEntry
from .context_types import JournalContext

logger = logging.getLogger(__name__)


@trace_mcp_operation("journal.generate_entry", attributes={"operation_type": "workflow_orchestration"})
def generate_journal_entry(commit, config, debug=False) -> Optional[JournalEntry]:
    """
    Generate a complete journal entry by orchestrating all context collection and section generation functions.
    
    This is the core workflow function that:
    1. Detects journal-only commits and skips them to prevent infinite loops
    2. Collects all available context (chat, terminal, git)
    3. Orchestrates all section generators to build a complete journal entry
    4. Implements graceful degradation - continues processing even if individual sections fail
    
    Args:
        commit: GitPython commit object
        config: Configuration object with journal settings
        debug: Enable debug logging for troubleshooting
        
    Returns:
        JournalEntry: Complete journal entry object, or None if commit should be skipped
    """
    from .context_collection import collect_chat_history, collect_git_context, collect_recent_journal_context
    from .journal import (
        generate_summary_section, generate_technical_synopsis_section,
        generate_accomplishments_section, generate_frustrations_section,
        generate_tone_mood_section, generate_discussion_notes_section,
        generate_commit_metadata_section
    )
    
    if debug:
        logger.debug(f"Starting journal entry generation for commit: {commit.hexsha}")
    
    # Step 1: Check if this is a journal-only commit and skip if so
    journal_path = config.get('journal', {}).get('path', 'sandbox-journal')
    try:
        if is_journal_only_commit(commit, journal_path):
            if debug:
                logger.debug("Skipping journal-only commit to prevent infinite loop")
            return None
    except Exception as e:
        logger.error(f"Error checking journal-only commit status: {e}")
        # Continue processing on error - prefer generating entry over skipping
    
    # Step 2: Collect all available context with graceful degradation
    context_data = {}
    
    # Collect chat history - fixed function signature
    try:
        if debug:
            logger.debug("Collecting chat history context")
        context_data['chat_history'] = collect_chat_history(since_commit=commit.hexsha, max_messages_back=150)
    except Exception as e:
        logger.error(f"Failed to collect chat history: {e}")
        context_data['chat_history'] = None
    
    # Terminal command collection removed per architectural decision
    # See Task 56: Remove Terminal Command Collection Infrastructure
    
    # Collect git context - fixed function signature
    try:
        if debug:
            logger.debug("Collecting git context")
        context_data['git_context'] = collect_git_context(commit_hash=commit.hexsha, journal_path=journal_path)
    except Exception as e:
        logger.error(f"Failed to collect git context: {e}")
        # Create minimal git context from commit object
        context_data['git_context'] = {
            'metadata': {
                'hash': commit.hexsha,
                'author': str(commit.author),
                'date': commit.committed_datetime.isoformat(),
                'message': commit.message.strip()
            },
            'diff_summary': '',
            'changed_files': [],
            'file_stats': {},
            'commit_context': {}
        }
    
    # Collect recent journal context (new in Task 51.4)
    try:
        if debug:
            logger.debug("Collecting recent journal context")
        context_data['journal_context'] = collect_recent_journal_context(commit)
    except Exception as e:
        logger.error(f"Failed to collect recent journal context: {e}")
        context_data['journal_context'] = None
    
    # Build JournalContext using correct 3-field structure: chat, git, journal
    journal_context = JournalContext(
        chat=context_data['chat_history'],
        git=context_data['git_context'],
        journal=context_data['journal_context']
    )
    
    if debug:
        logger.debug(f"Built journal context with git context and optional chat data")
    
    # Step 3: Generate all sections with graceful degradation
    sections = {}
    
    # List of all section generators and their corresponding fields (7 total, down from 8)
    section_generators = [
        ('summary', generate_summary_section),
        ('technical_synopsis', generate_technical_synopsis_section),
        ('accomplishments', generate_accomplishments_section),
        ('frustrations', generate_frustrations_section),
        ('tone_mood', generate_tone_mood_section),
        ('discussion_notes', generate_discussion_notes_section),
        ('commit_metadata', generate_commit_metadata_section)
    ]
    
    for section_name, generator_func in section_generators:
        try:
            if debug:
                logger.debug(f"Generating {section_name} section")
            
            section_content = generator_func(journal_context)
            
            # Extract content using correct field names from TypedDict definitions
            if section_name == 'summary':
                sections[section_name] = section_content.get('summary', '')
            elif section_name == 'technical_synopsis':
                sections[section_name] = section_content.get('technical_synopsis', '')
            elif section_name == 'accomplishments':
                sections[section_name] = section_content.get('accomplishments', [])
            elif section_name == 'frustrations':
                sections[section_name] = section_content.get('frustrations', [])
            elif section_name == 'tone_mood':
                mood_data = section_content
                if mood_data.get('mood') or mood_data.get('indicators'):
                    sections[section_name] = {
                        'mood': mood_data.get('mood', ''),
                        'indicators': mood_data.get('indicators', '')
                    }
            elif section_name == 'discussion_notes':
                sections[section_name] = section_content.get('discussion_notes', [])
            elif section_name == 'commit_metadata':
                sections[section_name] = section_content.get('commit_metadata', {})
                
        except Exception as e:
            logger.error(f"Failed to generate {section_name} section: {e}")
            # Graceful degradation - skip failed sections entirely
            if debug:
                logger.debug(f"Skipping {section_name} section due to generation failure")
    
    # Step 4: Build the final journal entry with cross-platform timestamp format
    # Use commit time for consistency (same approach as server.py)
    commit_datetime = commit.committed_datetime
    timestamp = commit_datetime.strftime("%I:%M %p").lstrip('0')  # Cross-platform format: "2:34 PM"
    
    if debug:
        logger.debug(f"Creating journal entry with {len(sections)} successful sections")
    
    # Create the journal entry using the approved section ordering (terminal_commands removed)
    journal_entry = JournalEntry(
        timestamp=timestamp,
        commit_hash=commit.hexsha,  # Use GitPython commit object property
        summary=sections.get('summary'),
        technical_synopsis=sections.get('technical_synopsis'),
        accomplishments=sections.get('accomplishments'),
        frustrations=sections.get('frustrations'),
        tone_mood=sections.get('tone_mood'),
        discussion_notes=sections.get('discussion_notes'),
        commit_metadata=sections.get('commit_metadata')
    )
    
    if debug:
        logger.debug("Journal entry generation completed successfully")
    
    return journal_entry


def is_journal_only_commit(commit, journal_path):
    """
    Check if a commit only touches files within the journal path.
    
    This function prevents infinite loops by detecting commits that only
    modify journal files themselves (like when journal entries are committed).
    
    Args:
        commit: GitPython commit object
        journal_path: Path to the journal directory
        
    Returns:
        bool: True if commit only touches journal files, False otherwise
    """
    # Import the actual implementation from git_utils
    from .git_utils import is_journal_only_commit as git_utils_impl
    
    # Handle GitPython commit object
    try:
        # Get list of changed files from GitPython commit
        parent = commit.parents[0] if commit.parents else None
        if parent:
            changed_files = [item.a_path or item.b_path for item in commit.diff(parent)]
        else:
            # Initial commit - diff against empty tree
            from .git_utils import NULL_TREE
            changed_files = [item.a_path or item.b_path for item in commit.diff(NULL_TREE)]
        
        # Check if all files are in journal path
        if not changed_files:
            return False
            
        return all(f.startswith(journal_path) for f in changed_files if f)
        
    except Exception as e:
        logger.error(f"Error checking journal-only commit: {e}")
        return False  # Default to processing on error


def save_journal_entry(journal_entry, config, debug=False, date_str=None):
    """
    Save a journal entry to the appropriate daily file with header logic.
    
    Detects when creating a new daily file and adds the appropriate header.
    Handles both Config objects and dict configurations.
    
    Args:
        journal_entry: JournalEntry object to save
        config: Configuration object with journal settings (Config object or dict)
        debug: Enable debug logging
        date_str: Optional date string (YYYY-MM-DD) to use instead of current date
        
    Returns:
        str: Path to the saved file
    """
    from .journal import append_to_journal_file, ensure_journal_directory, get_journal_file_path
    from pathlib import Path
    
    # Use provided date or fall back to current date
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Handle both Config objects and dict configurations to get journal path
    if hasattr(config, 'journal_path'):
        journal_path = config.journal_path
    else:
        journal_path = config.get('journal', {}).get('path', 'sandbox-journal')
    
    # Get relative path and combine with configured journal path
    relative_path = get_journal_file_path(date_str, "daily")
    full_path = Path(journal_path) / relative_path
    
    # Check if this is a new daily file
    file_exists = full_path.exists()
    
    # Ensure directory exists
    ensure_journal_directory(str(full_path))
    
    # Get entry markdown
    entry_markdown = journal_entry.to_markdown()
    
    # Add daily header if creating new file, otherwise append to existing file
    if not file_exists:
        # Parse the date string to create a formatted header
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%B %d, %Y")  # "June 3, 2025"
        content = f"# Daily Journal Entries - {date_formatted}\n\n{entry_markdown}"
        
        if debug:
            logger.debug(f"Adding daily header to new file: {full_path}")
        
        with open(str(full_path), 'w') as f:
            f.write(content)
    else:
        # File exists, use append function which handles separators correctly
        if debug:
            logger.debug(f"Appending to existing file: {full_path}")
        
        append_to_journal_file(entry_markdown, str(full_path))
    
    if debug:
        logger.debug(f"Saved journal entry to: {full_path}")
    
    return str(full_path)


def handle_journal_entry_creation(commit, config, debug=False):
    """
    Complete workflow to generate and save a journal entry.
    
    This combines generate_journal_entry() and save_journal_entry() into
    a single workflow function for use by MCP tools.
    
    Args:
        commit: GitPython commit object
        config: Configuration object
        debug: Enable debug logging
        
    Returns:
        dict: Result with success status and file path
    """
    try:
        # Generate journal entry
        journal_entry = generate_journal_entry(commit, config, debug)
        
        if journal_entry is None:
            return {
                'success': True,
                'skipped': True,
                'reason': 'journal-only commit',
                'file_path': None
            }
        
        # Save journal entry using commit date for consistency
        commit_date_str = commit.committed_datetime.strftime("%Y-%m-%d")
        file_path = save_journal_entry(journal_entry, config, debug, date_str=commit_date_str)
        
        return {
            'success': True,
            'skipped': False,
            'file_path': file_path,
            'entry_sections': len([
                s for s in [
                    journal_entry.summary,
                    journal_entry.technical_synopsis,
                    journal_entry.accomplishments,
                    journal_entry.frustrations,
                    journal_entry.tone_mood,
                    journal_entry.discussion_notes,
                    journal_entry.commit_metadata
                ] if s
            ])
        }
        
    except Exception as e:
        logger.error(f"Failed to create journal entry: {e}")
        return {
            'success': False,
            'error': str(e),
            'file_path': None
        } 