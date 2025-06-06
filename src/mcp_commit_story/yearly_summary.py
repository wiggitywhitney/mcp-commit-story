"""
Yearly summary generation module.

This module provides functionality for generating yearly summaries from quarterly summaries.
"""

import logging
from typing import Dict, Any
from mcp_commit_story.summary_utils import add_source_links_to_summary

logger = logging.getLogger(__name__)


def generate_yearly_summary(year_str: str, config: Dict) -> Dict[str, Any]:
    """
    Generate a yearly summary from quarterly summaries.
    
    Args:
        year_str: Year in format "YYYY" (e.g., "2025")
        config: Configuration dictionary with journal configuration
        
    Returns:
        Yearly summary dictionary with source file links
    """
    # Placeholder implementation for testing
    yearly_summary = {
        "year": year_str,
        "summary": f"Yearly summary for {year_str}",
        "key_accomplishments": [],
        "yearly_metrics": {}
    }
    
    # Add source file links
    journal_path = config.get("journal", {}).get("path", "")
    summary_with_links = add_source_links_to_summary(yearly_summary, "yearly", year_str, journal_path)
    
    return summary_with_links 