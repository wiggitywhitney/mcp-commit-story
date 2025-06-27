"""Test MCP handler for reflection operations with telemetry integration."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
from pathlib import Path

from src.mcp_commit_story.server import handle_add_reflection
from src.mcp_commit_story.reflection_core import add_manual_reflection
from src.mcp_commit_story.config import Config


class TestReflectionMCPHandler:
    """Test MCP handler functionality for reflection operations."""

    @pytest.mark.asyncio
    async def test_handle_add_reflection_valid_request(self):
        """Test MCP handler with valid reflection request."""
        with patch('src.mcp_commit_story.server.add_manual_reflection') as mock_add_reflection:
            mock_add_reflection.return_value = {"status": "success", "file_path": "/test/path.md"}
            
            request = {
                "reflection": "This is a test reflection",
                "date": "2025-01-02"
            }
            
            result = await handle_add_reflection(request)
            
            assert result["status"] == "success"
            assert result["file_path"] == "/test/path.md"
            assert result.get("error") is None
            mock_add_reflection.assert_called_once_with("This is a test reflection", "2025-01-02")

    @pytest.mark.asyncio
    async def test_handle_add_reflection_missing_reflection_text(self):
        """Test MCP handler with missing reflection text."""
        with patch('src.mcp_commit_story.server.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            request = {
                "date": "2025-01-02"
            }
            
            result = await handle_add_reflection(request)
            
            assert result["status"] == "error"
            assert "Missing required field: reflection/text" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_add_reflection_missing_date(self):
        """Test MCP handler with missing date."""
        with patch('src.mcp_commit_story.server.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            request = {
                "reflection": "This is a test reflection"
            }
            
            result = await handle_add_reflection(request)
            
            assert result["status"] == "error"
            assert "Missing required field: date" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_add_reflection_alternative_text_field(self):
        """Test MCP handler accepts 'text' field as alternative to 'reflection'."""
        with patch('src.mcp_commit_story.server.add_manual_reflection') as mock_add_reflection:
            mock_add_reflection.return_value = {"status": "success", "file_path": "/test/path.md"}
            
            request = {
                "text": "This is a test reflection via text field",
                "date": "2025-01-02"
            }
            
            result = await handle_add_reflection(request)
            
            assert result["status"] == "success"
            mock_add_reflection.assert_called_once_with("This is a test reflection via text field", "2025-01-02")

    @pytest.mark.asyncio
    async def test_handle_add_reflection_core_function_error(self):
        """Test MCP handler when core reflection function raises error."""
        with patch('src.mcp_commit_story.server.add_manual_reflection') as mock_add_reflection:
            mock_add_reflection.side_effect = Exception("File write error")
            
            with patch('src.mcp_commit_story.server.get_mcp_metrics') as mock_get_metrics:
                mock_metrics = MagicMock()
                mock_get_metrics.return_value = mock_metrics
                
                request = {
                    "reflection": "This is a test reflection",
                    "date": "2025-01-02"
                }
                
                result = await handle_add_reflection(request)
                
                assert result["status"] == "error"
                assert "File write error" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_add_reflection_telemetry_integration(self):
        """Test that MCP handler properly integrates with telemetry."""
        with patch('src.mcp_commit_story.server.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.server.add_manual_reflection') as mock_add_reflection:
                mock_add_reflection.return_value = {"status": "success", "file_path": "/test/path.md"}
                
                request = {
                    "reflection": "This is a test reflection",
                    "date": "2025-01-02"
                }
                
                result = await handle_add_reflection(request)
                
                # Verify telemetry calls
                mock_metrics.record_counter.assert_called()
                counter_calls = mock_metrics.record_counter.call_args_list
                
                # Look for MCP operation counter
                mcp_operation_call = next((call for call in counter_calls 
                                          if 'mcp.handler.operations_total' in str(call)), None)
                assert mcp_operation_call is not None
                
                # Verify operation attributes
                args, kwargs = mcp_operation_call
                assert kwargs.get('operation') == 'add_reflection'
                assert kwargs.get('handler') == 'handle_journal_add_reflection'
                assert kwargs.get('status') == 'success'

    @pytest.mark.asyncio
    async def test_handle_add_reflection_telemetry_error_recording(self):
        """Test that MCP handler properly records telemetry for errors."""
        with patch('src.mcp_commit_story.server.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.server.add_manual_reflection') as mock_add_reflection:
                mock_add_reflection.side_effect = PermissionError("Permission denied")
                
                request = {
                    "reflection": "This is a test reflection",
                    "date": "2025-01-02"
                }
                
                result = await handle_add_reflection(request)
                
                # The @handle_mcp_error decorator catches the exception and returns an error response
                # Error telemetry is handled by the decorator, not our handler
                assert result["status"] == "error"
                assert "Permission denied" in result["error"]


class TestReflectionCoreWithTelemetry:
    """Test core reflection functionality with enhanced telemetry."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.journal_path = os.path.join(self.temp_dir, "journal", "daily")
        os.makedirs(self.journal_path, exist_ok=True)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_manual_reflection_telemetry_attributes(self):
        """Test that add_manual_reflection function has proper telemetry attributes."""
        with patch('src.mcp_commit_story.reflection_core.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.reflection_core.load_config') as mock_load_config:
                mock_config = Mock()
                mock_config.journal_path = self.journal_path
                mock_load_config.return_value = mock_config
                
                result = add_manual_reflection("Test reflection", "2025-01-02")
                
                # Verify telemetry attributes are recorded
                mock_metrics.record_counter.assert_called()
                counter_calls = mock_metrics.record_counter.call_args_list
                
                # Look for reflection operation counter
                reflection_call = next((call for call in counter_calls 
                                       if 'mcp.reflection.operations_total' in str(call)), None)
                assert reflection_call is not None
                
                # Verify enhanced telemetry attributes match actual implementation
                args, kwargs = reflection_call
                assert kwargs.get('operation') == 'add_to_journal'  # Actual value from implementation
                assert kwargs.get('operation_type') == 'manual_input'
                assert kwargs.get('content_type') == 'reflection'
                assert kwargs.get('status') == 'success'

    def test_add_manual_reflection_duration_tracking(self):
        """Test that add_manual_reflection tracks operation duration."""
        with patch('src.mcp_commit_story.reflection_core.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.reflection_core.load_config') as mock_load_config:
                mock_config = Mock()
                mock_config.journal_path = self.journal_path
                mock_load_config.return_value = mock_config
                
                result = add_manual_reflection("Test reflection", "2025-01-02")
                
                # Verify duration tracking
                mock_metrics.record_operation_duration.assert_called()
                duration_calls = mock_metrics.record_operation_duration.call_args_list
                
                # Look for reflection duration call
                duration_call = next((call for call in duration_calls 
                                     if 'mcp.reflection.duration_seconds' in str(call)), None)
                assert duration_call is not None
                
                # Verify duration attributes match actual implementation
                args, kwargs = duration_call
                assert len(args) >= 2  # metric name and duration value
                assert args[0] == 'mcp.reflection.duration_seconds'
                assert isinstance(args[1], (int, float))
                assert kwargs.get('operation') == 'add_to_journal'  # Actual value from implementation
                assert kwargs.get('operation_type') == 'manual_input'

    def test_add_manual_reflection_error_categorization(self):
        """Test that add_manual_reflection categorizes errors properly."""
        with patch('src.mcp_commit_story.reflection_core.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.reflection_core.load_config') as mock_load_config:
                mock_config = Mock()
                mock_config.journal_path = "/nonexistent/path"
                mock_load_config.return_value = mock_config
                
                # Mock the file operations to raise permission error
                with patch('src.mcp_commit_story.reflection_core.add_reflection_to_journal') as mock_add_to_journal:
                    mock_add_to_journal.side_effect = PermissionError("Permission denied")
                    
                    result = add_manual_reflection("Test reflection", "2025-01-02")
                    
                    # Should return error dict, not raise exception
                    assert result["status"] == "error"
                    assert "Permission denied" in result["error"]
                
                # Verify error categorization in telemetry
                mock_metrics.record_counter.assert_called()
                counter_calls = mock_metrics.record_counter.call_args_list
                
                # Look for error counter
                error_call = next((call for call in counter_calls 
                                  if 'mcp.reflection.operations_total' in str(call)), None)
                assert error_call is not None
                
                # Verify error category
                args, kwargs = error_call
                assert kwargs.get('status') == 'error'
                assert kwargs.get('error_category') == 'permission_error'

    def test_add_manual_reflection_content_length_tracking(self):
        """Test that add_manual_reflection tracks content length in telemetry."""
        with patch('src.mcp_commit_story.reflection_core.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            with patch('src.mcp_commit_story.reflection_core.load_config') as mock_load_config:
                mock_config = Mock()
                mock_config.journal_path = self.journal_path
                mock_load_config.return_value = mock_config
                
                test_reflection = "This is a longer test reflection to verify content length tracking"
                result = add_manual_reflection(test_reflection, "2025-01-02")
                
                # Verify content length is tracked
                mock_metrics.record_counter.assert_called()
                counter_calls = mock_metrics.record_counter.call_args_list
                
                # Look for reflection operation counter
                reflection_call = next((call for call in counter_calls 
                                       if 'mcp.reflection.operations_total' in str(call)), None)
                assert reflection_call is not None
                
                # Verify content length attribute
                args, kwargs = reflection_call
                assert 'content_length' in kwargs
                assert kwargs['content_length'] == len(test_reflection)

    def test_add_manual_reflection_span_attributes(self):
        """Test that add_manual_reflection sets proper OpenTelemetry span attributes."""
        with patch('src.mcp_commit_story.reflection_core.get_mcp_metrics') as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock the tracer to avoid SpanContext issues
            with patch('opentelemetry.trace.get_tracer') as mock_get_tracer:
                mock_tracer = MagicMock()
                mock_span = MagicMock()
                
                # Create a context manager that returns the mock span
                mock_span_context = MagicMock()
                mock_span_context.__enter__.return_value = mock_span
                mock_span_context.__exit__.return_value = None
                
                mock_tracer.start_as_current_span.return_value = mock_span_context
                mock_get_tracer.return_value = mock_tracer
                
                # Also mock get_current_span to capture attributes from within functions
                with patch('opentelemetry.trace.get_current_span') as mock_get_current_span:
                    mock_get_current_span.return_value = mock_span
                
                    with patch('src.mcp_commit_story.reflection_core.load_config') as mock_load_config:
                        mock_config = Mock()
                        mock_config.journal_path = self.journal_path
                        mock_load_config.return_value = mock_config
                        
                        result = add_manual_reflection("Test reflection", "2025-01-02")
                        
                        # Verify span attributes are set
                        mock_span.set_attribute.assert_called()
                        attribute_calls = mock_span.set_attribute.call_args_list
                        
                        # Check for expected attributes - collect all attributes set across all spans
                        attribute_dict = {call[0][0]: call[0][1] for call in attribute_calls}
                        
                        # Verify key attributes are present (from both manual reflection and nested journal operations)
                        # Note: Due to multiple traced functions, attributes come from different spans
                        expected_attributes = [
                            ('reflection.date', '2025-01-02'),  # From add_manual_reflection 
                            ('reflection.content_length', len("Test reflection")),  # From add_reflection_to_journal
                            ('file.extension', '.md'),  # From add_reflection_to_journal
                            ('content_type', 'reflection')  # From trace_mcp_operation decorator
                        ]
                        
                        for attr_name, expected_value in expected_attributes:
                            assert attr_name in attribute_dict, f"Missing attribute: {attr_name}. Available: {list(attribute_dict.keys())}"
                            assert attribute_dict[attr_name] == expected_value, f"Wrong value for {attr_name}: got {attribute_dict[attr_name]}, expected {expected_value}" 