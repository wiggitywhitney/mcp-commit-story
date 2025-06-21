"""
Platform-specific path detection for Cursor SQLite workspaces.

This module provides cross-platform functionality to detect and validate
Cursor workspace database paths on Windows, macOS, Linux, and WSL.
"""

import os
import platform
from enum import Enum
from pathlib import Path
from typing import List, Union, Optional
import logging

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """Supported platform types for Cursor workspace detection."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"


class CursorPathError(Exception):
    """Exception raised when Cursor workspace path operations fail."""
    pass


def detect_platform() -> PlatformType:
    """
    Detect the current platform type.
    
    Returns:
        PlatformType: The detected platform type
        
    Raises:
        CursorPathError: If platform is unsupported
    """
    system = platform.system()
    
    if system == "Windows":
        return PlatformType.WINDOWS
    elif system == "Darwin":
        return PlatformType.MACOS
    elif system == "Linux":
        # Check if this is WSL by examining /proc/version
        try:
            proc_version_path = Path("/proc/version")
            if proc_version_path.exists():
                version_content = proc_version_path.read_text().lower()
                if "microsoft" in version_content or "wsl" in version_content:
                    return PlatformType.WSL
        except (OSError, IOError) as e:
            logger.debug(f"Could not read /proc/version for WSL detection: {e}")
            # Fall back to environment variable check
            if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
                return PlatformType.WSL
        
        return PlatformType.LINUX
    else:
        raise CursorPathError(f"Unsupported platform: {system}")


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
    except CursorPathError as e:
        logger.warning(f"Platform detection failed: {e}")
    
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
    
    return unique_paths


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


def validate_workspace_path(path: Union[str, Path, None]) -> bool:
    """
    Validate that a workspace path exists and is accessible.
    
    Args:
        path: Path to validate (can be string, Path object, or None)
        
    Returns:
        bool: True if path is valid and accessible, False otherwise
    """
    if path is None:
        return False
    
    try:
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists():
            return False
        
        # Check if it's a directory
        if not path_obj.is_dir():
            return False
        
        # Check if we can read the directory
        if not os.access(path_obj, os.R_OK):
            return False
        
        return True
        
    except (OSError, ValueError, TypeError) as e:
        logger.debug(f"Path validation failed for {path}: {e}")
        return False


def find_valid_workspace_paths() -> List[Path]:
    """
    Find all valid (existing and accessible) Cursor workspace paths.
    
    Returns:
        List[Path]: List of validated workspace paths
    """
    potential_paths = get_cursor_workspace_paths()
    valid_paths = []
    
    for path in potential_paths:
        if validate_workspace_path(path):
            valid_paths.append(path)
            logger.debug(f"Found valid workspace path: {path}")
        else:
            logger.debug(f"Invalid workspace path: {path}")
    
    return valid_paths


def get_primary_workspace_path() -> Optional[Path]:
    """
    Get the primary (first valid) Cursor workspace path.
    
    Returns:
        Optional[Path]: The primary workspace path, or None if none found
    """
    valid_paths = find_valid_workspace_paths()
    return valid_paths[0] if valid_paths else None 