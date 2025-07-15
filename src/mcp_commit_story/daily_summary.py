"""Daily summary file-creation-based trigger system.

This module provides functions to determine when daily summaries should be generated
based on journal file creation events, rather than maintaining state files.
"""

import os
import re
import logging
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from pathlib import Path

from .ai_invocation import invoke_ai

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
        
        # Check for standard summary file format (matches get_journal_file_path convention)
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
        from pathlib import Path
        
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


def _weekly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if any weekly boundaries were crossed that need summaries."""
    # Find all Mondays between last_date and current_date
    check_date = last_date + timedelta(days=1)
    
    while check_date <= current_date:
        if check_date.weekday() == 0:  # Monday - weekly boundary
            previous_week_end = check_date - timedelta(days=1)  # Last Sunday
            if not _weekly_summary_exists(previous_week_end, summaries_path):
                return True
        check_date += timedelta(days=1)
    
    return False


def _monthly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if any monthly boundaries were crossed that need summaries."""
    # Find all 1st-of-month dates between last_date and current_date
    check_date = last_date + timedelta(days=1)
    
    while check_date <= current_date:
        if check_date.day == 1:  # Monthly boundary
            previous_month_end = check_date - timedelta(days=1)  # Last day of previous month
            if not _monthly_summary_exists(previous_month_end, summaries_path):
                return True
        check_date += timedelta(days=1)
    
    return False


def _quarterly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if any quarterly boundaries were crossed that need summaries."""
    # Find all quarter start dates between last_date and current_date
    check_date = last_date + timedelta(days=1)
    
    while check_date <= current_date:
        if check_date.month in [1, 4, 7, 10] and check_date.day == 1:  # Quarterly boundary
            previous_quarter_end = check_date - timedelta(days=1)  # Last day of previous quarter
            if not _quarterly_summary_exists(previous_quarter_end, summaries_path):
                return True
        check_date += timedelta(days=1)
    
    return False


def _yearly_boundaries_crossed(last_date: date, current_date: date, summaries_path: Path) -> bool:
    """Check if any yearly boundaries were crossed that need summaries."""
    # Find all January 1st dates between last_date and current_date
    check_date = last_date + timedelta(days=1)
    
    while check_date <= current_date:
        if check_date.month == 1 and check_date.day == 1:  # Yearly boundary
            previous_year_end = check_date - timedelta(days=1)  # Dec 31 of previous year
            if not _yearly_summary_exists(previous_year_end, summaries_path):
                return True
        check_date += timedelta(days=1)
    
    return False


def _weekly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a weekly summary exists for the week containing the given date."""
    try:
        # Get the Monday of the week containing this date
        monday = date - timedelta(days=date.weekday())
        week_num = monday.isocalendar()[1]
        
        # Weekly summaries are stored as YYYY-MM-weekN.md
        weekly_dir = summaries_path / "weekly"
        possible_filenames = [
            f"{monday.strftime('%Y-%m')}-week{week_num}.md",
            f"{monday.strftime('%Y')}-week{week_num:02d}.md",
            f"{monday.strftime('%Y-W%W')}.md"  # Alternative format
        ]
        
        for filename in possible_filenames:
            if (weekly_dir / filename).exists():
                return True
        return False
    except Exception:
        return False


def _monthly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a monthly summary exists for the month containing the given date."""
    try:
        monthly_dir = summaries_path / "monthly"
        possible_filenames = [
            f"{date.strftime('%Y-%m')}.md",
            f"{date.strftime('%Y-%m')}-monthly.md",
            f"{date.strftime('%B-%Y').lower()}.md"  # Alternative format
        ]
        
        for filename in possible_filenames:
            if (monthly_dir / filename).exists():
                return True
        return False
    except Exception:
        return False


def _quarterly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a quarterly summary exists for the quarter containing the given date."""
    try:
        quarter = (date.month - 1) // 3 + 1
        quarterly_dir = summaries_path / "quarterly"
        possible_filenames = [
            f"{date.strftime('%Y')}-Q{quarter}.md",
            f"{date.strftime('%Y')}-quarter{quarter}.md"
        ]
        
        for filename in possible_filenames:
            if (quarterly_dir / filename).exists():
                return True
        return False
    except Exception:
        return False


def _yearly_summary_exists(date: date, summaries_path: Path) -> bool:
    """Check if a yearly summary exists for the year containing the given date."""
    try:
        yearly_dir = summaries_path / "yearly"
        possible_filenames = [
            f"{date.strftime('%Y')}.md",
            f"{date.strftime('%Y')}-yearly.md",
            f"{date.strftime('%Y')}-summary.md"
        ]
        
        for filename in possible_filenames:
            if (yearly_dir / filename).exists():
                return True
        return False
    except Exception:
        return False


# =============================================================================
# Daily Summary Generation Functions
# =============================================================================

from mcp_commit_story.telemetry import trace_mcp_operation
from mcp_commit_story.journal_workflow_types import DailySummary
from mcp_commit_story.journal_generate import JournalEntry


def load_journal_entries_for_date(date_str: str, config: Dict) -> List[JournalEntry]:
    """Load all journal entries for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        config: Configuration dictionary with journal configuration
        
    Returns:
        List of JournalEntry objects for the specified date
    """
    entries = []
    try:
        # Use the established journal file path utility
        from mcp_commit_story.journal_generate import get_journal_file_path
        
        journal_file_path = get_journal_file_path(date_str, "daily")
        
        if not os.path.exists(journal_file_path):
            logger.info(f"No journal file found for date {date_str}")
            return entries
        
        # Read and parse the journal file
        with open(journal_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse journal entries using the established parser
        from mcp_commit_story.journal_generate import JournalParser
        
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





def extract_all_reflections_from_markdown(markdown_content: str) -> List[Dict[str, str]]:
    """Extract all full reflections from journal markdown content.
    
    This function extracts reflections with the format:
    ### H:MM AM/PM — Reflection
    
    Args:
        markdown_content: Raw markdown content from journal file
        
    Returns:
        List of dictionaries with 'timestamp' and 'content' keys
    """
    reflections = []
    
    if not markdown_content:
        return reflections
    
    # Pattern to match reflection headers: ## or ### H:MM AM/PM — Reflection
    reflection_pattern = r'^#{2,3} (\d{1,2}:\d{2} [AP]M) — Reflection(?:\s*-\s*[\d\-\s\w:]+)?$'
    
    lines = markdown_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(reflection_pattern, line)
        
        if match:
            timestamp = match.group(1)
            content_lines = []
            
            # Collect content until next header or end of file
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # Stop at next ### header (either commit or reflection)
                if next_line.startswith('### '):
                    break
                content_lines.append(next_line)
                i += 1
            
            # Clean up content - remove empty lines from start and end
            content = '\n'.join(content_lines).strip()
            
            if content:  # Only add non-empty reflections
                reflections.append({
                    'timestamp': timestamp,
                    'content': content
                })
        else:
            i += 1
    
    return reflections


def extract_reflections_from_journal_file(date_str: str, config: Dict) -> List[Dict[str, str]]:
    """Extract reflections from journal file for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        config: Configuration with journal path
        
    Returns:
        List of reflection dictionaries
    """
    from .journal_generate import get_journal_file_path
    
    try:
        # Get journal file path
        relative_path = get_journal_file_path(date_str, "daily")
        journal_base_path = config.get("journal", {}).get("path", "")
        
        if not journal_base_path:
            logger.error("No journal path found in config")
            return []
        
        # Remove double "journal/" prefix if present
        if relative_path.startswith("journal/"):
            relative_path = relative_path[8:]
        
        journal_file_path = os.path.join(journal_base_path, relative_path)
        
        if not os.path.exists(journal_file_path):
            logger.debug(f"No journal file found for {date_str} at {journal_file_path}")
            return []
        
        # Read file and extract reflections
        with open(journal_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        reflections = extract_all_reflections_from_markdown(content)
        logger.info(f"Extracted {len(reflections)} reflections from {date_str}")
        
        return reflections
        
    except Exception as e:
        logger.error(f"Error extracting reflections from journal file for {date_str}: {e}")
        return []


def format_reflections_section(reflections: List[Dict[str, str]]) -> str:
    """Format reflections into markdown section for daily summary.
    
    Args:
        reflections: List of reflection dictionaries with 'timestamp' and 'content'
        
    Returns:
        Formatted markdown section string
    """
    if not reflections:
        return ""
    
    section_lines = ["## REFLECTIONS", ""]
    
    for reflection in reflections:
        timestamp = reflection['timestamp']
        content = reflection['content']
        
        # Add timestamp header and content
        section_lines.append(f"### {timestamp}")
        section_lines.append("")
        section_lines.append(content)
        section_lines.append("")
    
    return '\n'.join(section_lines)


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
        
        # Call AI with the prompt using real AI invocation
        context = {
            "date": date_str,
            "entries_count": len(entries),
            "operation": "daily_summary_generation"
        }
        
        ai_response_text = invoke_ai(prompt, context)
        
        # Parse the AI response as JSON
        try:
            response = json.loads(ai_response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"AI response text: {ai_response_text}")
            raise ValueError(f"AI returned invalid JSON response: {e}")
        
        # Validate response has required fields
        if not isinstance(response, dict):
            raise ValueError("AI response must be a JSON object")
        
        # Ensure required fields exist with defaults
        required_fields = ["summary", "progress_made", "key_accomplishments", "daily_metrics"]
        for field in required_fields:
            if field not in response:
                response[field] = "" if field != "key_accomplishments" and field != "daily_metrics" else ([] if field == "key_accomplishments" else {})
        
        logger.info(f"Generated daily summary for {date_str} from {len(entries)} entries")
        return response
        
    except Exception as e:
        logger.error(f"Error calling AI for daily summary: {e}")
        # Re-raise exceptions so callers can handle AI failures appropriately
        raise


def _format_entries_for_ai(entries: List[JournalEntry]) -> str:
    """Format journal entries into a structured context for AI generation.
    
    Args:
        entries: List of journal entries to format
        
    Returns:
        Formatted string containing all entry content
    """
    if not entries:
        return "No journal entries found for this date."
    
    lines = ["# Journal Entries for Daily Summary Generation", ""]
    
    for i, entry in enumerate(entries, 1):
        lines.extend([
            f"## Entry {i} - {entry.timestamp} (Commit {entry.commit_hash})",
            ""
        ])
        
        if entry.summary:
            lines.extend(["**Summary:**", entry.summary, ""])
        
        if entry.technical_synopsis:
            lines.extend(["**Technical Synopsis:**", entry.technical_synopsis, ""])
        
        if entry.accomplishments:
            lines.extend(["**Accomplishments:**"])
            for acc in entry.accomplishments:
                lines.append(f"- {acc}")
            lines.append("")
        
        if entry.frustrations:
            lines.extend(["**Frustrations/Roadblocks:**"])
            for frust in entry.frustrations:
                lines.append(f"- {frust}")
            lines.append("")
        
        if entry.discussion_notes:
            lines.extend(["**Discussion Notes:**"])
            for note in entry.discussion_notes:
                if isinstance(note, dict) and 'speaker' in note:
                    lines.append(f"- **{note['speaker']}:** {note.get('text', '')}")
                else:
                    lines.append(f"- {note}")
            lines.append("")
        
        if entry.tone_mood:
            lines.extend([
                "**Tone/Mood:**",
                f"- Mood: {entry.tone_mood.get('mood', '')}",
                f"- Indicators: {entry.tone_mood.get('indicators', '')}",
                ""
            ])
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def _build_daily_summary_prompt(journal_content: str, date_str: str) -> str:
    """Build the comprehensive AI prompt for daily summary generation.
    
    Args:
        journal_content: Formatted journal entries
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Complete AI prompt string
    """
    # Extract the comprehensive prompt from the generate_daily_summary docstring
    # This is the prompt that was provided by the user
    
    base_prompt = """
AI Prompt for Daily Summary Generation

Purpose: Generate a comprehensive daily summary from multiple journal entries for a solo developer,
prioritizing manual reflections and synthesizing the day's work into a cohesive, human-friendly narrative.

Instructions: Analyze all journal entries for the specified date and create a comprehensive
summary following the established structure. Focus on synthesis rather than simple aggregation.
Write for a solo developer reviewing their own work.

Developer Context:
Assume the developer is the same person who wrote the journal entries.
Write as if helping them reflect—not reporting to a manager or external party.

SIGNAL OVER NOISE - CRITICAL FILTERING FOR FRESH AI:
You are a fresh AI analyzing ONE day of journal entries. You don't know what happened on other days.

**PROJECT CONTEXT:** This is MCP Commit Story, a development journal system built with consistent TDD practices, task management, and systematic git workflow. The developer uses these practices daily throughout the project.

**ROUTINE PATTERNS TO FILTER OUT (these happen every day):**
- TDD workflow: "wrote tests first", "tests pass", "followed TDD", "test-driven development"
- Task management: "completed task X.Y", "marked subtask done", "updated tasks.json"
- Git workflow: "committed changes", "pushed to repo", "git add", "git commit"
- Methodology praise: "clean code", "good practices", "systematic approach", "rigorous testing"
- Generic progress: "made progress", "worked on implementation", "continued development"

**SIGNAL TO CAPTURE (what made THIS day different):**
- **Technical problems that required debugging/research** - not routine implementation
- **Architectural decisions with explicit reasoning** - choosing between approaches
- **Breakthrough moments** - when something clicked or major obstacles were overcome
- **Failures and lessons learned** - what went wrong and why
- **Process discoveries** - finding better ways to work
- **Emotional highs/lows** - frustration, excitement, satisfaction with specific outcomes
- **Design philosophy discussions** - strategic thinking about project direction
- **Performance/scaling challenges** - problems unique to this project's complexity

**FILTERING TEST:** Before including something, ask:
"Would this statement be true for most days of professional software development, or is this specific to what happened TODAY?"

If it's generic professional development work → FILTER OUT
If it's specific to this day's unique challenges/discoveries → INCLUDE

EXTERNAL READER ACCESSIBILITY GUIDELINES:
Write summaries that can be understood by someone outside the project who has no prior context.
Use specific, concrete language that explains real problems and solutions rather than abstract buzzwords.

❌ AVOID Abstract Corporate Speak:
- "Revolutionary Implementation Gap Solution"
- "Sophisticated AI prompting" 
- "Architectural maturity"
- "Systematic progression from infrastructure through breakthrough innovation"
- "Comprehensive optimization initiatives"
- "Strategic refactoring paradigms"

✅ USE Specific, Concrete Problems and Solutions:
- "Fixed Empty AI Function Problem: For months, the AI functions were supposed to generate rich journal content but were just returning empty stubs with TODO comments"
- "Made Git Hooks Actually Trigger Summaries: Previous git hook implementation was broken - it would install the hooks but they wouldn't actually generate summaries when you committed code"
- "Built smart calendar logic that can detect when summary periods have been crossed and backfill missing summaries"
- "Solved the 'I haven't committed in a week but still want summaries' problem by adding a file-watching trigger system"

AVOID MEANINGLESS TASK REFERENCES:
❌ "Completed task 61.2" (meaningless to external readers and future you)
❌ "Finished subtask 45.3" (internal organizational noise)
✅ "Fixed the database connection detection problem - the system can now automatically find and connect to Cursor's SQLite databases on different platforms"
✅ "Solved the cursor chat integration issue by implementing proper message filtering"

The improved approach:
- Explains real problems readers can understand
- Uses concrete language about what was built and why it matters  
- Avoids buzzwords that don't convey actual meaning
- Connects to developer experience that feels authentic and relatable
- Makes the summary valuable for conference talks, documentation, or future reference

SECTION REQUIREMENTS:

## Summary
High-level narrative of what happened during the day. Write as if you're narrating your day 
to your future self who wants to remember not just *what* happened, but *what mattered*. 
Be honest, detailed, and reflective—avoid vague phrasing. Focus on the broader story and 
context of the work, including why it was important and how different pieces connected.

## Reflections
**CRITICAL DISTINCTION:** Reflections vs Discussion Notes
- **Reflections** = Timestamped personal entries added by the developer (e.g., "17:47: I switched to claude-4-sonnet...")
- **Discussion Notes** = Conversation excerpts between human and AI during development work 

**FOR THIS SECTION:**
- Include ALL reflections (timestamped entries) found in journal entries, without exception
- Present each reflection verbatim with date/time context when available  
- Never summarize, paraphrase, or combine reflections
- If multiple reflections exist, include every single one
- DO NOT include discussion notes/conversation excerpts here (those go in Discussion Highlights)
- OMIT THIS SECTION ENTIRELY if no reflections found

## Progress Made
Human-friendly, conversational summary of what actually got accomplished—the "I did X and it worked" story.
This should feel like explaining your accomplishments to a fellow developer friend - what you're 
proud of getting done. Focus on concrete achievements and successful outcomes rather than 
technical implementation details. Accessible language that celebrates the wins.

## Key Accomplishments  
Structured list of wins and completions. Focus on meaningful progress and substantial work.

    ## Technical Progress (Detailed Implementation)
    **Career advancement focus**: Comprehensive technical analysis suitable for performance reviews, technical discussions, and demonstrating competence.
    Include architectural patterns, specific classes/functions modified, technical approaches taken, and implementation details. 
    Focus on implementation details that would help you remember your approach if you revisited this code months later.
    **Evidence of technical capability**: Write as concrete evidence of problem-solving skills, technical decision-making, and implementation expertise.
    Self-contained technical narrative that showcases professional development work.

    ## Challenges Overcome
    **Solution-focused narrative**: What obstacles were encountered and HOW they were successfully solved.
    Focus on demonstrating problem-solving capability, resilience, and technical troubleshooting skills rather than just listing difficulties.
    **Growth demonstration**: Show how challenges were approached systematically and resolved through skill and determination.
    Write in human, accessible language that highlights your problem-solving journey.
    OMIT THIS SECTION if no clear challenges found.

    ## Learning & Insights  
    **Knowledge synthesis**: What was learned, insights gained, or "aha!" moments discovered during the work.
    Include technical insights, process improvements, strategic understanding, or philosophical discoveries about development.
    **Stories for sharing**: Capture insights and learning moments that would be suitable for blog posts, conference talks, teaching moments, or mentoring conversations.
    **Threads of challenge and triumph**: Identify patterns or themes that connect to your broader engineering journey and growth narrative.
    Focus on the experience and learning rather than implementation details - this is about wisdom gained, not code written.
    OMIT THIS SECTION if no clear learning found.

## Discussion Highlights  
**CRITICAL PRIORITY:** This section captures the developer's wisdom and decision-making that would otherwise be lost forever. These moments are GOLD for career advancement and conference talks.

**AGGRESSIVE CAPTURE REQUIREMENTS:**
- Hunt for ANY moment where the developer sounds wise, insightful, or strategically thoughtful
- Extract ALL decision points where the developer weighs options or explains reasoning
- Preserve the developer's voice and strategic thinking as the most valuable elements
- Include context around decisions so future readers understand the "why"

**PRIORITY ORDER (capture everything in these categories):**
1. **Decision Points & Tradeoffs** – architectural choices, design philosophy, weighing pros/cons, "I chose X because Y"
2. **Developer Wisdom** – insightful observations, strategic thinking, "aha!" breakthroughs, smart insights
3. **Process Insights** – problem-solving approaches, quality insights, learning synthesis, wisdom about development
4. **Process Improvements** – repeated instructions to AI suggesting automation opportunities

**WHAT COUNTS AS "WISE MOMENTS":**
- Strategic thinking about architecture or design
- Insights about why certain approaches work better
- Lessons learned from failures or experiments
- Smart observations about code quality, patterns, or practices
- Thoughtful analysis of tradeoffs between approaches
- "Aha!" moments when something clicks
- Experienced developer intuition being articulated
- Philosophy about software development or project management

**FORMAT:** Present as VERBATIM QUOTES with speaker attribution:
> **Human:** "exact quote here"  
> **AI:** "exact response here"

**ABUNDANCE MINDSET:** Err on the side of including too much rather than too little. Better to capture wisdom that might not seem important now than to lose insights forever.

OMIT THIS SECTION ONLY if genuinely no meaningful discussion found.

## Tone/Mood
Capture the emotional journey during development - how it actually felt to do this work.

**SOURCES:** Mood statements, commit message tone, discussion confidence/frustration, celebration language
**FORMAT:** {mood}: {supporting evidence from their actual language}
**EXAMPLE:** "Frustrated then relieved: Struggled with 'This is getting ridiculous' in commits, but later expressed satisfaction with breakthrough"

Only include if there's clear evidence of emotional state in the developer's actual language.
OMIT THIS SECTION if insufficient evidence.

## Daily Metrics
Factual statistics about the day's work: commits, files changed, lines added/removed, 
tests created, documentation added, etc. Present as key-value pairs.

ANTI-HALLUCINATION RULES:
- Only synthesize information present in the provided journal entries
- Do not invent accomplishments, challenges, reflections, or discussions
- If insufficient content for a section, omit that section entirely  
- Preserve manual reflections exactly as written
- Only include mood/tone assessments with explicit evidence
- Never speculate about motivations or feelings not explicitly expressed

CHECKLIST:
- [ ] Distinguished reflections (timestamped entries) from discussion notes (conversations)  
- [ ] Included ALL reflections verbatim in Reflections section
- [ ] Prioritized decision points & developer wisdom in Discussion Highlights
- [ ] Noted any process inefficiencies/repeated instructions suggesting automation opportunities
- [ ] Applied SIGNAL OVER NOISE filtering - ignored routine TDD/task mentions, captured unique challenges
- [ ] Used concrete, accessible language - avoided abstract buzzwords
- [ ] Only included sections with meaningful content - omitted empty sections
- [ ] Preserved the "why" behind decisions that would otherwise be lost
- [ ] Told a cohesive story grounded in actual journal evidence

JOURNAL ENTRIES TO ANALYZE:

""" + journal_content + f"""

DATE: {date_str}

Please generate a comprehensive daily summary following the guidelines above. Return the response as a structured JSON object with the following format:

{{
    "summary": "High-level narrative...",
    "reflections": ["reflection1", "reflection2"] or null if none,
    "progress_made": "Human-friendly progress description...",
    "key_accomplishments": ["accomplishment1", "accomplishment2"],
    "technical_progress": "Detailed implementation analysis...",
    "challenges_overcome": ["challenge1 with solution", "challenge2 with solution"] or null if none,
    "learning_insights": ["insight1", "insight2"] or null if none,
    "discussion_highlights": ["highlight1", "highlight2"] or null if none,
    "tone_mood": {{"mood": "description", "indicators": "evidence"}} or null,
    "daily_metrics": {{"commits": 3, "files_changed": 10}}
}}
"""
    
    return base_prompt


def _generate_mock_daily_summary_response(entries: List[JournalEntry], date_str: str) -> Dict:
    """Generate a realistic mock response based on actual entry content.
    
    This function analyzes the real journal entries and creates a summary
    that reflects the actual content, providing a more realistic placeholder
    until full AI integration is implemented.
    
    Args:
        entries: List of journal entries to analyze
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing generated summary sections
    """
    if not entries:
        return {
            "summary": f"No development work recorded for {date_str}",
            "reflections": None,
            "progress_made": "No progress recorded for this date",
            "key_accomplishments": [],
            "technical_synopsis": "No technical work recorded",
            "challenges_and_learning": None,
            "discussion_highlights": None,
            "tone_mood": None,
            "daily_metrics": {"commits": 0}
        }
    
    # Aggregate content from all entries
    all_accomplishments = []
    all_frustrations = []
    all_discussions = []
    technical_work = []
    mood_indicators = []
    
    for entry in entries:
        if entry.accomplishments:
            all_accomplishments.extend(entry.accomplishments)
        if entry.frustrations:
            all_frustrations.extend(entry.frustrations)
        if entry.discussion_notes:
            all_discussions.extend(entry.discussion_notes)
        if entry.technical_synopsis:
            technical_work.append(entry.technical_synopsis)
        if entry.tone_mood:
            mood_indicators.append(entry.tone_mood)
    
    # Generate summary
    summary_parts = []
    if all_accomplishments:
        summary_parts.append(f"Accomplished {len(all_accomplishments)} key tasks")
    if technical_work:
        summary_parts.append("focused on technical implementation")
    if all_frustrations:
        summary_parts.append(f"encountered {len(all_frustrations)} challenges")
    
    summary = f"Development work on {date_str}: " + ", ".join(summary_parts) if summary_parts else f"Development session on {date_str}"
    
    # Build progress made
    progress_made = "Made progress on implementation tasks"
    if all_accomplishments:
        progress_made = f"Successfully completed {len(all_accomplishments)} development objectives"
    
    # Technical synopsis
    tech_synopsis = "Technical development session"
    if technical_work:
        tech_synopsis = " ".join(technical_work[:2])  # Combine first 2 technical summaries
    
    # Mood analysis
    tone_mood = None
    if mood_indicators:
        mood_data = mood_indicators[0]  # Use first mood indicator
        if mood_data.get('mood') or mood_data.get('indicators'):
            tone_mood = mood_data
    
    return {
        "summary": summary,
                    "reflections": None,  # Will be extracted from journal markdown (timestamped personal entries)
        "progress_made": progress_made,
        "key_accomplishments": all_accomplishments[:5],  # Limit to top 5
        "technical_progress": tech_synopsis,
        "challenges_overcome": all_frustrations[:2] if all_frustrations else None,
        "learning_insights": ["Mock learning insight from analysis"] if all_frustrations else None,
        "discussion_highlights": all_discussions[:3] if all_discussions else None,
        "tone_mood": tone_mood,
        "daily_metrics": {
            "commits": len(entries),
            "accomplishments": len(all_accomplishments),
            "challenges": len(all_frustrations),
            "discussions": len(all_discussions)
        }
    }


@trace_mcp_operation("daily_summary.generate", attributes={"operation_type": "ai_generation", "section_type": "daily_summary"})
def generate_daily_summary(journal_entries: List[JournalEntry], date_str: str, config: dict) -> DailySummary:
    """
    AI Prompt for Daily Summary Generation

    Purpose: Generate a comprehensive daily summary from multiple journal entries for a solo developer,
    prioritizing manual reflections and synthesizing the day's work into a cohesive, human-friendly narrative.

    Instructions: Analyze all journal entries for the specified date and create a comprehensive
    summary following the established structure. Focus on synthesis rather than simple aggregation.
    Write for a solo developer reviewing their own work.

    Developer Context:
    Assume the developer is the same person who wrote the journal entries.
    Write as if helping them reflect—not reporting to a manager or external party.

    SIGNAL OVER NOISE - CRITICAL FILTERING FOR FRESH AI:
    You are a fresh AI analyzing ONE day of journal entries. You don't know what happened on other days.

    **PROJECT CONTEXT:** This is MCP Commit Story, a development journal system built with consistent TDD practices, task management, and systematic git workflow. The developer uses these practices daily throughout the project.

    **ROUTINE PATTERNS TO FILTER OUT (these happen every day):**
    - TDD workflow: "wrote tests first", "tests pass", "followed TDD", "test-driven development"
    - Task management: "completed task X.Y", "marked subtask done", "updated tasks.json"
    - Git workflow: "committed changes", "pushed to repo", "git add", "git commit"
    - Methodology praise: "clean code", "good practices", "systematic approach", "rigorous testing"
    - Generic progress: "made progress", "worked on implementation", "continued development"

    **SIGNAL TO CAPTURE (what made THIS day different):**
    - **Technical problems that required debugging/research** - not routine implementation
    - **Architectural decisions with explicit reasoning** - choosing between approaches
    - **Breakthrough moments** - when something clicked or major obstacles were overcome
    - **Failures and lessons learned** - what went wrong and why
    - **Process discoveries** - finding better ways to work
    - **Emotional highs/lows** - frustration, excitement, satisfaction with specific outcomes
    - **Design philosophy discussions** - strategic thinking about project direction
    - **Performance/scaling challenges** - problems unique to this project's complexity

    **FILTERING TEST:** Before including something, ask:
    "Would this statement be true for most days of professional software development, or is this specific to what happened TODAY?"

    If it's generic professional development work → FILTER OUT
    If it's specific to this day's unique challenges/discoveries → INCLUDE

    EXTERNAL READER ACCESSIBILITY GUIDELINES:
    Write summaries that can be understood by someone outside the project who has no prior context.
    Use specific, concrete language that explains real problems and solutions rather than abstract buzzwords.
    
    ❌ AVOID Abstract Corporate Speak:
    - "Revolutionary Implementation Gap Solution"
    - "Sophisticated AI prompting"
    - "Architectural maturity"
    - "Systematic progression from infrastructure through breakthrough innovation"
    - "Comprehensive optimization initiatives"
    - "Strategic refactoring paradigms"
    
    ✅ USE Specific, Concrete Problems and Solutions:
    - "Fixed Empty AI Function Problem: For months, the AI functions were supposed to generate rich journal content but were just returning empty stubs with TODO comments"
    - "Made Git Hooks Actually Trigger Summaries: Previous git hook implementation was broken - it would install the hooks but they wouldn't actually generate summaries when you committed code"
    - "Built smart calendar logic that can detect when summary periods have been crossed and backfill missing summaries"
    - "Solved the 'I haven't committed in a week but still want summaries' problem by adding a file-watching trigger system"
    
    AVOID MEANINGLESS TASK REFERENCES:
    ❌ "Completed task 61.2" (meaningless to external readers and future you)
    ❌ "Finished subtask 45.3" (internal organizational noise)
    ✅ "Fixed the database connection detection problem - the system can now automatically find and connect to Cursor's SQLite databases on different platforms"
    ✅ "Solved the cursor chat integration issue by implementing proper message filtering"
    
    The improved approach:
    - Explains real problems readers can understand
    - Uses concrete language about what was built and why it matters
    - Avoids buzzwords that don't convey actual meaning
    - Connects to developer experience that feels authentic and relatable
    - Makes the summary valuable for conference talks, documentation, or future reference

    ORDER OF OPERATIONS:
    1. Extract all manual reflections (verbatim only)
    2. Scan for discussion quotes and classify by type
    3. Determine mood (if evidence exists)
    4. Identify notable accomplishments
    5. Summarize technical decisions and changes
    6. Reflect on challenges and what was learned
    7. Write narrative sections (Summary, Progress Made, Challenges)
    8. Assemble and format final output

    SECTION REQUIREMENTS:

    ## Summary
    High-level narrative of what happened during the day. Write as if you're narrating your day 
    to your future self who wants to remember not just *what* happened, but *what mattered*. 
    Be honest, detailed, and reflective—avoid vague phrasing. Focus on the broader story and 
    context of the work, including why it was important and how different pieces connected.

    ## Reflections
    **CRITICAL DISTINCTION:** Reflections vs Discussion Notes
    - **Reflections** = Timestamped personal entries added by the developer (e.g., "17:47: I switched to claude-4-sonnet...")
    - **Discussion Notes** = Conversation excerpts between human and AI during development work 
    
    **FOR THIS SECTION:**
    - Include ALL reflections (timestamped entries) found in journal entries, without exception
    - Present each reflection verbatim with date/time context when available  
    - Never summarize, paraphrase, or combine reflections
    - If multiple reflections exist, include every single one
    - DO NOT include discussion notes/conversation excerpts here (those go in Discussion Highlights)
    - OMIT THIS SECTION ENTIRELY if no reflections found

    ## Progress Made
    Human-friendly, conversational summary of what actually got accomplished—the "I did X and it worked" story.
    This should feel like explaining your accomplishments to a fellow developer friend - what you're 
    proud of getting done. Focus on concrete achievements and successful outcomes rather than 
    technical implementation details. Accessible language that celebrates the wins.

    ## Key Accomplishments  
    Structured list of wins and completions. Focus on meaningful progress and substantial work.

    ## Technical Progress (Detailed Implementation)
    **Career advancement focus**: Implementation details suitable for performance reviews and technical discussions.
    Include architectural patterns, specific classes/functions modified, approaches taken, and key technical decisions.
    Write as evidence of technical competence and problem-solving capability.

    ## Challenges Overcome
    **Solution-focused**: What obstacles were encountered and HOW they were solved.
    Focus on problem-solving capability and resilience rather than just listing difficulties.
    OMIT THIS SECTION if no clear challenges found.

    ## Learning & Insights  
    **Growth narrative**: What was learned, insights gained, or "aha!" moments discovered.
    Include technical insights, process improvements, or strategic understanding.
    **Stories for sharing**: Capture insights suitable for blog posts, conference talks, or teaching moments.
    OMIT THIS SECTION if no clear learning found.

    ## Discussion Highlights  
    **CRITICAL PRIORITY:** This section captures the developer's wisdom and decision-making that would otherwise be lost forever. These moments are GOLD for career advancement and conference talks.

    **AGGRESSIVE CAPTURE REQUIREMENTS:**
    - Hunt for ANY moment where the developer sounds wise, insightful, or strategically thoughtful
    - Extract ALL decision points where the developer weighs options or explains reasoning
    - Preserve the developer's voice and strategic thinking as the most valuable elements
    - Include context around decisions so future readers understand the "why"

    **PRIORITY ORDER (capture everything in these categories):**
    1. **Decision Points & Tradeoffs** – architectural choices, design philosophy, weighing pros/cons, "I chose X because Y"
    2. **Developer Wisdom** – insightful observations, strategic thinking, "aha!" breakthroughs, smart insights
    3. **Process Insights** – problem-solving approaches, quality insights, learning synthesis, wisdom about development
    4. **Process Improvements** – repeated instructions to AI suggesting automation opportunities

    **WHAT COUNTS AS "WISE MOMENTS":**
    - Strategic thinking about architecture or design
    - Insights about why certain approaches work better
    - Lessons learned from failures or experiments
    - Smart observations about code quality, patterns, or practices
    - Thoughtful analysis of tradeoffs between approaches
    - "Aha!" moments when something clicks
    - Experienced developer intuition being articulated
    - Philosophy about software development or project management

    **FORMAT:** Present as VERBATIM QUOTES with speaker attribution:
    > **Human:** "exact quote here"  
    > **AI:** "exact response here"

    **ABUNDANCE MINDSET:** Err on the side of including too much rather than too little. Better to capture wisdom that might not seem important now than to lose insights forever.

    OMIT THIS SECTION ONLY if genuinely no meaningful discussion found.

    ## Tone/Mood
    Capture the emotional journey during development - how it actually felt to do this work.
    
    **SOURCES:** Mood statements, commit message tone, discussion confidence/frustration, celebration language
    **FORMAT:** {mood}: {supporting evidence from their actual language}
    **EXAMPLE:** "Frustrated then relieved: Struggled with 'This is getting ridiculous' in commits, but later expressed satisfaction with breakthrough"
    
    Only include if there's clear evidence of emotional state in the developer's actual language.
    OMIT THIS SECTION if insufficient evidence.

    ## Daily Metrics
    Factual statistics about the day's work: commits, files changed, lines added/removed, 
    tests created, documentation added, etc. Present as key-value pairs.

    ANTI-HALLUCINATION RULES:
    - Only synthesize information present in the provided journal entries
    - Do not invent accomplishments, challenges, reflections, or discussions
    - If insufficient content for a section, omit that section entirely  
    - Preserve manual reflections exactly as written
    - Only include mood/tone assessments with explicit evidence
    - Never speculate about motivations or feelings not explicitly expressed

    OUTPUT REQUIREMENTS:
    - Omit any section headers that would be empty
    - Use conversational, human language throughout
    - Focus on what made this day unique rather than routine workflow
    - Ensure all content is grounded in actual journal entry evidence
    - Create a cohesive narrative that tells the story of the developer's day

    CHECKLIST:
    - [ ] Distinguished reflections (timestamped entries) from discussion notes (conversations)  
    - [ ] Included ALL reflections verbatim in Reflections section
    - [ ] Prioritized decision points & developer wisdom in Discussion Highlights
    - [ ] Noted any process inefficiencies/repeated instructions suggesting automation opportunities
    - [ ] Applied SIGNAL OVER NOISE filtering - ignored routine TDD/task mentions, captured unique challenges
    - [ ] Used concrete, accessible language - avoided abstract buzzwords
    - [ ] Only included sections with meaningful content - omitted empty sections
    - [ ] Preserved the "why" behind decisions that would otherwise be lost
    - [ ] Told a cohesive story grounded in actual journal evidence
    
    Args:
        journal_entries: List of journal entries for the specified date
        date_str: Date in YYYY-MM-DD format
        config: Configuration dictionary with AI model settings
        
    Returns:
        DailySummary object with generated content
    """
    try:
        # Extract reflections from journal markdown file (markdown header method)
        markdown_reflections = extract_reflections_from_journal_file(date_str, config)
        
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
        
        # Convert markdown reflections to string format for consistency with AI reflections
        string_reflections = []
        if markdown_reflections:
            for reflection in markdown_reflections:
                if isinstance(reflection, dict):
                    timestamp = reflection.get('timestamp', '')
                    content = reflection.get('content', '')
                    if timestamp and content:
                        string_reflections.append(f"[{timestamp}] {content}")
                    elif content:
                        string_reflections.append(content)
        
        # Combine markdown reflections with AI reflections
        all_reflections = string_reflections + ai_reflections
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
    """Save a daily summary to file.
    
    Args:
        summary: DailySummary object to save
        config: Configuration with journal configuration
        
    Returns:
        Path to the saved summary file
    """
    try:
        # Use established journal file utilities
        from mcp_commit_story.journal_generate import get_journal_file_path, ensure_journal_directory
        
        # Get the summary file path (summaries are stored in summaries/daily/)
        date_str = summary['date']
        summary_path = get_journal_file_path(date_str, "daily_summary")
        
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
        summary['summary'],
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
    
    lines.extend([
        "## Progress Made",
        summary['progress_made'],
        "",
        "## Key Accomplishments",
        ""
    ])
    
    for accomplishment in summary['key_accomplishments']:
        lines.append(f"- {accomplishment}")
    lines.append("")
    
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
            lines.extend([f"- {challenge}", ""])
    
    if summary.get('learning_insights'):
        lines.extend([
            "## Learning & Insights",
            ""
        ])
        for insight in summary['learning_insights']:
            lines.extend([f"- {insight}", ""])
    
    if summary.get('discussion_highlights'):
        lines.extend([
            "## Discussion Highlights",
            ""
        ])
        for highlight in summary['discussion_highlights']:
            lines.extend([f"- {highlight}", ""])
    
    if summary.get('tone_mood'):
        lines.extend([
            "## Tone/Mood",
            f"**Mood:** {summary['tone_mood'].get('mood', '')}",
            f"**Indicators:** {summary['tone_mood'].get('indicators', '')}",
            ""
        ])
    
    lines.extend([
        "## Daily Metrics",
        ""
    ])
    
    for key, value in summary['daily_metrics'].items():
        lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
    
    # Add REFLECTIONS section with full reflections if available
    if summary.get('full_reflections'):
        lines.append("")
        lines.append("## REFLECTIONS")
        lines.append("")
        
        for reflection in summary['full_reflections']:
            lines.append(f"### {reflection['timestamp']}")
            lines.append("")
            lines.append(reflection['content'])
            lines.append("")
    
    # Add source files section if available
    if summary.get('source_files'):
        from mcp_commit_story.summary_utils import generate_source_links_section, generate_coverage_description
        
        coverage_description = generate_coverage_description("daily", summary['date'])
        source_links_section = generate_source_links_section(summary['source_files'], coverage_description)
        
        if source_links_section:
            lines.extend(["", source_links_section])
    
    return "\n".join(lines)


