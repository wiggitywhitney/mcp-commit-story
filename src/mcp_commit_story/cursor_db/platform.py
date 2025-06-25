"""
Platform-specific path detection for Cursor SQLite workspaces.

This module provides cross-platform functionality to detect and validate
Cursor workspace database paths on Windows, macOS, Linux, and WSL.

Telemetry Behavior:
    All public functions are instrumented with OpenTelemetry tracing for 
    performance monitoring, error categorization, and operational metrics.
    
    Performance thresholds:
    - detect_platform(): 50ms
    - get_cursor_workspace_paths(): 100ms  
    - validate_workspace_path(): 200ms
    - find_valid_workspace_paths(): 1000ms
    - get_primary_workspace_path(): 200ms
    
    Error categories tracked:
    - platform_detection: Platform identification failures
    - path_operations: File system access issues
    - workspace_validation: Database validation problems
    
    Metrics collected:
    - Function duration and threshold breaches
    - Workspace count and validation success rates
    - Cache hit/miss ratios for path validation
    - Memory usage for large enumeration operations
    - Platform type and error subcategory distributions
"""

import os
import platform
import time
import sqlite3
from enum import Enum
from pathlib import Path
from typing import List, Union, Optional
import logging

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Import telemetry functionality
from ..telemetry import trace_mcp_operation, get_tracer, get_mcp_metrics

logger = logging.getLogger(__name__)

# Performance thresholds for telemetry (approved specifications)
TELEMETRY_THRESHOLDS = {
    "detect_platform": 50,
    "get_cursor_workspace_paths": 500,
    "validate_workspace_path": 100,
    "find_valid_workspace_paths": 1000,
    "get_primary_workspace_path": 200,
}

# Error categorization taxonomy (approved specifications)
ERROR_CATEGORIES = {
    "platform_detection": ["unsupported_platform", "detection_failure"],
    "path_operations": ["permission_denied", "path_not_found", "invalid_path_format"],
    "workspace_validation": ["no_valid_workspaces", "database_missing", "workspace_corrupted"]
}

# Simple cache for validation results to track cache hit/miss
_validation_cache = {}

class PlatformType(Enum):
    """Supported platform types for Cursor workspace detection."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"


class CursorPathError(Exception):
    """Exception raised when Cursor workspace path operations fail."""
    
    def __init__(self, message: str, error_category: str = "path_operations", error_subcategory: str = "path_not_found"):
        super().__init__(message)
        self.error_category = error_category
        self.error_subcategory = error_subcategory
        
        # Add telemetry context to exception
        tracer = get_tracer()
        current_span = tracer.start_span("cursor_path_error")
        if current_span:
            try:
                current_span.set_attribute('error.category', error_category)
                current_span.set_attribute('error.subcategory', error_subcategory)
                current_span.set_attribute('error.platform_type', platform.system())
            finally:
                current_span.end()


@trace_mcp_operation("detect_platform")
def detect_platform() -> PlatformType:
    """
    Detect the current platform type.
    
    Returns:
        PlatformType: The detected platform type
        
    Raises:
        CursorPathError: If platform is unsupported
    """
    start_time = time.time()
    tracer = get_tracer()
    
    with tracer.start_as_current_span("detect_platform_operation") as span:
        try:
            span.set_attribute('performance.threshold_ms', TELEMETRY_THRESHOLDS["detect_platform"])
            
            system = platform.system()
            
            if system == "Windows":
                result = PlatformType.WINDOWS
            elif system == "Darwin":
                result = PlatformType.MACOS
            elif system == "Linux":
                # Check if this is WSL by examining /proc/version
                try:
                    proc_version_path = Path("/proc/version")
                    if proc_version_path.exists():
                        version_content = proc_version_path.read_text().lower()
                        if "microsoft" in version_content or "wsl" in version_content:
                            result = PlatformType.WSL
                        else:
                            result = PlatformType.LINUX
                    else:
                        # Fall back to environment variable check
                        if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
                            result = PlatformType.WSL
                        else:
                            result = PlatformType.LINUX
                except (OSError, IOError) as e:
                    logger.debug(f"Could not read /proc/version for WSL detection: {e}")
                    # Fall back to environment variable check
                    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
                        result = PlatformType.WSL
                    else:
                        result = PlatformType.LINUX
            else:
                raise CursorPathError(
                    f"Unsupported platform: {system}",
                    error_category="platform_detection",
                    error_subcategory="unsupported_platform"
                )
            
            # Record telemetry attributes
            span.set_attribute('platform_type', result.value)
            
            # Check performance threshold
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > TELEMETRY_THRESHOLDS["detect_platform"]:
                span.set_attribute('performance.exceeded_threshold', True)
                span.set_attribute('performance.duration_ms', duration_ms)
            
            return result
            
        except Exception as e:
            span.set_attribute('error.category', getattr(e, 'error_category', 'platform_detection'))
            span.set_attribute('error.subcategory', getattr(e, 'error_subcategory', 'detection_failure'))
            raise


@trace_mcp_operation("get_cursor_workspace_paths")
def get_cursor_workspace_paths() -> List[Path]:
    """
    Get potential Cursor workspace database paths for the current platform.
    
    Priority order:
    1. Custom environment variable (CURSOR_WORKSPACE_PATH)
    2. Platform-specific default paths
    3. Additional fallback locations
    
    Returns:
        List[Path]: List of potential workspace paths to check
    """
    start_time = time.time()
    tracer = get_tracer()
    
    with tracer.start_as_current_span("get_cursor_workspace_paths_operation") as span:
        try:
            span.set_attribute('performance.threshold_ms', TELEMETRY_THRESHOLDS["get_cursor_workspace_paths"])
            
            # Track memory if available
            initial_memory_mb = None
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process()
                    initial_memory_mb = process.memory_info().rss / (1024 * 1024)
                except Exception:
                    pass
            
            paths = []
            
            # Priority 1: Custom environment variable
            custom_path = os.environ.get("CURSOR_WORKSPACE_PATH")
            if custom_path:
                paths.append(Path(custom_path))
            
            # Priority 2: Platform-specific defaults
            try:
                platform_type = detect_platform()
                platform_paths = _get_platform_default_paths(platform_type)
                paths.extend(platform_paths)
                span.set_attribute('platform_type', platform_type.value)
            except CursorPathError as e:
                logger.warning(f"Platform detection failed: {e}")
                span.set_attribute('error.category', 'platform_detection')
                span.set_attribute('error.subcategory', 'detection_failure')
            
            # Priority 3: Additional fallback locations (common alternative paths)
            fallback_paths = _get_fallback_paths()
            paths.extend(fallback_paths)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_paths = []
            for path in paths:
                if path not in seen:
                    seen.add(path)
                    unique_paths.append(path)
            
            # Record telemetry attributes
            span.set_attribute('workspace_count', len(unique_paths))
            
            # Check performance threshold
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > TELEMETRY_THRESHOLDS["get_cursor_workspace_paths"]:
                span.set_attribute('performance.exceeded_threshold', True)
                span.set_attribute('performance.duration_ms', duration_ms)
            
            # Track memory usage if available
            if PSUTIL_AVAILABLE and initial_memory_mb is not None:
                try:
                    process = psutil.Process()
                    final_memory_mb = process.memory_info().rss / (1024 * 1024)
                    memory_increase = final_memory_mb - initial_memory_mb
                    if memory_increase > 1.0:  # Only track significant increases
                        span.set_attribute('memory.increase_mb', memory_increase)
                except Exception:
                    pass
            
            return unique_paths
            
        except Exception as e:
            span.set_attribute('error.category', getattr(e, 'error_category', 'path_operations'))
            span.set_attribute('error.subcategory', getattr(e, 'error_subcategory', 'path_not_found'))
            raise


def _get_platform_default_paths(platform_type: PlatformType) -> List[Path]:
    """Get default workspace paths for a specific platform."""
    if platform_type == PlatformType.WINDOWS:
        return _get_windows_paths()
    elif platform_type == PlatformType.MACOS:
        return _get_macos_paths()
    elif platform_type == PlatformType.LINUX:
        return _get_linux_paths()
    elif platform_type == PlatformType.WSL:
        return _get_wsl_paths()
    else:
        return []


def _get_windows_paths() -> List[Path]:
    """Get Windows-specific Cursor workspace paths."""
    paths = []
    
    # Primary: APPDATA environment variable
    appdata = os.environ.get("APPDATA")
    if appdata:
        # Normalize path separators for cross-platform compatibility
        normalized_appdata = appdata.replace("\\", "/")
        paths.append(Path(normalized_appdata) / "Cursor" / "User" / "workspaceStorage")
    
    # Fallback: User profile with AppData
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        normalized_userprofile = userprofile.replace("\\", "/")
        paths.append(Path(normalized_userprofile) / "AppData" / "Roaming" / "Cursor" / "User" / "workspaceStorage")
    
    return paths


def _get_macos_paths() -> List[Path]:
    """Get macOS-specific Cursor workspace paths."""
    paths = []
    
    # Primary: User's Library/Application Support
    home = Path.home()
    paths.append(home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage")
    
    return paths


def _get_linux_paths() -> List[Path]:
    """Get Linux-specific Cursor workspace paths."""
    paths = []
    
    # Primary: XDG config directory
    home = Path.home()
    xdg_config = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
    paths.append(Path(xdg_config) / "Cursor" / "User" / "workspaceStorage")
    
    # Fallback: Direct .config path
    if xdg_config != str(home / ".config"):
        paths.append(home / ".config" / "Cursor" / "User" / "workspaceStorage")
    
    return paths


def _get_wsl_paths() -> List[Path]:
    """Get WSL-specific Cursor workspace paths."""
    paths = []
    
    # WSL typically mounts Windows drives under /mnt/c
    # Look for Windows user directories
    windows_users_paths = [
        Path("/mnt/c/Users"),
        Path("/mnt/C/Users")  # Case variation
    ]
    
    for users_path in windows_users_paths:
        if users_path.exists():
            # Find user directories
            try:
                for user_dir in users_path.iterdir():
                    if user_dir.is_dir():
                        cursor_path = user_dir / "AppData" / "Roaming" / "Cursor" / "User" / "workspaceStorage"
                        paths.append(cursor_path)
            except (OSError, PermissionError) as e:
                logger.debug(f"Could not enumerate user directories in {users_path}: {e}")
    
    # Also check Linux-style paths in case Cursor is installed in WSL
    paths.extend(_get_linux_paths())
    
    return paths


def _get_fallback_paths() -> List[Path]:
    """Get additional fallback paths for edge cases."""
    paths = []
    
    # Common alternative installation locations
    home = Path.home()
    
    # Portable installations
    paths.extend([
        home / "cursor-portable" / "User" / "workspaceStorage",
        home / "Cursor" / "User" / "workspaceStorage",
        Path("/opt/cursor/User/workspaceStorage"),  # Linux system-wide
        Path("/Applications/Cursor.app/Contents/Resources/User/workspaceStorage"),  # macOS app bundle
    ])
    
    return paths


@trace_mcp_operation("validate_workspace_path")
def validate_workspace_path(path: Union[str, Path, None]) -> bool:
    """
    Validate that a workspace path exists and is accessible.
    
    Args:
        path: Path to validate (can be string, Path object, or None)
        
    Returns:
        bool: True if path is valid and accessible, False otherwise
    """
    start_time = time.time()
    tracer = get_tracer()
    
    with tracer.start_as_current_span("validate_workspace_path_operation") as span:
        try:
            span.set_attribute('performance.threshold_ms', TELEMETRY_THRESHOLDS["validate_workspace_path"])
            
            if path is None:
                span.set_attribute('cache_hit', False)
                span.set_attribute('error.category', 'path_operations')
                span.set_attribute('error.subcategory', 'invalid_path_format')
                return False
            
            # Check cache first
            path_str = str(path)
            cache_key = path_str
            cache_hit = cache_key in _validation_cache
            span.set_attribute('cache_hit', cache_hit)
            
            if cache_hit:
                return _validation_cache[cache_key]
            
            try:
                path_obj = Path(path)
                
                # Check if path exists
                if not path_obj.exists():
                    result = False
                    span.set_attribute('error.category', 'path_operations')
                    span.set_attribute('error.subcategory', 'path_not_found')
                elif not path_obj.is_dir():
                    result = False
                    span.set_attribute('error.category', 'path_operations')
                    span.set_attribute('error.subcategory', 'invalid_path_format')
                elif not os.access(path_obj, os.R_OK):
                    result = False
                    span.set_attribute('error.category', 'path_operations')
                    span.set_attribute('error.subcategory', 'permission_denied')
                else:
                    # Basic validation passed: path exists, is directory, and is readable
                    result = True
                    
                    # Optional enhanced validation: check if it looks like a workspace directory
                    # This is informational only and won't cause validation to fail
                    try:
                        # Look for .db files or workspace indicators
                        db_files = list(path_obj.glob("*.db"))
                        if db_files:
                            span.set_attribute('workspace.has_databases', True)
                            span.set_attribute('workspace.database_count', len(db_files))
                            
                            # Try to validate one of the databases for telemetry
                            valid_dbs = 0
                            for db_file in db_files:
                                try:
                                    with sqlite3.connect(str(db_file), timeout=1.0) as conn:
                                        cursor = conn.cursor()
                                        # Check for workspace-like tables
                                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                                        if cursor.fetchone():
                                            valid_dbs += 1
                                except sqlite3.Error:
                                    continue
                            span.set_attribute('workspace.valid_database_count', valid_dbs)
                        else:
                            span.set_attribute('workspace.has_databases', False)
                            span.set_attribute('workspace.database_count', 0)
                    except Exception:
                        # Enhanced validation failed, but basic validation passed
                        span.set_attribute('workspace.enhanced_validation_failed', True)
                
                # Cache the result
                _validation_cache[cache_key] = result
                
                # Check performance threshold
                duration_ms = (time.time() - start_time) * 1000
                if duration_ms > TELEMETRY_THRESHOLDS["validate_workspace_path"]:
                    span.set_attribute('performance.exceeded_threshold', True)
                    span.set_attribute('performance.duration_ms', duration_ms)
                
                return result
                
            except (OSError, ValueError, TypeError) as e:
                logger.debug(f"Path validation failed for {path}: {e}")
                span.set_attribute('error.category', 'path_operations')
                span.set_attribute('error.subcategory', 'path_not_found')
                result = False
                _validation_cache[cache_key] = result
                return result
                
        except Exception as e:
            span.set_attribute('error.category', getattr(e, 'error_category', 'path_operations'))
            span.set_attribute('error.subcategory', getattr(e, 'error_subcategory', 'path_not_found'))
            raise


@trace_mcp_operation("find_valid_workspace_paths")
def find_valid_workspace_paths() -> List[Path]:
    """
    Find all valid (existing and accessible) Cursor workspace paths.
    
    Returns:
        List[Path]: List of validated workspace paths
    """
    start_time = time.time()
    tracer = get_tracer()
    
    with tracer.start_as_current_span("find_valid_workspace_paths_operation") as span:
        try:
            span.set_attribute('performance.threshold_ms', TELEMETRY_THRESHOLDS["find_valid_workspace_paths"])
            
            # Track memory usage for large operations
            initial_memory_mb = None
            peak_memory_mb = None
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process()
                    initial_memory_mb = process.memory_info().rss / (1024 * 1024)
                    peak_memory_mb = initial_memory_mb
                except Exception:
                    pass
            
            potential_paths = get_cursor_workspace_paths()
            valid_paths = []
            
            for i, path in enumerate(potential_paths):
                if validate_workspace_path(path):
                    valid_paths.append(path)
                    logger.debug(f"Found valid workspace path: {path}")
                else:
                    logger.debug(f"Invalid workspace path: {path}")
                
                # Track peak memory usage during large enumerations
                if PSUTIL_AVAILABLE and i % 10 == 0:  # Check every 10 paths
                    try:
                        process = psutil.Process()
                        current_memory_mb = process.memory_info().rss / (1024 * 1024)
                        if current_memory_mb > peak_memory_mb:
                            peak_memory_mb = current_memory_mb
                    except Exception:
                        pass
            
            # Record telemetry attributes
            span.set_attribute('workspace_count', len(potential_paths))
            span.set_attribute('valid_workspace_count', len(valid_paths))
            
            # Record memory usage metrics
            if PSUTIL_AVAILABLE and initial_memory_mb is not None and peak_memory_mb is not None:
                span.set_attribute('memory.peak_usage_mb', peak_memory_mb)
                memory_increase = peak_memory_mb - initial_memory_mb
                if memory_increase > 1.0:
                    span.set_attribute('memory.increase_mb', memory_increase)
            
            # Check performance threshold
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > TELEMETRY_THRESHOLDS["find_valid_workspace_paths"]:
                span.set_attribute('performance.exceeded_threshold', True)
                span.set_attribute('performance.duration_ms', duration_ms)
            
            # Check if no valid workspaces found
            if not valid_paths:
                span.set_attribute('error.category', 'workspace_validation')
                span.set_attribute('error.subcategory', 'no_valid_workspaces')
            
            return valid_paths
            
        except Exception as e:
            span.set_attribute('error.category', getattr(e, 'error_category', 'workspace_validation'))
            span.set_attribute('error.subcategory', getattr(e, 'error_subcategory', 'no_valid_workspaces'))
            raise


@trace_mcp_operation("get_primary_workspace_path")
def get_primary_workspace_path() -> Optional[Path]:
    """
    Get the primary (first valid) Cursor workspace path.
    
    Returns:
        Optional[Path]: The primary workspace path, or None if none found
    """
    start_time = time.time()
    tracer = get_tracer()
    
    with tracer.start_as_current_span("get_primary_workspace_path_operation") as span:
        try:
            span.set_attribute('performance.threshold_ms', TELEMETRY_THRESHOLDS["get_primary_workspace_path"])
            
            valid_paths = find_valid_workspace_paths()
            result = valid_paths[0] if valid_paths else None
            
            # Record telemetry attributes
            span.set_attribute('workspace_count', len(valid_paths))
            span.set_attribute('primary_found', result is not None)
            
            # Check performance threshold
            duration_ms = (time.time() - start_time) * 1000
            if duration_ms > TELEMETRY_THRESHOLDS["get_primary_workspace_path"]:
                span.set_attribute('performance.exceeded_threshold', True)
                span.set_attribute('performance.duration_ms', duration_ms)
            
            return result
            
        except Exception as e:
            span.set_attribute('error.category', getattr(e, 'error_category', 'workspace_validation'))
            span.set_attribute('error.subcategory', getattr(e, 'error_subcategory', 'no_valid_workspaces'))
            raise 