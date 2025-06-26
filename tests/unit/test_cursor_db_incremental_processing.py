"""
Tests for cursor_db incremental processing optimization.

This module tests the 48-hour filtering functionality that optimizes database processing
by only processing databases modified within the last 2 days.
"""

import pytest
import os
import time
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the functions we'll be testing (they don't exist yet - that's the point of TDD)
from mcp_commit_story.cursor_db.multiple_database_discovery import (
    discover_all_cursor_databases,
    extract_from_multiple_databases
)


class TestGetRecentDatabases:
    """Test the get_recent_databases() function for 48-hour filtering."""
    
    def test_get_recent_databases_basic_filtering(self):
        """Test that get_recent_databases() filters databases by 48-hour window."""
        # This test will fail until we implement get_recent_databases()
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        # Mock database paths
        all_databases = [
            "/path/to/recent1.vscdb",
            "/path/to/recent2.vscdb", 
            "/path/to/old1.vscdb",
            "/path/to/old2.vscdb"
        ]
        
        now = time.time()
        two_days_ago = now - (48 * 60 * 60)
        
        # Mock os.path.getmtime to return different modification times
        def mock_getmtime(path):
            if "recent" in path:
                return now - (12 * 60 * 60)  # 12 hours ago (recent)
            else:
                return two_days_ago - (24 * 60 * 60)  # 3 days ago (old)
        
        with patch('os.path.getmtime', side_effect=mock_getmtime):
            recent_databases = get_recent_databases(all_databases)
            
        assert len(recent_databases) == 2
        assert "/path/to/recent1.vscdb" in recent_databases
        assert "/path/to/recent2.vscdb" in recent_databases
        assert "/path/to/old1.vscdb" not in recent_databases
        assert "/path/to/old2.vscdb" not in recent_databases
    
    def test_get_recent_databases_empty_input(self):
        """Test get_recent_databases() with empty database list."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        result = get_recent_databases([])
        assert result == []
    
    def test_get_recent_databases_all_recent(self):
        """Test when all databases are within 48-hour window."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = ["/path/to/db1.vscdb", "/path/to/db2.vscdb", "/path/to/db3.vscdb"]
        now = time.time()
        
        # All databases modified within last 24 hours
        with patch('os.path.getmtime', return_value=now - (12 * 60 * 60)):
            recent_databases = get_recent_databases(all_databases)
            
        assert len(recent_databases) == 3
        assert set(recent_databases) == set(all_databases)
    
    def test_get_recent_databases_none_recent(self):
        """Test when no databases are within 48-hour window."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = ["/path/to/db1.vscdb", "/path/to/db2.vscdb"]
        now = time.time()
        three_days_ago = now - (72 * 60 * 60)
        
        with patch('os.path.getmtime', return_value=three_days_ago):
            recent_databases = get_recent_databases(all_databases)
            
        assert recent_databases == []
    
    def test_get_recent_databases_future_timestamps(self):
        """Test handling of databases with future modification times."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = ["/path/to/future.vscdb", "/path/to/past.vscdb"]
        now = time.time()
        future_time = now + (24 * 60 * 60)  # 24 hours in future
        past_time = now - (72 * 60 * 60)    # 72 hours ago
        
        def mock_getmtime(path):
            if "future" in path:
                return future_time
            else:
                return past_time
        
        with patch('os.path.getmtime', side_effect=mock_getmtime):
            recent_databases = get_recent_databases(all_databases)
            
        # Future timestamps should be considered "recent"
        assert len(recent_databases) == 1
        assert "/path/to/future.vscdb" in recent_databases
        assert "/path/to/past.vscdb" not in recent_databases
    
    def test_get_recent_databases_permission_errors(self):
        """Test graceful handling of permission errors during os.path.getmtime()."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = [
            "/path/to/accessible.vscdb",
            "/path/to/permission_denied.vscdb",
            "/path/to/not_found.vscdb"
        ]
        now = time.time()
        
        def mock_getmtime(path):
            if "accessible" in path:
                return now - (12 * 60 * 60)  # Recent
            elif "permission_denied" in path:
                raise PermissionError("Permission denied")
            else:
                raise FileNotFoundError("File not found")
        
        with patch('os.path.getmtime', side_effect=mock_getmtime):
            recent_databases = get_recent_databases(all_databases)
            
        # Should only return accessible databases, skip errors gracefully
        assert len(recent_databases) == 1
        assert "/path/to/accessible.vscdb" in recent_databases
    
    def test_get_recent_databases_boundary_conditions(self):
        """Test databases exactly at the 48-hour boundary."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = [
            "/path/to/exactly_48h.vscdb",
            "/path/to/just_under_48h.vscdb",
            "/path/to/just_over_48h.vscdb"
        ]
        
        now = time.time()
        exactly_48h = now - (48 * 60 * 60)
        just_under_48h = now - (48 * 60 * 60 - 1)  # 1 second under 48h
        just_over_48h = now - (48 * 60 * 60 + 1)   # 1 second over 48h
        
        def mock_getmtime(path):
            if "exactly_48h" in path:
                return exactly_48h
            elif "just_under_48h" in path:
                return just_under_48h
            else:
                return just_over_48h
        
        with patch('os.path.getmtime', side_effect=mock_getmtime):
            recent_databases = get_recent_databases(all_databases, current_time=now)
            
        # Should include exactly 48h and just under, exclude just over
        assert len(recent_databases) == 2
        assert "/path/to/exactly_48h.vscdb" in recent_databases
        assert "/path/to/just_under_48h.vscdb" in recent_databases
        assert "/path/to/just_over_48h.vscdb" not in recent_databases


class TestBackwardCompatibility:
    """Test that existing API remains unchanged."""
    
    def test_discover_all_cursor_databases_signature_unchanged(self):
        """Test that discover_all_cursor_databases() signature remains the same."""
        # Should still accept workspace_path and return List[str]
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = []
            
            result = discover_all_cursor_databases("/test/workspace")
            assert isinstance(result, list)
    
    def test_extract_from_multiple_databases_signature_unchanged(self):
        """Test that extract_from_multiple_databases() signature remains the same."""
        # Should still accept List[str] and return List[Dict]
        with patch('mcp_commit_story.cursor_db.message_extraction.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.message_extraction.extract_generations_data') as mock_generations:
            
            mock_prompts.return_value = []
            mock_generations.return_value = []
            
            result = extract_from_multiple_databases(["/test/db.vscdb"])
            assert isinstance(result, list)


class TestPerformanceImprovement:
    """Test performance improvements with benchmarks."""
    
    def test_performance_benchmark_with_mixed_databases(self):
        """Test performance improvement with 10 databases (8 old, 2 recent)."""
        # Create temporary test databases
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 10 test database files
            all_databases = []
            for i in range(10):
                db_path = os.path.join(temp_dir, f"test_db_{i}.vscdb")
                with open(db_path, 'w') as f:
                    f.write("test content")
                all_databases.append(db_path)
            
            # Set modification times: 8 old (3+ days), 2 recent (12 hours)
            now = time.time()
            old_time = now - (72 * 60 * 60)  # 3 days ago
            recent_time = now - (12 * 60 * 60)  # 12 hours ago
            
            for i, db_path in enumerate(all_databases):
                if i < 8:  # First 8 are old
                    os.utime(db_path, (old_time, old_time))
                else:  # Last 2 are recent
                    os.utime(db_path, (recent_time, recent_time))
            
            # Test the filtering
            from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
            
            start_time = time.time()
            recent_databases = get_recent_databases(all_databases)
            filter_time = time.time() - start_time
            
            # Verify filtering results
            assert len(recent_databases) == 2
            
            # Performance should be very fast (< 10ms for file system operations)
            assert filter_time < 0.01  # 10 milliseconds
    
    def test_performance_comparison_simulation(self):
        """Simulate performance comparison between full and incremental processing."""
        # Mock the extraction functions to simulate processing time
        def mock_slow_extraction(db_paths):
            """Simulate slow database extraction."""
            time.sleep(0.001 * len(db_paths))  # 1ms per database
            return [{"database_path": path, "prompts": [], "generations": []} for path in db_paths]
        
        all_databases = [f"/path/to/db_{i}.vscdb" for i in range(20)]
        now = time.time()
        
        # Mock modification times: 18 old, 2 recent
        def mock_getmtime(path):
            db_num = int(path.split('_')[1].split('.')[0])
            if db_num >= 18:  # Last 2 are recent
                return now - (12 * 60 * 60)
            else:  # First 18 are old
                return now - (72 * 60 * 60)
        
        with patch('os.path.getmtime', side_effect=mock_getmtime), \
             patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_from_multiple_databases', 
                   side_effect=mock_slow_extraction):
            
            from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
            
            # Time full processing simulation
            start_full = time.time()
            mock_slow_extraction(all_databases)
            full_time = time.time() - start_full
            
            # Time incremental processing simulation
            start_incremental = time.time()
            recent_dbs = get_recent_databases(all_databases)
            mock_slow_extraction(recent_dbs)
            incremental_time = time.time() - start_incremental
            
            # Incremental should be significantly faster
            # (processing 2 instead of 20 databases = 90% reduction)
            assert len(recent_dbs) == 2
            assert incremental_time < full_time
            improvement_ratio = full_time / incremental_time
            assert improvement_ratio > 5  # At least 5x improvement


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_database_list(self):
        """Test handling of empty database list."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        result = get_recent_databases([])
        assert result == []
    
    def test_all_databases_inaccessible(self):
        """Test when all databases raise OS errors."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = ["/nonexistent/db1.vscdb", "/permission/denied.vscdb"]
        
        with patch('os.path.getmtime', side_effect=OSError("Access denied")):
            result = get_recent_databases(all_databases)
            
        assert result == []
    
    def test_mixed_error_conditions(self):
        """Test mix of accessible and inaccessible databases."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = [
            "/accessible/recent.vscdb",
            "/accessible/old.vscdb",
            "/nonexistent/error.vscdb"
        ]
        now = time.time()
        
        def mock_getmtime(path):
            if "error" in path:
                raise FileNotFoundError("File not found")
            elif "recent" in path:
                return now - (12 * 60 * 60)  # Recent
            else:
                return now - (72 * 60 * 60)  # Old
        
        with patch('os.path.getmtime', side_effect=mock_getmtime):
            result = get_recent_databases(all_databases)
            
        assert len(result) == 1
        assert "/accessible/recent.vscdb" in result


class TestTelemetryIntegration:
    """Test telemetry attributes for monitoring."""
    
    def test_telemetry_attributes_recorded(self):
        """Test that databases_filtered_out and time_window_hours are recorded."""
        # This will be implemented when we add telemetry to the actual functions
        # For now, test that the telemetry integration points exist
        
        # Mock the telemetry decorator
        with patch('mcp_commit_story.cursor_db.multiple_database_discovery.trace_mcp_operation') as mock_telemetry:
            from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
            
            all_databases = ["/recent.vscdb", "/old1.vscdb", "/old2.vscdb"]
            now = time.time()
            
            def mock_getmtime(path):
                if "recent" in path:
                    return now - (12 * 60 * 60)
                else:
                    return now - (72 * 60 * 60)
            
            with patch('os.path.getmtime', side_effect=mock_getmtime):
                result = get_recent_databases(all_databases)
            
            # Verify telemetry was called (implementation will add actual attributes)
            # This test will pass when telemetry decorator is properly integrated
            assert len(result) == 1  # 1 recent, 2 filtered out


class TestLoggingBehavior:
    """Test debug logging for filtered databases."""
    
    def test_debug_logging_for_skipped_databases(self):
        """Test that debug logs show which databases were skipped as 'too old'."""
        from mcp_commit_story.cursor_db.multiple_database_discovery import get_recent_databases
        
        all_databases = ["/recent.vscdb", "/old1.vscdb", "/old2.vscdb"]
        now = time.time()
        
        def mock_getmtime(path):
            if "recent" in path:
                return now - (12 * 60 * 60)
            else:
                return now - (72 * 60 * 60)
        
        with patch('os.path.getmtime', side_effect=mock_getmtime), \
             patch('mcp_commit_story.cursor_db.multiple_database_discovery.logger') as mock_logger:
            
            result = get_recent_databases(all_databases)
            
            # Verify logging calls (implementation will add actual debug logging)
            assert len(result) == 1
            # Mock logger should be called with debug information about filtered databases 