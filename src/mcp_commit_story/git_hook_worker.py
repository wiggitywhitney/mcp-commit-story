"""
Git hook worker module for daily summary triggering and direct journal generation.

This module is called by the enhanced git post-commit hook to handle:
- Direct journal generation with bridge to journal_workflow 
- File-creation-based daily summary triggering
- Period summary boundary detection  
- Background journal generation with detached processes
- Graceful error handling that never blocks git operations

"""

import sys
import os
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import git

# Import additional modules for direct journal generation
from . import journal_workflow
from . import config
from . import git_utils
from .daily_summary import generate_daily_summary_standalone
from .telemetry import trace_git_operation

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
        # Journal files are stored in journal_path/daily/ subdirectory
        daily_journal_dir = os.path.join(journal_path, "daily")
        if not os.path.exists(daily_journal_dir):
            log_hook_activity(f"Daily journal directory not found: {daily_journal_dir}", "info", repo_path)
            return None
        
        # Look for journal files in the daily subdirectory
        journal_files = []
        for filename in os.listdir(daily_journal_dir):
            if filename.endswith('-journal.md'):
                file_path = os.path.join(daily_journal_dir, filename)
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
def determine_summary_trigger(repo_path: str, date_str: str) -> bool:
    """
    Determine if AI should be awakened for summary generation based on commit patterns.
    
    This function implements the "AI beast awakening" logic by analyzing commit
    frequency and patterns to decide when summaries should be generated.
    
    Args:
        repo_path: Path to git repository
        date_str: Date string to check (YYYY-MM-DD format)
        
    Returns:
        bool: True if summary should be generated (awaken the beast!)
    """
    try:
        # For now, use simple logic - can be enhanced later
        # In practice, this could analyze:
        # - Number of commits today
        # - Commit message patterns
        # - File change complexity
        # - Time since last summary
        
        commits_today = count_commits_today(repo_path, date_str)
        
        # Awaken AI beast if we have enough commits for a meaningful summary
        return commits_today >= 3  # Threshold for summary generation
        
    except Exception as e:
        log_hook_activity(f"Summary trigger check failed: {e}", "warning", repo_path)
        return False  # Graceful degradation - don't block operations


@handle_errors_gracefully
def count_commits_today(repo_path: str, date_str: str) -> int:
    """
    Count commits made on a specific date.
    
    Args:
        repo_path: Path to git repository  
        date_str: Date string (YYYY-MM-DD format)
        
    Returns:
        int: Number of commits on that date
    """
    try:
        from mcp_commit_story.git_utils import get_repo
        
        repo = get_repo(repo_path)
        
        # Count commits on the specified date
        # This is a simplified implementation
        commits = list(repo.iter_commits(since=f"{date_str} 00:00:00", until=f"{date_str} 23:59:59"))
        return len(commits)
        
    except Exception:
        return 0  # Graceful degradation


@handle_errors_gracefully
def extract_commit_metadata(repo_path: str) -> Dict[str, Any]:
    """Extract commit metadata for telemetry and summary generation.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Dictionary containing commit metadata following approved design.
        Used for telemetry tracking and direct summary generation.
    """
    try:
        from mcp_commit_story.git_utils import get_repo, get_current_commit, get_commit_details
        
        repo = get_repo(repo_path)
        commit = get_current_commit(repo)
        
        # Use existing git_utils function to get standard metadata
        commit_details = get_commit_details(commit)
        
        # Convert to approved metadata format
        # Extract files changed from the commit
        files_changed = []
        for file_path in commit.stats.files.keys():
            files_changed.append(file_path)
        
        return {
            "hash": commit_details["hash"],
            "author": commit_details["author"],
            "date": commit.committed_datetime.isoformat(),
            "message": commit_details["message"].strip(),
            "files_changed": files_changed,
            "stats": commit_details["stats"]
        }
        
    except Exception as e:
        log_hook_activity(f"Error extracting commit metadata: {str(e)}", "error", repo_path)
        # Return minimal metadata for graceful degradation
        return {
            "hash": "unknown",
            "author": "unknown",
            "date": datetime.now().isoformat(),
            "message": "unknown",
            "files_changed": [],
            "stats": {"files": 0, "insertions": 0, "deletions": 0}
        }


@handle_errors_gracefully
def daily_summary_telemetry(success: bool, duration_ms: Optional[float] = None, error_type: Optional[str] = None, entries_count: Optional[int] = None) -> None:
    """Record telemetry for daily summary generation operations."""
    try:
        from mcp_commit_story.telemetry import get_mcp_metrics
        
        metrics = get_mcp_metrics()
        if not metrics:
            return
        
        # Record operation count
        labels = {
            "success": "true" if success else "false"
        }
        
        if error_type:
            labels["error_type"] = error_type
        
        metrics.git_hook_daily_summary_trigger_total.add(1, labels)
        
        # Record duration if provided
        if duration_ms is not None:
            metrics.git_hook_daily_summary_duration_seconds.record(duration_ms / 1000.0, labels)
        
        # Record entries count if provided
        if entries_count is not None:
            metrics.git_hook_daily_summary_entries_count.record(entries_count, labels)
    
    except Exception as e:
        # Silent failure - don't break git operations for telemetry
        pass


@handle_errors_gracefully
def period_summary_placeholder(period: str, date: str, commit_metadata: Dict[str, Any], repo_path: str) -> bool:
    """
    Placeholder for period summary generation.
    
    This function logs the period summary request for future implementation.
    In the future, this could be replaced with direct summary generation calls.
    
    Args:
        period: The period type (weekly, monthly, quarterly, yearly)
        date: The date for the summary
        commit_metadata: Git commit metadata
        repo_path: Path to the repository
        
    Returns:
        bool: Always returns True to indicate successful placeholder execution
    """
    try:
        log_hook_activity(f"Period summary placeholder triggered for {period} summary on {date}", "info", repo_path)
        
        # Future implementation could call summary generation directly here
        # For now, this is a placeholder to maintain git hook workflow
        
        return True
        
    except Exception as e:
        log_hook_activity(f"Period summary placeholder failed for {period}: {str(e)}", "warning", repo_path)
        return False


@handle_errors_gracefully
@trace_git_operation("hook.journal_generation", 
                    timeout_seconds=30.0,
                    performance_thresholds={"duration": 10.0},
                    error_categories=["git", "config", "journal_generation", "filesystem"])
def generate_journal_entry_safe(repo_path: str) -> bool:
    """
    Safe wrapper function that converts git_hook_worker's repo path input into the commit object 
    and config required by journal_workflow.generate_journal_entry().
    
    This function bridges the gap between git hook operations (which work with repo paths) 
    and the journal workflow system (which expects commit objects and config objects).
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        bool: True if journal entry was generated successfully, False otherwise
        
    Note:
        This function follows the existing *_safe() wrapper pattern for error handling
        and ensures git operations are never blocked by journal generation failures.
    """
    from opentelemetry import trace
    
    # Get current span to add telemetry attributes
    current_span = trace.get_current_span()
    
    try:
        # Validate input and add to telemetry
        if not repo_path:
            current_span.set_attribute("repo_path", str(repo_path))
            current_span.set_attribute("error.type", "invalid_input")
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid repo path"))
            log_hook_activity(f"Invalid repo path: {repo_path}", "error", repo_path)
            return False
        
        current_span.set_attribute("repo_path", repo_path)
        
        # Get repository object
        try:
            repo = git_utils.get_repo(repo_path)
        except git.InvalidGitRepositoryError as e:
            current_span.set_attribute("error.type", "git_repo_detection_failed")
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Git repository detection failed: {str(e)}"))
            log_hook_activity(f"Git repository detection failed: {str(e)}", "error", repo_path)
            return False
        
        # Get current commit
        try:
            commit = git_utils.get_current_commit(repo)
            current_span.set_attribute("commit_hash", commit.hexsha)
        except Exception as e:
            current_span.set_attribute("error.type", "git_commit_retrieval_failed")
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Git commit retrieval failed: {str(e)}"))
            log_hook_activity(f"Git commit retrieval failed: {str(e)}", "error", repo_path)
            return False
        
        # Load configuration
        try:
            config_obj = config.load_config()
        except Exception as e:
            current_span.set_attribute("error.type", "config_loading_failed")
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Configuration loading failed: {str(e)}"))
            log_hook_activity(f"Configuration loading failed: {str(e)}", "error", repo_path)
            return False
        
        # Generate and save journal entry
        try:
            result = journal_workflow.handle_journal_entry_creation(commit, config_obj)
            
            if result['success']:
                current_span.set_attribute("journal.generation_result", "success")
                if result.get('skipped'):
                    current_span.set_attribute("journal.skipped", True)
                    current_span.set_attribute("journal.skip_reason", result.get('reason', 'unknown'))
                    log_hook_activity(f"Journal entry skipped: {result.get('reason', 'unknown reason')}", "info", repo_path)
                else:
                    current_span.set_attribute("journal.file_path", result.get('file_path', 'unknown'))
                    log_hook_activity(f"Journal entry generated successfully for commit {commit.hexsha}", "info", repo_path)
                    log_hook_activity(f"Journal entry saved to: {result.get('file_path', 'unknown path')}", "info", repo_path)
                
                return True
            else:
                error_msg = result.get('error', 'Unknown journal creation error')
                current_span.set_attribute("error.type", "journal_generation_failed")
                current_span.set_attribute("journal.error_message", error_msg)
                current_span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                log_hook_activity(f"Journal generation failed: {error_msg}", "error", repo_path)
                
                return False
                
        except Exception as e:
            current_span.set_attribute("error.type", "journal_generation_failed")
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Journal generation failed: {str(e)}"))
            log_hook_activity(f"Journal generation failed: {str(e)}", "error", repo_path)
            
            return False
            
    except Exception as e:
        # Catch-all for any unexpected errors
        current_span.set_attribute("error.type", "unexpected_error")
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Unexpected error: {str(e)}"))
        log_hook_activity(f"Unexpected error in generate_journal_entry_safe: {str(e)}", "error", repo_path)
        return False


def main() -> None:
    """Main entry point called by the git hook.
    
    Handles post-commit processing including:
    - Direct journal entry generation via generate_journal_entry_safe()
    - Daily/period summary generation when appropriate
    - Comprehensive error handling to ensure git operations are never blocked
    
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
        
        # Extract commit metadata once for telemetry tracking and summary generation
        commit_metadata = extract_commit_metadata(repo_path)
        
        # 1. Check if daily summary should be generated
        date_to_generate = check_daily_summary_trigger(repo_path)
        
        if date_to_generate:
            # Generate daily summary directly
            import time
            start_time = time.time()
            
            try:
                entries_count = generate_daily_summary_standalone(
                    date_to_generate, 
                    repo_path, 
                    commit_metadata
                )
                duration_ms = (time.time() - start_time) * 1000.0
                
                if entries_count is not None:
                    log_hook_activity(f"Daily summary generated directly for {date_to_generate} with {entries_count} entries", "info", repo_path)
                    daily_summary_telemetry(success=True, duration_ms=duration_ms, entries_count=entries_count)
                else:
                    log_hook_activity(f"Daily summary generated directly for {date_to_generate} (no entries)", "info", repo_path)
                    daily_summary_telemetry(success=True, duration_ms=duration_ms)  # No entries is still success
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000.0
                error_type = "ai_generation_error" if "ai" in str(e).lower() else "unknown_error"
                log_hook_activity(f"Daily summary generation failed for {date_to_generate}: {str(e)}", "warning", repo_path)
                daily_summary_telemetry(success=False, duration_ms=duration_ms, error_type=error_type)
            
            # 2. Check if period summaries should be generated
            period_triggers = check_period_summary_triggers(date_to_generate, repo_path)
            
            for period, should_generate in period_triggers.items():
                if should_generate:
                    result = period_summary_placeholder(
                        period, 
                        date_to_generate, 
                        commit_metadata, 
                        repo_path
                    )
                    if result:
                        log_hook_activity(f"{period.title()} summary placeholder executed", "info", repo_path)
                    else:
                        log_hook_activity(f"{period.title()} summary placeholder failed", "warning", repo_path)
        
        # 3. Always attempt to generate journal entry (maintains existing behavior)
        log_hook_activity("Generating journal entry directly", "info", repo_path)
        # Generate journal entry directly using our bridge function
        journal_success = generate_journal_entry_safe(repo_path)
        
        if journal_success:
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