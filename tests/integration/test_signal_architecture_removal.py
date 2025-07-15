"""
Integration tests for signal architecture removal verification.

This test suite verifies that the removal of signal-based architecture 
from the codebase was successful and that essential functionality remains working.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Server functionality is tested through MCP tool registration verification
from mcp_commit_story.git_hook_worker import main as git_hook_main
from mcp_commit_story.daily_summary_standalone import generate_daily_summary_standalone
from mcp_commit_story.reflection_core import add_manual_reflection
from mcp_commit_story.journal_handlers import handle_journal_capture_context


class TestSignalArchitectureRemoval:
    """Test suite verifying signal architecture removal was successful."""
    
    def test_mcp_server_starts_without_signal_references(self):
        """Test that MCP server starts without any signal-related code."""
        # Import the server module and verify no signal management imports
        import src.mcp_commit_story.server as server_module
        import inspect
        
        # Check that signal_management is not imported
        source = inspect.getsource(server_module)
        assert "signal_management" not in source, "Signal management still referenced in server"
        assert "create_tool_signal" not in source, "Signal creation still referenced in server"
        
        # Verify only essential MCP tools are registered
        # This checks the actual tool registration code exists
        assert "journal_add_reflection" in source, "Essential MCP tool journal_add_reflection missing"
        assert "journal_capture_context" in source, "Essential MCP tool journal_capture_context missing"
        
        # Verify obsolete tools are not registered
        assert "journal_new_entry" not in source, "Obsolete MCP tool journal_new_entry still present"
        assert "journal_init" not in source, "Obsolete MCP tool journal_init still present"
        assert "journal_install_hook" not in source, "Obsolete MCP tool journal_install_hook still present"
        assert "journal_generate_daily_summary" not in source, "Obsolete MCP tool journal_generate_daily_summary still present"
    
    def test_git_hook_worker_uses_direct_calls(self):
        """Test that git hook worker uses direct calls instead of signal creation."""
        import src.mcp_commit_story.git_hook_worker as git_hook_module
        import inspect
        
        # Check that signal management is not imported
        source = inspect.getsource(git_hook_module)
        assert "signal_management" not in source, "Signal management still referenced in git hook worker"
        assert "create_tool_signal" not in source, "Signal creation still referenced in git hook worker"
        assert "create_tool_signal_safe" not in source, "Signal creation still referenced in git hook worker"
        
        # Verify direct call patterns exist
        assert "generate_daily_summary_standalone" in source, "Direct call to daily summary missing"
    
    @patch('mcp_commit_story.git_utils.get_git_root')
    @patch('mcp_commit_story.git_utils.get_current_commit_hash')
    @patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary_standalone')
    def test_git_hook_operations_work_without_signals(self, mock_daily_summary, mock_commit_hash, mock_git_root):
        """Test that git hook operations complete successfully without signal infrastructure."""
        # Setup mocks
        mock_git_root.return_value = "/fake/repo"
        mock_commit_hash.return_value = "abc1234"
        mock_daily_summary.return_value = None
        
        # Test that git hook processing works
        with patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger', return_value="2025-01-01"):
            with patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers', return_value={"weekly": False, "monthly": False, "quarterly": False, "yearly": False}):
                # This should not raise any exceptions
                git_hook_main()
        
        # Verify direct calls were made instead of signal creation
        mock_daily_summary.assert_called_once()
    
    def test_no_signal_files_created_during_operations(self):
        """Test that no signal files are created during any operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the journal path to use our temp directory
            with patch('mcp_commit_story.config.get_journal_path', return_value=temp_dir):
                with patch('mcp_commit_story.git_utils.get_git_root', return_value=temp_dir):
                    with patch('mcp_commit_story.git_utils.get_current_commit_hash', return_value="abc1234"):
                        with patch('mcp_commit_story.daily_summary_standalone.generate_daily_summary_standalone'):
                            with patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger', return_value="2025-01-01"):
                                with patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers', return_value={"weekly": False, "monthly": False, "quarterly": False, "yearly": False}):
                                    # Run git hook processing
                                    git_hook_main()
            
            # Check that no signal files were created
            signal_files = list(Path(temp_dir).rglob("*signal*"))
            assert len(signal_files) == 0, f"Signal files found: {signal_files}"
    
    def test_journal_add_reflection_functionality_works(self):
        """Test that journal_add_reflection MCP tool functionality works correctly after cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test environment
            with patch('mcp_commit_story.config.get_journal_path', return_value=temp_dir):
                # Test the reflection function directly
                result = add_manual_reflection(
                    reflection_text="Test reflection",
                    date="2025-01-01"
                )
                
                # Verify it works (should return success response)
                assert result is not None
                assert result.get("success") is True
    
    @patch('mcp_commit_story.ai_invocation.invoke_ai_function')
    def test_journal_capture_context_functionality_works(self, mock_ai_invoke):
        """Test that journal_capture_context MCP tool functionality works correctly after cleanup."""
        mock_ai_invoke.return_value = "Test context content"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test environment
            with patch('mcp_commit_story.config.get_journal_path', return_value=temp_dir):
                # Test the context capture function directly
                result = handle_journal_capture_context(
                    text="Test content"
                )
                
                # Verify it works (should return success response)
                assert result is not None
    
    def test_daily_summary_generation_works_directly(self):
        """Test that daily summary generation works with direct calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test journal entry
            journal_file = Path(temp_dir) / "journal" / "daily" / "2025-01-01-journal.md"
            journal_file.parent.mkdir(parents=True, exist_ok=True)
            journal_file.write_text("# Test Journal Entry\n\nTest content")
            
            # Mock the AI invocation to return summary content
            with patch('mcp_commit_story.ai_invocation.invoke_ai_function') as mock_ai:
                mock_ai.return_value = "Test summary content"
                
                with patch('mcp_commit_story.config.get_journal_path', return_value=temp_dir):
                    with patch('mcp_commit_story.git_utils.get_git_root', return_value=temp_dir):
                        # Test direct daily summary generation
                        result = generate_daily_summary_standalone(date="2025-01-01")
                        
                        # Verify it works
                        assert result is not None
                        mock_ai.assert_called()
    
    def test_no_signal_management_imports_in_codebase(self):
        """Test that no files in the codebase import signal_management."""
        import os
        import glob
        
        # Find all Python files in the source directory
        python_files = glob.glob("src/**/*.py", recursive=True)
        
        for file_path in python_files:
            with open(file_path, 'r') as f:
                content = f.read()
                assert "from mcp_commit_story.signal_management" not in content, f"Signal management import found in {file_path}"
                assert "import mcp_commit_story.signal_management" not in content, f"Signal management import found in {file_path}"
                assert "from .signal_management" not in content, f"Signal management import found in {file_path}"
    
    def test_signal_related_functions_removed_from_modules(self):
        """Test that signal-related functions are removed from key modules."""
        # Test git_hook_worker module
        import src.mcp_commit_story.git_hook_worker as git_hook_module
        
        # These functions should not exist anymore
        assert not hasattr(git_hook_module, 'create_tool_signal'), "create_tool_signal function still exists"
        assert not hasattr(git_hook_module, 'create_tool_signal_safe'), "create_tool_signal_safe function still exists"
        assert not hasattr(git_hook_module, 'signal_creation_telemetry'), "signal_creation_telemetry function still exists"
        
        # Test daily_summary module
        import src.mcp_commit_story.daily_summary as daily_summary_module
        
        # This function should not exist anymore
        assert not hasattr(daily_summary_module, 'generate_daily_summary_mcp_tool'), "generate_daily_summary_mcp_tool function still exists" 