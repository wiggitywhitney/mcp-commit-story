"""
Source file linking utilities for summary generation.

This module provides functionality to track and link to the source files
that each summary type was built from, creating a navigable hierarchy.
"""

import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from calendar import monthrange
import logging

logger = logging.getLogger(__name__)


def determine_source_files_for_summary(summary_type: str, date_identifier: str, journal_path: str) -> List[Dict[str, Any]]:
    """
    Determine what source files a summary should link to based on its type.
    
    Args:
        summary_type: Type of summary ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
        date_identifier: Date string in appropriate format for the summary type
        journal_path: Path to the journal directory
        
    Returns:
        List of source file dictionaries with path, exists, and type information
    """
    base_path = Path(journal_path)
    source_files = []
    
    if summary_type == "daily":
        source_files = _get_daily_summary_sources(date_identifier, base_path)
    elif summary_type == "weekly":
        source_files = _get_weekly_summary_sources(date_identifier, base_path)
    elif summary_type == "monthly":
        source_files = _get_monthly_summary_sources(date_identifier, base_path)
    elif summary_type == "quarterly":
        source_files = _get_quarterly_summary_sources(date_identifier, base_path)
    elif summary_type == "yearly":
        source_files = _get_yearly_summary_sources(date_identifier, base_path)
    else:
        logger.warning(f"Unknown summary type: {summary_type}")
    
    return source_files


def _get_daily_summary_sources(date_str: str, base_path: Path) -> List[Dict[str, Any]]:
    """Get source files for daily summary (journal entries)."""
    journal_file = f"{date_str}-journal.md"
    journal_path = base_path / "daily" / journal_file
    
    return [{
        'path': f"daily/{journal_file}",
        'exists': journal_path.exists(),
        'type': 'journal_entry'
    }]


def _get_weekly_summary_sources(start_date_str: str, base_path: Path) -> List[Dict[str, Any]]:
    """Get source files for weekly summary (daily summaries)."""
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        # Ensure we start on a Monday
        monday = start_date - timedelta(days=start_date.weekday())
        
        source_files = []
        daily_summaries_dir = base_path / "summaries" / "daily"
        
        # Generate all 7 days of the week
        for day_offset in range(7):
            current_date = monday + timedelta(days=day_offset)
            daily_file = f"{current_date.strftime('%Y-%m-%d')}-summary.md"
            daily_path = daily_summaries_dir / daily_file
            
            source_files.append({
                'path': f"summaries/daily/{daily_file}",
                'exists': daily_path.exists(),
                'type': 'daily_summary'
            })
        
        return source_files
    except ValueError as e:
        logger.error(f"Error parsing weekly start date {start_date_str}: {e}")
        return []


def _get_monthly_summary_sources(month_str: str, base_path: Path) -> List[Dict[str, Any]]:
    """Get source files for monthly summary (weekly summaries)."""
    try:
        year, month = map(int, month_str.split('-'))
        
        # Find all weeks that overlap with this month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        source_files = []
        weekly_summaries_dir = base_path / "summaries" / "weekly"
        
        # Find all Mondays that start within this month
        current_date = first_day
        # Move to the first Monday of the month
        if current_date.weekday() != 0:  # If first day is not Monday
            current_date += timedelta(days=(7 - current_date.weekday()) % 7)
        
        while current_date <= last_day:
            week_num = current_date.isocalendar()[1]
            
            # Try different weekly file naming conventions
            possible_filenames = [
                f"{current_date.strftime('%Y-%m')}-week{week_num}.md",
                f"{current_date.strftime('%Y')}-week{week_num:02d}.md",
                f"{current_date.strftime('%Y-W%W')}.md"
            ]
            
            file_found = False
            for filename in possible_filenames:
                weekly_path = weekly_summaries_dir / filename
                if not file_found:  # Only add the first match to avoid duplicates
                    source_files.append({
                        'path': f"summaries/weekly/{filename}",
                        'exists': weekly_path.exists(),
                        'type': 'weekly_summary'
                    })
                    file_found = True
                    if weekly_path.exists():
                        break  # Use the existing file format
            
            current_date += timedelta(weeks=1)
        
        return source_files
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing monthly identifier {month_str}: {e}")
        return []


def _get_quarterly_summary_sources(year_quarter_str: str, base_path: Path) -> List[Dict[str, Any]]:
    """Get source files for quarterly summary (monthly summaries)."""
    try:
        # Handle both "2025" and "2025,2" format
        if ',' in year_quarter_str:
            year_str, quarter_str = year_quarter_str.split(',')
            year, quarter = int(year_str), int(quarter_str)
        else:
            # If just year passed, we need quarter from context
            # This function signature needs the quarter parameter
            raise ValueError("Quarter number required for quarterly summary sources")
        
        # Get the three months in this quarter
        quarter_months = {
            1: [1, 2, 3],    # Q1: Jan, Feb, Mar
            2: [4, 5, 6],    # Q2: Apr, May, Jun
            3: [7, 8, 9],    # Q3: Jul, Aug, Sep
            4: [10, 11, 12]  # Q4: Oct, Nov, Dec
        }
        
        months = quarter_months.get(quarter, [])
        source_files = []
        monthly_summaries_dir = base_path / "summaries" / "monthly"
        
        for month in months:
            month_file = f"{year}-{month:02d}.md"
            monthly_path = monthly_summaries_dir / month_file
            
            source_files.append({
                'path': f"summaries/monthly/{month_file}",
                'exists': monthly_path.exists(),
                'type': 'monthly_summary'
            })
        
        return source_files
    except (ValueError, KeyError) as e:
        logger.error(f"Error parsing quarterly identifier {year_quarter_str}: {e}")
        return []


def _get_yearly_summary_sources(year_str: str, base_path: Path) -> List[Dict[str, Any]]:
    """Get source files for yearly summary (quarterly summaries)."""
    try:
        year = int(year_str)
        
        source_files = []
        quarterly_summaries_dir = base_path / "summaries" / "quarterly"
        
        # All four quarters
        for quarter in range(1, 5):
            quarter_file = f"{year}-Q{quarter}.md"
            quarterly_path = quarterly_summaries_dir / quarter_file
            
            source_files.append({
                'path': f"summaries/quarterly/{quarter_file}",
                'exists': quarterly_path.exists(),
                'type': 'quarterly_summary'
            })
        
        return source_files
    except ValueError as e:
        logger.error(f"Error parsing yearly identifier {year_str}: {e}")
        return []


def generate_source_links_section(source_files: List[Dict[str, Any]], coverage_description: str) -> str:
    """
    Generate a markdown section with links to source files.
    
    Args:
        source_files: List of source file dictionaries
        coverage_description: Human-readable description of what period this covers
        
    Returns:
        Markdown string with formatted source links
    """
    if not source_files:
        return ""
    
    markdown_lines = [
        "#### Source Files",
        "",
        f"**Coverage**: {coverage_description}",
        ""
    ]
    
    existing_files = [sf for sf in source_files if sf['exists']]
    missing_files = [sf for sf in source_files if not sf['exists']]
    
    if existing_files:
        markdown_lines.append("**Available Files**:")
        for source_file in existing_files:
            filename = os.path.basename(source_file['path'])
            markdown_lines.append(f"- [{filename}]({source_file['path']})")
        markdown_lines.append("")
    
    if missing_files:
        markdown_lines.append("**Missing Files**:")
        for source_file in missing_files:
            filename = os.path.basename(source_file['path'])
            markdown_lines.append(f"- [{filename}]({source_file['path']}) *(file not found)*")
        markdown_lines.append("")
    
    return "\n".join(markdown_lines)


def generate_coverage_description(summary_type: str, date_identifier: str) -> str:
    """
    Generate a human-readable description of what time period a summary covers.
    
    Args:
        summary_type: Type of summary ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
        date_identifier: Date string in appropriate format for the summary type
        
    Returns:
        Human-readable coverage description
    """
    try:
        if summary_type == "daily":
            date_obj = datetime.strptime(date_identifier, "%Y-%m-%d").date()
            return date_obj.strftime("%B %d, %Y")
        
        elif summary_type == "weekly":
            start_date = datetime.strptime(date_identifier, "%Y-%m-%d").date()
            monday = start_date - timedelta(days=start_date.weekday())
            sunday = monday + timedelta(days=6)
            return f"{monday.strftime('%B %d')} - {sunday.strftime('%B %d, %Y')}"
        
        elif summary_type == "monthly":
            year, month = map(int, date_identifier.split('-'))
            date_obj = date(year, month, 1)
            return date_obj.strftime("%B %Y")
        
        elif summary_type == "quarterly":
            if ',' in date_identifier:
                year_str, quarter_str = date_identifier.split(',')
                year, quarter = int(year_str), int(quarter_str)
            else:
                return f"Quarter ({date_identifier})"
            
            quarter_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
            return f"{quarter_names.get(quarter, 'Q?')} {year}"
        
        elif summary_type == "yearly":
            return f"Year {date_identifier}"
        
        else:
            return date_identifier
    
    except (ValueError, IndexError) as e:
        logger.warning(f"Error generating coverage description for {summary_type} {date_identifier}: {e}")
        return date_identifier


def add_source_links_to_summary(summary_obj: Any, summary_type: str, date_identifier: str, journal_path: str) -> Any:
    """
    Add source file links to a summary object.
    
    Args:
        summary_obj: Summary object to enhance with source links
        summary_type: Type of summary ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
        date_identifier: Date string in appropriate format for the summary type
        journal_path: Path to the journal directory
        
    Returns:
        Enhanced summary object with source_files attribute
    """
    try:
        source_files = determine_source_files_for_summary(summary_type, date_identifier, journal_path)
        
        # Add source_files attribute to the summary object
        if hasattr(summary_obj, '__dict__'):
            summary_obj.source_files = source_files
        elif isinstance(summary_obj, dict):
            summary_obj['source_files'] = source_files
        else:
            # For other types, try to set as attribute
            setattr(summary_obj, 'source_files', source_files)
        
        return summary_obj
    except Exception as e:
        logger.error(f"Error adding source links to {summary_type} summary: {e}")
        return summary_obj


def enhance_summary_markdown_with_source_links(markdown_content: str, summary_type: str, date_identifier: str, journal_path: str) -> str:
    """
    Add source links section to existing summary markdown content.
    
    Args:
        markdown_content: Existing markdown content
        summary_type: Type of summary ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
        date_identifier: Date string in appropriate format for the summary type
        journal_path: Path to the journal directory
        
    Returns:
        Enhanced markdown content with source links section
    """
    try:
        source_files = determine_source_files_for_summary(summary_type, date_identifier, journal_path)
        coverage_description = generate_coverage_description(summary_type, date_identifier)
        source_links_section = generate_source_links_section(source_files, coverage_description)
        
        if source_links_section:
            # Add the source links section at the end
            return f"{markdown_content}\n\n{source_links_section}"
        else:
            return markdown_content
    except Exception as e:
        logger.error(f"Error enhancing markdown with source links: {e}")
        return markdown_content 