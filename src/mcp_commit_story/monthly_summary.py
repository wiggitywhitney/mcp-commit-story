"""
Monthly summary generation module.

This module provides functionality for generating monthly summaries from weekly summaries.
"""

import logging
from typing import Dict, Any
from mcp_commit_story.summary_utils import add_source_links_to_summary

logger = logging.getLogger(__name__)


def generate_monthly_summary(month_str: str, config: Dict) -> Dict[str, Any]:
    """
    Generate a monthly summary from weekly summaries.
    
    Args:
        month_str: Month identifier in YYYY-MM format
        config: Configuration dictionary with journal configuration
        
    Returns:
        Monthly summary dictionary with source file links
    """
    # Placeholder implementation for testing
    monthly_summary = {
        "month": month_str,
        "summary": f"Monthly summary for {month_str}",
        "key_accomplishments": [],
        "monthly_metrics": {}
    }
    
    # Add source file links
    journal_path = config.get("journal", {}).get("path", "")
    summary_with_links = add_source_links_to_summary(monthly_summary, "monthly", month_str, journal_path)
    
    return summary_with_links 