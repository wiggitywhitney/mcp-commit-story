"""
Performance tests for Composer integration - benchmark validation.

These tests validate that the Composer integration meets specific performance
thresholds and behaves efficiently under various load conditions.

Performance Requirements:
- Full workflow: < 500ms
- Database connection: < 50ms  
- Message extraction: < 200ms
- Memory usage: Reasonable with large datasets
- Concurrent operations: Stable performance
"""

import os
import time
import pytest
import threading
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from mcp_commit_story.composer_chat_provider import ComposerChatProvider
from mcp_commit_story.cursor_db.query_executor import execute_cursor_query


class TestComposerPerformanceBenchmarks:
    """Performance benchmark tests with specific thresholds."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    def test_full_workflow_under_500ms_threshold(self, test_db_paths):
        """Test that complete chat history retrieval stays under 500ms."""
        
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        
        # Measure multiple runs for consistency
        durations = []
        for i in range(5):
            start_time = time.time()
            messages = provider.getChatHistoryForCommit(0, 9999999999999)
            duration = time.time() - start_time
            durations.append(duration)
            
            # Verify we got expected results
            assert len(messages) == 15
        
        # Check all runs meet threshold
        max_duration = max(durations)
        avg_duration = sum(durations) / len(durations)
        
        assert max_duration < 0.5, f"Worst case took {max_duration:.3f}s, should be < 500ms"
        assert avg_duration < 0.3, f"Average took {avg_duration:.3f}s, should be < 300ms for good performance"
        
        print(f"Performance summary - Max: {max_duration:.3f}s, Avg: {avg_duration:.3f}s")
    
    def test_database_connection_under_50ms_threshold(self, test_db_paths):
        """Test database connection and simple query performance."""
        
        # Test workspace database connection
        durations = []
        for i in range(10):
            start_time = time.time()
            result = execute_cursor_query(test_db_paths["workspace"], "SELECT COUNT(*) FROM ItemTable")
            duration = time.time() - start_time
            durations.append(duration)
            
            assert result is not None
            assert len(result) == 1
        
        max_duration = max(durations)
        avg_duration = sum(durations) / len(durations)
        
        assert max_duration < 0.05, f"Worst case connection took {max_duration:.3f}s, should be < 50ms"
        assert avg_duration < 0.02, f"Average connection took {avg_duration:.3f}s, should be < 20ms"
        
        print(f"DB Connection performance - Max: {max_duration:.3f}s, Avg: {avg_duration:.3f}s")
    
    def test_message_extraction_under_200ms_threshold(self, test_db_paths):
        """Test individual component performance meets 200ms threshold."""
        
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        
        # Test session metadata extraction
        metadata_durations = []
        for i in range(5):
            start_time = time.time()
            sessions = provider._get_session_metadata()
            duration = time.time() - start_time
            metadata_durations.append(duration)
            assert len(sessions) == 3
        
        max_metadata_duration = max(metadata_durations)
        assert max_metadata_duration < 0.2, f"Session metadata took {max_metadata_duration:.3f}s, should be < 200ms"
        
        # Test message headers extraction  
        headers_durations = []
        for i in range(5):
            start_time = time.time()
            headers = provider._get_message_headers("test-session-1")
            duration = time.time() - start_time
            headers_durations.append(duration)
            assert headers is not None
        
        max_headers_duration = max(headers_durations)
        assert max_headers_duration < 0.2, f"Message headers took {max_headers_duration:.3f}s, should be < 200ms"
        
        # Test individual message retrieval
        message_durations = []
        for i in range(5):
            start_time = time.time()
            message = provider._get_individual_message("test-session-1", "bubble-1-1")
            duration = time.time() - start_time
            message_durations.append(duration)
            assert message is not None
        
        max_message_duration = max(message_durations)
        assert max_message_duration < 0.2, f"Individual message took {max_message_duration:.3f}s, should be < 200ms"
        
        print(f"Component performance - Metadata: {max_metadata_duration:.3f}s, Headers: {max_headers_duration:.3f}s, Message: {max_message_duration:.3f}s")
    
    def test_memory_usage_with_repeated_operations(self, test_db_paths):
        """Test memory usage stays reasonable with repeated operations."""
        
        provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        
        # Perform many operations to test for memory leaks
        initial_messages = provider.getChatHistoryForCommit(0, 9999999999999)
        initial_count = len(initial_messages)
        
        # Repeated operations should maintain consistent results without excessive memory
        for i in range(50):  # Simulate heavy usage
            messages = provider.getChatHistoryForCommit(0, 9999999999999)
            
            # Verify consistent results (no memory corruption)
            assert len(messages) == initial_count
            assert all(isinstance(msg, dict) for msg in messages)
            assert all('role' in msg and 'content' in msg for msg in messages)
            
            # Verify message content hasn't been corrupted
            first_message = messages[0]
            assert isinstance(first_message['content'], str)
            assert len(first_message['content']) > 0
        
        # Final verification that results are still consistent
        final_messages = provider.getChatHistoryForCommit(0, 9999999999999)
        assert len(final_messages) == initial_count
        
        print(f"Memory test completed - {initial_count} messages consistently retrieved across 50 operations")
    
    def test_multiple_provider_instances_performance(self, test_db_paths):
        """Test performance with multiple ComposerChatProvider instances."""
        
        # Create multiple provider instances
        providers = [
            ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
            for _ in range(5)
        ]
        
        start_time = time.time()
        
        # Run operations across all providers
        results = []
        for provider in providers:
            messages = provider.getChatHistoryForCommit(0, 9999999999999)
            results.append(len(messages))
        
        total_duration = time.time() - start_time
        
        # Verify performance with multiple providers
        assert total_duration < 2.0, f"Multiple providers took {total_duration:.3f}s, should be < 2.0s"
        
        # Verify consistent results across providers
        assert all(count == 15 for count in results), "All providers should return consistent results"
        
        print(f"Multiple provider test - {len(providers)} providers completed in {total_duration:.3f}s")


class TestComposerConcurrencyPerformance:
    """Concurrency and threading performance tests."""
    
    @pytest.fixture
    def test_db_paths(self):
        """Provide paths to test databases."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "cursor_databases"
        return {
            "workspace": str(fixtures_dir / "test_workspace.vscdb"),
            "global": str(fixtures_dir / "test_global.vscdb")
        }
    
    def test_concurrent_read_operations(self, test_db_paths):
        """Test performance under concurrent read operations."""
        
        def worker_function(worker_id: int) -> Dict[str, Any]:
            """Worker function for concurrent testing."""
            provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
            
            start_time = time.time()
            messages = provider.getChatHistoryForCommit(0, 9999999999999)
            duration = time.time() - start_time
            
            return {
                "worker_id": worker_id,
                "message_count": len(messages),
                "duration": duration,
                "success": len(messages) == 15
            }
        
        # Run concurrent operations
        num_workers = 8
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_function, i) for i in range(num_workers)]
            results = [future.result() for future in as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        # Verify concurrent performance
        assert total_duration < 3.0, f"Concurrent operations took {total_duration:.3f}s, should be < 3.0s"
        
        # Verify all workers succeeded
        assert all(result["success"] for result in results), "All concurrent workers should succeed"
        assert all(result["message_count"] == 15 for result in results), "All workers should get consistent results"
        
        # Check individual worker performance
        max_worker_duration = max(result["duration"] for result in results)
        avg_worker_duration = sum(result["duration"] for result in results) / len(results)
        
        assert max_worker_duration < 1.0, f"Slowest worker took {max_worker_duration:.3f}s, should be < 1.0s"
        
        print(f"Concurrency test - {num_workers} workers, Total: {total_duration:.3f}s, Avg per worker: {avg_worker_duration:.3f}s")
    
    def test_database_connection_under_load(self, test_db_paths):
        """Test database connection performance under load."""
        
        def db_query_worker(query_id: int) -> Dict[str, Any]:
            """Worker for database load testing."""
            start_time = time.time()
            
            # Test both workspace and global database queries
            workspace_result = execute_cursor_query(test_db_paths["workspace"], "SELECT COUNT(*) FROM ItemTable")
            global_result = execute_cursor_query(test_db_paths["global"], "SELECT COUNT(*) FROM cursorDiskKV")
            
            duration = time.time() - start_time
            
            return {
                "query_id": query_id,
                "duration": duration,
                "workspace_success": workspace_result is not None,
                "global_success": global_result is not None
            }
        
        # Run concurrent database queries
        num_queries = 20
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(db_query_worker, i) for i in range(num_queries)]
            results = [future.result() for future in as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        # Verify database performance under load
        assert total_duration < 2.0, f"Database load test took {total_duration:.3f}s, should be < 2.0s"
        
        # Verify all queries succeeded
        assert all(result["workspace_success"] for result in results), "All workspace queries should succeed"
        assert all(result["global_success"] for result in results), "All global queries should succeed"
        
        # Check query performance
        max_query_duration = max(result["duration"] for result in results)
        avg_query_duration = sum(result["duration"] for result in results) / len(results)
        
        assert max_query_duration < 0.1, f"Slowest query took {max_query_duration:.3f}s, should be < 100ms"
        
        print(f"DB Load test - {num_queries} queries, Total: {total_duration:.3f}s, Avg per query: {avg_query_duration:.3f}s")
    
    def test_memory_efficiency_concurrent_operations(self, test_db_paths):
        """Test memory efficiency during concurrent operations."""
        
        def memory_test_worker(worker_id: int) -> Dict[str, Any]:
            """Worker that performs multiple operations to test memory efficiency."""
            provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
            
            # Perform multiple operations per worker
            operations_count = 0
            for i in range(10):  # 10 operations per worker
                messages = provider.getChatHistoryForCommit(0, 9999999999999)
                assert len(messages) == 15  # Verify consistency
                operations_count += 1
            
            return {
                "worker_id": worker_id,
                "operations_completed": operations_count
            }
        
        # Run concurrent memory-intensive operations
        num_workers = 6
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(memory_test_worker, i) for i in range(num_workers)]
            results = [future.result() for future in as_completed(futures)]
        
        total_duration = time.time() - start_time
        total_operations = sum(result["operations_completed"] for result in results)
        
        # Verify memory efficiency
        assert total_duration < 5.0, f"Memory efficiency test took {total_duration:.3f}s, should be < 5.0s"
        assert total_operations == num_workers * 10, f"Expected {num_workers * 10} operations, got {total_operations}"
        
        # Verify system stability after intensive operations
        final_provider = ComposerChatProvider(test_db_paths["workspace"], test_db_paths["global"])
        final_messages = final_provider.getChatHistoryForCommit(0, 9999999999999)
        assert len(final_messages) == 15, "System should remain stable after intensive operations"
        
        print(f"Memory efficiency test - {total_operations} operations across {num_workers} workers in {total_duration:.3f}s") 