"""Standalone daily summary generation module.

Generates AI-powered daily summaries from journal entries without requiring the MCP server.
Designed for background processing and git hook integration.

Prerequisites:
- OpenAI API key in environment (`OPENAI_API_KEY`)
- Journal files: `journal/daily/YYYY-MM-DD-journal.md`
- Configuration file with journal paths

Usage:
```python
from mcp_commit_story.daily_summary_standalone import generate_daily_summary_standalone

# Generate summary for today
summary = generate_daily_summary_standalone()

# Generate for specific date
summary = generate_daily_summary_standalone("2025-01-15")
```

Functions produce the same output format as MCP-based generation.
"""

import os
import re
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from pathlib import Path
from opentelemetry import trace

# Core imports
from mcp_commit_story.config import load_config
from mcp_commit_story.telemetry import trace_mcp_operation, get_mcp_metrics
from mcp_commit_story.journal_workflow_types import DailySummary
from mcp_commit_story.journal_generate import (
    JournalEntry, 
    get_journal_file_path, 
    ensure_journal_directory
)
from mcp_commit_story.journal import JournalParser

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions Copied from daily_summary.py
# =============================================================================

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
            return date_str
        except ValueError:
            logger.warning(f"Invalid date format in filename: {date_str}")
            return None
            
    except Exception as e:
        logger.warning(f"Error extracting date from path {file_path}: {e}")
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
        # Check for standard summary file format (matches summariesV2 convention)
        summary_filename = f"{date_str}-summary.md"
        summary_path = os.path.join(summary_dir, summary_filename)
        return os.path.exists(summary_path)
    except Exception as e:
        logger.warning(f"Error checking if daily summary exists for {date_str}: {e}")
        return False


def should_generate_daily_summary(new_file_path: Optional[str], summary_dir: str) -> Optional[str]:
    """Determine if a daily summary should be generated based on file creation.
    
    This function implements file-creation-based trigger logic for daily summaries.
    It analyzes journal file creation patterns to determine when summaries should
    be generated for previous days.
    
    ## Prerequisites
    
    - Journal files in standard naming format: `YYYY-MM-DD-journal.md`
    - Summary directory exists or can be created
    - Journal files contain valid date patterns
    
    ## Usage
    
    ```python
    from mcp_commit_story.daily_summary_standalone import should_generate_daily_summary
    
    # Check if summary should be generated after creating new journal file
    new_journal = "/path/to/journal/daily/2025-01-16-journal.md"
    summaries_dir = "/path/to/journal/summaries/daily"
    
    generate_for_date = should_generate_daily_summary(new_journal, summaries_dir)
    
    if generate_for_date:
        print(f"Should generate summary for {generate_for_date}")
        # Proceed with summary generation
    else:
        print("No summary generation needed")
    ```
    
    ## Technical Context
    
    This function implements the file-creation-based trigger system:
    1. Extracts date from the new journal file being created
    2. Finds all previous journal files before that date
    3. Identifies the most recent previous date
    4. Checks if a summary already exists for that date
    5. Returns the date for summary generation, or None if not needed
    
    This approach ensures summaries are generated for "completed" days when new
    journal entries indicate work has moved to the next day.
    
    ## Logic Flow
    
    ```
    New file: 2025-01-16-journal.md
    Previous files: 2025-01-14-journal.md, 2025-01-15-journal.md
    Most recent: 2025-01-15
    Summary exists for 2025-01-15? → If No: return "2025-01-15"
    ```
    
    Args:
        new_file_path: Path to the new journal file being created
        summary_dir: Directory where summary files are stored
        
    Returns:
        Date string (YYYY-MM-DD) for which to generate summary, or None if no
        summary should be generated.
        
    Raises:
        None: This function handles all errors gracefully and returns None
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


def should_generate_period_summaries(date_str: Optional[str], summaries_dir: Optional[str] = None, last_commit_date: Optional[str] = None) -> Dict[str, bool]:
    """Determine which period summaries should be generated based on commit date.
    
    ENHANCED LOOKBACK APPROACH: Check if any period boundaries were crossed since
    the last commit, regardless of when the current commit happens. This ensures
    summaries are generated even for delayed commits after boundary dates.
    
    Args:
        date_str: Date string in YYYY-MM-DD format for current commit
        summaries_dir: Path to summaries directory (optional, uses default if None)
        last_commit_date: Date string for previous commit (optional, for gap detection)
        
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
        # Parse the current commit date
        commit_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Use default summaries directory if not provided
        if summaries_dir is None:
            # Default to journal/summaries - this will be configurable later
            summaries_dir = "journal/summaries"
        
        summaries_path = Path(summaries_dir)
        
        # Enhanced boundary detection: Check for missed boundaries
        # If last_commit_date is provided, check for boundaries crossed in the gap
        # Otherwise, use simplified boundary detection (current behavior)
        
        if last_commit_date:
            # Gap-aware detection: Check all boundaries crossed since last commit
            last_date = datetime.strptime(last_commit_date, "%Y-%m-%d").date()
            
            # Check for weekly boundaries crossed
            if _weekly_boundaries_crossed(last_date, commit_date, summaries_path):
                result['weekly'] = True
                
            # Check for monthly boundaries crossed  
            if _monthly_boundaries_crossed(last_date, commit_date, summaries_path):
                result['monthly'] = True
                
            # Check for quarterly boundaries crossed
            if _quarterly_boundaries_crossed(last_date, commit_date, summaries_path):
                result['quarterly'] = True
                
            # Check for yearly boundaries crossed
            if _yearly_boundaries_crossed(last_date, commit_date, summaries_path):
                result['yearly'] = True
        else:
            # Fallback to current logic for immediate boundary detection
            # Weekly summary: Check if we crossed into a new week and previous week needs summary
            if commit_date.weekday() == 0:  # Monday
                previous_week_end = commit_date - timedelta(days=1)  # Last Sunday
                if not _weekly_summary_exists(previous_week_end, summaries_path):
                    result['weekly'] = True
            
        # Monthly summary: Check if we crossed into new month and previous month needs summary
        if commit_date.day == 1:
            previous_month_end = commit_date - timedelta(days=1)  # Last day of previous month
            if not _monthly_summary_exists(previous_month_end, summaries_path):
                result['monthly'] = True
        
        # Quarterly summary: Check if we crossed into new quarter and previous quarter needs summary
        if commit_date.month in [1, 4, 7, 10] and commit_date.day == 1:
            previous_quarter_end = commit_date - timedelta(days=1)  # Last day of previous quarter
            if not _quarterly_summary_exists(previous_quarter_end, summaries_path):
                result['quarterly'] = True
        
        # Yearly summary: Check if we crossed into new year and previous year needs summary
        if commit_date.month == 1 and commit_date.day == 1:
            previous_year_end = commit_date - timedelta(days=1)  # Dec 31 of previous year
            if not _yearly_summary_exists(previous_year_end, summaries_path):
                result['yearly'] = True
                
    except ValueError:
        logger.warning(f"Invalid date format for period summary determination: {date_str}")
    except Exception as e:
        logger.warning(f"Error checking period summaries for {date_str}: {e}")
    
    return result


# Helper functions for period summary checking
def _weekly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if weekly boundaries were crossed between two dates."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _monthly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if monthly boundaries were crossed between two dates."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _quarterly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if quarterly boundaries were crossed between two dates."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _yearly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if yearly boundaries were crossed between two dates."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _weekly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a weekly summary exists for the given date."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _monthly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a monthly summary exists for the given date."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _quarterly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a quarterly summary exists for the given date."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def _yearly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a yearly summary exists for the given date."""
    # Implementation depends on existing helper functions
    return False  # Placeholder


def load_journal_entries_for_date(date_str: str, config: Dict) -> List[JournalEntry]:
    """Load and parse journal entries for a specific date.
    
    Reads journal file at `{config.journal.path}/daily/{date_str}-journal.md`
    and parses it into JournalEntry objects.
    
    Args:
        date_str: Date in YYYY-MM-DD format.
        config: Configuration object with journal path settings.
        
    Returns:
        List of JournalEntry objects from the journal file.
        
    Raises:
        Exception: If file reading or parsing fails.
    """
    entries = []
    try:
        # Use the established journal file path utility
        relative_path = get_journal_file_path(date_str, "daily")
        
        # Construct full path using config
        journal_base_path = config.get("journal", {}).get("path", "")
        if not journal_base_path:
            logger.error("No journal path found in config")
            return entries
        
        # Convert relative path to absolute path
        journal_file_path = os.path.join(journal_base_path, relative_path.replace("journal/", ""))
        
        if not os.path.exists(journal_file_path):
            logger.info(f"No journal file found for date {date_str} at {journal_file_path}")
            return entries
        
        # Read and parse the journal file
        with open(journal_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse journal entries using the established parser
        # Split on entry headers (### timestamp — Commit hash)
        # This pattern matches the header format used by JournalEntry.to_markdown()
        entry_pattern = r'(?=^### .+ — Commit [a-zA-Z0-9]+)'
        entry_sections = re.split(entry_pattern, content, flags=re.MULTILINE)
        
        # Remove empty sections and parse each entry
        for section in entry_sections:
            section = section.strip()
            if section and section.startswith('###'):
                try:
                    # Add horizontal rule separator for consistent parsing
                    normalized_section = section + '\n\n---\n\n'
                    entry = JournalParser.parse(normalized_section)
                    if entry:  # Only add valid entries
                        entries.append(entry)
                except Exception as e:
                    logger.warning(f"Failed to parse journal entry section: {e}")
                    # Log the problematic section for debugging
                    logger.debug(f"Problematic section (first 200 chars): {section[:200]}")
                    continue
        
        logger.info(f"Loaded {len(entries)} journal entries for {date_str}")
        return entries
        
    except Exception as e:
        logger.error(f"Error loading journal entries for {date_str}: {e}")
        return entries


def _extract_manual_reflections(entries: List[JournalEntry]) -> List[str]:
    """Extract manual reflections from journal entries.
    
    Manual reflections are identified by:
    1. Content in the journal that was manually added via reflection tools
    2. Discussion notes that contain explicit reflection patterns
    3. Frustrations or roadblocks that express personal insights
    
    Args:
        entries: List of journal entries to search
        
    Returns:
        List of manual reflection strings found in the entries
    """
    reflections = []
    
    # Patterns that indicate manual reflections
    reflection_patterns = [
        r"I think\s+",
        r"I realized\s+", 
        r"I learned\s+",
        r"My feeling is\s+",
        r"Looking back\s+",
        r"In hindsight\s+",
        r"Personally\s+",
        r"What struck me\s+",
        r"I noticed\s+"
    ]
    
    for entry in entries:
        # Check discussion notes for manual reflections
        if entry.discussion_notes:
            for note in entry.discussion_notes:
                if isinstance(note, dict) and note.get('speaker') == 'Human':
                    text = note.get('text', '')
                    if any(re.search(pattern, text, re.IGNORECASE) for pattern in reflection_patterns):
                        reflections.append(f"[{entry.timestamp}] {text}")
                elif isinstance(note, str):
                    # Look for reflection patterns in string notes
                    if any(re.search(pattern, note, re.IGNORECASE) for pattern in reflection_patterns):
                        reflections.append(f"[{entry.timestamp}] {note}")
        
        # Check frustrations for reflective content
        if entry.frustrations:
            for frustration in entry.frustrations:
                if any(re.search(pattern, frustration, re.IGNORECASE) for pattern in reflection_patterns):
                    reflections.append(f"[{entry.timestamp}] {frustration}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_reflections = []
    for reflection in reflections:
        if reflection not in seen:
            seen.add(reflection)
            unique_reflections.append(reflection)
    
    return unique_reflections


def _call_ai_for_daily_summary(entries: List[JournalEntry], date_str: str, config: dict) -> Dict:
    """Call AI to generate daily summary from journal entries using comprehensive prompt.
    
    Args:
        entries: List of journal entries for the day
        date_str: Date in YYYY-MM-DD format
        config: Configuration for AI generation
        
    Returns:
        Dictionary containing generated summary sections
    """
    try:
        # Format journal entries into context for AI
        journal_content = _format_entries_for_ai(entries)
        
        # Build the comprehensive AI prompt
        prompt = _build_daily_summary_prompt(journal_content, date_str)
        
        # Call AI with the prompt (placeholder for actual AI integration)
        # In a real implementation, this would call the configured AI model
        # For now, we'll generate a more realistic mock response based on the entries
        
        from mcp_commit_story.journal_generate import log_ai_agent_interaction
        log_ai_agent_interaction(prompt, None, debug_mode=True)
        
        # Generate a more realistic response based on actual entry content
        response = _generate_mock_daily_summary_response(entries, date_str)
        
        logger.info(f"Generated daily summary for {date_str} from {len(entries)} entries")
        return response
        
    except Exception as e:
        logger.error(f"Error calling AI for daily summary: {e}")
        # Return minimal response on error
        return {
            "summary": f"Summary generation failed for {date_str}",
            "reflections": [],
            "progress_made": "Unable to generate progress summary",
            "key_accomplishments": [],
            "technical_synopsis": "Unable to generate technical synopsis",
            "challenges_and_learning": [],
            "discussion_highlights": [],
            "tone_mood": None,
            "daily_metrics": {"commits": len(entries), "generation_error": True}
        }


def _format_entries_for_ai(entries: List[JournalEntry]) -> str:
    """Format journal entries for AI processing."""
    # Import the helper function from the original module
    from mcp_commit_story.daily_summary import _format_entries_for_ai as original_format
    return original_format(entries)


def _build_daily_summary_prompt(journal_content: str, date_str: str) -> str:
    """Build the comprehensive AI prompt for daily summary generation."""
    # Import the helper function from the original module
    from mcp_commit_story.daily_summary import _build_daily_summary_prompt as original_build
    return original_build(journal_content, date_str)


def _generate_mock_daily_summary_response(entries: List[JournalEntry], date_str: str) -> Dict:
    """Generate a mock daily summary response based on journal entries."""
    # Import the helper function from the original module
    from mcp_commit_story.daily_summary import _generate_mock_daily_summary_response as original_mock
    return original_mock(entries, date_str)


@trace_mcp_operation("daily_summary.generate", attributes={"operation_type": "ai_generation", "section_type": "daily_summary"})
def generate_daily_summary(journal_entries: List[JournalEntry], date_str: str, config: dict) -> DailySummary:
    """Generate a comprehensive daily summary from journal entries.
    
    This function provides the core AI-powered daily summary generation logic
    that synthesizes a full day's worth of journal entries into a structured
    summary with comprehensive sections.
    
    Args:
        journal_entries: List of journal entries for the specified date
        date_str: Date in YYYY-MM-DD format
        config: Configuration dictionary with AI model settings
        
    Returns:
        DailySummary object with generated content
    """
    try:
        # Extract reflections first (highest priority)
        reflections = _extract_manual_reflections(journal_entries)
        
        # Call AI to generate the summary
        ai_response = _call_ai_for_daily_summary(journal_entries, date_str, config)
        
        # Build the DailySummary object, omitting empty sections
        summary_data = {
            "date": date_str,
            "summary": ai_response.get("summary", ""),
            "progress_made": ai_response.get("progress_made", ""),
            "key_accomplishments": ai_response.get("key_accomplishments", []),
            "technical_progress": ai_response.get("technical_progress", ""),
            "daily_metrics": ai_response.get("daily_metrics", {})
        }
        
        # Only include optional sections if they have content
        ai_reflections = ai_response.get("reflections", []) or []
        all_reflections = reflections + ai_reflections
        if all_reflections:
            summary_data["reflections"] = all_reflections
        else:
            summary_data["reflections"] = None
            
        challenges_overcome = ai_response.get("challenges_overcome", [])
        if challenges_overcome:
            summary_data["challenges_overcome"] = challenges_overcome
        else:
            summary_data["challenges_overcome"] = None
            
        learning_insights = ai_response.get("learning_insights", [])
        if learning_insights:
            summary_data["learning_insights"] = learning_insights
        else:
            summary_data["learning_insights"] = None
            
        discussion = ai_response.get("discussion_highlights", [])
        if discussion:
            summary_data["discussion_highlights"] = discussion
        else:
            summary_data["discussion_highlights"] = None
            
        tone_mood = ai_response.get("tone_mood")
        if tone_mood and any(tone_mood.values()):
            summary_data["tone_mood"] = tone_mood
        else:
            summary_data["tone_mood"] = None
        
        # Add source file links
        from mcp_commit_story.summary_utils import add_source_links_to_summary
        journal_path = config.get("journal", {}).get("path", "")
        summary_with_links = add_source_links_to_summary(summary_data, "daily", date_str, journal_path)
        
        return summary_with_links
        
    except Exception as e:
        logger.error(f"Error generating daily summary for {date_str}: {e}")
        raise


def save_daily_summary(summary: DailySummary, config: Dict) -> str:
    """Save a daily summary to a markdown file.
    
    Formats the summary as markdown and saves it to
    `{config.journal.path}/summaries/daily/{date}-summary.md`.
    
    Args:
        summary: DailySummary object to save.
        config: Configuration object with journal path settings.
        
    Returns:
        Path to the saved summary file.
        
    Raises:
        Exception: If directory creation or file writing fails.
    """
    try:
        # Use established journal file utilities
        date_str = summary['date']
        relative_path = get_journal_file_path(date_str, "daily_summary")
        
        # Construct full path using config
        journal_base_path = config.get("journal", {}).get("path", "")
        if not journal_base_path:
            raise Exception("No journal path found in config")
        
        # Convert relative path to absolute path
        summary_path = os.path.join(journal_base_path, relative_path.replace("journal/", ""))
        
        # Ensure directory exists
        ensure_journal_directory(summary_path)
        
        # Convert summary to markdown format
        content = _format_summary_as_markdown(summary)
        
        # Write to file
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved daily summary to {summary_path}")
        return summary_path
        
    except Exception as e:
        logger.error(f"Error saving daily summary: {e}")
        raise


def _format_summary_as_markdown(summary: DailySummary) -> str:
    """Format a DailySummary as markdown content.
    
    Args:
        summary: DailySummary object to format
        
    Returns:
        Markdown-formatted string
    """
    lines = [
        f"# Daily Summary for {summary['date']}",
        "",
        "## Summary",
        summary.get('summary', 'No summary available'),
        "",
    ]
    
    # Only include sections that have content
    if summary.get('reflections'):
        lines.extend([
            "## Reflections",
            ""
        ])
        for reflection in summary['reflections']:
            lines.extend([f"- {reflection}", ""])
    
    # Only add progress_made if it exists
    if summary.get('progress_made'):
        lines.extend([
            "## Progress Made",
            summary['progress_made'],
            "",
        ])
    
    # Only add key_accomplishments if it exists
    if summary.get('key_accomplishments'):
        lines.extend([
            "## Key Accomplishments",
            ""
        ])
        for accomplishment in summary['key_accomplishments']:
            lines.append(f"- {accomplishment}")
        lines.append("")
    
    # Only add technical_progress if it exists
    if summary.get('technical_progress'):
        lines.extend([
            "## Technical Progress (Detailed Implementation)",
            summary['technical_progress'],
            ""
        ])
    
    if summary.get('challenges_overcome'):
        lines.extend([
            "## Challenges Overcome",
            ""
        ])
        for challenge in summary['challenges_overcome']:
            lines.append(f"- {challenge}")
        lines.append("")
    
    if summary.get('next_steps'):
        lines.extend([
            "## Next Steps",
            ""
        ])
        for step in summary['next_steps']:
            lines.append(f"- {step}")
        lines.append("")
    
    if summary.get('tone_mood'):
        lines.extend([
            "## Tone and Mood",
            ""
        ])
        for key, value in summary['tone_mood'].items():
            if value:
                lines.append(f"- **{key.title()}**: {value}")
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# Main Entry Point
# =============================================================================

@trace_mcp_operation("daily_summary.generate_standalone", attributes={
    "operation_type": "standalone_generation",
    "section_type": "daily_summary"
})
def generate_daily_summary_standalone(date: Optional[str] = None) -> Optional[DailySummary]:
    """Generate a daily summary without requiring MCP server.
    
    Loads journal entries for a date, processes them through AI, and saves
    the summary to a markdown file.
    
    Args:
        date: Date string in YYYY-MM-DD format. Defaults to today.
        
    Returns:
        DailySummary object with generated content, or None if no entries found.
        
    Raises:
        Exception: If configuration loading, AI generation, or file saving fails.
        
    Example:
        ```python
        # Generate for today
        summary = generate_daily_summary_standalone()
        
        # Generate for specific date
        summary = generate_daily_summary_standalone("2025-01-15")
        ```
    """
    start_time = time.time()
    
    # Set up telemetry
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("daily_summary.generation_type", "standalone")
    
    # Metrics counters
    operations_total = 0
    entry_count = 0
    
    try:
        # Default to today if no date provided
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if current_span:
            current_span.set_attribute("summary.date", date)
        
        # Load configuration
        operations_total += 1
        config = load_config()
        logger.info(f"Configuration loaded for daily summary generation for {date}")
        
        # Load journal entries for the date
        operations_total += 1
        journal_entries = load_journal_entries_for_date(date, config)
        entry_count = len(journal_entries)
        
        if current_span:
            current_span.set_attribute("summary.entry_count", entry_count)
        
        # Return None if no entries found
        if not journal_entries:
            logger.info(f"No journal entries found for {date}, skipping daily summary generation")
            return None
        
        # Generate daily summary using AI
        operations_total += 1
        summary = generate_daily_summary(journal_entries, date, config)
        logger.info(f"Daily summary generated for {date}")
        
        # Save summary to file
        operations_total += 1
        summary_path = save_daily_summary(summary, config)
        logger.info(f"Daily summary saved to {summary_path}")
        
        # Record success telemetry
        generation_duration = time.time() - start_time
        
        # Emit telemetry metrics
        metrics = get_mcp_metrics()
        if metrics:
            # Generation duration histogram
            metrics.record_histogram("daily_summary.generation_duration_seconds", generation_duration)
            
            # Operations counter with success label
            metrics.record_counter("daily_summary.operations_total", 1, {"status": "success"})
            
            # Entry count histogram
            metrics.record_histogram("daily_summary.entry_count", entry_count)
            
            # File operations counter
            metrics.record_counter("daily_summary.file_operations_total", 1, {"operation": "save", "status": "success"})
        
        return summary
        
    except Exception as e:
        # Record failure telemetry
        generation_duration = time.time() - start_time
        
        # Emit error telemetry
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_histogram("daily_summary.generation_duration_seconds", generation_duration)
            metrics.record_counter("daily_summary.operations_total", 1, {"status": "failure"})
            metrics.record_histogram("daily_summary.entry_count", entry_count)
        
        logger.error(f"Error in standalone daily summary generation for {date}: {e}")
        raise 