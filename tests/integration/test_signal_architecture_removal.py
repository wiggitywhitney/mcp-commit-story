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
    
    @patch('mcp_commit_story.git_utils.get_repo')
    @patch('mcp_commit_story.git_utils.get_current_commit')
    @patch('mcp_commit_story.git_utils.get_commit_details')
    @patch('mcp_commit_story.git_hook_worker.generate_daily_summary_standalone')
    def test_git_hook_operations_work_without_signals(self, mock_daily_summary, mock_get_commit_details, mock_current_commit, mock_get_repo):
        """Test that git hook operations complete successfully without signal infrastructure."""
        # Setup mocks
        mock_repo = Mock()
        mock_get_repo.return_value = mock_repo
        
        mock_commit = Mock()
        mock_commit.hexsha = "abc1234"
        mock_commit.committed_datetime.isoformat.return_value = "2025-01-01T12:00:00"
        mock_commit.stats.files = {"file1.py": {}}
        mock_current_commit.return_value = mock_commit
        
        mock_get_commit_details.return_value = {
            'hash': 'abc1234',
            'message': 'Test commit',
            'timestamp': 1640995200,
            'datetime': '2025-01-01 12:00:00',
            'author': 'Test User <test@example.com>',
            'stats': {'files': 1, 'insertions': 10, 'deletions': 2}
        }
        
        mock_daily_summary.return_value = None
        
        # Test that git hook processing works
        with patch('mcp_commit_story.git_hook_worker.extract_commit_metadata', return_value={
            'hash': 'abc1234',
            'message': 'Test commit',
            'date': '2025-01-01T12:00:00',
            'author': 'Test User <test@example.com>',
            'files_changed': ['file1.py'],
            'stats': {'files': 1, 'insertions': 10, 'deletions': 2}
        }):
            with patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger', return_value="2025-01-01"):
                with patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers', return_value={"weekly": False, "monthly": False, "quarterly": False, "yearly": False}):
                    with patch('sys.argv', ['git_hook_worker', '/fake/repo']):
                        with patch('os.path.exists', return_value=True):
                            with patch('mcp_commit_story.git_hook_worker.setup_hook_logging'):
                                with patch('mcp_commit_story.git_hook_worker.log_hook_activity'):
                                    with patch('mcp_commit_story.git_hook_worker.generate_journal_entry_safe', return_value=True):
                                        with patch('mcp_commit_story.git_hook_worker.daily_summary_telemetry'):
                                            with patch('mcp_commit_story.git_hook_worker.period_summary_placeholder', return_value=True):
                                                with patch('sys.exit'):
                                                    # This should not raise any exceptions
                                                    try:
                                                        git_hook_main()
                                                    except Exception as e:
                                                        print(f"Exception in git_hook_main: {e}")
                                                        raise
        
        # Verify direct calls were made instead of signal creation
        assert mock_daily_summary.call_count == 1, f"Expected 1 call, got {mock_daily_summary.call_count}"
    
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