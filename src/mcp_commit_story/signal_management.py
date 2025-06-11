"""
Signal file management for MCP tool signaling.

SIGNAL FILES ARE TEMPORARY - cleared automatically with each new commit.
These files enable AI-powered journal generation from git commits.

The .mcp-commit-story/ directory is in .gitignore and won't be committed.
Users don't need to manage these files manually.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import time
import shutil

from mcp_commit_story.telemetry import trace_mcp_operation, get_mcp_metrics


# Custom exceptions with graceful degradation support
class SignalDirectoryError(Exception):
    """Exception raised when signal directory operations fail."""
    
    def __init__(self, message: str, graceful_degradation: bool = False):
        super().__init__(message)
        self.graceful_degradation = graceful_degradation


class SignalFileError(Exception):
    """Exception raised when signal file operations fail."""
    
    def __init__(self, message: str, graceful_degradation: bool = False):
        super().__init__(message)
        self.graceful_degradation = graceful_degradation


class SignalValidationError(Exception):
    """Exception raised when signal format validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message)


# Thread lock for concurrent signal creation
_signal_creation_lock = threading.Lock()


@trace_mcp_operation("signal_management.ensure_directory")
def ensure_signal_directory(repo_path: str) -> str:
    """
    Ensure signal directory exists and return its path.
    
    Creates .mcp-commit-story/signals directory structure if needed.
    
    Args:
        repo_path: Path to the git repository root
        
    Returns:
        str: Absolute path to the signal directory
        
    Raises:
        SignalDirectoryError: If directory creation fails
    """
    metrics = get_mcp_metrics()
    
    try:
        # Validate repository path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            if metrics:
                metrics.record_counter("signal_directory_invalid_path", 1)
            raise SignalDirectoryError(
                f"Invalid repository path: {repo_path}", 
                graceful_degradation=True
            )
        
        # Create signal directory structure
        mcp_dir = repo_path_obj / ".mcp-commit-story"
        signal_dir = mcp_dir / "signals"
        
        try:
            signal_dir.mkdir(parents=True, exist_ok=True)
            if metrics:
                metrics.record_counter("signal_directory_created", 1)
        except PermissionError as e:
            if metrics:
                metrics.record_counter("signal_directory_permission_error", 1)
            raise SignalDirectoryError(
                f"Permission denied creating signal directory: {e}",
                graceful_degradation=True
            )
        except OSError as e:
            if metrics:
                metrics.record_counter("signal_directory_os_error", 1)
            raise SignalDirectoryError(
                f"OS error creating signal directory: {e}",
                graceful_degradation=True
            )
        
        return str(signal_dir.absolute())
        
    except Exception as e:
        if isinstance(e, SignalDirectoryError):
            raise
        if metrics:
            metrics.record_counter("signal_directory_unexpected_error", 1)
        raise SignalDirectoryError(
            f"Unexpected error ensuring signal directory: {e}",
            graceful_degradation=True
        )


@trace_mcp_operation("signal_management.create_signal_file")
def create_signal_file(
    signal_directory: str,
    tool_name: str, 
    parameters: Dict[str, Any],
    commit_metadata: Dict[str, Any]
) -> str:
    """
    Create a signal file for MCP tool execution.
    
    Uses approved design: timestamp-based naming, standard metadata scope,
    pretty JSON format with thread safety and graceful degradation.
    
    Args:
        signal_directory: Path to signal directory
        tool_name: Name of the MCP tool (e.g., "journal_new_entry")
        parameters: Parameters to pass to the tool
        commit_metadata: Git commit metadata
        
    Returns:
        str: Path to created signal file
        
    Raises:
        SignalFileError: If file creation fails
    """
    metrics = get_mcp_metrics()
    
    # Use thread lock for concurrent signal creation safety
    with _signal_creation_lock:
        try:
            # Validate commit metadata has required hash
            if not commit_metadata.get("hash"):
                if metrics:
                    metrics.record_counter("signal_file_missing_commit_hash", 1)
                raise SignalFileError(
                    "Commit metadata must contain 'hash' field for minimal signal creation",
                    graceful_degradation=True
                )
            
            # Generate unique timestamp-based filename with microsecond precision and counter
            now = datetime.now(timezone.utc)
            # Use full microsecond precision for better uniqueness
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            
            # Extract short hash for filename (first 8 chars)
            commit_hash = commit_metadata.get("hash", "unknown")
            hash_prefix = commit_hash[:8] if commit_hash != "unknown" else "unknown"
            
            # Create filename: {timestamp}_{tool_name}_{hash_prefix}.json
            signal_id = f"{timestamp}_{tool_name}_{hash_prefix}"
            filename = f"{signal_id}.json"
            file_path = Path(signal_directory) / filename
            
            # Handle the rare case where files might still collide by adding a suffix
            counter = 0
            while file_path.exists():
                counter += 1
                signal_id = f"{timestamp}_{tool_name}_{hash_prefix}_{counter:04d}"
                filename = f"{signal_id}.json"
                file_path = Path(signal_directory) / filename
            
            # Create minimal signal data structure (privacy-safe, no redundancy)
            # Add commit_hash to params for on-demand context retrieval
            minimal_params = {
                **parameters,
                "commit_hash": commit_metadata.get("hash", "unknown")
            }
            
            signal_data = {
                "tool": tool_name,
                "params": minimal_params,
                "created_at": now.isoformat()
            }
            
            # Validate signal format before writing
            if not validate_signal_format(signal_data):
                if metrics:
                    metrics.record_counter("signal_file_validation_failed", 1)
                raise SignalFileError(
                    f"Signal validation failed for tool {tool_name}",
                    graceful_degradation=True
                )
            
            # Write signal file with pretty JSON formatting
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(signal_data, f, indent=2, ensure_ascii=False, sort_keys=True)
                
                if metrics:
                    metrics.record_counter("signal_file_created", 1)
                    metrics.record_counter(f"signal_file_created_{tool_name}", 1)
                
                return str(file_path.absolute())
                
            except (OSError, IOError) as e:
                error_msg = str(e).lower()
                if "no space left" in error_msg:
                    if metrics:
                        metrics.record_counter("signal_file_disk_space_error", 1)
                    raise SignalFileError(
                        f"No space left on device: {e}",
                        graceful_degradation=True
                    )
                elif "permission denied" in error_msg:
                    if metrics:
                        metrics.record_counter("signal_file_permission_error", 1)
                    raise SignalFileError(
                        f"Permission denied: {e}",
                        graceful_degradation=True
                    )
                else:
                    if metrics:
                        metrics.record_counter("signal_file_io_error", 1)
                    raise SignalFileError(
                        f"I/O error creating signal file: {e}",
                        graceful_degradation=True
                    )
            
        except Exception as e:
            if isinstance(e, (SignalFileError, SignalValidationError)):
                raise
            if metrics:
                metrics.record_counter("signal_file_unexpected_error", 1)
            raise SignalFileError(
                f"Unexpected error creating signal file: {e}",
                graceful_degradation=True
            )


@trace_mcp_operation("signal_management.validate_signal_format")
def validate_signal_format(signal_data: Any) -> bool:
    """
    Validate signal file format and structure.
    
    Ensures signal contains required fields with correct types.
    
    Args:
        signal_data: Signal data to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        SignalValidationError: If validation fails
    """
    metrics = get_mcp_metrics()
    
    try:
        # Must be a dictionary
        if not isinstance(signal_data, dict):
            if metrics:
                metrics.record_counter("signal_validation_not_dict", 1)
            raise SignalValidationError(
                f"Signal data must be a dictionary, got {type(signal_data)}"
            )
        
        # Required fields with their expected types (minimal format)
        required_fields = {
            "tool": str,
            "params": dict,
            "created_at": str
        }
        
        # Check all required fields are present
        for field_name, field_type in required_fields.items():
            if field_name not in signal_data:
                if metrics:
                    metrics.record_counter("signal_validation_missing_field", 1)
                raise SignalValidationError(f"Missing required field: {field_name}")
            
            # Check field type
            field_value = signal_data[field_name]
            if not isinstance(field_value, field_type):
                if metrics:
                    metrics.record_counter("signal_validation_wrong_type", 1)
                raise SignalValidationError(
                    f"Field '{field_name}' must be {field_type.__name__}, got {type(field_value)}"
                )
            
            # Check string fields are not empty
            if field_type == str and not field_value.strip():
                if metrics:
                    metrics.record_counter("signal_validation_empty_string", 1)
                raise SignalValidationError(f"Field '{field_name}' cannot be empty")
        
        # Check no extra fields are present (enforce minimal format)
        allowed_fields = set(required_fields.keys())
        present_fields = set(signal_data.keys())
        extra_fields = present_fields - allowed_fields
        
        if extra_fields:
            if metrics:
                metrics.record_counter("signal_validation_extra_fields", 1)
            raise SignalValidationError(f"Extra fields not allowed in minimal format: {extra_fields}")
        
        if metrics:
            metrics.record_counter("signal_validation_success", 1)
        return True
        
    except SignalValidationError:
        raise
    except Exception as e:
        if metrics:
            metrics.record_counter("signal_validation_unexpected_error", 1)
        raise SignalValidationError(f"Unexpected validation error: {e}")


# Utility functions for signal management

def get_signal_directory_path(repo_path: str) -> str:
    """
    Get the expected signal directory path without creating it.
    
    Args:
        repo_path: Path to git repository
        
    Returns:
        str: Expected signal directory path
    """
    return str(Path(repo_path) / ".mcp-commit-story" / "signals")


def is_signal_directory_ready(repo_path: str) -> bool:
    """
    Check if signal directory exists and is writable.
    
    Args:
        repo_path: Path to git repository
        
    Returns:
        bool: True if directory exists and is writable
    """
    signal_dir = Path(get_signal_directory_path(repo_path))
    return signal_dir.exists() and signal_dir.is_dir() and os.access(signal_dir, os.W_OK)


def count_signal_files(signal_directory: str) -> int:
    """
    Count the number of signal files in directory.
    
    Args:
        signal_directory: Path to signal directory
        
    Returns:
        int: Number of .json signal files
    """
    try:
        signal_dir = Path(signal_directory)
        if not signal_dir.exists():
            return 0
        return len(list(signal_dir.glob("*.json")))
    except Exception:
        return 0


def get_latest_signal_file(signal_directory: str) -> Optional[str]:
    """
    Get the path to the most recently created signal file.
    
    Args:
        signal_directory: Path to signal directory
        
    Returns:
        Optional[str]: Path to latest signal file, or None if none exist
    """
    try:
        signal_dir = Path(signal_directory)
        if not signal_dir.exists():
            return None
        
        json_files = list(signal_dir.glob("*.json"))
        if not json_files:
            return None
            
        # Sort by filename (timestamp-based naming ensures chronological order)
        latest_file = sorted(json_files, key=lambda x: x.name)[-1]
        return str(latest_file.absolute())
        
    except Exception:
        return None


def read_signal_file(file_path: str) -> Dict[str, Any]:
    """
    Read and parse a signal file.
    
    Args:
        file_path: Path to signal file
        
    Returns:
        Dict[str, Any]: Parsed signal data
        
    Raises:
        SignalValidationError: If file cannot be read or parsed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            signal_data = json.load(f)
        
        # Validate the loaded data
        validate_signal_format(signal_data)
        return signal_data
        
    except json.JSONDecodeError as e:
        raise SignalValidationError(f"Invalid JSON in signal file {file_path}: {e}")
    except FileNotFoundError:
        raise SignalValidationError(f"Signal file not found: {file_path}")
    except Exception as e:
        raise SignalValidationError(f"Error reading signal file {file_path}: {e}")


# On-demand context retrieval functions for minimal signal processing

def fetch_git_context_on_demand(commit_hash: str, repo_path: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full git context on-demand using existing git_utils functions.
    
    This function retrieves git metadata when needed, eliminating the need to store
    redundant metadata in signal files. Uses existing git_utils for consistency.
    
    Args:
        commit_hash: Git commit hash from minimal signal
        repo_path: Path to git repository
        
    Returns:
        Optional[Dict[str, Any]]: Full commit context or None if failed
    """
    try:
        from mcp_commit_story.git_utils import get_repo, get_commit_details
        
        # Use existing git_utils functions for consistency
        repo = get_repo(repo_path)
        
        # Find commit by hash
        try:
            commit = repo.commit(commit_hash)
        except Exception:
            # If hash not found, try shorter hash
            commit = repo.commit(commit_hash[:7])
        
        # Get full details using existing function
        context = get_commit_details(commit)
        return context
        
    except Exception as e:
        # Graceful degradation - log but don't fail signal processing
        from mcp_commit_story.git_hook_worker import log_hook_activity
        log_hook_activity(f"Failed to fetch git context for {commit_hash}: {e}", "warning", repo_path)
        return None


def process_signal_with_context(signal_data: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
    """
    Process a minimal signal by fetching git context on-demand.
    
    This function combines minimal signal data with on-demand git context retrieval,
    providing full context to AI clients while maintaining signal privacy/efficiency.
    
    Args:
        signal_data: Minimal signal data
        repo_path: Path to git repository
        
    Returns:
        Dict[str, Any]: Signal data enriched with git context
    """
    # Start with signal data
    result = {
        "tool": signal_data["tool"],
        "params": signal_data["params"],
        "created_at": signal_data["created_at"]
    }
    
    # Fetch git context on-demand if commit hash is available
    commit_hash = signal_data.get("params", {}).get("commit_hash")
    if commit_hash:
        commit_context = fetch_git_context_on_demand(commit_hash, repo_path)
        if commit_context:
            result["commit_context"] = commit_context
    
    return result


# Signal cleanup functions - commit-based design for AI clarity

# Simple cleanup lock for thread safety
_cleanup_lock = threading.Lock()


def validate_cleanup_safety(signal_directory: str) -> tuple[bool, str]:
    """
    Validate that it's safe to perform cleanup operations.
    
    Args:
        signal_directory: Path to check for cleanup safety
        
    Returns:
        tuple[bool, str]: (is_safe, reason)
    """
    try:
        signal_path = Path(signal_directory)
        
        # Must be a .mcp-commit-story/signals directory
        if not (signal_path.name == "signals" and 
                signal_path.parent.name == ".mcp-commit-story"):
            return False, "Path is not a signal directory"
        
        return True, "Valid signal directory, safe for cleanup"
        
    except Exception as e:
        return False, f"Safety validation error: {e}"


@trace_mcp_operation("signal_management.cleanup_old_signals")
def cleanup_old_signals(signal_directory: str, max_age_hours: Optional[float] = None) -> Dict[str, Any]:
    """
    Clear all signals for new commit (simplified commit-based cleanup).
    
    This function removes all existing signals when a new commit is made,
    ensuring AI only sees signals for the current commit.
    
    Args:
        signal_directory: Path to signal directory
        max_age_hours: Ignored (kept for test compatibility)
        
    Returns:
        Dict[str, Any]: Cleanup results
    """
    metrics = get_mcp_metrics()
    
    result = {
        "success": False,
        "files_removed": 0,
        "files_preserved": 0,
        "total_size_freed": 0,
        "errors": 0
    }
    
    try:
        if metrics:
            metrics.record_counter("signal_cleanup_started", 1)
        
        # Validate directory safety
        is_safe, reason = validate_cleanup_safety(signal_directory)
        if not is_safe:
            if metrics:
                metrics.record_counter("signal_cleanup_safety_rejected", 1)
            result["error"] = f"Cleanup safety validation failed: {reason}"
            return result
        
        signal_dir = Path(signal_directory)
        if not signal_dir.exists():
            result["success"] = True  # No directory = already clean
            return result
        
        # Use thread lock for safety during concurrent operations
        with _cleanup_lock:
            # Remove all .json signal files
            for file_path in signal_dir.glob("*.json"):
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    result["files_removed"] += 1
                    result["total_size_freed"] += file_size
                    if metrics:
                        metrics.record_counter("signal_cleanup_file_removed", 1)
                except Exception as e:
                    result["errors"] += 1
                    if metrics:
                        metrics.record_counter("signal_cleanup_file_error", 1)
        
        result["success"] = True
        if metrics:
            metrics.record_counter("signal_cleanup_completed", 1)
            metrics.record_counter("signal_cleanup_files_removed", result["files_removed"])
        
    except Exception as e:
        result["error"] = str(e)
        if metrics:
            metrics.record_counter("signal_cleanup_error", 1)
    
    return result


# In-memory tracking for within-session processing
_processed_signals = set()

def mark_signal_processed(signal_file_path: str):
    """Mark a signal as processed (in-memory only)."""
    _processed_signals.add(os.path.basename(signal_file_path))


def is_signal_processed(signal_file_path: str) -> bool:
    """Check if signal has been processed this session."""
    return os.path.basename(signal_file_path) in _processed_signals


@trace_mcp_operation("signal_management.remove_processed_signals")
def remove_processed_signals(signal_directory: str) -> Dict[str, Any]:
    """
    Remove signals marked as processed.
    
    Args:
        signal_directory: Path to signal directory
        
    Returns:
        Dict[str, Any]: Removal results
    """
    metrics = get_mcp_metrics()
    
    result = {
        "processed_removed": 0,
        "unprocessed_preserved": 0,
        "orphaned_markers_cleaned": 0
    }
    
    try:
        signal_dir = Path(signal_directory)
        if not signal_dir.exists():
            return result
        
        with _cleanup_lock:
            for file_path in signal_dir.glob("*.json"):
                if is_signal_processed(str(file_path)):
                    file_path.unlink()
                    result["processed_removed"] += 1
                    if metrics:
                        metrics.record_counter("signal_processed_removed", 1)
                else:
                    result["unprocessed_preserved"] += 1
        
        if metrics:
            metrics.record_counter("signal_processed_cleanup_completed", 1)
            
    except Exception as e:
        if metrics:
            metrics.record_counter("signal_processed_cleanup_error", 1)
    
    return result


@trace_mcp_operation("signal_management.monitor_disk_space_and_cleanup")  
def monitor_disk_space_and_cleanup(signal_directory: str, min_free_mb: int = 100) -> Dict[str, Any]:
    """
    Monitor disk space and trigger cleanup if needed.
    
    Args:
        signal_directory: Path to signal directory
        min_free_mb: Minimum free space in MB before triggering cleanup
        
    Returns:
        Dict[str, Any]: Monitoring results
    """
    metrics = get_mcp_metrics()
    
    result = {
        "cleanup_triggered": False,
        "disk_space_before": 0,
        "disk_space_after": 0,
        "files_cleaned": 0
    }
    
    try:
        # Check disk space
        total, used, free = shutil.disk_usage(signal_directory)
        result["disk_space_before"] = free
        
        free_mb = free / (1024 * 1024)  # Convert to MB
        
        if free_mb < min_free_mb:
            # Low disk space - clear all signals
            result["cleanup_triggered"] = True
            
            if metrics:
                metrics.record_counter("signal_disk_space_cleanup_triggered", 1)
            
            cleanup_result = cleanup_old_signals(signal_directory)
            result["files_cleaned"] = cleanup_result.get("files_removed", 0)
            
            # Check space after cleanup
            total, used, free = shutil.disk_usage(signal_directory)
            result["disk_space_after"] = free
        
        if metrics:
            metrics.record_gauge("signal_disk_space_free_bytes", free)
            
    except Exception as e:
        if metrics:
            metrics.record_counter("signal_disk_space_monitoring_error", 1)
        result["error"] = str(e)
    
    return result


def cleanup_signals_for_new_commit(repo_path: str) -> Dict[str, Any]:
    """
    Clear all previous signals when a new commit is made.
    
    This ensures AI only sees signals for the current commit,
    maintaining a clean and predictable signal directory.
    
    Args:
        repo_path: Path to git repository
        
    Returns:
        Dict[str, Any]: Cleanup results
    """
    try:
        signal_directory = get_signal_directory_path(repo_path)
        
        # Clear all existing signals for the new commit
        cleanup_result = cleanup_old_signals(signal_directory)
        
        return {
            "previous_signals_cleared": cleanup_result.get("files_removed", 0),
            "success": cleanup_result.get("success", False)
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "previous_signals_cleared": 0,
            "success": False
        }


# Legacy function name for backward compatibility
def cleanup_signals_post_commit(repo_path: str) -> Dict[str, Any]:
    """Legacy function - use cleanup_signals_for_new_commit instead."""
    return cleanup_signals_for_new_commit(repo_path)