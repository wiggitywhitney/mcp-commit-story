"""
Workspace detection module for Cursor chat databases.

Implements fuzzy matching workspace detection strategy that finds the correct
Cursor workspace database based on git repository path using:
1. Git remote URL matching (highest confidence)
2. Folder path matching (medium confidence) 
3. Folder name similarity (lowest confidence)
4. Fallback to most recently modified workspace

Follows approved design decisions with comprehensive telemetry instrumentation.
"""

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Tuple, Union

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .exceptions import CursorDatabaseNotFoundError
from .platform import get_cursor_workspace_paths
from ..telemetry import trace_mcp_operation, get_mcp_metrics, PERFORMANCE_THRESHOLDS

logger = logging.getLogger(__name__)

# Configuration constants
CONFIDENCE_THRESHOLD = 0.8
WORKSPACE_DETECTION_THRESHOLD_MS = 200.0


@dataclass
class WorkspaceMatch:
    """Represents a potential workspace match with confidence score."""
    path: Path
    confidence: float
    match_type: str  # "git_remote", "folder_path", "folder_name", "most_recent"
    workspace_folder: str
    git_remote: Optional[str] = None


class WorkspaceDetectionError(Exception):
    """Exception raised when workspace detection fails."""
    
    def __init__(self, message: str, repo_path: Optional[str] = None, 
                 candidates_scanned: Optional[int] = None, 
                 fallback_attempted: Optional[bool] = None):
        super().__init__(message)
        self.repo_path = repo_path
        self.candidates_scanned = candidates_scanned
        self.fallback_attempted = fallback_attempted


@trace_mcp_operation("cursor_db.detect_workspace_for_repo")
def detect_workspace_for_repo(repo_path: Union[str, Path]) -> WorkspaceMatch:
    """
    Detect the correct Cursor workspace database for a git repository.
    
    Uses fuzzy matching strategy with multiple approaches:
    1. Git remote URL matching (strongest signal - survives repo moves)
    2. Folder path matching (handles case where repo hasn't moved)
    3. Project/folder name similarity (last resort before fallback)
    4. Fallback to most recently modified workspace
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        WorkspaceMatch object containing the detected workspace info
        
    Raises:
        WorkspaceDetectionError: When no suitable workspace can be found
        
    Telemetry Attributes:
        - repo_path: The repository path being analyzed
        - detection_strategy: Which strategy succeeded
        - candidates_found: Number of potential workspaces scanned
        - match_confidence: 0.0-1.0 confidence score
        - match_type: Type of match found
        - fallback_used: Whether fallback strategy was used
        - selected_workspace_path: Final selected workspace path
    """
    span = trace.get_current_span()
    start_time = time.time()
    repo_path = Path(repo_path)
    
    # Set initial telemetry attributes
    span.set_attribute("repo_path", str(repo_path))
    span.set_attribute("fallback_used", False)
    
    # Initialize metrics tracking
    metrics = get_mcp_metrics()
    detection_strategy = "unknown"
    success = False
    
    # Validate repository path exists
    if not repo_path.exists():
        error_msg = f"Repository path does not exist: {repo_path}"
        detection_strategy = "invalid_path"
        span.set_attribute("error.category", "workspace_detection")
        span.set_attribute("error.subcategory", "invalid_repo_path")
        span.set_status(Status(StatusCode.ERROR, error_msg))
        
        # Record failure metrics
        _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
        raise WorkspaceDetectionError(error_msg, repo_path=str(repo_path))
    
    try:
        # Scan workspace directories for potential matches
        logger.info(f"Scanning workspaces for repository: {repo_path}")
        candidates = _scan_workspace_directories(str(repo_path))
        
        span.set_attribute("candidates_found", len(candidates))
        
        if not candidates:
            # No candidates found, try fallback
            logger.warning("No workspace candidates found, trying fallback strategy")
            span.set_attribute("fallback_used", True)
            
            fallback_workspace = _get_most_recent_workspace()
            if fallback_workspace:
                detection_strategy = "most_recent"
                success = True
                span.set_attribute("detection_strategy", detection_strategy)
                span.set_attribute("match_confidence", fallback_workspace.confidence)
                span.set_attribute("match_type", fallback_workspace.match_type)
                span.set_attribute("selected_workspace_path", str(fallback_workspace.path))
                logger.info(f"Using fallback workspace: {fallback_workspace.path}")
                
                # Record successful fallback metrics
                _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
                return fallback_workspace
            else:
                error_msg = "No Cursor workspaces found"
                detection_strategy = "not_found"
                span.set_attribute("error.category", "workspace_detection")
                span.set_attribute("error.subcategory", "no_workspaces_found")
                span.set_status(Status(StatusCode.ERROR, error_msg))
                
                # Record failure metrics
                _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
                raise WorkspaceDetectionError(
                    error_msg, 
                    repo_path=str(repo_path),
                    candidates_scanned=0,
                    fallback_attempted=True
                )
        
        # Find best match above confidence threshold
        best_match = candidates[0]  # Already sorted by confidence
        
        if best_match.confidence >= CONFIDENCE_THRESHOLD:
            # Good match found
            detection_strategy = "workspace_json_match"
            success = True
            span.set_attribute("detection_strategy", detection_strategy)
            span.set_attribute("match_confidence", best_match.confidence)
            span.set_attribute("match_type", best_match.match_type)
            span.set_attribute("selected_workspace_path", str(best_match.path))
            logger.info(f"Found good workspace match: {best_match.path} (confidence: {best_match.confidence:.2f})")
            
            # Record successful metrics
            _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
            return best_match
        else:
            # No good matches, use fallback
            logger.warning(f"Best match confidence {best_match.confidence:.2f} below threshold {CONFIDENCE_THRESHOLD}")
            span.set_attribute("fallback_used", True)
            
            fallback_workspace = _get_most_recent_workspace()
            if fallback_workspace:
                detection_strategy = "most_recent"
                success = True
                span.set_attribute("detection_strategy", detection_strategy)
                span.set_attribute("match_confidence", fallback_workspace.confidence)
                span.set_attribute("match_type", fallback_workspace.match_type)
                span.set_attribute("selected_workspace_path", str(fallback_workspace.path))
                logger.warning(f"Using fallback workspace: {fallback_workspace.path}")
                
                # Record successful fallback metrics
                _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
                return fallback_workspace
            else:
                error_msg = f"No suitable workspace match found (best confidence: {best_match.confidence:.2f})"
                detection_strategy = "low_confidence"
                span.set_attribute("error.category", "workspace_detection")
                span.set_attribute("error.subcategory", "low_confidence_matches")
                span.set_status(Status(StatusCode.ERROR, error_msg))
                
                # Record failure metrics
                _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
                raise WorkspaceDetectionError(
                    error_msg,
                    repo_path=str(repo_path),
                    candidates_scanned=len(candidates),
                    fallback_attempted=True
                )
                
    except Exception as e:
        if isinstance(e, WorkspaceDetectionError):
            raise
        
        # Wrap unexpected errors
        error_msg = f"Failed to scan workspace directories: {e}"
        detection_strategy = "scanning_failure"
        span.set_attribute("error.category", "workspace_detection")
        span.set_attribute("error.subcategory", "scanning_failure")
        span.set_status(Status(StatusCode.ERROR, error_msg))
        logger.error(error_msg, exc_info=True)
        
        # Record failure metrics
        _record_workspace_detection_metrics(metrics, start_time, detection_strategy, success)
        raise WorkspaceDetectionError(
            error_msg,
            repo_path=str(repo_path),
            fallback_attempted=False
        ) from e


def _scan_workspace_directories(repo_path: str) -> List[WorkspaceMatch]:
    """
    Scan all workspace directories and find potential matches.
    
    Args:
        repo_path: Repository path to match against
        
    Returns:
        List of WorkspaceMatch objects sorted by confidence (highest first)
    """
    try:
        potential_paths = get_cursor_workspace_paths()
        # Find the first existing workspaceStorage path
        storage_path = None
        for path in potential_paths:
            if path.exists():
                storage_path = path
                break
        
        if not storage_path:
            logger.warning("No existing workspace storage paths found")
            return []
    except Exception as e:
        logger.error(f"Failed to get cursor workspace paths: {e}")
        return []
    
    # Get git remote URLs for the repository
    repo_git_remotes = _get_git_remote_urls(repo_path)
    
    matches = []
    
    # Scan all workspace hash directories
    for workspace_dir in storage_path.iterdir():
        if not workspace_dir.is_dir():
            continue
            
        # Check for workspace.json file
        workspace_json = workspace_dir / "workspace.json"
        if not workspace_json.exists():
            continue
            
        # Check for state.vscdb file
        db_file = workspace_dir / "state.vscdb"
        if not db_file.exists():
            continue
            
        try:
            # Extract workspace information
            workspace_info = _extract_workspace_info(workspace_json)
            if not workspace_info:
                continue
                
            # Calculate match confidence
            confidence, match_type = _calculate_match_confidence(
                repo_path, repo_git_remotes, workspace_info
            )
            
            # Create match object
            match = WorkspaceMatch(
                path=db_file,
                confidence=confidence,
                match_type=match_type,
                workspace_folder=workspace_info.get("folder", ""),
                git_remote=workspace_info.get("git_remote")
            )
            matches.append(match)
            
        except Exception as e:
            logger.warning(f"Error processing workspace {workspace_dir}: {e}")
            continue
    
    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x.confidence, reverse=True)
    return matches


def _extract_workspace_info(workspace_json_path: Path) -> Optional[dict]:
    """
    Extract workspace information from workspace.json file.
    
    Args:
        workspace_json_path: Path to workspace.json file
        
    Returns:
        Dictionary with workspace information or None if extraction fails
    """
    try:
        with open(workspace_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return {
            "folder": data.get("folder", ""),
            # Note: git_remote is not typically stored in workspace.json
            # but we include it in the structure for consistency
            "git_remote": None
        }
        
    except (json.JSONDecodeError, OSError, KeyError) as e:
        logger.warning(f"Failed to parse workspace.json {workspace_json_path}: {e}")
        return None


def _calculate_match_confidence(repo_path: str, repo_git_remotes: List[str], 
                               workspace_info: dict) -> Tuple[float, str]:
    """
    Calculate confidence score for a workspace match.
    
    Args:
        repo_path: Repository path being matched
        repo_git_remotes: List of git remote URLs for the repository
        workspace_info: Workspace information extracted from workspace.json
        
    Returns:
        Tuple of (confidence_score, match_type)
    """
    workspace_folder = workspace_info.get("folder", "")
    
    # Remove file:// prefix if present
    if workspace_folder.startswith("file://"):
        workspace_folder = workspace_folder[7:]
    
    # 1. Git remote URL matching (highest confidence: 0.95-1.0)
    workspace_git_remote = workspace_info.get("git_remote")
    if workspace_git_remote and repo_git_remotes:
        for repo_remote in repo_git_remotes:
            if workspace_git_remote == repo_remote:
                return 1.0, "git_remote"
            # Check for similar remotes (different protocols, etc.)
            if _normalize_git_url(workspace_git_remote) == _normalize_git_url(repo_remote):
                return 0.95, "git_remote"
    
    # 2. Folder path matching (medium confidence: 0.8-0.9)
    repo_path_normalized = os.path.normpath(repo_path)
    workspace_path_normalized = os.path.normpath(workspace_folder)
    
    if repo_path_normalized == workspace_path_normalized:
        return 0.85, "folder_path"
    
    # Check if one is a symlink or different case
    try:
        if os.path.realpath(repo_path_normalized) == os.path.realpath(workspace_path_normalized):
            return 0.82, "folder_path"
    except OSError:
        pass  # Ignore path resolution errors
    
    # 3. Folder name similarity (lower confidence: 0.5-0.8)
    repo_name = os.path.basename(repo_path_normalized)
    workspace_name = os.path.basename(workspace_path_normalized)
    
    # Calculate similarity using sequence matcher
    similarity = SequenceMatcher(None, repo_name.lower(), workspace_name.lower()).ratio()
    
    # Convert similarity to confidence score
    if similarity >= 0.9:
        confidence = 0.75
    elif similarity >= 0.8:
        confidence = 0.7
    elif similarity >= 0.6:
        confidence = 0.6
    else:
        confidence = similarity * 0.5  # Lower confidence for poor matches
    
    return confidence, "folder_name"


def _normalize_git_url(url: str) -> str:
    """
    Normalize git URL for comparison.
    
    Args:
        url: Git URL to normalize
        
    Returns:
        Normalized URL string
    """
    # Remove .git suffix
    if url.endswith('.git'):
        url = url[:-4]
    
    # Convert SSH to HTTPS format for comparison
    if url.startswith('git@'):
        # Convert git@github.com:user/repo to https://github.com/user/repo
        parts = url.split(':')
        if len(parts) == 2:
            host_part = parts[0].replace('git@', '')
            repo_part = parts[1]
            url = f"https://{host_part}/{repo_part}"
    
    return url.lower().strip('/')


def _get_git_remote_urls(repo_path: str) -> List[str]:
    """
    Get git remote URLs for a repository.
    
    Args:
        repo_path: Path to git repository
        
    Returns:
        List of remote URLs
    """
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.debug(f"Git remote command failed: {result.stderr}")
            return []
        
        # Parse remote URLs
        remotes = set()
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                # Format: "origin	https://github.com/user/repo.git (fetch)"
                parts = line.split('\t')
                if len(parts) >= 2:
                    url_part = parts[1].split(' ')[0]  # Remove (fetch)/(push)
                    remotes.add(url_part)
        
        return list(remotes)
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        logger.debug(f"Failed to get git remotes for {repo_path}: {e}")
        return []


def _get_most_recent_workspace() -> Optional[WorkspaceMatch]:
    """
    Get the most recently modified workspace as fallback.
    
    Returns:
        WorkspaceMatch for the most recent workspace or None if none found
    """
    try:
        potential_paths = get_cursor_workspace_paths()
        # Find the first existing workspaceStorage path
        storage_path = None
        for path in potential_paths:
            if path.exists():
                storage_path = path
                break
        
        if not storage_path:
            return None
    except Exception as e:
        logger.error(f"Failed to get cursor workspace paths: {e}")
        return None
    
    most_recent_db = None
    most_recent_time = 0
    
    # Find most recently modified state.vscdb file
    for workspace_dir in storage_path.iterdir():
        if not workspace_dir.is_dir():
            continue
            
        db_file = workspace_dir / "state.vscdb"
        if not db_file.exists():
            continue
            
        try:
            mtime = db_file.stat().st_mtime
            if mtime > most_recent_time:
                most_recent_time = mtime
                most_recent_db = db_file
        except OSError:
            continue
    
    if most_recent_db:
        # Try to get workspace folder if available
        workspace_json = most_recent_db.parent / "workspace.json"
        workspace_folder = ""
        if workspace_json.exists():
            workspace_info = _extract_workspace_info(workspace_json)
            if workspace_info:
                workspace_folder = workspace_info.get("folder", "")
        
        return WorkspaceMatch(
            path=most_recent_db,
            confidence=0.0,  # Fallback has no confidence
            match_type="most_recent",
            workspace_folder=workspace_folder,
            git_remote=None
        )
    
    return None


def _record_workspace_detection_metrics(metrics, start_time: float, detection_strategy: str, success: bool):
    """
    Record metrics for workspace detection operations.
    
    Args:
        metrics: MCP metrics instance
        start_time: Operation start time
        detection_strategy: Strategy that was used/attempted
        success: Whether the operation succeeded
    """
    if not metrics:
        return
        
    duration_seconds = time.time() - start_time
    duration_ms = duration_seconds * 1000
    
    # Record counter metric
    metrics.record_counter(
        "mcp_workspace_detection_total",
        1,
        attributes={
            "strategy": detection_strategy,
            "success": str(success).lower()
        }
    )
    
    # Record duration histogram
    metrics.record_histogram(
        "mcp_workspace_detection_duration_seconds",
        duration_seconds,
        attributes={"strategy": detection_strategy}
    )
    
    # Check performance threshold
    span = trace.get_current_span()
    span.set_attribute("duration_ms", duration_ms)
    span.set_attribute("performance.threshold_ms", WORKSPACE_DETECTION_THRESHOLD_MS)
    
    if duration_ms > WORKSPACE_DETECTION_THRESHOLD_MS:
        span.set_attribute("performance.threshold_exceeded", True)
        logger.warning(
            f"Workspace detection took {duration_ms:.1f}ms "
            f"(>{WORKSPACE_DETECTION_THRESHOLD_MS:.0f}ms threshold) "
            f"using strategy: {detection_strategy}"
        )