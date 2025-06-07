"""
Git hook worker module for daily summary triggering.

This module is called by the enhanced git post-commit hook to handle:
- File-creation-based daily summary triggering
- Period summary boundary detection  
- MCP server communication for summary generation
- Graceful error handling that never blocks git operations

Based on approved design decisions for subtask 27.3.
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import git

# Configure logging for hook operations
logger = logging.getLogger(__name__)


def get_log_file_path(repo_path: str) -> str:
    """Get the path for the git hook log file.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Path to log file in .git/hooks/mcp-commit-story.log
    """
    return os.path.join(repo_path, '.git', 'hooks', 'mcp-commit-story.log')


def setup_hook_logging(repo_path: str) -> None:
    """Set up logging for git hook operations.
    
    Args:
        repo_path: Path to the git repository
    """
    try:
        log_file = get_log_file_path(repo_path)
        
        # Ensure hooks directory exists
        hooks_dir = os.path.dirname(log_file)
        os.makedirs(hooks_dir, exist_ok=True)
        
        # Configure file handler with rotation-like behavior
        # Keep log file reasonable size (truncate if > 10MB)
        if os.path.exists(log_file) and os.path.getsize(log_file) > 10 * 1024 * 1024:
            # Move to .old and start fresh
            old_log = log_file + '.old'
            if os.path.exists(old_log):
                os.unlink(old_log)
            os.rename(log_file, old_log)
        
        # Set up file handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        
        # Configure logger
        logger.setLevel(logging.INFO)
        logger.handlers.clear()  # Remove any existing handlers
        logger.addHandler(file_handler)
        
    except Exception as e:
        # If logging setup fails, continue without logging
        # This maintains the graceful degradation principle
        pass


def get_git_commit_timestamp(repo_path: str) -> Optional[str]:
    """Get the timestamp from the most recent git commit.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        ISO format timestamp string from the latest commit, or None if unavailable
    """
    try:
        repo = git.Repo(repo_path)
        if not repo.heads:
            return None
        
        latest_commit = repo.head.commit
        return latest_commit.committed_datetime.isoformat()
    except Exception:
        return None


def log_hook_activity(message: str, level: str = "info", repo_path: str = None) -> None:
    """Log hook activity with appropriate level using git commit timestamp.
    
    Args:
        message: Message to log
        level: Log level ("info", "warning", "error")
        repo_path: Path to git repository for timestamp consistency
    """
    try:
        # Get git commit timestamp for consistency with rest of system
        timestamp = get_git_commit_timestamp(repo_path) if repo_path else None
        if timestamp:
            # Use git commit timestamp for consistency
            log_message = f"[{timestamp}] {message}"
        else:
            # Fallback to current time if git timestamp unavailable
            log_message = f"[{datetime.now().isoformat()}] {message}"
        
        if level == "warning":
            logger.warning(log_message)
        elif level == "error":
            logger.error(log_message)
        else:
            logger.info(log_message)
    except Exception:
        # If logging fails, continue silently
        pass


def handle_errors_gracefully(func):
    """Decorator to handle errors gracefully in hook operations.
    
    Ensures that any exception is logged but never propagated,
    maintaining git operation reliability.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Try to get repo_path from args for consistent timestamping
            repo_path = None
            if args and isinstance(args[0], str):
                repo_path = args[0]
            log_hook_activity(f"Error in {func.__name__}: {str(e)}", "error", repo_path)
            return None
    return wrapper


@handle_errors_gracefully
def check_daily_summary_trigger(repo_path: str) -> Optional[str]:
    """Check if daily summary should be generated based on file creation.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Date string if summary should be generated, None otherwise
    """
    try:
        from mcp_commit_story.daily_summary import should_generate_daily_summary
        from mcp_commit_story.config import load_config
        
        # Load configuration to get journal path
        config = load_config()
        journal_config = config.get("journal", {})
        journal_path = journal_config.get("path", "journal")
        
        # Get the absolute journal path
        if not os.path.isabs(journal_path):
            journal_path = os.path.join(repo_path, journal_path)
        
        # Find the most recent journal file (if any)
        if not os.path.exists(journal_path):
            log_hook_activity(f"Journal directory not found: {journal_path}", "info", repo_path)
            return None
        
        # Look for journal files
        journal_files = []
        for filename in os.listdir(journal_path):
            if filename.endswith('-journal.md'):
                file_path = os.path.join(journal_path, filename)
                journal_files.append(file_path)
        
        if not journal_files:
            log_hook_activity("No journal files found in repository", "info", repo_path)
            return None
        
        # Get the most recent journal file
        most_recent_file = max(journal_files, key=os.path.getmtime)
        
        # Get summaries directory
        summaries_dir = os.path.join(journal_path, "summaries", "daily")
        
        # Check if daily summary should be generated
        date_to_generate = should_generate_daily_summary(most_recent_file, summaries_dir)
        
        if date_to_generate:
            log_hook_activity(f"Daily summary should be generated for: {date_to_generate}", "info", repo_path)
            return date_to_generate
        else:
            log_hook_activity("No daily summary generation needed", "info", repo_path)
            return None
            
    except ImportError as e:
        log_hook_activity(f"Import error in daily summary check: {str(e)}", "error", repo_path)
        return None
    except Exception as e:
        log_hook_activity(f"Unexpected error in daily summary check: {str(e)}", "error", repo_path)
        return None


@handle_errors_gracefully  
def check_period_summary_triggers(date_str: str, repo_path: str) -> Dict[str, bool]:
    """Check if period summaries should be generated.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        repo_path: Path to the git repository
        
    Returns:
        Dictionary indicating which period summaries to generate
    """
    try:
        from mcp_commit_story.daily_summary import should_generate_period_summaries
        from mcp_commit_story.config import load_config
        
        # Load configuration to get journal path
        config = load_config()
        journal_config = config.get("journal", {})
        journal_path = journal_config.get("path", "journal")
        
        # Get the absolute summaries path
        if not os.path.isabs(journal_path):
            journal_path = os.path.join(repo_path, journal_path)
        
        summaries_dir = os.path.join(journal_path, "summaries")
        
        # Check period boundaries
        period_triggers = should_generate_period_summaries(date_str, summaries_dir)
        
        # Log which periods need summaries
        triggered_periods = [period for period, should_generate in period_triggers.items() if should_generate]
        if triggered_periods:
            log_hook_activity(f"Period summaries needed for {date_str}: {', '.join(triggered_periods)}", "info", repo_path)
        else:
            log_hook_activity(f"No period summaries needed for {date_str}", "info", repo_path)
        
        return period_triggers
        
    except ImportError as e:
        log_hook_activity(f"Import error in period summary check: {str(e)}", "error", repo_path)
        return {'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False}
    except Exception as e:
        log_hook_activity(f"Unexpected error in period summary check: {str(e)}", "error", repo_path)
        return {'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False}


@handle_errors_gracefully
def call_mcp_tool(tool_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call an MCP tool with graceful fallback.
    
    Args:
        tool_name: Name of the MCP tool to call
        parameters: Parameters to pass to the tool
        
    Returns:
        Tool response if successful, None if failed
    """
    try:
        # For now, log the MCP call attempt
        # In a full implementation, this would attempt to communicate with MCP server
        log_hook_activity(f"MCP tool call: {tool_name} with params: {parameters}")
        
        # Placeholder for actual MCP integration
        # This would be implemented based on the specific MCP communication mechanism
        # For example:
        # - HTTP requests to MCP server
        # - Direct Python function calls
        # - CLI subprocess calls
        
        log_hook_activity("MCP integration not yet fully implemented", "warning")
        return None
        
    except Exception as e:
        log_hook_activity(f"Error calling MCP tool {tool_name}: {str(e)}", "error")
        return None


def main() -> None:
    """Main entry point called by the git hook.
    
    Expected to be called as:
    python -m mcp_commit_story.git_hook_worker "$PWD"
    """
    try:
        # Get repository path from command line argument
        if len(sys.argv) != 2:
            log_hook_activity("Invalid arguments - expected repo path", "error")
            return
        
        repo_path = sys.argv[1]
        
        # Set up logging
        setup_hook_logging(repo_path)
        
        log_hook_activity("=== Git hook worker starting ===", "info", repo_path)
        log_hook_activity(f"Repository path: {repo_path}", "info", repo_path)
        
        # Check if we're in a git repository
        if not os.path.exists(os.path.join(repo_path, '.git')):
            log_hook_activity(f"Not a git repository: {repo_path}", "warning", repo_path)
            return
        
        # 1. Check if daily summary should be generated
        date_to_generate = check_daily_summary_trigger(repo_path)
        
        if date_to_generate:
            # Attempt to generate daily summary via MCP
            result = call_mcp_tool("generate_daily_summary", {"date": date_to_generate})
            if result:
                log_hook_activity(f"Daily summary generated successfully for {date_to_generate}", "info", repo_path)
            else:
                log_hook_activity(f"Daily summary generation failed for {date_to_generate}", "warning", repo_path)
            
            # 2. Check if period summaries should be generated
            period_triggers = check_period_summary_triggers(date_to_generate, repo_path)
            
            for period, should_generate in period_triggers.items():
                if should_generate:
                    result = call_mcp_tool(f"generate_{period}_summary", {"date": date_to_generate})
                    if result:
                        log_hook_activity(f"{period.title()} summary generated successfully", "info", repo_path)
                    else:
                        log_hook_activity(f"{period.title()} summary generation failed", "warning", repo_path)
        
        # 3. Always attempt to generate journal entry (maintains existing behavior)
        log_hook_activity("Attempting journal entry generation", "info", repo_path)
        result = call_mcp_tool("new_journal_entry", {"repo_path": repo_path})
        if result:
            log_hook_activity("Journal entry generated successfully", "info", repo_path)
        else:
            log_hook_activity("Journal entry generation failed", "warning", repo_path)
        
        log_hook_activity("=== Git hook worker completed ===", "info", repo_path)
        
    except Exception as e:
        # Final safety net - log error and exit gracefully
        log_hook_activity(f"Critical error in git hook worker: {str(e)}", "error", repo_path if 'repo_path' in locals() else None)
    finally:
        # Always exit successfully to maintain git operation reliability
        sys.exit(0)


if __name__ == "__main__":
    main() 