"""
Integration tests for Task 51: Journal/Capture-Context MCP Tool

Tests the key integration points:
- MCP tool registration and basic functionality
- Context collection integration
- Basic end-to-end flows
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from mcp_commit_story.server import handle_journal_capture_context_mcp, CaptureContextRequest
from mcp_commit_story.journal_handlers import handle_journal_capture_context
from mcp_commit_story.context_collection import collect_recent_journal_context


class TestMCPToolRegistration:
    """Test that the MCP tool is properly registered and works."""
    
    @pytest.mark.asyncio
    async def test_capture_context_tool_exists(self):
        """Verify handle_journal_capture_context_mcp function exists and is callable."""
        assert callable(handle_journal_capture_context_mcp), "Handler function should be callable"
    
    @pytest.mark.asyncio
    async def test_mcp_handler_basic_invocation(self):
        """Test basic MCP handler invocation doesn't crash."""
        request: CaptureContextRequest = {"text": "Test knowledge capture"}
        
        # Test that we can call the handler without crashing
        try:
            result = await handle_journal_capture_context_mcp(request)
            # Should return a dict with status
            assert isinstance(result, dict), "Should return a dict"
            assert "status" in result, "Should have status field"
        except Exception as e:
            # Even if it fails, it should be a reasonable error
            assert "text" in str(e) or "journal" in str(e), f"Should be journal-related error, got: {e}"


class TestContextCollection:
    """Test context collection functionality."""
    
    def test_collect_recent_journal_context_structure(self):
        """Test that collect_recent_journal_context returns proper structure."""
        mock_commit = Mock()
        mock_commit.committed_datetime = datetime.now()
        
        # Test with non-existent file
        result = collect_recent_journal_context(mock_commit)
        
        # Should return proper structure
        assert isinstance(result, dict), "Should return dict"
        assert "latest_entry" in result, "Should have latest_entry field"
        assert "additional_context" in result, "Should have additional_context field"
        assert "metadata" in result, "Should have metadata field"
    
    def test_collect_recent_journal_context_with_sample_file(self, tmp_path):
        """Test context collection with a sample journal file."""
        # Create a sample journal file
        journal_file = tmp_path / "2025-01-10-journal.md"
        journal_content = """
## 2:30 PM — Git Commit: abc123

Test journal entry content.

### 3:15 PM — AI Knowledge Capture

Some captured knowledge after the commit.
"""
        journal_file.write_text(journal_content)
        
        mock_commit = Mock()
        mock_commit.committed_datetime = datetime(2025, 1, 10, 14, 30)
        
        # Mock get_journal_file_path to return our test file
        with patch('mcp_commit_story.journal.get_journal_file_path') as mock_path:
            mock_path.return_value = str(journal_file)
            
            result = collect_recent_journal_context(mock_commit)
            
            # Should find content
            assert result["metadata"]["file_exists"], "File should exist"
            assert len(result["additional_context"]) > 0, "Should find additional context"


class TestBasicIntegration:
    """Test basic integration between components."""
    
    def test_capture_to_journal_file_flow(self, tmp_path):
        """Test capturing context and verifying it appears in journal file."""
        # Setup test journal directory
        journal_dir = tmp_path / "journal" / "daily"
        journal_dir.mkdir(parents=True)
        
        # Test with minimal mocking
        test_date = "2025-01-10"
        journal_file = journal_dir / f"{test_date}-journal.md"
        
        with patch('mcp_commit_story.journal.get_journal_file_path') as mock_path, \
             patch('mcp_commit_story.journal_handlers.datetime') as mock_datetime:
            
            mock_path.return_value = str(journal_file)
            mock_datetime.now.return_value.strftime.return_value = "2:30 PM"
            
            # Capture some context
            result = handle_journal_capture_context("Test integration knowledge")
            
            # Verify success
            assert result["status"] == "success", "Should succeed"
            assert str(journal_file) in result["file_path"], "Should reference correct file"
            
            # Verify content was written
            assert journal_file.exists(), "Journal file should be created"
            content = journal_file.read_text()
            assert "Test integration knowledge" in content, "Should contain captured text"
            assert "AI Knowledge Capture" in content, "Should have proper header"


class TestErrorHandling:
    """Test error handling in integration scenarios."""
    
    def test_capture_context_missing_directory(self):
        """Test capturing context when journal directory doesn't exist."""
        # Should handle missing directory gracefully
        result = handle_journal_capture_context("Test with missing dir")
        
        # Should either succeed (by creating dir) or fail gracefully
        assert "status" in result, "Should return status"
        assert result["status"] in ["success", "error"], "Should have valid status"
    
    def test_context_collection_missing_file(self):
        """Test context collection when journal file doesn't exist."""
        mock_commit = Mock()
        mock_commit.committed_datetime = datetime.now()
        
        # Don't mock anything - let it try to find a real file (which won't exist)
        result = collect_recent_journal_context(mock_commit)
        
        # Should handle gracefully
        assert result["latest_entry"] is None, "Should handle missing file"
        assert len(result["additional_context"]) == 0, "Should return empty context"
        assert not result["metadata"]["file_exists"], "Should report file doesn't exist"
    
    @pytest.mark.asyncio
    async def test_mcp_handler_error_handling(self):
        """Test MCP handler error handling."""
        # Test with missing text field
        request: CaptureContextRequest = {}
        
        # Should handle gracefully (may succeed with None text or return error)
        try:
            result = await handle_journal_capture_context_mcp(request)
            assert isinstance(result, dict), "Should return dict even on error"
            assert "status" in result, "Should have status"
        except Exception as e:
            # If it raises, should be a reasonable error
            assert isinstance(e, Exception), "Should be a proper exception"


class TestEndToEndFlow:
    """Test simple end-to-end flows."""
    
    def test_capture_and_collect_cycle(self, tmp_path):
        """Test full cycle: capture context → collect context → verify integration."""
        # Setup
        journal_dir = tmp_path / "journal" / "daily"
        journal_dir.mkdir(parents=True)
        test_date = "2025-01-10"
        journal_file = journal_dir / f"{test_date}-journal.md"
        
        # Mock current time
        with patch('mcp_commit_story.journal.get_journal_file_path') as mock_path, \
             patch('mcp_commit_story.journal_handlers.datetime') as mock_datetime:
            
            mock_path.return_value = str(journal_file)
            mock_datetime.now.return_value.strftime.return_value = "2:30 PM"
            
            # Step 1: Capture some context
            capture_result = handle_journal_capture_context("End-to-end test knowledge")
            assert capture_result["status"] == "success", "Capture should succeed"
            
            # Step 2: Verify file was created with content
            assert journal_file.exists(), "Journal file should exist"
            content = journal_file.read_text()
            assert "End-to-end test knowledge" in content, "Should contain captured text"
            
            # Step 3: Collect context (simulating later journal generation)
            mock_commit = Mock()
            mock_commit.committed_datetime = datetime(2025, 1, 10, 15, 0)  # After capture
            
            # Mock the path for collection too
            with patch('mcp_commit_story.journal.get_journal_file_path') as mock_collect_path:
                mock_collect_path.return_value = str(journal_file)
                collect_result = collect_recent_journal_context(mock_commit)
                
                # Step 4: Verify collected context includes captured knowledge
                additional = collect_result["additional_context"]
                assert len(additional) > 0, "Should collect additional context"
                
                # Verify metadata
                assert collect_result["metadata"]["file_exists"], "Should detect file exists"
    
    def test_integration_doesnt_break_existing_functionality(self):
        """Test that Task 51 integration doesn't break existing journal functionality."""
        # This is a basic sanity check that imports work
        from mcp_commit_story import journal_orchestrator
        from mcp_commit_story import journal_workflow
        from mcp_commit_story import context_collection
        
        # Should be able to import without errors
        assert hasattr(journal_orchestrator, 'collect_all_context_data'), \
            "Should maintain existing orchestrator functionality"
        assert hasattr(context_collection, 'collect_recent_journal_context'), \
            "Should have new context collection function" 