"""Core reflection functionality for manual reflection addition.

This module provides the core components for adding manual reflections to journal entries:
- format_reflection: Formats reflection text with timestamp and proper structure
- add_reflection_to_journal: Adds formatted reflection to journal files with proper separation

The implementation follows the on-demand directory creation pattern and uses \n\n separation
for sections as established in the existing codebase.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Union

# Import existing directory utility
from .journal import ensure_journal_directory


def format_reflection(reflection_text: str) -> str:
    """
    Format a reflection with timestamp and proper structure.
    
    Args:
        reflection_text: The user's reflection content
        
    Returns:
        Formatted reflection string with H2 header, timestamp, and double newlines
        
    Format:
        \n\n## Reflection (YYYY-MM-DD HH:MM:SS)\n\n[reflection_text]
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"\n\n## Reflection ({timestamp})\n\n{reflection_text}"


def add_reflection_to_journal(journal_path: Union[str, Path], reflection_text: str) -> bool:
    """
    Add a reflection to a journal entry file.
    
    This function follows the on-demand directory creation pattern and uses \n\n
    separation for sections as established in the existing codebase.
    
    Args:
        journal_path: Path to the journal file (will be created if doesn't exist)
        reflection_text: The reflection content to add
        
    Returns:
        True if successful
        
    Raises:
        OSError: If directory creation or file writing fails
    """
    # Ensure parent directory exists using existing utility
    ensure_journal_directory(journal_path)
    
    # Format the reflection
    formatted_reflection = format_reflection(reflection_text)
    
    # Append to file with UTF-8 encoding
    with open(journal_path, 'a', encoding='utf-8') as f:
        f.write(formatted_reflection)
    
    return True 