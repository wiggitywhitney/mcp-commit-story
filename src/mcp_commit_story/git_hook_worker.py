"""
Git hook worker module for daily summary triggering and background journal generation.

This module is called by the enhanced git post-commit hook to handle:
- File-creation-based daily summary triggering
- Period summary boundary detection  
- MCP server communication for summary generation
- Background journal generation with detached processes (Task 57.4)
- Graceful error handling that never blocks git operations

Based on approved design decisions for subtask 27.3 and Task 57.4.
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
    """Extract commit metadata for signal creation.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Dictionary containing commit metadata following approved design
    """
    try:
        from mcp_commit_story.git_utils import get_repo, get_current_commit, get_commit_details
        
        repo = get_repo(repo_path)
        commit = get_current_commit(repo)
        
        # Use existing git_utils function to get standard metadata
        commit_details = get_commit_details(commit)
        
        # Convert to approved signal format
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


def signal_creation_telemetry(tool_name: str, success: bool, error_type: str = None, duration_ms: float = None) -> None:
    """Record telemetry for signal creation operations.
    
    Args:
        tool_name: Name of the MCP tool for the signal
        success: Whether signal creation was successful
        error_type: Type of error if success=False
        duration_ms: Duration of signal creation in milliseconds
    """
    try:
        from mcp_commit_story.telemetry import get_mcp_metrics
        
        metrics = get_mcp_metrics()
        if not metrics:
            return  # Graceful degradation if no metrics available
        
        if success:
            # Record success metrics
            metrics.record_counter("signal_creation_success", 1)
            metrics.record_counter(f"signal_creation_success_{tool_name}", 1)
        else:
            # Record failure metrics
            metrics.record_counter("signal_creation_failure", 1)
            metrics.record_counter(f"signal_creation_failure_{tool_name}", 1)
            
            if error_type:
                metrics.record_counter(f"signal_creation_error_{error_type}", 1)
        
        # Record performance metrics if available
        if duration_ms is not None:
            metrics.record_histogram("signal_creation_duration_ms", duration_ms)
            
    except Exception as e:
        # Telemetry failures should never block signal creation
        log_hook_activity(f"Telemetry recording failed: {str(e)}", "warning")


def create_tool_signal(tool_name: str, parameters: Dict[str, Any], commit_metadata: Dict[str, Any], repo_path: str) -> Optional[str]:
    """Create a signal file for MCP tool execution.
    
    Approved design: Complete replacement of call_mcp_tool() with generic signal creation
    that works for any MCP tool type while maintaining comprehensive telemetry.
    
    Args:
        tool_name: Name of the MCP tool (e.g., "journal_new_entry")
        parameters: Parameters to pass to the tool
        commit_metadata: Git commit metadata following approved standard scope
        repo_path: Path to the git repository
        
    Returns:
        Path to created signal file if successful, None if failed
        
    Raises:
        ValueError: For parameter validation errors (allows tests to check validation)
    """
    import time
    
    start_time = time.time()
    
    # Validate inputs - these should raise for tests
    if not tool_name or not isinstance(tool_name, str):
        raise ValueError("tool_name must be a non-empty string")
    if parameters is None or not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")
    if commit_metadata is None or not isinstance(commit_metadata, dict):
        raise ValueError("commit_metadata must be a dictionary")
    if not repo_path or not isinstance(repo_path, str):
        raise ValueError("repo_path must be a non-empty string")
    
    try:
        from mcp_commit_story.signal_management import ensure_signal_directory, create_signal_file
        
        # Ensure signal directory exists
        signal_directory = ensure_signal_directory(repo_path)
        
        # Create signal file using existing signal management
        signal_file_path = create_signal_file(
            signal_directory=signal_directory,
            tool_name=tool_name,
            parameters=parameters,
            commit_metadata=commit_metadata
        )
        
        # Record success telemetry
        duration_ms = (time.time() - start_time) * 1000
        signal_creation_telemetry(tool_name, success=True, duration_ms=duration_ms)
        
        log_hook_activity(f"Signal created for {tool_name}: {signal_file_path}", "info", repo_path)
        return signal_file_path
        
    except Exception as e:
        # Check if it's a graceful degradation error
        error_type = "unknown_error"
        if hasattr(e, 'graceful_degradation') and e.graceful_degradation:
            error_type = "graceful_degradation"
        elif "permission" in str(e).lower():
            error_type = "permission_error"
        elif "space" in str(e).lower():
            error_type = "disk_space_error"
        
        duration_ms = (time.time() - start_time) * 1000
        signal_creation_telemetry(tool_name, success=False, error_type=error_type, duration_ms=duration_ms)
        
        log_hook_activity(f"Signal creation failed for {tool_name}: {str(e)}", "error", repo_path)
        return None


@handle_errors_gracefully  
def create_tool_signal_safe(tool_name: str, parameters: Dict[str, Any], commit_metadata: Dict[str, Any], repo_path: str) -> Optional[str]:
    """Safe wrapper for create_tool_signal that handles all errors gracefully for use in main().
    
    This version catches validation errors to ensure git operations never fail.
    """
    try:
        return create_tool_signal(tool_name, parameters, commit_metadata, repo_path)
    except ValueError as e:
        # Parameter validation errors - log and continue for graceful degradation in git hooks
        log_hook_activity(f"Signal creation validation error for {tool_name}: {str(e)}", "error", repo_path)
        signal_creation_telemetry(tool_name, success=False, error_type="validation_error")
        return None


@handle_errors_gracefully
def spawn_background_journal_generation(commit_hash: str, repo_path: str = None) -> Dict[str, Any]:
    """
    Spawn background journal generation process for the given commit.
    
    Implements Task 57.4 approved design decisions:
    - Detached background process execution
    - Immediate return (no blocking)
    - Silent failure with telemetry capture
    - Emergency bypass mechanism via environment variable
    - 30-second max delay (generous since background)
    
    Args:
        commit_hash: Git commit hash to generate journal entry for
        repo_path: Path to git repository (defaults to current directory)
        
    Returns:
        Dict with status and process information:
        - background_spawned: Normal background execution
        - emergency_synchronous_complete: Emergency bypass completed
        - error: Failed to spawn (should be rare)
    """
    if repo_path is None:
        repo_path = os.getcwd()
    
    try:
        # Check for emergency bypass mechanism
        if os.environ.get('MCP_JOURNAL_EMERGENCY_BYPASS', '').lower() == 'true':
            log_hook_activity("Emergency bypass activated - running synchronous journal generation", "info", repo_path)
            return _run_emergency_synchronous_generation(commit_hash, repo_path)
        
        # Normal background execution path
        log_hook_activity(f"Spawning background journal generation for commit {commit_hash[:8]}", "info", repo_path)
        
        # Create background process command
        python_executable = sys.executable
        script_path = os.path.join(os.path.dirname(__file__), 'background_journal_worker.py')
        
        # Command to run in background
        cmd = [
            python_executable,
            script_path,
            '--commit-hash', commit_hash,
            '--repo-path', repo_path
        ]
        
        # Spawn detached background process
        if os.name == 'nt':  # Windows
            # Windows detached process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:  # Unix/Linux/macOS
            # Unix detached process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid  # Create new session
            )
        
        log_hook_activity(f"Background journal generation spawned with PID {process.pid}", "info", repo_path)
        
        return {
            'status': 'background_spawned',
            'process_id': process.pid,
            'commit_hash': commit_hash
        }
        
    except Exception as e:
        # Silent failure with telemetry
        error_msg = f"Failed to spawn background journal generation: {str(e)}"
        log_hook_activity(error_msg, "error", repo_path)
        
        # Record telemetry for monitoring
        _record_background_spawn_telemetry(False, str(e))
        
        return {
            'status': 'error',
            'error': error_msg,
            'commit_hash': commit_hash
        }


def _run_emergency_synchronous_generation(commit_hash: str, repo_path: str) -> Dict[str, Any]:
    """
    Run journal generation synchronously for emergency bypass.
    
    Args:
        commit_hash: Git commit hash to generate journal entry for
        repo_path: Path to git repository
        
    Returns:
        Dict with emergency completion status
    """
    try:
        start_time = time.time()
        
        # Import and run journal generation synchronously
        from mcp_commit_story.journal_orchestrator import orchestrate_journal_generation
        from mcp_commit_story.journal import get_journal_file_path
        from datetime import datetime
        
        # Get journal file path
        date_str = datetime.now().strftime("%Y-%m-%d")
        journal_path = get_journal_file_path(date_str, "daily")
        
        # Run synchronous generation
        result = orchestrate_journal_generation(commit_hash, str(journal_path))
        
        execution_time = time.time() - start_time
        
        if result.get('success'):
            log_hook_activity(f"Emergency synchronous journal generation completed in {execution_time:.2f}s", "info", repo_path)
            return {
                'status': 'emergency_synchronous_complete',
                'execution_time': execution_time,
                'journal_path': str(journal_path)
            }
        else:
            error_msg = result.get('error', 'Unknown error in emergency generation')
            log_hook_activity(f"Emergency synchronous journal generation failed: {error_msg}", "error", repo_path)
            return {
                'status': 'emergency_synchronous_error',
                'error': error_msg,
                'execution_time': execution_time
            }
            
    except Exception as e:
        error_msg = f"Emergency synchronous generation failed: {str(e)}"
        log_hook_activity(error_msg, "error", repo_path)
        return {
            'status': 'emergency_synchronous_error',
            'error': error_msg
        }


def _record_background_spawn_telemetry(success: bool, error_type: str = None) -> None:
    """
    Record telemetry for background process spawning.
    
    Args:
        success: Whether the spawn was successful
        error_type: Type of error if spawn failed
    """
    try:
        from mcp_commit_story.telemetry import get_mcp_metrics
        
        metrics = get_mcp_metrics()
        if metrics:
            metrics.record_counter(
                'background_journal_spawn_total',
                attributes={
                    'success': str(success).lower(),
                    'error_type': error_type or 'none'
                }
            )
    except Exception:
        # Silent failure for telemetry - don't let telemetry issues block operations
        pass


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
        
        # Extract commit metadata once for all signal creation
        commit_metadata = extract_commit_metadata(repo_path)
        
        # 1. Check if daily summary should be generated
        date_to_generate = check_daily_summary_trigger(repo_path)
        
        if date_to_generate:
            # Create signal for daily summary generation
            result = create_tool_signal_safe(
                "generate_daily_summary", 
                {"date": date_to_generate}, 
                commit_metadata, 
                repo_path
            )
            if result:
                log_hook_activity(f"Daily summary signal created for {date_to_generate}: {result}", "info", repo_path)
            else:
                log_hook_activity(f"Daily summary signal creation failed for {date_to_generate}", "warning", repo_path)
            
            # 2. Check if period summaries should be generated
            period_triggers = check_period_summary_triggers(date_to_generate, repo_path)
            
            for period, should_generate in period_triggers.items():
                if should_generate:
                    result = create_tool_signal_safe(
                        f"generate_{period}_summary", 
                        {"date": date_to_generate}, 
                        commit_metadata, 
                        repo_path
                    )
                    if result:
                        log_hook_activity(f"{period.title()} summary signal created: {result}", "info", repo_path)
                    else:
                        log_hook_activity(f"{period.title()} summary signal creation failed", "warning", repo_path)
        
        # 3. Always attempt to generate journal entry (maintains existing behavior)
        log_hook_activity("Creating journal entry signal", "info", repo_path)
        # Create signal for AI processing
        create_tool_signal_safe(
            "journal_new_entry", 
            {},  # ✅ Minimal - repo location inferred from signal file location
            commit_metadata, 
            repo_path
        )
        
        log_hook_activity("=== Git hook worker completed ===", "info", repo_path)
        
    except Exception as e:
        # Final safety net - log error and exit gracefully
        log_hook_activity(f"Critical error in git hook worker: {str(e)}", "error", repo_path if 'repo_path' in locals() else None)
    finally:
        # Always exit successfully to maintain git operation reliability
        sys.exit(0)


if __name__ == "__main__":
    main() 