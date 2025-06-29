"""
Commit-based time window filtering for chat history collection.

Provides functionality to determine precise time windows for collecting chat history
based on git commit timestamps, handling edge cases like first commits and merge commits.
"""

import time
import logging
from typing import Dict, Optional, Union
import git
from git.exc import GitCommandError, BadName

from .telemetry import trace_mcp_operation, get_mcp_metrics, get_tracer
from .git_hook_worker import handle_errors_gracefully

logger = logging.getLogger(__name__)

# Performance threshold for time window operations (matching query performance expectations)
PERFORMANCE_THRESHOLD_MS = 100.0


def is_merge_commit(commit: git.Commit) -> bool:
    """
    Detect if a commit is a merge commit.
    
    Uses the established pattern from context_collection.py:
    len(commit.parents) > 1 indicates a merge commit.
    
    Args:
        commit: GitPython commit object
        
    Returns:
        True if commit is a merge commit, False otherwise
    """
    return len(commit.parents) > 1


def get_commit_timestamp_ms(commit: git.Commit) -> int:
    """
    Get commit timestamp converted to milliseconds.
    
    Converts git's second-based timestamps to milliseconds to match
    Cursor's timestamp format.
    
    Args:
        commit: GitPython commit object
        
    Returns:
        Timestamp in milliseconds
    """
    return int(commit.committed_date * 1000)


def calculate_time_window(commit: git.Commit) -> Dict[str, Union[str, int, float]]:
    """
    Calculate time window for a specific commit.
    
    Determines the appropriate time window based on commit characteristics:
    - Normal commits: parent timestamp to current timestamp
    - First commits: 24-hour lookback from current timestamp
    - Error cases: 24-hour fallback window
    
    Args:
        commit: GitPython commit object
        
    Returns:
        Dictionary containing:
        - strategy: 'commit_based', 'first_commit', or 'fallback_24h'
        - start_timestamp_ms: Start time in milliseconds
        - end_timestamp_ms: End time in milliseconds
        - duration_hours: Time window duration in hours
    """
    try:
        current_timestamp_ms = get_commit_timestamp_ms(commit)
        
        # Handle first commit (no parents)
        if not commit.parents:
            # 24-hour lookback window for first commit
            start_timestamp_ms = current_timestamp_ms - (24 * 3600 * 1000)
            
            logger.debug(f"First commit detected: using 24-hour lookback window")
            
            return {
                'strategy': 'first_commit',
                'start_timestamp_ms': start_timestamp_ms,
                'end_timestamp_ms': current_timestamp_ms,
                'duration_hours': 24.0
            }
        
        # Use first parent for time window (established pattern: commit.parents[0])
        parent = commit.parents[0]
        parent_timestamp_ms = get_commit_timestamp_ms(parent)
        
        # Calculate duration in hours
        duration_seconds = (current_timestamp_ms - parent_timestamp_ms) / 1000
        duration_hours = duration_seconds / 3600
        
        logger.debug(
            f"Using commit_based time window: {parent_timestamp_ms} to {current_timestamp_ms} "
            f"({duration_hours:.2f} hours)"
        )
        
        return {
            'strategy': 'commit_based',
            'start_timestamp_ms': parent_timestamp_ms,
            'end_timestamp_ms': current_timestamp_ms,
            'duration_hours': duration_hours
        }
        
    except (AttributeError, TypeError, ValueError) as e:
        # Fall back to 24-hour window on any calculation errors
        current_timestamp_ms = get_commit_timestamp_ms(commit)
        start_timestamp_ms = current_timestamp_ms - (24 * 3600 * 1000)
        
        logger.warning(f"Error calculating commit time window, using 24-hour fallback: {str(e)}")
        
        return {
            'strategy': 'fallback_24h',
            'start_timestamp_ms': start_timestamp_ms,
            'end_timestamp_ms': current_timestamp_ms,
            'duration_hours': 24.0
        }


@trace_mcp_operation("commit_time_window_filtering")
def get_commit_time_window(repo: git.Repo, commit_hash: str) -> Optional[Dict[str, Union[str, int, float]]]:
    """
    Get time window for collecting chat history based on a git commit.
    
    Main entry point for commit-based time window filtering. Handles all edge cases
    including merge commits (which are skipped), first commits, and error scenarios.
    
    Args:
        repo: GitPython repository object
        commit_hash: Git commit hash to analyze
        
    Returns:
        Dictionary with time window details, or None for skipped commits (merges)
        
    Raises:
        Errors are handled gracefully with fallback strategies
    """
    start_time = time.time()
    metrics = get_mcp_metrics()
    
    try:
        # Get the commit object
        try:
            commit = repo.commit(commit_hash)
        except (GitCommandError, BadName) as e:
            logger.warning(f"Invalid commit hash {commit_hash}: {str(e)}")
            
            # Fallback to 24-hour window using current time
            current_timestamp_ms = int(time.time() * 1000)
            start_timestamp_ms = current_timestamp_ms - (24 * 3600 * 1000)
            
            result = {
                'strategy': 'fallback_24h',
                'start_timestamp_ms': start_timestamp_ms,
                'end_timestamp_ms': current_timestamp_ms,
                'duration_hours': 24.0,
                'error_category': 'invalid_commit'
            }
            
            # Track metrics for invalid commit
            if metrics:
                _track_metrics(metrics, result, start_time)
            _set_span_attributes(result)
            
            return result
        
        # Skip merge commits entirely (don't generate journal entries for merges)
        if is_merge_commit(commit):
            logger.debug(f"Skipping merge commit {commit_hash}")
            
            # Track metrics for skipped merge
            if metrics:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_counter(
                    "mcp_commit_time_window_total",
                    value=1,
                    attributes={
                        "strategy": "merge_skipped",
                        "success": "true"
                    }
                )
                metrics.record_histogram(
                    "mcp_commit_time_window_duration_ms",
                    value=duration_ms,
                    attributes={"strategy": "merge_skipped"}
                )
            
            return None
        
        # Calculate the time window
        result = calculate_time_window(commit)
        
        # Track metrics and telemetry
        if metrics:
            _track_metrics(metrics, result, start_time)
        _set_span_attributes(result)
        
        # Check performance threshold
        duration_ms = (time.time() - start_time) * 1000
        if duration_ms > PERFORMANCE_THRESHOLD_MS:
            logger.warning(
                f"Commit time window filtering took {duration_ms:.1f}ms "
                f"(above {PERFORMANCE_THRESHOLD_MS}ms threshold)"
            )
        
        return result
        
    except Exception as e:
        # Ultimate fallback for any unexpected errors
        logger.warning(f"Unexpected error in commit time window filtering: {str(e)}")
        
        current_timestamp_ms = int(time.time() * 1000)
        start_timestamp_ms = current_timestamp_ms - (24 * 3600 * 1000)
        
        result = {
            'strategy': 'fallback_24h',
            'start_timestamp_ms': start_timestamp_ms,
            'end_timestamp_ms': current_timestamp_ms,
            'duration_hours': 24.0,
            'error_category': 'git_command'
        }
        
        # Track metrics for error case
        if metrics:
            _track_metrics(metrics, result, start_time)
        _set_span_attributes(result)
        
        return result


def _track_metrics(metrics, result: Dict, start_time: float) -> None:
    """
    Track metrics for time window operations.
    
    Records counter and histogram metrics following established patterns.
    
    Args:
        metrics: Metrics instance from get_mcp_metrics()
        result: Time window calculation result
        start_time: Operation start time for duration calculation
    """
    duration_ms = (time.time() - start_time) * 1000
    strategy = result['strategy']
    success = "true" if 'error_category' not in result else "false"
    
    # Counter metric for strategy usage
    metrics.record_counter(
        "mcp_commit_time_window_total",
        value=1,
        attributes={
            "strategy": strategy,
            "success": success
        }
    )
    
    # Histogram metric for operation duration
    metrics.record_histogram(
        "mcp_commit_time_window_duration_ms",
        value=duration_ms,
        attributes={"strategy": strategy}
    )


def _set_span_attributes(result: Dict) -> None:
    """
    Set telemetry span attributes for time window operations.
    
    Sets all required span attributes as specified in the approved design.
    Uses the current span from @trace_mcp_operation decorator.
    
    Args:
        result: Time window calculation result
    """
    try:
        from opentelemetry import trace
        
        span = trace.get_current_span()
        if span:
            span.set_attribute("time_window.strategy", result['strategy'])
            span.set_attribute("time_window.start_timestamp", result['start_timestamp_ms'])
            span.set_attribute("time_window.end_timestamp", result['end_timestamp_ms'])
            span.set_attribute("time_window.duration_hours", result['duration_hours'])
            
            # Set error category if present
            if 'error_category' in result:
                span.set_attribute("error.category", result['error_category'])
    except Exception:
        # Don't let telemetry errors break the main functionality
        pass 