"""
Unit tests for cursor database message extraction module.

Tests the message data extraction functionality that pulls user prompts and AI responses
from Cursor's ItemTable key-value structure, with robust JSON parsing and error handling.
"""

import json
import tempfile
from pathlib import Path
from typing import List, Tuple, Any
from unittest.mock import patch, MagicMock, call

import pytest

from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseQueryError,
    CursorDatabaseAccessError,
    CursorDatabaseNotFoundError
)
from mcp_commit_story.cursor_db.message_extraction import (
    extract_prompts_data,
    extract_generations_data
)


class TestExtractPromptsData:
    """Test the extract_prompts_data function."""

    def test_extract_prompts_data_success(self):
        """Test successful extraction of user prompts data."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.prompts', json.dumps([
                {"text": "Fix this bug please", "commandType": 4},
                {"text": "Add a new feature", "commandType": 4}
            ]).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_prompts_data(mock_db_path)
            
            # Assert
            assert len(result) == 2
            assert result[0] == {"text": "Fix this bug please", "commandType": 4}
            assert result[1] == {"text": "Add a new feature", "commandType": 4}
            
            # Verify query was called correctly
            mock_query.assert_called_once_with(
                mock_db_path,
                "SELECT [key], value FROM ItemTable WHERE [key] = ?",
                ("aiService.prompts",)
            )

    def test_extract_prompts_data_empty_result(self):
        """Test extraction when no prompts data is found."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = []
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_prompts_data(mock_db_path)
            
            # Assert
            assert result == []

    def test_extract_prompts_data_malformed_json_skip_and_log(self):
        """Test handling of malformed JSON data with skip and log approach."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.prompts', b'invalid json content')
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query, \
             patch('mcp_commit_story.cursor_db.message_extraction.logger') as mock_logger:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_prompts_data(mock_db_path)
            
            # Assert
            assert result == []  # Empty due to skipped malformed data
            mock_logger.warning.assert_called_once()
            assert "Failed to parse JSON" in mock_logger.warning.call_args[0][0]

    def test_extract_prompts_data_mixed_valid_invalid_json(self):
        """Test handling mix of valid and invalid JSON data."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.prompts', json.dumps([
                {"text": "Valid message 1", "commandType": 4}
            ]).encode()),
            ('aiService.prompts', b'invalid json'),
            ('aiService.prompts', json.dumps([
                {"text": "Valid message 2", "commandType": 4}
            ]).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query, \
             patch('mcp_commit_story.cursor_db.message_extraction.logger') as mock_logger:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_prompts_data(mock_db_path)
            
            # Assert
            assert len(result) == 2
            assert result[0] == {"text": "Valid message 1", "commandType": 4}
            assert result[1] == {"text": "Valid message 2", "commandType": 4}
            mock_logger.warning.assert_called_once()

    def test_extract_prompts_data_non_list_json(self):
        """Test handling of valid JSON that's not a list."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.prompts', json.dumps({"not": "a list"}).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query, \
             patch('mcp_commit_story.cursor_db.message_extraction.logger') as mock_logger:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_prompts_data(mock_db_path)
            
            # Assert
            assert result == []
            mock_logger.warning.assert_called_once()
            assert "Expected list format" in mock_logger.warning.call_args[0][0]

    def test_extract_prompts_data_database_error_propagation(self):
        """Test that database errors are properly propagated."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.side_effect = CursorDatabaseAccessError("Database locked", path=mock_db_path)
            
            # Act & Assert
            with pytest.raises(CursorDatabaseAccessError):
                extract_prompts_data(mock_db_path)


class TestExtractGenerationsData:
    """Test the extract_generations_data function."""

    def test_extract_generations_data_success(self):
        """Test successful extraction of AI generations data."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.generations', json.dumps([
                {
                    "unixMs": 1750492546467,
                    "generationUUID": "53a3d753-1bbb-4cb2-9178-8c1ea10b7954",
                    "type": "composer",
                    "textDescription": "Here's the solution to your bug"
                },
                {
                    "unixMs": 1750492547000,
                    "generationUUID": "64b4e864-2ccb-5dc3-a189-9d2fb20c8065",
                    "type": "composer", 
                    "textDescription": "I've added the new feature as requested"
                }
            ]).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_generations_data(mock_db_path)
            
            # Assert
            assert len(result) == 2
            assert result[0]["unixMs"] == 1750492546467
            assert result[0]["generationUUID"] == "53a3d753-1bbb-4cb2-9178-8c1ea10b7954"
            assert result[0]["type"] == "composer"
            assert result[0]["textDescription"] == "Here's the solution to your bug"
            
            assert result[1]["unixMs"] == 1750492547000
            assert result[1]["textDescription"] == "I've added the new feature as requested"
            
            # Verify query was called correctly
            mock_query.assert_called_once_with(
                mock_db_path,
                "SELECT [key], value FROM ItemTable WHERE [key] = ?",
                ("aiService.generations",)
            )

    def test_extract_generations_data_empty_result(self):
        """Test extraction when no generations data is found."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = []
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_generations_data(mock_db_path)
            
            # Assert
            assert result == []

    def test_extract_generations_data_malformed_json_skip_and_log(self):
        """Test handling of malformed JSON data with skip and log approach."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.generations', b'{"invalid": json content')
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query, \
             patch('mcp_commit_story.cursor_db.message_extraction.logger') as mock_logger:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_generations_data(mock_db_path)
            
            # Assert
            assert result == []
            mock_logger.warning.assert_called_once()
            assert "Failed to parse JSON" in mock_logger.warning.call_args[0][0]

    def test_extract_generations_data_mixed_valid_invalid_json(self):
        """Test resilience with mix of valid and invalid JSON entries."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_raw_data = [
            ('aiService.generations', json.dumps([
                {
                    "unixMs": 1750492546467,
                    "generationUUID": "53a3d753-1bbb-4cb2-9178-8c1ea10b7954",
                    "type": "composer",
                    "textDescription": "Valid response 1"
                }
            ]).encode()),
            ('aiService.generations', b'malformed json'),
            ('aiService.generations', json.dumps([
                {
                    "unixMs": 1750492547000,
                    "generationUUID": "64b4e864-2ccb-5dc3-a189-9d2fb20c8065",
                    "type": "composer",
                    "textDescription": "Valid response 2"
                }
            ]).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query, \
             patch('mcp_commit_story.cursor_db.message_extraction.logger') as mock_logger:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_generations_data(mock_db_path)
            
            # Assert
            assert len(result) == 2
            assert result[0]["textDescription"] == "Valid response 1"
            assert result[1]["textDescription"] == "Valid response 2"
            mock_logger.warning.assert_called_once()

    def test_extract_generations_data_database_error_propagation(self):
        """Test that database errors are properly propagated."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.side_effect = CursorDatabaseQueryError("Invalid SQL", sql="SELECT bad syntax")
            
            # Act & Assert
            with pytest.raises(CursorDatabaseQueryError):
                extract_generations_data(mock_db_path)

    def test_extract_generations_data_large_chat_history_memory_strategy(self):
        """Test memory strategy for large chat histories (load everything into memory)."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        # Simulate 100 messages (Cursor's limit)
        large_data = []
        for i in range(100):
            large_data.append({
                "unixMs": 1750492546467 + i,
                "generationUUID": f"uuid-{i:03d}",
                "type": "composer",
                "textDescription": f"AI response number {i}"
            })
        
        mock_raw_data = [
            ('aiService.generations', json.dumps(large_data).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.return_value = mock_raw_data
            
            # Act
            result = extract_generations_data(mock_db_path)
            
            # Assert
            assert len(result) == 100
            assert result[0]["textDescription"] == "AI response number 0"
            assert result[99]["textDescription"] == "AI response number 99"
            # All data loaded into memory successfully


class TestMessageExtractionIntegration:
    """Integration tests for message extraction functions."""

    def test_both_functions_use_execute_cursor_query(self):
        """Test that both functions use the execute_cursor_query from 46.1."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            mock_query.return_value = []
            
            # Act
            extract_prompts_data(mock_db_path)
            extract_generations_data(mock_db_path)
            
            # Assert
            assert mock_query.call_count == 2
            
            # Verify specific calls
            expected_calls = [
                call(mock_db_path, "SELECT [key], value FROM ItemTable WHERE [key] = ?", ("aiService.prompts",)),
                call(mock_db_path, "SELECT [key], value FROM ItemTable WHERE [key] = ?", ("aiService.generations",))
            ]
            mock_query.assert_has_calls(expected_calls)

    def test_return_format_raw_tuples_from_database(self):
        """Test that functions return raw parsed data, not interpreted messages."""
        # Arrange
        mock_db_path = "/fake/path/to/test.db"
        mock_prompts_data = [
            ('aiService.prompts', json.dumps([
                {"text": "user message", "commandType": 4}
            ]).encode())
        ]
        mock_generations_data = [
            ('aiService.generations', json.dumps([
                {"unixMs": 1750492546467, "textDescription": "AI response"}
            ]).encode())
        ]
        
        with patch('mcp_commit_story.cursor_db.message_extraction.execute_cursor_query') as mock_query:
            # Test prompts
            mock_query.return_value = mock_prompts_data
            prompts_result = extract_prompts_data(mock_db_path)
            
            # Test generations
            mock_query.return_value = mock_generations_data
            generations_result = extract_generations_data(mock_db_path)
            
            # Assert raw data structure is preserved
            assert isinstance(prompts_result, list)
            assert isinstance(prompts_result[0], dict)
            assert "text" in prompts_result[0]
            assert "commandType" in prompts_result[0]
            
            assert isinstance(generations_result, list)
            assert isinstance(generations_result[0], dict)
            assert "unixMs" in generations_result[0]
            assert "textDescription" in generations_result[0] 