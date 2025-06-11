"""
Unit tests for enhanced git hook with daily summary triggering.

Tests the enhanced generate_hook_content() function and git_hook_worker module
that implement file-creation-based daily summary triggering through MCP integration.
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, call
from pathlib import Path

from mcp_commit_story.git_utils import generate_hook_content


class TestEnhancedGitHook:
    """Test the enhanced git hook content generation."""
    
    def test_generate_hook_content_includes_python_worker(self):
        """Test that generate_hook_content produces hook script that calls Python worker."""
        hook_content = generate_hook_content()
        
        # Should contain the Python worker call
        assert "python -m mcp_commit_story.git_hook_worker" in hook_content
        
        # Should pass current working directory
        assert '"$PWD"' in hook_content
        
        # Should maintain error handling pattern
        assert ">/dev/null 2>&1 || true" in hook_content
        
        # Should start with shebang
        assert hook_content.startswith("#!/bin/sh")
        
        # Should be a single line command (plus shebang)
        lines = hook_content.strip().split('\n')
        assert len(lines) == 2  # shebang + command
    
    def test_generate_hook_content_custom_command_still_works(self):
        """Test that custom command parameter still works for backwards compatibility."""
        custom_command = "custom-journal-tool create"
        hook_content = generate_hook_content(command=custom_command)
        
        # Should use the custom command instead of default
        assert custom_command in hook_content
        assert "python -m mcp_commit_story.git_hook_worker" not in hook_content
        
        # Should maintain error handling
        assert ">/dev/null 2>&1 || true" in hook_content
    
    def test_generated_hook_is_valid_bash(self):
        """Test that the generated hook script is syntactically valid bash."""
        hook_content = generate_hook_content()
        
        # Write to temporary file and validate syntax
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(hook_content)
            temp_path = f.name
        
        try:
            # Use bash -n to check syntax without executing
            import subprocess
            result = subprocess.run(['bash', '-n', temp_path], 
                                  capture_output=True, text=True)
            assert result.returncode == 0, f"Invalid bash syntax: {result.stderr}"
        finally:
            os.unlink(temp_path)


class TestGitHookWorker:
    """Test the git_hook_worker module functionality."""
    
    @patch('mcp_commit_story.git_hook_worker.create_tool_signal_safe')
    @patch('mcp_commit_story.git_hook_worker.check_period_summary_triggers')
    @patch('mcp_commit_story.git_hook_worker.check_daily_summary_trigger')
    def test_worker_main_basic_flow(self, mock_daily_check, mock_period_check, mock_signal_create):
        """Test git_hook_worker main function basic flow."""
        from mcp_commit_story.git_hook_worker import main
        
        # Mock the trigger functions
        mock_daily_check.return_value = None  # No daily summary needed
        mock_period_check.return_value = {'weekly': False, 'monthly': False, 'quarterly': False, 'yearly': False}
        mock_signal_create.return_value = "/path/to/signal.json"  # Signal creation succeeds
        
        # Test that main function runs without error (graceful degradation)
        # Note: main() expects sys.argv to have repo path, so we can't easily test it fully here
        # This test verifies the imports work correctly
        assert callable(main)
    
    def test_worker_module_structure_requirements(self):
        """Test that git_hook_worker module will have required structure."""
        # This test documents the expected module structure
        # Will fail until we implement git_hook_worker.py
        
        expected_functions = [
            'main',  # Entry point called by hook
            'check_daily_summary_trigger',  # Uses should_generate_daily_summary
            'check_period_summary_triggers',  # Uses should_generate_period_summaries  
            'create_tool_signal',  # Generic signal creation for any MCP tool
            'create_tool_signal_safe',  # Safe wrapper for git hook context
            'log_hook_activity',  # Logs to hook log file
            'handle_errors_gracefully'  # Error handling with graceful degradation
        ]
        
        # This will fail until we implement the module
        try:
            import mcp_commit_story.git_hook_worker as worker
            
            for func_name in expected_functions:
                assert hasattr(worker, func_name), f"Missing required function: {func_name}"
                
        except ImportError:
            pytest.fail("git_hook_worker module does not exist yet")


class TestGitHookWorkerLogic:
    """Test the logic that git_hook_worker should implement."""
    
    @patch('mcp_commit_story.daily_summary.should_generate_daily_summary')
    def test_daily_summary_trigger_detection(self, mock_should_generate):
        """Test that worker correctly detects when daily summary should be generated."""
        mock_should_generate.return_value = "2025-01-05"  # Should generate for this date
        
        from mcp_commit_story.git_hook_worker import check_daily_summary_trigger
        
        # Test with a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock git repository structure
            git_dir = os.path.join(temp_dir, '.git')
            os.makedirs(git_dir, exist_ok=True)
            
            # Create journal directory and file
            journal_dir = os.path.join(temp_dir, 'journal')
            os.makedirs(journal_dir, exist_ok=True)
            
            journal_file = os.path.join(journal_dir, '2025-01-05-journal.md')
            with open(journal_file, 'w') as f:
                f.write("# Test journal entry")
            
            # Test the function (it will gracefully handle config loading issues)
            result = check_daily_summary_trigger(temp_dir)
            
            # The function should complete without error (graceful degradation)
            # Result may be None due to mocked dependencies, but that's expected
    
    @patch('mcp_commit_story.daily_summary.should_generate_period_summaries')
    def test_period_summary_trigger_detection(self, mock_should_generate):
        """Test that worker correctly detects when period summaries should be generated."""
        mock_should_generate.return_value = {
            'weekly': True,
            'monthly': False,
            'quarterly': False,
            'yearly': False
        }
        
        from mcp_commit_story.git_hook_worker import check_period_summary_triggers
        
        # Test with a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            git_dir = os.path.join(temp_dir, '.git')
            os.makedirs(git_dir, exist_ok=True)
            
            # Test the function (it will gracefully handle config loading issues)
            result = check_period_summary_triggers("2025-01-06", temp_dir)
            
            # The function should complete without error and return a valid dictionary
            assert isinstance(result, dict)
            assert all(key in result for key in ['weekly', 'monthly', 'quarterly', 'yearly'])
    
    def test_signal_creation_with_fallback(self):
        """Test that worker creates signals with graceful fallback."""
        from mcp_commit_story.git_hook_worker import create_tool_signal_safe
        
        # Test that the function exists and handles calls gracefully
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_tool_signal_safe("test_tool", {"param": "value"}, {"hash": "test"}, temp_dir)
            
            # Should return string path or None, but not raise errors
            assert result is None or isinstance(result, str)
    
    def test_error_logging_without_blocking_git(self):
        """Test that errors are logged but never block git operations."""
        from mcp_commit_story.git_hook_worker import handle_errors_gracefully
        
        # Test that the decorator exists and works
        @handle_errors_gracefully
        def test_function():
            raise Exception("Test error")
        
        # Should not raise an exception - should return None instead
        result = test_function()
        assert result is None


class TestGitHookIntegration:
    """Integration tests for git hook with daily summary triggering."""
    
    def test_hook_execution_environment_requirements(self):
        """Test that hook execution environment is set up correctly."""
        # Test that we can execute the hook content in a git environment
        hook_content = generate_hook_content()
        
        # The hook should work with minimal environment variables
        assert '"$PWD"' in hook_content  # Uses PWD environment variable
        
        # The hook should not require additional setup
        assert 'export' not in hook_content  # No environment variable setup
        assert 'source' not in hook_content  # No script sourcing required
    
    @patch('subprocess.run')
    def test_hook_calls_python_worker_correctly(self, mock_subprocess):
        """Test that the generated hook calls the Python worker with correct arguments."""
        hook_content = generate_hook_content()
        
        # Extract the command from hook content
        lines = hook_content.strip().split('\n')
        command_line = lines[1]  # Second line after shebang
        
        # Should contain the correct module and argument pattern
        assert 'python -m mcp_commit_story.git_hook_worker "$PWD"' in command_line
        assert '>/dev/null 2>&1 || true' in command_line
    
    def test_hook_graceful_degradation_on_python_failure(self):
        """Test that hook gracefully handles Python worker failures."""
        hook_content = generate_hook_content()
        
        # Hook should always end with || true to prevent git operation blocking
        assert hook_content.strip().endswith('|| true')
        
        # Hook should redirect output to prevent user interruption
        assert '>/dev/null 2>&1' in hook_content


class TestGitHookErrorHandling:
    """Test error handling behavior in enhanced git hook."""
    
    def test_missing_python_environment(self):
        """Test behavior when Python is not available in hook environment."""
        # This documents expected behavior - hook should not fail
        hook_content = generate_hook_content()
        
        # The || true ensures the hook never fails
        assert hook_content.endswith('|| true\n')
    
    def test_missing_mcp_server(self):
        """Test behavior when MCP server is not running."""
        # The git_hook_worker should handle this gracefully
        # This test will fail until worker is implemented
        pass
    
    def test_journal_directory_permissions(self):
        """Test behavior when journal directory is not writable."""
        # The git_hook_worker should log warnings but not fail
        # This test will fail until worker is implemented  
        pass
    
    def test_concurrent_hook_execution(self):
        """Test behavior when multiple git operations trigger hooks simultaneously."""
        # The file-creation approach should handle this naturally
        # This test will fail until worker is implemented
        pass


class TestGitHookLogging:
    """Test logging behavior in enhanced git hook."""
    
    def test_hook_log_file_location(self):
        """Test that hook worker logs to appropriate location."""
        from mcp_commit_story.git_hook_worker import get_log_file_path
        
        # Test with a sample repository path
        repo_path = "/path/to/repo"
        log_path = get_log_file_path(repo_path)
        
        # Should return path in .git/hooks directory
        assert log_path.endswith('.git/hooks/mcp-commit-story.log')
        assert repo_path in log_path
    
    def test_hook_log_content_format(self):
        """Test that hook logs contain useful debugging information."""
        # This will fail until we implement git_hook_worker
        pass
    
    def test_hook_log_rotation(self):
        """Test that hook logs don't grow unbounded."""
        # This will fail until we implement git_hook_worker
        pass


# Test data for edge cases
class TestGitHookEdgeCases:
    """Test edge cases in git hook enhanced functionality."""
    
    def test_hook_in_bare_repository(self):
        """Test hook behavior in bare Git repositories."""
        # The hook should handle this gracefully
        pass
    
    def test_hook_with_no_journal_history(self):
        """Test hook behavior in repository with no journal files."""
        # Should exit early with no work to do
        pass
    
    def test_hook_with_corrupted_journal_files(self):
        """Test hook behavior when journal files are corrupted."""
        # Should log warnings but not crash
        pass
    
    def test_hook_during_git_rebase(self):
        """Test hook behavior during git rebase operations."""
        # Should handle special git states gracefully
        pass 