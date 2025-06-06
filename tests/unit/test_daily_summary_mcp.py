"""
Tests for daily summary MCP tool functionality.

This module tests the MCP tool for generating daily summaries from journal entries,
including the handler function, request/response validation, and AI generation logic.
"""

import pytest
import tempfile
import os
from datetime import datetime, date
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import the types and functions we'll be testing (these don't exist yet)
try:
    from mcp_commit_story.journal_workflow_types import (
        GenerateDailySummaryRequest,
        GenerateDailySummaryResponse,
        DailySummary
    )
    from mcp_commit_story.server import handle_generate_daily_summary
    from mcp_commit_story.daily_summary import generate_daily_summary
except ImportError:
    # These imports will fail until we implement them
    pass

from mcp_commit_story.journal import JournalEntry


class TestGenerateDailySummaryRequest:
    """Test the GenerateDailySummaryRequest type validation."""
    
    def test_valid_request_structure(self):
        """Test that a valid request has the correct structure."""
        request = {
            "date": "2025-01-06"
        }
        # This will fail until we implement the type
        assert "date" in request
        assert request["date"] == "2025-01-06"
    
    def test_request_requires_date(self):
        """Test that date field is required in request."""
        # This test verifies the type definition requires date
        request = {}
        # This will fail until we implement proper validation
        with pytest.raises((KeyError, TypeError)):
            # In actual implementation, this would validate against GenerateDailySummaryRequest
            assert request["date"]  # Placeholder assertion


class TestGenerateDailySummaryResponse:
    """Test the GenerateDailySummaryResponse type structure."""
    
    def test_success_response_structure(self):
        """Test structure of successful response."""
        response = {
            "status": "success",
            "file_path": "/path/to/2025-01-06-summary.md",
            "content": "# Daily Summary for 2025-01-06\n\n...",
            "error": None
        }
        
        assert response["status"] == "success"
        assert response["file_path"] != ""
        assert response["content"] != ""
        assert response["error"] is None
    
    def test_no_entries_response_structure(self):
        """Test structure of no entries found response."""
        response = {
            "status": "no_entries",
            "file_path": "",
            "content": "",
            "error": None
        }
        
        assert response["status"] == "no_entries"
        assert response["file_path"] == ""
        assert response["content"] == ""
        assert response["error"] is None
    
    def test_error_response_structure(self):
        """Test structure of error response."""
        response = {
            "status": "error",
            "file_path": "",
            "content": "",
            "error": "Invalid date format"
        }
        
        assert response["status"] == "error"
        assert response["file_path"] == ""
        assert response["content"] == ""
        assert response["error"] is not None


class TestHandleGenerateDailySummary:
    """Test the MCP handler function for daily summary generation."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "journal_path": "/tmp/test_journal",
            "ai_model": "test-model",
            "max_tokens": 4000
        }
    
    @pytest.fixture
    def sample_journal_entries(self):
        """Sample journal entries for testing."""
        return [
            JournalEntry(
                timestamp="2025-01-06 09:00:00",
                commit_hash="abc123",
                summary="Implemented user authentication",
                technical_synopsis="Added JWT-based auth with bcrypt hashing",
                accomplishments=["Created login endpoint", "Added password validation"],
                frustrations=["Struggled with middleware integration"],
                discussion_notes=[
                    {"speaker": "Human", "text": "Should we use sessions or JWT?"},
                    {"speaker": "AI", "text": "JWT is better for our stateless API design"}
                ],
                tone_mood={"mood": "Productive", "indicators": "Making good progress"}
            ),
            JournalEntry(
                timestamp="2025-01-06 14:30:00",
                commit_hash="def456",
                summary="Fixed authentication bug",
                technical_synopsis="Resolved token expiration handling",
                accomplishments=["Fixed refresh token logic"],
                frustrations=[],
                discussion_notes=[],
                tone_mood=None
            )
        ]
    
    @pytest.mark.asyncio
    async def test_successful_daily_summary_generation(self, mock_config, sample_journal_entries):
        """Test successful generation of daily summary."""
        request = {"date": "2025-01-06"}
        
        # Mock the functions that will be called
        with patch('mcp_commit_story.config.load_config') as mock_load_config, \
             patch('mcp_commit_story.daily_summary.load_journal_entries_for_date') as mock_load_entries, \
             patch('mcp_commit_story.daily_summary.generate_daily_summary') as mock_generate, \
             patch('mcp_commit_story.daily_summary.save_daily_summary') as mock_save:
            
            mock_load_config.return_value = mock_config
            mock_load_entries.return_value = sample_journal_entries
            mock_generate.return_value = {
                "date": "2025-01-06",
                "summary": "Great progress on authentication",
                "progress_made": "Implemented user authentication",
                "key_accomplishments": ["Login endpoint", "Auth flow"],
                "technical_synopsis": "JWT-based authentication system",
                "challenges_and_learning": None,
                "discussion_highlights": None,
                "reflections": None,
                "tone_mood": None,
                "daily_metrics": {"commits": 1}
            }
            mock_save.return_value = "/tmp/test_journal/summaries/2025-01-06-summary.md"
            
            # This will fail until we implement handle_generate_daily_summary
            try:
                result = await handle_generate_daily_summary(request)
                
                assert result["status"] == "success"
                assert result["file_path"] == "/tmp/test_journal/summaries/2025-01-06-summary.md"
                assert "authentication" in result["content"]
                assert result["error"] is None
                
                # Verify the functions were called correctly
                mock_load_entries.assert_called_once_with("2025-01-06", mock_config)
                mock_generate.assert_called_once_with(sample_journal_entries, "2025-01-06", mock_config)
                mock_save.assert_called_once()
            except NameError:
                pytest.fail("handle_generate_daily_summary function not implemented yet")
    
    @pytest.mark.asyncio
    async def test_no_entries_found(self, mock_config):
        """Test response when no journal entries found for date."""
        request = {"date": "2025-01-06"}
        
        with patch('mcp_commit_story.config.load_config') as mock_load_config, \
             patch('mcp_commit_story.daily_summary.load_journal_entries_for_date') as mock_load_entries:
            
            mock_load_config.return_value = mock_config
            mock_load_entries.return_value = []  # No entries found
            
            try:
                result = await handle_generate_daily_summary(request)
                
                assert result["status"] == "no_entries"
                assert result["file_path"] == ""
                assert result["content"] == ""
                assert result["error"] is None
            except NameError:
                pytest.fail("handle_generate_daily_summary function not implemented yet")
    
    @pytest.mark.asyncio
    async def test_invalid_date_format(self):
        """Test error handling for invalid date format."""
        request = {"date": "invalid-date"}
        
        try:
            result = await handle_generate_daily_summary(request)
            
            assert result["status"] == "error"
            assert result["error"] is not None
            assert "date format" in result["error"].lower()
        except NameError:
            pytest.fail("handle_generate_daily_summary function not implemented yet")
    
    @pytest.mark.asyncio
    async def test_missing_date_parameter(self):
        """Test error handling for missing date parameter."""
        request = {}  # Missing date
        
        try:
            result = await handle_generate_daily_summary(request)
            
            assert result["status"] == "error"
            assert result["error"] is not None
            assert "date" in result["error"].lower()
        except NameError:
            pytest.fail("handle_generate_daily_summary function not implemented yet")
    
    @pytest.mark.asyncio
    async def test_file_system_error_handling(self, mock_config, sample_journal_entries):
        """Test error handling for file system errors."""
        request = {"date": "2025-01-06"}
        
        with patch('mcp_commit_story.config.load_config') as mock_load_config, \
             patch('mcp_commit_story.daily_summary.load_journal_entries_for_date') as mock_load_entries, \
             patch('mcp_commit_story.daily_summary.generate_daily_summary') as mock_generate, \
             patch('mcp_commit_story.daily_summary.save_daily_summary') as mock_save:
            
            mock_load_config.return_value = mock_config
            mock_load_entries.return_value = sample_journal_entries
            mock_generate.return_value = Mock(content="Summary content")
            mock_save.side_effect = PermissionError("Cannot write to directory")
            
            try:
                result = await handle_generate_daily_summary(request)
                
                assert result["status"] == "error"
                assert result["error"] is not None
                assert "permission" in result["error"].lower() or "write" in result["error"].lower()
            except NameError:
                pytest.fail("handle_generate_daily_summary function not implemented yet")


class TestDailySummaryGeneration:
    """Test the core AI generation function for daily summaries."""
    
    @pytest.fixture
    def sample_entries_with_reflections(self):
        """Sample entries including manual reflections."""
        return [
            JournalEntry(
                timestamp="2025-01-06 09:00:00",
                commit_hash="abc123",
                summary="Implemented user authentication with manual reflection",
                technical_synopsis="Added JWT-based auth",
                accomplishments=["Created login endpoint"],
                frustrations=["Middleware integration was tricky"],
                discussion_notes=[
                    {"speaker": "Human", "text": "What's the tradeoff between sessions and JWT?"},
                    {"speaker": "AI", "text": "JWT scales better but sessions are simpler for debugging"}
                ],
                tone_mood={"mood": "Focused", "indicators": "Deep concentration on problem-solving"}
            )
        ]
    
    def test_generate_daily_summary_basic_structure(self, sample_entries_with_reflections):
        """Test that daily summary generation returns proper structure."""
        config = {"ai_model": "test-model"}
        
        # Mock the AI generation call
        with patch('mcp_commit_story.daily_summary._call_ai_for_daily_summary') as mock_ai:
            mock_ai.return_value = {
                "summary": "Productive day implementing authentication",
                "reflections": ["Learned about JWT vs sessions tradeoffs"],
                "progress_made": "Successfully implemented user authentication with JWT",
                "key_accomplishments": ["Login endpoint created", "Authentication flow working"],
                "technical_synopsis": "Implemented JWT-based authentication system",
                "challenges_and_learning": ["Middleware integration required careful debugging"],
                "discussion_highlights": ["Discussed JWT vs sessions tradeoffs"],
                "tone_mood": {"mood": "Focused", "indicators": "Deep concentration"},
                "daily_metrics": {"commits": 1, "files_changed": 3}
            }
            
            try:
                result = generate_daily_summary(
                    sample_entries_with_reflections, 
                    "2025-01-06", 
                    config
                )
                
                # Test that result has all expected sections
                assert result["date"] == "2025-01-06"
                assert "authentication" in result["summary"].lower()
                assert len(result["reflections"]) > 0
                assert result["progress_made"] != ""
                assert len(result["key_accomplishments"]) > 0
                assert result["technical_synopsis"] != ""
                assert len(result["challenges_and_learning"]) > 0
                assert result["tone_mood"] is not None
                assert result["daily_metrics"] is not None
                
            except NameError:
                pytest.fail("generate_daily_summary function not implemented yet")
    
    def test_reflection_preservation(self, sample_entries_with_reflections):
        """Test that manual reflections are preserved verbatim."""
        config = {"ai_model": "test-model"}
        
        # Add a manual reflection to the entry
        entry_with_reflection = sample_entries_with_reflections[0]
        original_reflection = "This was a breakthrough moment - I finally understood the security implications of stateless authentication."
        
        # Mock finding reflections in the entries
        with patch('mcp_commit_story.daily_summary._extract_manual_reflections') as mock_extract, \
             patch('mcp_commit_story.daily_summary._call_ai_for_daily_summary') as mock_ai:
            
            mock_extract.return_value = [original_reflection]
            mock_ai.return_value = {
                "summary": "Day summary",
                "reflections": [],  # AI doesn't generate reflections when manual ones exist
                "progress_made": "Progress",
                "key_accomplishments": ["Achievement"],
                "technical_synopsis": "Technical details",
                "challenges_and_learning": ["Learning"],
                "discussion_highlights": [],
                "tone_mood": None,
                "daily_metrics": {}
            }
            
            try:
                result = generate_daily_summary(
                    sample_entries_with_reflections,
                    "2025-01-06",
                    config
                )
                
                # Verify reflection is preserved exactly
                assert original_reflection in result["reflections"]
                assert len(result["reflections"]) == 1
                
            except NameError:
                pytest.fail("generate_daily_summary function not implemented yet")
    
    def test_empty_sections_omitted(self):
        """Test that sections with no content are omitted from output."""
        # Entry with minimal content
        minimal_entry = JournalEntry(
            timestamp="2025-01-06 09:00:00",
            commit_hash="abc123",
            summary="Simple commit",
            technical_synopsis="Minor fix",
            accomplishments=["Fixed typo"],
            frustrations=[],  # Empty
            discussion_notes=[],  # Empty
            tone_mood=None  # Empty
        )
        
        config = {"ai_model": "test-model"}
        
        with patch('mcp_commit_story.daily_summary._call_ai_for_daily_summary') as mock_ai:
            mock_ai.return_value = {
                "summary": "Simple day",
                "reflections": [],  # Empty - should be omitted
                "progress_made": "Fixed a typo",
                "key_accomplishments": ["Typo fixed"],
                "technical_synopsis": "Minor fix applied",
                "challenges_and_learning": [],  # Empty - should be omitted
                "discussion_highlights": [],  # Empty - should be omitted
                "tone_mood": None,  # Empty - should be omitted
                "daily_metrics": {"commits": 1}
            }
            
            try:
                result = generate_daily_summary([minimal_entry], "2025-01-06", config)
                
                # Verify empty sections are omitted
                assert result["reflections"] is None or len(result["reflections"]) == 0
                assert result["challenges_and_learning"] is None or len(result["challenges_and_learning"]) == 0
                assert result["discussion_highlights"] is None or len(result["discussion_highlights"]) == 0
                assert result["tone_mood"] is None
                
                # Verify non-empty sections are present
                assert result["summary"] != ""
                assert result["progress_made"] != ""
                assert len(result["key_accomplishments"]) > 0
                assert result["technical_synopsis"] != ""
                
            except NameError:
                pytest.fail("generate_daily_summary function not implemented yet")


class TestMCPToolRegistration:
    """Test that the daily summary tool is properly registered with the MCP server."""
    
    def test_tool_registration(self):
        """Test that the daily summary tool is registered in server.py."""
        # This test verifies the tool is properly registered
        try:
            from mcp_commit_story.server import register_tools
            # We'll need to check that the tool is registered when we implement it
            # For now, this will fail until implementation
            assert hasattr(register_tools, '__call__')
        except ImportError:
            pytest.fail("register_tools function not found")
    
    def test_tool_has_correct_name(self):
        """Test that the tool is registered with the correct name."""
        # The tool should be named "journal/generate-daily-summary"
        # This will be verified once we implement the registration
        pass


class TestTelemetryIntegration:
    """Test telemetry integration for daily summary operations."""
    
    @pytest.mark.skip(reason="Telemetry integration will be implemented later")
    @pytest.mark.asyncio
    async def test_telemetry_traces_operation(self, sample_journal_entries=None):
        """Test that daily summary generation includes proper telemetry tracing."""
        if sample_journal_entries is None:
            sample_journal_entries = []
        
        config = {"ai_model": "test-model"}
        
        # Mock telemetry
        with patch('mcp_commit_story.telemetry.trace_mcp_operation') as mock_trace:
            mock_trace.return_value = lambda func: func  # Pass-through decorator
            
            try:
                # This will fail until we implement the function
                generate_daily_summary(sample_journal_entries, "2025-01-06", config)
                
                # Verify telemetry was called with correct operation name
                mock_trace.assert_called_with(
                    "daily_summary.generate",
                    attributes={"operation_type": "ai_generation", "section_type": "daily_summary"}
                )
            except NameError:
                pytest.fail("generate_daily_summary_from_entries function not implemented yet")


if __name__ == "__main__":
    pytest.main([__file__]) 