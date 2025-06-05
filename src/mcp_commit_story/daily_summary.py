"""Daily summary file-creation-based trigger system.

This module provides functions to determine when daily summaries should be generated
based on journal file creation events, rather than maintaining state files.
"""

import os
import re
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Configure logging
logger = logging.getLogger(__name__)


def extract_date_from_journal_path(file_path: Optional[str], debug_context: Optional[str] = None) -> Optional[str]:
    """Extract date from journal file path.
    
    Args:
        file_path: Path to journal file (e.g., "/path/to/2025-01-06-journal.md")
        debug_context: Optional context for debugging (e.g., "new_journal_file", "git_commit")
        
    Returns:
        Date string in YYYY-MM-DD format, or None if invalid
    """
    if not file_path or not isinstance(file_path, str):
        return None
    
    try:
        # Extract filename from path
        filename = os.path.basename(file_path)
        
        # File extension validation - early exit for non-journal files
        if not filename.endswith('-journal.md'):
            return None  # Not a journal file, no date to extract
        
        # Match YYYY-MM-DD pattern in filename
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        match = re.search(date_pattern, filename)
        
        if not match:
            return None
        
        date_str = match.group(1)
        
        # Validate date format by parsing it
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Sanity checks with appropriate handling
            if parsed_date.date() > datetime.now().date():
                logger.info(f"Future date detected in journal filename: {date_str} (this may be normal for git operations)")
            
            # Check for obviously invalid historical dates  
            if parsed_date.year < 1970:  # Unix epoch start
                logger.warning(f"Suspiciously old date in filename: {date_str}")
                return None
            
            # Debug logging with context
            if date_str:
                context_msg = f" (source: {debug_context})" if debug_context else ""
                logger.debug(f"Extracted date {date_str} from {filename}{context_msg}")
            
            return date_str
            
        except ValueError:
            # Invalid date (e.g., 2025-13-40)
            logger.warning(f"Invalid date in filename: {date_str}")
            return None
            
    except Exception as e:
        logger.warning(f"Error extracting date from path '{file_path}': {e}")
        return None


def daily_summary_exists(date_str: str, summary_dir: str) -> bool:
    """Check if a daily summary file already exists for the given date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        summary_dir: Directory where summary files are stored
        
    Returns:
        True if summary file exists, False otherwise
    """
    try:
        if not os.path.exists(summary_dir):
            return False
        
        # Check for standard summary file format
        summary_filename = f"{date_str}-summary.md"
        summary_path = os.path.join(summary_dir, summary_filename)
        
        return os.path.exists(summary_path)
        
    except Exception as e:
        logger.warning(f"Error checking summary existence for {date_str}: {e}")
        return False


def should_generate_daily_summary(new_file_path: Optional[str], summary_dir: str) -> Optional[str]:
    """Determine if a daily summary should be generated based on new journal file creation.
    
    This function implements the file-creation-based trigger logic:
    1. Extract date from the new journal file being created
    2. Find the most recent journal file before this date
    3. Check if summary already exists for that date
    4. Return the date for which summary should be generated, or None
    
    Args:
        new_file_path: Path to the new journal file being created
        summary_dir: Directory where summary files are stored
        
    Returns:
        Date string (YYYY-MM-DD) for which to generate summary, or None
    """
    if not new_file_path:
        return None
    
    try:
        # Extract date from the new file being created
        new_file_date = extract_date_from_journal_path(new_file_path, "new_journal_file")
        if not new_file_date:
            logger.warning(f"Could not extract date from new file: {new_file_path}")
            return None
        
        # Find the directory containing journal files
        journal_dir = os.path.dirname(new_file_path)
        if not os.path.exists(journal_dir):
            logger.warning(f"Journal directory does not exist: {journal_dir}")
            return None
        
        # Find all previous journal files (before the new file date)
        previous_files = []
        
        try:
            for filename in os.listdir(journal_dir):
                if filename.endswith('-journal.md'):
                    file_path = os.path.join(journal_dir, filename)
                    file_date_str = extract_date_from_journal_path(file_path, "existing_journal_file")
                    
                    if file_date_str and file_date_str < new_file_date:
                        previous_files.append((file_date_str, file_path))
        
        except OSError as e:
            logger.warning(f"Error reading journal directory {journal_dir}: {e}")
            return None
        
        if not previous_files:
            logger.info(f"No previous journal entries found before {new_file_date}")
            return None
        
        # Get the most recent previous date
        most_recent_date = max(previous_files, key=lambda x: x[0])[0]
        
        # Check if daily summary already exists for that date
        if daily_summary_exists(most_recent_date, summary_dir):
            logger.info(f"Daily summary already exists for {most_recent_date}")
            return None
        
        logger.info(f"Should generate daily summary for {most_recent_date}")
        return most_recent_date
        
    except Exception as e:
        logger.warning(f"Error determining if daily summary should be generated: {e}")
        return None


def should_generate_period_summaries(date_str: Optional[str]) -> Dict[str, bool]:
    """Determine which period summaries should be generated based on commit date.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Dictionary indicating which period summaries to generate:
        {'weekly': bool, 'monthly': bool, 'quarterly': bool, 'yearly': bool}
    """
    result = {
        'weekly': False,
        'monthly': False,
        'quarterly': False,
        'yearly': False
    }
    
    if not date_str or not isinstance(date_str, str):
        return result
    
    try:
        # Parse the date string
        commit_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Weekly summary on Mondays (weekday() returns 0 for Monday)
        if commit_date.weekday() == 0:
            result['weekly'] = True
        
        # Monthly summary on 1st of month
        if commit_date.day == 1:
            result['monthly'] = True
        
        # Quarterly summary on quarter start dates (Jan 1, Apr 1, Jul 1, Oct 1)
        if commit_date.month in [1, 4, 7, 10] and commit_date.day == 1:
            result['quarterly'] = True
        
        # Yearly summary on January 1st
        if commit_date.month == 1 and commit_date.day == 1:
            result['yearly'] = True
            
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid date format '{date_str}': {e}")
        return result
    except Exception as e:
        logger.warning(f"Error determining period summaries for '{date_str}': {e}")
        return result 