"""
Tests for the high-level query_cursor_chat_database function.

This module tests the main user-facing API function that orchestrates
all cursor_db components to provide complete chat history with workspace metadata.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import os
from pathlib import Path

from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.cursor_db.exceptions import CursorDatabaseError


class TestQueryCursorChatDatabaseSuccess:
    """Test successful data retrieval scenarios."""
    
    def test_successful_query_with_workspace_info(self):
        """Test successful query returns proper workspace_info and chat_history structure."""
        # Mock the functions where they're imported in __init__.py
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('mcp_commit_story.cursor_db.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.extract_generations_data') as mock_generations, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getmtime') as mock_getmtime:
            
            # Setup mocks
            mock_workspace.return_value = Path("/test/workspace")
            mock_exists.return_value = True
            mock_prompts.return_value = [{"id": 1, "content": "test prompt"}]
            mock_generations.return_value = [{"id": 1, "content": "test response"}]
            mock_reconstruct.return_value = [{"role": "user", "content": "test prompt"}]
            mock_getmtime.return_value = 1640995200.0  # 2022-01-01 00:00:00
            
            result = query_cursor_chat_database()
            
            # Verify structure
            assert "workspace_info" in result
            assert "chat_history" in result
            
            # Verify workspace_info content
            workspace_info = result["workspace_info"]
            assert workspace_info["workspace_path"] == "/test/workspace"
            assert workspace_info["database_path"] == "/test/workspace/.cursor/state.vscdb"
            assert workspace_info["total_messages"] == 1
            assert "last_updated" in workspace_info
            
            # Verify chat_history content
            assert result["chat_history"] == [{"role": "user", "content": "test prompt"}]
    
    def test_component_orchestration_flow(self):
        """Test that all components are called in correct order."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('mcp_commit_story.cursor_db.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.extract_generations_data') as mock_generations, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getmtime') as mock_getmtime:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_exists.return_value = True
            mock_prompts.return_value = [{"id": 1}]
            mock_generations.return_value = [{"id": 1}]
            mock_reconstruct.return_value = [{"role": "user"}]
            mock_getmtime.return_value = 1640995200.0
            
            result = query_cursor_chat_database()
            
            # Verify components were called in order
            mock_workspace.assert_called_once()
            mock_prompts.assert_called_once_with("/test/workspace/.cursor/state.vscdb")
            mock_generations.assert_called_once_with("/test/workspace/.cursor/state.vscdb")
            mock_reconstruct.assert_called_once()


class TestQueryCursorChatDatabaseErrorHandling:
    """Test error handling scenarios."""
    
    def test_missing_workspace_graceful_handling(self):
        """Test graceful handling when workspace cannot be detected."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
            mock_workspace.return_value = None
            
            result = query_cursor_chat_database()
            
            # Verify graceful error structure
            assert result["workspace_info"]["workspace_path"] is None
            assert result["workspace_info"]["database_path"] is None
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []
            
    def test_missing_database_graceful_handling(self):
        """Test graceful handling when database file doesn't exist."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('os.path.exists') as mock_exists:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_exists.return_value = False
            
            result = query_cursor_chat_database()
            
            # Verify graceful error structure
            assert result["workspace_info"]["workspace_path"] == "/test/workspace"
            assert result["workspace_info"]["database_path"] == "/test/workspace/.cursor/state.vscdb"
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []
    
    def test_empty_database_handling(self):
        """Test handling of database with no chat data."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('mcp_commit_story.cursor_db.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.extract_generations_data') as mock_generations, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getmtime') as mock_getmtime:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_exists.return_value = True
            mock_prompts.return_value = []
            mock_generations.return_value = []
            mock_reconstruct.return_value = []
            mock_getmtime.return_value = 1640995200.0
            
            result = query_cursor_chat_database()
            
            # Verify empty but valid structure
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []
            
    def test_exception_graceful_handling(self):
        """Test that exceptions are handled gracefully."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('mcp_commit_story.cursor_db.extract_prompts_data') as mock_prompts, \
             patch('os.path.exists') as mock_exists:
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_exists.return_value = True
            mock_prompts.side_effect = Exception("Database connection failed")
            
            result = query_cursor_chat_database()
            
            # Verify graceful error return
            assert result["workspace_info"]["total_messages"] == 0
            assert result["chat_history"] == []


class TestQueryCursorChatDatabaseIntegration:
    """Test integration scenarios with component orchestration."""
            
    def test_large_chat_history_performance(self):
        """Test performance with large chat histories."""
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace, \
             patch('mcp_commit_story.cursor_db.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.extract_generations_data') as mock_generations, \
             patch('mcp_commit_story.cursor_db.reconstruct_chat_history') as mock_reconstruct, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getmtime') as mock_getmtime:
            
            # Mock large dataset
            large_prompts = [{"id": i, "content": f"prompt {i}"} for i in range(1000)]
            large_generations = [{"id": i, "content": f"response {i}"} for i in range(1000)]
            large_history = [{"role": "user", "content": f"message {i}"} for i in range(2000)]
            
            mock_workspace.return_value = Path("/test/workspace")
            mock_exists.return_value = True
            mock_prompts.return_value = large_prompts
            mock_generations.return_value = large_generations
            mock_reconstruct.return_value = large_history
            mock_getmtime.return_value = 1640995200.0
            
            result = query_cursor_chat_database()
            
            # Verify large dataset handling
            assert result["workspace_info"]["total_messages"] == 2000
            assert len(result["chat_history"]) == 2000


class TestQueryCursorChatDatabaseTelemetry:
    """Test telemetry instrumentation."""
    
    def test_telemetry_decorator_applied(self):
        """Test that the function has the telemetry decorator."""
        # Check that the function has been wrapped by the decorator
        assert hasattr(query_cursor_chat_database, '__wrapped__'), \
            "query_cursor_chat_database should have @trace_mcp_operation decorator" 