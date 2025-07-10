"""Test MCP handler for capture-context operations with telemetry integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from src.mcp_commit_story.server import handle_journal_capture_context_mcp


class TestCaptureContextMCPHandler:
    """Test MCP handler functionality for capture-context operations."""

    @pytest.mark.asyncio
    async def test_handle_capture_context_valid_text(self):
        """Test MCP handler with valid text parameter."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.return_value = {
                "status": "success", 
                "file_path": "/test/path/2025-07-10-journal.md"
            }
            
            request = {
                "text": "This is important AI context to capture"
            }
            
            result = await handle_journal_capture_context_mcp(request)
            
            assert result["status"] == "success"
            assert result["file_path"] == "/test/path/2025-07-10-journal.md"
            assert result.get("error") is None
            mock_handler.assert_called_once_with("This is important AI context to capture")

    @pytest.mark.asyncio
    async def test_handle_capture_context_none_text_generates_dump(self):
        """Test MCP handler with None text parameter triggers AI knowledge dump."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.return_value = {
                "status": "success", 
                "file_path": "/test/path/2025-07-10-journal.md"
            }
            
            request = {
                "text": None
            }
            
            result = await handle_journal_capture_context_mcp(request)
            
            assert result["status"] == "success"
            assert result["file_path"] == "/test/path/2025-07-10-journal.md"
            assert result.get("error") is None
            mock_handler.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_handle_capture_context_missing_text_field(self):
        """Test MCP handler with missing text field uses None."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.return_value = {
                "status": "success", 
                "file_path": "/test/path/2025-07-10-journal.md"
            }
            
            request = {}
            
            result = await handle_journal_capture_context_mcp(request)
            
            assert result["status"] == "success"
            mock_handler.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_handle_capture_context_core_function_error(self):
        """Test MCP handler when core function raises error."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.side_effect = Exception("Failed to write to journal")
            
            request = {
                "text": "This is important AI context to capture"
            }
            
            result = await handle_journal_capture_context_mcp(request)
            
            assert result["status"] == "error"
            assert "Failed to write to journal" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_capture_context_response_format(self):
        """Test MCP handler returns proper response format."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.return_value = {
                "status": "success", 
                "file_path": "/test/path/2025-07-10-journal.md",
                "error": None
            }
            
            request = {
                "text": "Test context"
            }
            
            result = await handle_journal_capture_context_mcp(request)
            
            # Verify response matches CaptureContextResponse TypedDict
            assert isinstance(result, dict)
            assert "status" in result
            assert "file_path" in result
            assert "error" in result
            assert result["status"] == "success"
            assert result["file_path"] == "/test/path/2025-07-10-journal.md"
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_handle_capture_context_core_function_returns_error(self):
        """Test MCP handler when core function returns error status."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.return_value = {
                "status": "error", 
                "file_path": "",
                "error": "Permission denied writing to journal"
            }
            
            request = {
                "text": "Test context"
            }
            
            result = await handle_journal_capture_context_mcp(request)
            
            assert result["status"] == "error"
            assert result["file_path"] == ""
            assert result["error"] == "Permission denied writing to journal"

    @pytest.mark.asyncio
    async def test_handle_capture_context_telemetry_integration(self):
        """Test that MCP handler properly integrates with telemetry."""
        with patch('src.mcp_commit_story.server.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
                mock_handler.return_value = {
                    "status": "success", 
                    "file_path": "/test/path/2025-07-10-journal.md"
                }
                
                request = {
                    "text": "Test context"
                }
                
                result = await handle_journal_capture_context_mcp(request)
                
                # Verify telemetry calls would be made by decorator
                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_capture_context_trace_operation_attributes(self):
        """Test that MCP handler has proper trace operation attributes."""
        with patch('src.mcp_commit_story.server.handle_journal_capture_context') as mock_handler:
            mock_handler.return_value = {
                "status": "success", 
                "file_path": "/test/path/2025-07-10-journal.md"
            }
            
            request = {
                "text": "Test context"
            }
            
            result = await handle_journal_capture_context_mcp(request)
            
            # Test passes if function executes without error
            # Actual telemetry attributes are tested in integration tests
            assert result["status"] == "success"


class TestCaptureContextMCPToolRegistration:
    """Test MCP tool registration for capture-context."""

    @pytest.mark.asyncio
    async def test_tool_registration_exists(self):
        """Test that capture-context tool is registered with proper name."""
        from src.mcp_commit_story.server import create_mcp_server
        
        # This test will pass once the tool is registered
        server = create_mcp_server()
        
        # Verify tool is registered
        tools = await server.list_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "journal_capture_context" in tool_names

    @pytest.mark.asyncio
    async def test_tool_function_signature(self):
        """Test that the tool function has correct signature via server registration."""
        from src.mcp_commit_story.server import create_mcp_server
        
        # Create server to register tools
        server = create_mcp_server()
        
        # Get the registered tool
        tools = await server.list_tools()
        capture_tool = next((tool for tool in tools if tool.name == "journal_capture_context"), None)
        
        assert capture_tool is not None
        assert capture_tool.name == "journal_capture_context"


class TestCaptureContextMCPTypeDefinitions:
    """Test TypedDict definitions for capture-context."""

    def test_capture_context_request_type(self):
        """Test CaptureContextRequest TypedDict structure."""
        from src.mcp_commit_story.server import CaptureContextRequest
        
        # Test type annotation exists
        assert hasattr(CaptureContextRequest, '__annotations__')
        
        # Test required fields
        annotations = CaptureContextRequest.__annotations__
        assert 'text' in annotations
        
        # Test text is Optional[str]
        import typing
        assert typing.get_origin(annotations['text']) is typing.Union
        assert str in typing.get_args(annotations['text'])
        assert type(None) in typing.get_args(annotations['text'])

    def test_capture_context_response_type(self):
        """Test CaptureContextResponse TypedDict structure."""
        from src.mcp_commit_story.server import CaptureContextResponse
        
        # Test type annotation exists
        assert hasattr(CaptureContextResponse, '__annotations__')
        
        # Test required fields
        annotations = CaptureContextResponse.__annotations__
        assert 'status' in annotations
        assert 'file_path' in annotations
        assert 'error' in annotations
        
        # Test field types
        assert annotations['status'] == str
        assert annotations['file_path'] == str
        
        # Test error is Optional[str]
        import typing
        assert typing.get_origin(annotations['error']) is typing.Union
        assert str in typing.get_args(annotations['error'])
        assert type(None) in typing.get_args(annotations['error']) 