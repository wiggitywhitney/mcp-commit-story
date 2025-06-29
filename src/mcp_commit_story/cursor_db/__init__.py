"""
Cursor database integration package.

This package provides functionality for detecting, connecting to, and querying
Cursor's SQLite workspace databases across different platforms.
"""

import os
import time
from datetime import datetime
from typing import Dict, Optional, Any

from .platform import (
    PlatformType,
    CursorPathError,
    detect_platform,
    get_cursor_workspace_paths,
    validate_workspace_path,
    get_primary_workspace_path
)
from .query_executor import execute_cursor_query
from .message_extraction import (
    extract_prompts_data,
    extract_generations_data
)
from .message_reconstruction import reconstruct_chat_history
from .message_limiting import (
    limit_chat_messages,
    DEFAULT_MAX_HUMAN_MESSAGES,
    DEFAULT_MAX_AI_MESSAGES
)
from ..telemetry import trace_mcp_operation
from .multiple_database_discovery import (
    discover_all_cursor_databases, 
    get_recent_databases, 
    extract_from_multiple_databases
)

@trace_mcp_operation("cursor_db.query_chat_database")
def query_cursor_chat_database() -> Dict[str, Any]:
    """
    Query cursor chat database to get complete chat history with workspace metadata.
    
    Scans the workspace storage directory for hash subdirectories containing
    state.vscdb files, filters to recent ones (48h), and extracts complete chat history.
    
    Returns:
        Dict containing:
        - workspace_info: Basic workspace and database metadata
        - chat_history: List of reconstructed chat messages
        
    Raises:
        Exception: If critical database operations fail
    """
    try:
        # Step 1: Get workspace storage path
        workspace_storage_path = get_primary_workspace_path()
        if not workspace_storage_path:
            return {
                "workspace_info": {
                    "workspace_path": None,
                    "database_path": None,
                    "total_messages": 0,
                    "last_updated": None
                },
                "chat_history": []
            }
        
        # Step 2: Directly scan workspace storage for hash subdirectories with databases
        all_databases = []
        for item in os.listdir(workspace_storage_path):
            item_path = os.path.join(workspace_storage_path, item)
            if os.path.isdir(item_path):
                db_path = os.path.join(item_path, 'state.vscdb')
                if os.path.exists(db_path):
                    all_databases.append(db_path)
        
        if not all_databases:
            return {
                "workspace_info": {
                    "workspace_path": str(workspace_storage_path),
                    "database_path": None,
                    "total_messages": 0,
                    "last_updated": None
                },
                "chat_history": []
            }
        
        # Step 3: Filter to recent databases (48-hour window)
        recent_databases = get_recent_databases(all_databases)
        if not recent_databases:
            return {
                "workspace_info": {
                    "workspace_path": str(workspace_storage_path),
                    "database_path": None,
                    "total_messages": 0,
                    "last_updated": None
                },
                "chat_history": []
            }
        
        # Step 4: Extract data from recent databases
        extraction_results = extract_from_multiple_databases(recent_databases)
        
        # Always report the first recent database path, even if extraction failed
        # (maintains backward compatibility with corrupted database handling)
        primary_db_path = recent_databases[0] if recent_databases else None
        
        if not extraction_results:
            return {
                "workspace_info": {
                    "workspace_path": str(workspace_storage_path),
                    "database_path": primary_db_path,
                    "total_messages": 0,
                    "last_updated": None
                },
                "chat_history": []
            }
        
        # Step 5: Combine all prompts and generations
        all_prompts = []
        all_generations = []
        for result in extraction_results:
            all_prompts.extend(result.get("prompts", []))
            all_generations.extend(result.get("generations", []))
        
        # Step 6: Reconstruct chat history
        chat_history = reconstruct_chat_history(all_prompts, all_generations)
        
        # Step 7: Build response with metadata
        return {
            "workspace_info": {
                "workspace_path": str(workspace_storage_path),
                "database_path": primary_db_path,  # Primary database
                "total_messages": len(chat_history.get("messages", [])) if isinstance(chat_history, dict) else len(chat_history),
                "last_updated": datetime.now().isoformat()
            },
            "chat_history": chat_history
        }
        
    except Exception as e:
        # Graceful error handling - return empty but valid structure
        return {
            "workspace_info": {
                "workspace_path": str(workspace_storage_path) if 'workspace_storage_path' in locals() else None,
                "database_path": None,
                "total_messages": 0,
                "last_updated": None
            },
            "chat_history": []
        }

__all__ = [
    'PlatformType',
    'CursorPathError', 
    'detect_platform',
    'get_cursor_workspace_paths',
    'validate_workspace_path',
    'execute_cursor_query',
    'extract_prompts_data',
    'extract_generations_data',
    'reconstruct_chat_history',
    'limit_chat_messages',
    'DEFAULT_MAX_HUMAN_MESSAGES',
    'DEFAULT_MAX_AI_MESSAGES',
    'query_cursor_chat_database',
    'get_primary_workspace_path',
    'discover_all_cursor_databases',
    'get_recent_databases',
    'extract_from_multiple_databases'
] 