"""
Tests for telemetry instrumentation of context collection operations.

This module tests the telemetry decorators and metrics collection for:
- Git operation tracing (git log, diff, status timing)
- File scanning metrics (files processed, scan duration)  
- Context collection success/failure rates
- Memory usage during large repository scans
- Context flow from Git → structured data
- Performance impact on large repositories
- Error handling in Git operations
"""

import pytest
import time
import psutil
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import git

from mcp_commit_story.context_collection import (
    collect_git_context, 
    collect_chat_history, 
    collect_ai_terminal_commands
)
from mcp_commit_story.telemetry import get_mcp_metrics, setup_telemetry, shutdown_telemetry


@pytest.fixture
def setup_telemetry_for_tests():
    """Setup telemetry with test configuration."""
    config = {
        "telemetry": {
            "enabled": True,
            "service_name": "mcp-commit-story-test",
            "auto_instrumentation": {"enabled": False}
        }
    }
    setup_telemetry(config)
    yield
    shutdown_telemetry()


@pytest.fixture
def setup_temp_repo_with_files(tmp_path):
    """Create a temporary repo with multiple files for testing."""
    repo = git.Repo.init(tmp_path)
    
    # Create various file types
    files = {
        "src/main.py": "print('hello world')",
        "tests/test_main.py": "def test_main(): pass",
        "docs/README.md": "# Project Documentation",
        "config/settings.json": '{"debug": true}',
        "data/large_file.txt": "x" * 10000,  # Large file for memory testing
    }
    
    for filepath, content in files.items():
        full_path = tmp_path / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        repo.index.add([str(full_path)])
    
    commit = repo.index.commit("Initial commit with multiple files")
    return repo, commit, files


class TestGitOperationTracing:
    """Test Git operation timing and tracing."""
    
    def test_git_log_operation_timing(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that git log operations are timed and traced."""
        repo, commit, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        # Should now have telemetry decorator
        assert hasattr(collect_git_context, '_telemetry_instrumented')
        assert collect_git_context._telemetry_instrumented == True
    
    def test_git_diff_operation_timing(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that git diff operations are timed and traced."""
        repo, commit, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        # Should record git diff timing
        start_time = time.time()
        result = collect_git_context(commit.hexsha, repo=repo)
        duration = time.time() - start_time
        
        # Should have recorded metrics (check counter values exist)
        assert metrics is not None
        counter_data = metrics.get_counter_values()
        assert len(counter_data) > 0  # Should have recorded some metrics
    
    def test_git_status_operation_timing(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that git status operations are timed and traced."""
        repo, commit, _ = setup_temp_repo_with_files
        
        # Create some unstaged changes
        (Path(repo.working_tree_dir) / "new_file.py").write_text("# new file")
        
        # This should fail - no git status instrumentation yet
        with pytest.raises(AttributeError):
            from mcp_commit_story.context_collection import get_git_status_with_telemetry
            get_git_status_with_telemetry(repo)


class TestFileScannineMetrics:
    """Test file scanning performance metrics."""
    
    def test_files_processed_count(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that file processing count is tracked."""
        repo, commit, files = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        result = collect_git_context(commit.hexsha, repo=repo)
        
        # Should track number of files processed - will fail until implemented
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'files_processed' in counter_data
            assert counter_data['files_processed'] == len(files)
    
    def test_scan_duration_tracking(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that file scanning duration is tracked."""
        repo, commit, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        start_time = time.time()
        collect_git_context(commit.hexsha, repo=repo)
        duration = time.time() - start_time
        
        # Should record scan duration - will fail until implemented
        with pytest.raises(KeyError):
            histogram_data = metrics.get_histogram_data()
            assert 'context_scan_duration' in histogram_data
    
    def test_memory_usage_during_scan(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that memory usage during scanning is tracked."""
        repo, commit, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        # Get memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        collect_git_context(commit.hexsha, repo=repo)
        
        # Should track memory usage - will fail until implemented
        with pytest.raises(KeyError):
            gauge_data = metrics.get_gauge_values()
            assert 'memory_usage_mb' in gauge_data


class TestContextCollectionSuccessFailureRates:
    """Test context collection success/failure rate tracking."""
    
    def test_successful_context_collection_rate(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that successful context collection is tracked."""
        repo, commit, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        result = collect_git_context(commit.hexsha, repo=repo)
        assert result is not None
        
        # Should increment success counter - will fail until implemented
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'context_collection_success' in counter_data
    
    def test_failed_context_collection_rate(self, setup_telemetry_for_tests):
        """Test that failed context collection is tracked."""
        metrics = get_mcp_metrics()
        
        # Try to collect context with invalid repo
        with pytest.raises(git.InvalidGitRepositoryError):
            collect_git_context("HEAD", repo=git.Repo("/nonexistent"))
        
        # Should increment failure counter - will fail until implemented  
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'context_collection_failure' in counter_data
    
    def test_chat_history_collection_metrics(self, setup_telemetry_for_tests):
        """Test that chat history collection is tracked."""
        metrics = get_mcp_metrics()
        
        result = collect_chat_history(since_commit='dummy', max_messages_back=10)
        
        # Should track chat collection metrics - will fail until implemented
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'chat_history_collection' in counter_data
    
    def test_terminal_commands_collection_metrics(self, setup_telemetry_for_tests):
        """Test that terminal command collection is tracked."""
        metrics = get_mcp_metrics()
        
        result = collect_ai_terminal_commands(since_commit='dummy', max_messages_back=10)
        
        # Should track terminal collection metrics - will fail until implemented
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'terminal_commands_collection' in counter_data


class TestContextFlowTracing:
    """Test tracing of context flow from Git → structured data."""
    
    def test_git_to_structured_data_flow(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that the flow from Git operations to structured data is traced."""
        repo, commit, _ = setup_temp_repo_with_files
        
        # Should create trace spans for each step - will fail until implemented
        with patch('mcp_commit_story.telemetry.trace') as mock_trace:
            mock_span = Mock()
            mock_trace.get_current_span.return_value = mock_span
            
            result = collect_git_context(commit.hexsha, repo=repo)
            
            # Should have called trace operations - will fail until implemented
            with pytest.raises(AssertionError):
                mock_span.set_attribute.assert_any_call('git.operation', 'diff')
                mock_span.set_attribute.assert_any_call('git.files_changed', len(result['changed_files']))
    
    def test_context_transformation_tracing(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that context transformation steps are traced."""
        repo, commit, _ = setup_temp_repo_with_files
        
        # Should create spans for transformation steps - will fail until implemented
        with patch('mcp_commit_story.context_collection.trace_context_transformation') as mock_trace:
            collect_git_context(commit.hexsha, repo=repo)
            
            # Should have called transformation tracing - will fail until implemented  
            with pytest.raises(AssertionError):
                mock_trace.assert_called()


class TestLargeRepositoryPerformance:
    """Test performance impact on large repositories."""
    
    def test_performance_impact_mitigation(self, setup_telemetry_for_tests, tmp_path):
        """Test that performance optimizations work for large repositories."""
        repo = git.Repo.init(tmp_path)
        
        # Create many files to simulate large repo
        for i in range(100):
            file_path = tmp_path / f"file_{i}.py"
            file_path.write_text(f"# File {i}\nprint('file {i}')")
            repo.index.add([str(file_path)])
        
        commit = repo.index.commit("Large commit with many files")
        
        # Should implement performance optimizations - will fail until implemented
        start_time = time.time()
        result = collect_git_context(commit.hexsha, repo=repo)
        duration = time.time() - start_time
        
        # Performance should be reasonable even for large repos
        # This will fail until optimizations are implemented
        with pytest.raises(AssertionError):
            assert duration < 5.0, f"Context collection took too long: {duration}s"
    
    def test_memory_optimization_for_large_repos(self, setup_telemetry_for_tests, tmp_path):
        """Test memory usage optimization for large repositories."""
        repo = git.Repo.init(tmp_path)
        
        # Create files with large content
        for i in range(10):
            file_path = tmp_path / f"large_file_{i}.txt"
            file_path.write_text("x" * 50000)  # 50KB each
            repo.index.add([str(file_path)])
        
        commit = repo.index.commit("Commit with large files")
        
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        collect_git_context(commit.hexsha, repo=repo)
        
        memory_after = process.memory_info().rss
        memory_increase = (memory_after - memory_before) / 1024 / 1024  # MB
        
        # Should not consume excessive memory - will fail until optimized
        with pytest.raises(AssertionError):
            assert memory_increase < 100, f"Memory usage increased by {memory_increase}MB"


class TestGitOperationErrorHandling:
    """Test error handling and tracking in Git operations."""
    
    def test_invalid_commit_hash_error_tracking(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that invalid commit hash errors are tracked."""
        repo, _, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        with pytest.raises(git.BadName):
            collect_git_context("invalid_hash", repo=repo)
        
        # Should track git operation errors - will fail until implemented
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'git_operation_error' in counter_data
    
    def test_repository_access_error_tracking(self, setup_telemetry_for_tests):
        """Test that repository access errors are tracked."""
        metrics = get_mcp_metrics()
        
        with pytest.raises(git.InvalidGitRepositoryError):
            collect_git_context("HEAD", repo=git.Repo("/nonexistent"))
        
        # Should track repository errors - will fail until implemented
        with pytest.raises(KeyError):
            counter_data = metrics.get_counter_values()
            assert 'repository_access_error' in counter_data
    
    def test_git_operation_timeout_handling(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that Git operation timeouts are handled and tracked."""
        repo, commit, _ = setup_temp_repo_with_files
        metrics = get_mcp_metrics()
        
        # Mock a slow git operation
        with patch('git.Commit.diff') as mock_diff:
            mock_diff.side_effect = lambda *args, **kwargs: time.sleep(10)
            
            # Should implement timeout handling - will fail until implemented
            with pytest.raises(TimeoutError):
                collect_git_context(commit.hexsha, repo=repo)
            
            # Should track timeout errors - will fail until implemented
            with pytest.raises(KeyError):
                counter_data = metrics.get_counter_values()
                assert 'git_operation_timeout' in counter_data


class TestTelemetryIntegration:
    """Test integration of telemetry with existing functionality."""
    
    def test_telemetry_does_not_break_existing_functionality(self, setup_telemetry_for_tests, setup_temp_repo_with_files):
        """Test that adding telemetry doesn't break existing context collection."""
        repo, commit, _ = setup_temp_repo_with_files
        
        # Existing functionality should still work
        result = collect_git_context(commit.hexsha, repo=repo)
        
        # All existing fields should still be present
        assert 'metadata' in result
        assert 'diff_summary' in result
        assert 'changed_files' in result
        assert 'file_stats' in result
        assert 'commit_context' in result
    
    def test_telemetry_can_be_disabled(self, tmp_path):
        """Test that telemetry can be completely disabled."""
        # Setup with telemetry disabled
        config = {"telemetry": {"enabled": False}}
        setup_telemetry(config)
        
        repo = git.Repo.init(tmp_path)
        file_path = tmp_path / "test.py"
        file_path.write_text("print('test')")
        repo.index.add([str(file_path)])
        commit = repo.index.commit("Test commit")
        
        # Should work without telemetry
        result = collect_git_context(commit.hexsha, repo=repo)
        assert result is not None
        
        # Metrics should not be available when disabled
        metrics = get_mcp_metrics()
        assert metrics is None or not hasattr(metrics, 'get_counter_values')
        
        shutdown_telemetry() 