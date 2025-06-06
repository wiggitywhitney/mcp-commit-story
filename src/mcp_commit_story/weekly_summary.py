"""
Weekly summary generation module.

This module provides functionality for generating weekly summaries from daily summaries.
"""

import logging
from typing import Dict, Any
from mcp_commit_story.summary_utils import add_source_links_to_summary

logger = logging.getLogger(__name__)


def generate_weekly_summary(start_date: str, config: Dict) -> Dict[str, Any]:
    """
    Generate a weekly summary from daily summaries.
    
    Args:
        start_date: Start date of the week in YYYY-MM-DD format (should be Monday)
        config: Configuration dictionary with journal configuration
        
    Returns:
        Weekly summary dictionary with source file links
    """
    # Placeholder implementation for testing
    weekly_summary = {
        "start_date": start_date,
        "summary": f"Weekly summary for week starting {start_date}",
        "key_accomplishments": [],
        "weekly_metrics": {}
    }
    
    # Add source file links
    journal_path = config.get("journal", {}).get("path", "")
    summary_with_links = add_source_links_to_summary(weekly_summary, "weekly", start_date, journal_path)
    
    return summary_with_links 