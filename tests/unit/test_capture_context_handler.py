"""
Test suite for journal capture context handler.

Tests the core handler function that processes capture-context requests
and appends AI knowledge captures to journal files.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from pathlib import Path
import tempfile
import os

# Import the functions we'll be testing (they don't exist yet - TDD approach)
from mcp_commit_story.journal_handlers import (
    handle_journal_capture_context,
    format_ai_knowledge_capture,
    generate_ai_knowledge_dump
)


class TestHandleJournalCaptureContext:
    """Test the core capture-context handler function."""
    
    def test_handle_journal_capture_context_with_valid_text(self):
        """Test successful capture with valid text parameter."""
        test_text = "This is important context to capture"
        
        with patch('mcp_commit_story.journal_handlers.get_journal_file_path') as mock_get_path, \
             patch('mcp_commit_story.journal_handlers.append_to_journal_file') as mock_append:
            
            mock_get_path.return_value = "daily/2025-07-09-journal.md"
            
            result = handle_journal_capture_context(test_text)
            
            assert result["status"] == "success"
            assert "file_path" in result
            assert result["error"] is None
            
            # Verify append was called with formatted content
            mock_append.assert_called_once()
            appended_content = mock_append.call_args[0][0]
            assert "AI Knowledge Capture" in appended_content
            assert test_text in appended_content
            assert "____" in appended_content  # Separator
    
    def test_handle_journal_capture_context_with_empty_text(self):
        """Test error handling with empty text parameter."""
        result = handle_journal_capture_context("")
        
        assert result["status"] == "error"
        assert "empty" in result["error"].lower()
        assert result["file_path"] is None
    
    def test_handle_journal_capture_context_with_none_text_triggers_ai_dump(self):
        """Test that None text parameter triggers AI knowledge dump generation."""
        with patch('mcp_commit_story.journal_handlers.generate_ai_knowledge_dump') as mock_gen_dump, \
             patch('mcp_commit_story.journal_handlers.get_journal_file_path') as mock_get_path, \
             patch('mcp_commit_story.journal_handlers.append_to_journal_file') as mock_append:
            
            mock_gen_dump.return_value = "AI-generated comprehensive knowledge dump"
            mock_get_path.return_value = "daily/2025-07-09-journal.md"
            
            result = handle_journal_capture_context(None)
            
            assert result["status"] == "success"
            mock_gen_dump.assert_called_once()
            mock_append.assert_called_once()
            
            # Verify AI dump content was used
            appended_content = mock_append.call_args[0][0]
            assert "AI-generated comprehensive knowledge dump" in appended_content
    
    def test_handle_journal_capture_context_unified_header_format(self):
        """Test that the unified header format is used correctly."""
        test_text = "Context to capture"
        
        with patch('mcp_commit_story.journal_handlers.get_journal_file_path') as mock_get_path, \
             patch('mcp_commit_story.journal_handlers.append_to_journal_file') as mock_append, \
             patch('mcp_commit_story.journal_handlers.datetime') as mock_datetime:
            
            # Mock datetime to return consistent timestamp
            mock_datetime.now.return_value = datetime(2025, 7, 9, 14, 30, 0)
            mock_datetime.strftime = datetime.strftime
            
            mock_get_path.return_value = "daily/2025-07-09-journal.md"
            
            result = handle_journal_capture_context(test_text)
            
            assert result["status"] == "success"
            
            # Verify unified header format: ### 2:30 PM — AI Knowledge Capture
            appended_content = mock_append.call_args[0][0]
            assert "### 2:30 PM — AI Knowledge Capture" in appended_content
            assert "____" in appended_content  # Separator
    
    def test_handle_journal_capture_context_directory_creation(self):
        """Test that journal directory is created if missing."""
        test_text = "Context to capture"
        
        with patch('mcp_commit_story.journal_handlers.get_journal_file_path') as mock_get_path, \
             patch('mcp_commit_story.journal_handlers.append_to_journal_file') as mock_append:
            
            mock_get_path.return_value = "daily/2025-07-09-journal.md"
            
            result = handle_journal_capture_context(test_text)
            
            assert result["status"] == "success"
            # append_to_journal_file should handle directory creation
            mock_append.assert_called_once()
    
    def test_handle_journal_capture_context_returns_file_path(self):
        """Test that file path is returned in response."""
        test_text = "Context to capture"
        
        with patch('mcp_commit_story.journal_handlers.get_journal_file_path') as mock_get_path, \
             patch('mcp_commit_story.journal_handlers.append_to_journal_file') as mock_append, \
             patch('mcp_commit_story.journal_handlers.load_config') as mock_config:
            
            mock_get_path.return_value = "daily/2025-07-09-journal.md"
            mock_config.return_value = Mock(journal_path="journal")
            
            result = handle_journal_capture_context(test_text)
            
            assert result["status"] == "success"
            assert result["file_path"] is not None
            assert "journal" in result["file_path"]
    
    def test_handle_journal_capture_context_exception_handling(self):
        """Test graceful error handling when exceptions occur."""
        test_text = "Context to capture"
        
        with patch('mcp_commit_story.journal_handlers.get_journal_file_path') as mock_get_path:
            mock_get_path.side_effect = Exception("Test error")
            
            result = handle_journal_capture_context(test_text)
            
            assert result["status"] == "error"
            assert "Test error" in result["error"]
            assert result["file_path"] is None


class TestFormatAIKnowledgeCapture:
    """Test the formatting function for AI knowledge capture."""
    
    def test_format_ai_knowledge_capture_unified_header_format(self):
        """Test that the unified header format is used correctly."""
        test_text = "Test AI knowledge content"
        
        with patch('mcp_commit_story.journal_handlers.datetime') as mock_datetime:
            # Mock datetime to return consistent timestamp
            mock_datetime.now.return_value = datetime(2025, 7, 9, 14, 30, 0)
            mock_datetime.strftime = datetime.strftime
            
            result = format_ai_knowledge_capture(test_text)
            
            expected_parts = [
                "\n\n____\n\n",  # Separator
                "### 2:30 PM — AI Knowledge Capture",  # Unified header
                test_text
            ]
            
            for part in expected_parts:
                assert part in result
    
    def test_format_ai_knowledge_capture_timestamp_format(self):
        """Test timestamp formatting matches journal entry format."""
        test_text = "Test content"
        
        with patch('mcp_commit_story.journal_handlers.datetime') as mock_datetime:
            # Test various times to verify format
            test_times = [
                (datetime(2025, 7, 9, 9, 5, 0), "9:05 AM"),  # Single digit hour/minute
                (datetime(2025, 7, 9, 14, 30, 0), "2:30 PM"),  # PM time
                (datetime(2025, 7, 9, 0, 0, 0), "12:00 AM"),  # Midnight
                (datetime(2025, 7, 9, 12, 0, 0), "12:00 PM"),  # Noon
            ]
            
            for dt, expected_time in test_times:
                mock_datetime.now.return_value = dt
                mock_datetime.strftime = datetime.strftime
                
                result = format_ai_knowledge_capture(test_text)
                assert f"### {expected_time} — AI Knowledge Capture" in result
    
    def test_format_ai_knowledge_capture_separator_inclusion(self):
        """Test that the separator is included correctly."""
        test_text = "Test content"
        
        result = format_ai_knowledge_capture(test_text)
        
        # Should start with separator
        assert result.startswith("\n\n____\n\n")
        
        # Should have header after separator
        assert "### " in result
        assert " — AI Knowledge Capture" in result


class TestGenerateAIKnowledgeDump:
    """Test the AI knowledge dump generation function."""
    
    def test_generate_ai_knowledge_dump_uses_approved_prompt(self):
        """Test that the approved prompt is used for AI knowledge dump."""
        with patch('mcp_commit_story.journal_handlers.invoke_ai') as mock_invoke_ai:
            mock_invoke_ai.return_value = "Generated knowledge dump"
            
            result = generate_ai_knowledge_dump()
            
            assert result == "Generated knowledge dump"
            mock_invoke_ai.assert_called_once()
            
            # Verify the approved prompt is used
            call_args = mock_invoke_ai.call_args[0]
            prompt_used = call_args[0]
            
            # Check for key phrases from the approved prompt
            assert "comprehensive knowledge capture" in prompt_used
            assert "current understanding of this project" in prompt_used
            assert "recent development insights" in prompt_used
            assert "fresh AI understand where we are" in prompt_used
            assert "future journal entries" in prompt_used
    
    def test_generate_ai_knowledge_dump_handles_ai_errors(self):
        """Test graceful handling of AI invocation errors."""
        with patch('mcp_commit_story.journal_handlers.invoke_ai') as mock_invoke_ai:
            mock_invoke_ai.side_effect = Exception("AI service error")
            
            result = generate_ai_knowledge_dump()
            
            # Should return fallback message on error
            assert "Unable to generate AI knowledge dump" in result
            assert "AI service error" in result 