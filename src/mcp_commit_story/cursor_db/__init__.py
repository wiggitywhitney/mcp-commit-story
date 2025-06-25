"""
Cursor database integration package.

This package provides functionality for detecting, connecting to, and querying
Cursor's SQLite workspace databases across different platforms.
"""

from .platform import (
    PlatformType,
    CursorPathError,
    detect_platform,
    get_cursor_workspace_paths,
    validate_workspace_path
)
from .query_executor import execute_cursor_query
from .message_extraction import (
    extract_prompts_data,
    extract_generations_data
)

__all__ = [
    'PlatformType',
    'CursorPathError', 
    'detect_platform',
    'get_cursor_workspace_paths',
    'validate_workspace_path',
    'execute_cursor_query',
    'extract_prompts_data',
    'extract_generations_data'
] 