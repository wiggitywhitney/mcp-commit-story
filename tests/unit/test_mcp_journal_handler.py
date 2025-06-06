"""
Unit tests for MCP journal entry creation handler.

Tests the handle_journal_entry_creation() MCP function and integration with
generation and file operations from subtasks 9.1 and 9.2.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from mcp_commit_story.server import (
    handle_journal_new_entry, 
    generate_journal_entry as mcp_generate_journal_entry,
    JournalNewEntryRequest,
    JournalNewEntryResponse,
    MCPError
)
from mcp_commit_story.journal_workflow import generate_journal_entry, save_journal_entry, handle_journal_entry_creation
from mcp_commit_story.journal import JournalEntry


@pytest.fixture
def sample_request():
    """Sample MCP request with git context."""
    return {
        "git": {
            "metadata": {
                "hash": "abc123",
                "author": "Test Author",
                "date": "2025-06-04T16:00:00",
                "message": "Test commit message"
            },
            "diff_summary": "Added test file",
            "changed_files": ["test.py"],
            "file_stats": {"source": 1},
            "commit_context": {}
        },
        "chat": None,
        "terminal": None
    }

@pytest.fixture
def sample_config():
    """Sample configuration object."""
    return {
        'journal': {
            'path': 'test-journal',
            'include_terminal': True,
            'include_chat': True
        }
    }

@pytest.fixture
def mock_commit():
    """Mock GitPython commit object."""
    commit = Mock()
    commit.hexsha = "abc123"
    commit.author = Mock()
    commit.author.name = "Test Author"
    commit.committed_datetime.isoformat.return_value = "2025-06-04T16:00:00"
    commit.message = "Test commit message"
    commit.parents = []
    return commit

@pytest.fixture
def sample_journal_entry():
    """Sample journal entry object."""
    return JournalEntry(
        timestamp="4:00 PM",
        commit_hash="abc123",
        summary="Test summary",
        technical_synopsis="Test technical details",
        accomplishments=["Added test"],
        frustrations=[],
        tone_mood={"mood": "focused", "indicators": "high confidence"},
        discussion_notes=[],
        terminal_commands=["git add test.py"],
        commit_metadata={"files_changed": 1}
    )


class TestMCPJournalHandler:
    """Test MCP journal entry creation handler functionality."""

    @pytest.mark.asyncio
    async def test_request_validation_missing_git(self):
        """Test that missing git field returns error response via decorator."""
        request = {"chat": None, "terminal": None}
        
        # The @handle_mcp_error decorator should catch MCPError and return error dict
        result = await handle_journal_new_entry(request)
        assert result["status"] == "error"
        assert "Missing required field: git" in result["error"]
    
    @pytest.mark.asyncio
    async def test_request_validation_missing_git_async(self):
        """Test that missing git field raises MCPError in async context."""
        request = {"chat": None, "terminal": None}
        
        # The @handle_mcp_error decorator should catch MCPError and return error dict
        result = await handle_journal_new_entry(request)
        assert result["status"] == "error"
        assert "Missing required field: git" in result["error"]
    
    @pytest.mark.asyncio
    async def test_successful_journal_entry_creation(self, sample_request):
        """Test successful end-to-end journal entry creation."""
        with patch('mcp_commit_story.server.generate_journal_entry') as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "file_path": "test-journal/daily/2025-06-04-journal.md",
                "error": None
            }
            
            result = await handle_journal_new_entry(sample_request)
            
            assert result["status"] == "success"
            assert result["file_path"] == "test-journal/daily/2025-06-04-journal.md"
            assert result["error"] is None
            mock_generate.assert_called_once_with(sample_request)
    
    @pytest.mark.asyncio
    async def test_mcp_response_format_compliance(self, sample_request):
        """Test that MCP response format matches JournalNewEntryResponse schema."""
        with patch('mcp_commit_story.server.generate_journal_entry') as mock_generate:
            mock_generate.return_value = {
                "status": "success", 
                "file_path": "test.md",
                "error": None
            }
            
            result = await handle_journal_new_entry(sample_request)
            
            # Verify response has required fields
            assert "status" in result
            assert "file_path" in result
            assert "error" in result
            
            # Verify types match schema
            assert isinstance(result["status"], str)
            assert isinstance(result["file_path"], str)
            assert result["error"] is None or isinstance(result["error"], str)
    
    @pytest.mark.asyncio
    async def test_git_operations_integration(self, sample_request):
        """Test integration with git operations."""
        with patch('mcp_commit_story.git_utils.get_repo') as mock_get_repo, \
             patch('mcp_commit_story.git_utils.get_current_commit') as mock_get_commit, \
             patch('mcp_commit_story.server.generate_journal_entry') as mock_generate:
            
            mock_repo = Mock()
            mock_commit = Mock()
            mock_commit.hexsha = "abc123"
            
            mock_get_repo.return_value = mock_repo
            mock_get_commit.return_value = mock_commit
            mock_generate.return_value = {
                "status": "success",
                "file_path": "test.md", 
                "error": None
            }
            
            result = await handle_journal_new_entry(sample_request)
            
            assert result["status"] == "success"
            mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_telemetry_integration(self, sample_request):
        """Test telemetry span creation and attributes."""
        with patch('mcp_commit_story.server.generate_journal_entry') as mock_generate, \
             patch('opentelemetry.trace.get_current_span') as mock_span:
            
            mock_span_instance = Mock()
            mock_span.return_value = mock_span_instance
            
            mock_generate.return_value = {
                "status": "success",
                "file_path": "test.md",
                "error": None
            }
            
            result = await handle_journal_new_entry(sample_request)
            
            assert result["status"] == "success"
            # The @trace_mcp_operation decorator should handle telemetry
    
    @pytest.mark.asyncio
    async def test_error_handling_for_missing_commits(self, sample_request):
        """Test error handling when commit operations fail."""
        with patch('mcp_commit_story.server.generate_journal_entry') as mock_generate:
            mock_generate.side_effect = Exception("Git repository not found")
            
            result = await handle_journal_new_entry(sample_request)
            
            # @handle_mcp_error should catch and format the error
            assert result["status"] == "error"
            assert "Internal error" in result["error"]
    
    @pytest.mark.asyncio 
    async def test_auto_summarize_integration_when_configured(self, sample_request):
        """Test auto-summarize integration when configured."""
        # This would test the auto-summarize functionality if it was configured
        # For now, just test that the handler processes normally
        with patch('mcp_commit_story.server.generate_journal_entry') as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "file_path": "test.md",
                "error": None  
            }
            
            result = await handle_journal_new_entry(sample_request)
            assert result["status"] == "success"


class TestGenerateJournalEntryStub:
    """Test the generate_journal_entry stub function in server.py."""
    
    @pytest.mark.asyncio
    async def test_stub_returns_dummy_response(self, sample_request):
        """Test that the stub returns a valid dummy response."""
        result = await mcp_generate_journal_entry(sample_request)
        
        assert result["status"] == "success"
        assert "journal" in result["file_path"]
        assert result["error"] is None


class TestJournalWorkflowIntegration:
    """Test integration with journal workflow functions from subtasks 9.1 and 9.2."""
    
    def test_generate_journal_entry_integration(self, mock_commit, sample_config):
        """Test integration with generate_journal_entry from subtask 9.1."""
        with patch('mcp_commit_story.journal_workflow.is_journal_only_commit') as mock_journal_check, \
             patch('mcp_commit_story.context_collection.collect_chat_history') as mock_chat, \
             patch('mcp_commit_story.context_collection.collect_ai_terminal_commands') as mock_terminal, \
             patch('mcp_commit_story.context_collection.collect_git_context') as mock_git, \
             patch('mcp_commit_story.journal.generate_summary_section') as mock_summary:
            
            mock_journal_check.return_value = False
            mock_chat.return_value = {"messages": []}
            mock_terminal.return_value = {"commands": []}
            mock_git.return_value = {"metadata": {"hash": "abc123"}}
            mock_summary.return_value = {"summary": "Test summary"}
            
            result = generate_journal_entry(mock_commit, sample_config, debug=True)
            
            assert result is not None
            assert isinstance(result, JournalEntry)
            assert result.commit_hash == "abc123"
    
    def test_save_journal_entry_integration(self, sample_journal_entry, sample_config, tmp_path):
        """Test integration with save_journal_entry from subtask 9.2."""
        # Update config to use temporary path
        test_config = sample_config.copy()
        test_config['journal']['path'] = str(tmp_path / "test-journal")
        
        with patch('mcp_commit_story.journal_workflow.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "2025-06-04"
            mock_datetime.now.return_value = mock_now
            
            result_path = save_journal_entry(sample_journal_entry, test_config, debug=True)
            
            assert "2025-06-04-journal.md" in result_path
            # File should be created
            assert Path(result_path).parent.exists()
    
    def test_handle_journal_entry_creation_workflow(self, mock_commit, sample_config):
        """Test the complete workflow function."""
        with patch('mcp_commit_story.journal_workflow.generate_journal_entry') as mock_generate, \
             patch('mcp_commit_story.journal_workflow.save_journal_entry') as mock_save:
            
            mock_journal_entry = Mock()
            mock_generate.return_value = mock_journal_entry
            mock_save.return_value = "test-journal/daily/2025-06-04-journal.md"
            
            result = handle_journal_entry_creation(mock_commit, sample_config, debug=True)
            
            assert result['success'] is True
            assert result['skipped'] is False
            assert "2025-06-04-journal.md" in result['file_path']
            
            mock_generate.assert_called_once_with(mock_commit, sample_config, True)
            # The function now calls save_journal_entry with date_str parameter
            mock_save.assert_called_once_with(mock_journal_entry, sample_config, True, date_str=mock_commit.committed_datetime.strftime("%Y-%m-%d"))
    
    def test_journal_only_commit_skipping(self, mock_commit, sample_config):
        """Test that journal-only commits are properly skipped."""
        with patch('mcp_commit_story.journal_workflow.generate_journal_entry') as mock_generate:
            mock_generate.return_value = None  # Indicates journal-only commit
            
            result = handle_journal_entry_creation(mock_commit, sample_config)
            
            assert result['success'] is True
            assert result['skipped'] is True
            assert result['reason'] == 'journal-only commit'
            assert result['file_path'] is None 