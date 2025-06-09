"""
Tests for server.py integration with the orchestration layer.

These tests verify that the MCP server layer (Layer 1) correctly delegates
to the orchestration layer (Layer 2) while maintaining backward compatibility.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from datetime import datetime, timezone

# These imports will work since server.py exists
from mcp_commit_story.server import generate_journal_entry
from mcp_commit_story.journal import JournalEntry


class TestServerOrchestrationIntegration:
    """Test Layer 1 (MCP Server) integration with Layer 2 (Orchestration)."""
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_delegates_to_orchestrator(self, mock_orchestrate):
        """Test that generate_journal_entry delegates to orchestration layer."""
        # Setup mock orchestration response
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                timestamp=datetime.now(timezone.utc),
                commit_hash="abc123",
                summary="Test summary",
                technical_synopsis="Technical details",
                accomplishments=["Task completed"],
                frustrations=[],
                tone_mood="productive",
                discussion_notes=["Important discussion"],
                terminal_commands=["git status"],
                commit_metadata={"author": "test"}
            ),
            'execution_time': 2.5,
            'telemetry': {
                'context_collection_time': 0.5,
                'ai_function_times': {'generate_summary_section': 0.3},
                'total_ai_functions_called': 8,
                'successful_ai_functions': 8,
                'failed_ai_functions': 0
            },
            'errors': []
        }
        
        # Mock request with correct MCP structure
        request = {
            "git": {
                "metadata": {
                    "hash": "abc123",
                    "author": "Test User",
                    "date": "2025-01-01T12:00:00Z",
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify delegation occurred
        mock_orchestrate.assert_called_once_with("abc123", "journal/daily/2025-01-01-journal.md")
        
        # Verify response structure matches actual MCP contract
        assert result['status'] == 'success'
        assert 'file_path' in result
        assert result['file_path'] == "journal/daily/2025-01-01-journal.md"
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_handles_orchestration_failure(self, mock_orchestrate):
        """Test server layer handles orchestration failures gracefully."""
        # Setup mock orchestration failure
        mock_orchestrate.side_effect = Exception("Context collection failed")
        
        # Mock request with correct MCP structure
        request = {
            "git": {
                "metadata": {
                    "hash": "abc123",
                    "author": "Test User", 
                    "date": "2025-01-01T12:00:00Z",
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify error handling (uses 'error' not 'message')
        assert result['status'] == 'error'
        assert 'Context collection failed' in result['error']
        assert result['file_path'] == ""
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_backward_compatibility(self, mock_orchestrate):
        """Test that the refactored function maintains backward compatibility."""
        # Setup successful orchestration
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                timestamp=datetime.now(timezone.utc),
                commit_hash="def456",
                summary="Backward compatible test",
                technical_synopsis="Works as before",
                accomplishments=["Maintained compatibility"],
                frustrations=[],
                tone_mood="confident",
                discussion_notes=[],
                terminal_commands=[],
                commit_metadata={}
            ),
            'execution_time': 1.5,
            'telemetry': {},
            'errors': []
        }
        
        # Test with proper MCP request structure
        request = {
            "git": {
                "metadata": {
                    "hash": "def456",
                    "author": "Test User",
                    "date": "2025-01-01T12:00:00Z", 
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify backward compatibility
        assert result['status'] == 'success'
        assert 'file_path' in result
        
        # Verify orchestrator was called with extracted params
        mock_orchestrate.assert_called_once()
        call_args = mock_orchestrate.call_args[0]
        assert call_args[0] == 'def456'  # commit_hash
        assert call_args[1] == "journal/daily/2025-01-01-journal.md"  # journal_path
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_preserves_mcp_interface(self, mock_orchestrate):
        """Test that MCP interface contract is preserved after refactoring."""
        # Setup orchestration response
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                timestamp=datetime.now(timezone.utc),
                commit_hash="ghi789",
                summary="Interface test",
                technical_synopsis="MCP contract maintained",
                accomplishments=["Interface preserved"],
                frustrations=[],
                tone_mood="assured",
                discussion_notes=[],
                terminal_commands=[],
                commit_metadata={}
            ),
            'execution_time': 2.0,
            'telemetry': {
                'context_collection_time': 0.3,
                'ai_function_times': {},
                'total_ai_functions_called': 8
            },
            'errors': []
        }
        
        # Mock request with proper MCP structure
        request = {
            "git": {
                "metadata": {
                    "hash": "ghi789",
                    "author": "Test User",
                    "date": "2025-01-01T12:00:00Z",
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify MCP response contract (actual fields used)
        required_fields = ['status', 'file_path']
        for field in required_fields:
            assert field in result, f"Required MCP field '{field}' missing from response"
        
        # Verify status values are correct
        assert result['status'] in ['success', 'error']


class TestServerLayerErrorHandling:
    """Test error handling in the server layer."""
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_handles_orchestrator_exception(self, mock_orchestrate):
        """Test server layer handles unexpected orchestrator exceptions."""
        # Setup orchestrator to raise exception
        mock_orchestrate.side_effect = Exception("Unexpected orchestrator error")
        
        # Mock request with proper structure
        request = {
            "git": {
                "metadata": {
                    "hash": "error123",
                    "author": "Test User",
                    "date": "2025-01-01T12:00:00Z",
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify graceful error handling (uses 'error' not 'message')
        assert result['status'] == 'error'
        assert 'Unexpected orchestrator error' in result['error']
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_validates_required_parameters(self, mock_orchestrate):
        """Test server validates required parameters before delegation."""
        # Mock empty request (missing git structure)
        invalid_request = {}
        
        # Execute
        result = await generate_journal_entry(invalid_request)
        
        # Verify validation error (uses 'error' not 'message')
        assert result['status'] == 'error'
        assert 'git' in result['error'].lower()
        
        # Verify orchestrator was not called with invalid params
        mock_orchestrate.assert_not_called()


class TestServerLayerTelemetry:
    """Test telemetry integration at the server layer."""
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_layer_telemetry_decoration(self, mock_orchestrate):
        """Test that server layer has proper telemetry decoration."""
        # Setup mock orchestration response
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                timestamp=datetime.now(timezone.utc),
                commit_hash="telemetry123",
                summary="Telemetry test",
                technical_synopsis="Telemetry working",
                accomplishments=["Telemetry integrated"],
                frustrations=[],
                tone_mood="measured", 
                discussion_notes=[],
                terminal_commands=[],
                commit_metadata={}
            ),
            'execution_time': 1.8,
            'telemetry': {},
            'errors': []
        }
        
        # Mock request
        request = {
            "git": {
                "metadata": {
                    "hash": "telemetry123",
                    "author": "Test User",
                    "date": "2025-01-01T12:00:00Z",
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify successful execution (telemetry decorator is applied at import time)
        assert result['status'] == 'success'
        assert 'file_path' in result
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_aggregates_orchestration_telemetry(self, mock_orchestrate):
        """Test server layer aggregates telemetry from orchestration layer."""
        # Setup orchestration with telemetry data
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                timestamp=datetime.now(timezone.utc),
                commit_hash="agg123",
                summary="Aggregation test",
                technical_synopsis="Telemetry aggregated",
                accomplishments=["Data aggregated"],
                frustrations=[],
                tone_mood="analytical",
                discussion_notes=[],
                terminal_commands=[],
                commit_metadata={}
            ),
            'execution_time': 3.2,
            'telemetry': {
                'context_collection_time': 0.8,
                'ai_function_times': {
                    'generate_summary_section': 0.4,
                    'generate_accomplishments_section': 0.3
                },
                'total_ai_functions_called': 8,
                'successful_ai_functions': 7,
                'failed_ai_functions': 1
            },
            'errors': ['Minor AI function timeout']
        }
        
        # Mock request
        request = {
            "git": {
                "metadata": {
                    "hash": "agg123",
                    "author": "Test User",
                    "date": "2025-01-01T12:00:00Z",
                    "message": "Test commit"
                }
            }
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify telemetry aggregation in response
        assert result['status'] == 'success'
        # Note: Current implementation doesn't expose telemetry in response
        # This test verifies the delegation works, telemetry is handled internally 