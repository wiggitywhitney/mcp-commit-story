"""
Tests for server.py integration with the orchestration layer.

These tests verify that the MCP server layer (Layer 1) correctly delegates
to the orchestration layer (Layer 2) while maintaining backward compatibility.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

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
        
        # Mock request
        request = {
            'commit_hash': 'abc123',
            'journal_path': '/path/to/journal.md',
            'repo_path': '/path/to/repo'
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify delegation occurred
        mock_orchestrate.assert_called_once_with('abc123', '/path/to/journal.md')
        
        # Verify response structure matches MCP contract
        assert result['status'] == 'success'
        assert 'content' in result
        assert 'telemetry' in result
        assert result['execution_time'] == 2.5
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_handles_orchestration_failure(self, mock_orchestrate):
        """Test server layer handles orchestration failures gracefully."""
        # Setup mock orchestration failure
        mock_orchestrate.return_value = {
            'success': False,
            'error': 'Context collection failed',
            'phase': 'context_collection',
            'execution_time': 1.0
        }
        
        # Mock request
        request = {
            'commit_hash': 'abc123',
            'journal_path': '/path/to/journal.md'
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify error handling
        assert result['status'] == 'error'
        assert 'Context collection failed' in result['message']
        assert result['phase'] == 'context_collection'
        assert result['execution_time'] == 1.0
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_backward_compatibility(self, mock_orchestrate):
        """Test that the refactored function maintains backward compatibility."""
        # Setup successful orchestration
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
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
        
        # Test with minimal request (backward compatibility)
        minimal_request = {
            'commit_hash': 'def456'
        }
        
        # Execute
        result = await generate_journal_entry(minimal_request)
        
        # Verify backward compatibility
        assert result['status'] == 'success'
        assert 'content' in result
        
        # Verify orchestrator was called with defaults
        mock_orchestrate.assert_called_once()
        call_args = mock_orchestrate.call_args[0]
        assert call_args[0] == 'def456'  # commit_hash
        # Should have default journal path
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_generate_journal_entry_preserves_mcp_interface(self, mock_orchestrate):
        """Test that MCP interface contract is preserved after refactoring."""
        # Setup orchestration response
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
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
        
        # Mock request with all expected MCP parameters
        request = {
            'commit_hash': 'ghi789',
            'journal_path': '/custom/journal.md',
            'repo_path': '/custom/repo',
            'since_commit': 'since123',
            'max_messages_back': 150
        }
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify MCP response contract
        required_fields = ['status', 'content', 'execution_time', 'telemetry']
        for field in required_fields:
            assert field in result, f"Required MCP field '{field}' missing from response"
        
        # Verify status values are correct
        assert result['status'] in ['success', 'error']
        
        # Verify telemetry structure
        assert isinstance(result['telemetry'], dict)
        assert 'execution_time' in result['telemetry'] or result['execution_time'] is not None


class TestServerLayerErrorHandling:
    """Test error handling in the server layer."""
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_handles_orchestrator_exception(self, mock_orchestrate):
        """Test server layer handles unexpected orchestrator exceptions."""
        # Setup orchestrator to raise exception
        mock_orchestrate.side_effect = Exception("Unexpected orchestrator error")
        
        # Mock request
        request = {'commit_hash': 'error123'}
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify graceful error handling
        assert result['status'] == 'error'
        assert 'Unexpected orchestrator error' in result['message']
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_validates_required_parameters(self, mock_orchestrate):
        """Test server validates required parameters before delegation."""
        # Mock empty request (missing commit_hash)
        invalid_request = {}
        
        # Execute
        result = await generate_journal_entry(invalid_request)
        
        # Verify validation error
        assert result['status'] == 'error'
        assert 'commit_hash' in result['message'].lower()
        
        # Verify orchestrator was not called with invalid params
        mock_orchestrate.assert_not_called()


class TestServerLayerTelemetry:
    """Test telemetry integration at the server layer."""
    
    @patch('mcp_commit_story.server.trace_mcp_operation')
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_layer_telemetry_decoration(self, mock_orchestrate, mock_trace):
        """Test that server layer function has proper telemetry decoration."""
        # Setup orchestration success
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                summary="Telemetry test",
                technical_synopsis="",
                accomplishments=[],
                frustrations=[],
                tone_mood=None,
                discussion_notes=[],
                terminal_commands=[],
                commit_metadata={}
            ),
            'execution_time': 1.0,
            'telemetry': {},
            'errors': []
        }
        
        # Mock request
        request = {'commit_hash': 'telemetry123'}
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify telemetry decorator was applied to server function
        # (This tests that the function is properly decorated)
        mock_trace.assert_called_with("generate_journal_entry")
    
    @patch('mcp_commit_story.server.orchestrate_journal_generation')
    async def test_server_aggregates_orchestration_telemetry(self, mock_orchestrate):
        """Test server layer properly aggregates telemetry from orchestration."""
        # Setup orchestration with detailed telemetry
        orchestration_telemetry = {
            'context_collection_time': 0.8,
            'ai_function_times': {
                'generate_summary_section': 0.4,
                'generate_accomplishments_section': 0.3
            },
            'total_ai_functions_called': 8,
            'successful_ai_functions': 7,
            'failed_ai_functions': 1,
            'assembly_time': 0.1
        }
        
        mock_orchestrate.return_value = {
            'success': True,
            'journal_entry': JournalEntry(
                summary="Telemetry aggregation test",
                technical_synopsis="",
                accomplishments=[],
                frustrations=[],
                tone_mood=None,
                discussion_notes=[],
                terminal_commands=[],
                commit_metadata={}
            ),
            'execution_time': 2.2,
            'telemetry': orchestration_telemetry,
            'errors': []
        }
        
        # Mock request
        request = {'commit_hash': 'aggregate123'}
        
        # Execute
        result = await generate_journal_entry(request)
        
        # Verify telemetry aggregation
        assert 'telemetry' in result
        server_telemetry = result['telemetry']
        
        # Verify orchestration telemetry is included
        assert 'orchestration' in server_telemetry
        assert server_telemetry['orchestration'] == orchestration_telemetry
        
        # Verify server-level metrics
        assert 'server_processing_time' in server_telemetry
        assert server_telemetry['total_execution_time'] == 2.2 