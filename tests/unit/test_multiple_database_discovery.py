"""
Tests for multiple database discovery functionality.

This module tests the functions that discover and extract data from multiple
Cursor databases to handle database rotation after 100 generations.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from mcp_commit_story.cursor_db.multiple_database_discovery import (
    discover_all_cursor_databases,
    extract_from_multiple_databases
)


class TestDiscoverAllCursorDatabases:
    """Test the discover_all_cursor_databases function."""
    
    def test_finds_multiple_state_vscdb_files(self):
        """Test finding multiple state.vscdb files in subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = temp_dir
            cursor_dir = os.path.join(workspace_path, ".cursor")
            os.makedirs(cursor_dir)
            
            # Create multiple database files in different subdirectories
            db1_dir = os.path.join(cursor_dir, "session1")
            db2_dir = os.path.join(cursor_dir, "session2", "nested")
            os.makedirs(db1_dir)
            os.makedirs(db2_dir)
            
            db1_path = os.path.join(db1_dir, "state.vscdb")
            db2_path = os.path.join(db2_dir, "state.vscdb")
            db3_path = os.path.join(cursor_dir, "state.vscdb")  # Root level
            
            # Create the database files
            for db_path in [db1_path, db2_path, db3_path]:
                with open(db_path, 'w') as f:
                    f.write("fake database content")
            
            # Create non-database files that should be ignored
            with open(os.path.join(cursor_dir, "other.db"), 'w') as f:
                f.write("not a state.vscdb file")
            
            result = discover_all_cursor_databases(workspace_path)
            
            # Should find all 3 state.vscdb files
            assert len(result) == 3
            assert db1_path in result
            assert db2_path in result
            assert db3_path in result
            
            # Should not include other files
            assert not any("other.db" in path for path in result)
    
    def test_recursive_search_through_cursor_directory(self):
        """Test recursive search through .cursor directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = temp_dir
            
            # Create deep nested structure
            deep_path = os.path.join(workspace_path, ".cursor", "a", "b", "c", "d")
            os.makedirs(deep_path)
            
            db_path = os.path.join(deep_path, "state.vscdb")
            with open(db_path, 'w') as f:
                f.write("deep database")
            
            result = discover_all_cursor_databases(workspace_path)
            
            assert len(result) == 1
            assert db_path in result
    
    def test_handles_permission_errors_gracefully(self):
        """Test handling of permission errors and inaccessible directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = temp_dir
            cursor_dir = os.path.join(workspace_path, ".cursor")
            os.makedirs(cursor_dir)
            
            # Create accessible database
            accessible_db = os.path.join(cursor_dir, "state.vscdb")
            with open(accessible_db, 'w') as f:
                f.write("accessible database")
            
            # Mock os.walk to simulate permission error
            def mock_walk(path):
                if path == cursor_dir:
                    yield cursor_dir, ["subdir"], ["state.vscdb"]
                    # Simulate permission error on subdirectory
                    raise PermissionError("Permission denied")
            
            with patch('os.walk', side_effect=mock_walk):
                result = discover_all_cursor_databases(workspace_path)
                
                # Should still find the accessible database
                assert len(result) == 1
                assert accessible_db in result
    
    def test_returns_empty_list_when_no_cursor_directory(self):
        """Test returns empty list when .cursor directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = discover_all_cursor_databases(temp_dir)
            assert result == []
    
    def test_returns_empty_list_when_no_databases_found(self):
        """Test returns empty list when no state.vscdb files found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cursor_dir = os.path.join(temp_dir, ".cursor")
            os.makedirs(cursor_dir)
            
            # Create non-database files
            with open(os.path.join(cursor_dir, "config.json"), 'w') as f:
                f.write("{}")
            
            result = discover_all_cursor_databases(temp_dir)
            assert result == []
    
    def test_returns_absolute_paths(self):
        """Test that returned paths are absolute."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cursor_dir = os.path.join(temp_dir, ".cursor")
            os.makedirs(cursor_dir)
            
            db_path = os.path.join(cursor_dir, "state.vscdb")
            with open(db_path, 'w') as f:
                f.write("database")
            
            result = discover_all_cursor_databases(temp_dir)
            
            assert len(result) == 1
            assert os.path.isabs(result[0])
            assert result[0] == os.path.abspath(db_path)


class TestExtractFromMultipleDatabases:
    """Test the extract_from_multiple_databases function."""
    
    def test_extracts_from_multiple_databases_successfully(self):
        """Test extracting prompts and generations from multiple databases."""
        database_paths = ["/path/db1.vscdb", "/path/db2.vscdb"]
        
        # Mock the extraction functions
        with patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_generations_data') as mock_generations:
            
            # Setup mock returns
            mock_prompts.side_effect = [
                [{"id": 1, "content": "prompt1"}],  # db1 prompts
                [{"id": 2, "content": "prompt2"}]   # db2 prompts
            ]
            mock_generations.side_effect = [
                [{"id": 1, "content": "gen1"}],     # db1 generations
                [{"id": 2, "content": "gen2"}]      # db2 generations
            ]
            
            result = extract_from_multiple_databases(database_paths)
            
            # Should return list with results from both databases
            assert len(result) == 2
            
            # Check first database result
            assert result[0]["database_path"] == "/path/db1.vscdb"
            assert result[0]["prompts"] == [{"id": 1, "content": "prompt1"}]
            assert result[0]["generations"] == [{"id": 1, "content": "gen1"}]
            
            # Check second database result
            assert result[1]["database_path"] == "/path/db2.vscdb"
            assert result[1]["prompts"] == [{"id": 2, "content": "prompt2"}]
            assert result[1]["generations"] == [{"id": 2, "content": "gen2"}]
            
            # Verify extraction functions were called correctly
            assert mock_prompts.call_count == 2
            assert mock_generations.call_count == 2
            mock_prompts.assert_any_call("/path/db1.vscdb")
            mock_prompts.assert_any_call("/path/db2.vscdb")
    
    def test_handles_partial_success_when_some_databases_fail(self):
        """Test partial success when some databases fail but others succeed."""
        database_paths = ["/path/good.vscdb", "/path/bad.vscdb", "/path/good2.vscdb"]
        
        with patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_generations_data') as mock_generations:
            
            # Setup mocks using path-based returns for better control
            def prompts_side_effect(db_path):
                if db_path == "/path/good.vscdb":
                    return [{"id": 1, "content": "prompt1"}]
                elif db_path == "/path/bad.vscdb":
                    raise Exception("Database corrupted")
                elif db_path == "/path/good2.vscdb":
                    return [{"id": 3, "content": "prompt3"}]
                else:
                    raise Exception(f"Unexpected path: {db_path}")
            
            def generations_side_effect(db_path):
                if db_path == "/path/good.vscdb":
                    return [{"id": 1, "content": "gen1"}]
                elif db_path == "/path/bad.vscdb":
                    raise Exception("Database corrupted")
                elif db_path == "/path/good2.vscdb":
                    return [{"id": 3, "content": "gen3"}]
                else:
                    raise Exception(f"Unexpected path: {db_path}")
            
            mock_prompts.side_effect = prompts_side_effect
            mock_generations.side_effect = generations_side_effect
            
            result = extract_from_multiple_databases(database_paths)
            
            # Should return results from successful databases only
            assert len(result) == 2
            assert result[0]["database_path"] == "/path/good.vscdb"
            assert result[1]["database_path"] == "/path/good2.vscdb"
            
            # Failed database should not be in results
            assert not any(r["database_path"] == "/path/bad.vscdb" for r in result)
    
    def test_returns_empty_list_when_no_databases_provided(self):
        """Test returns empty list when no database paths provided."""
        result = extract_from_multiple_databases([])
        assert result == []
    
    def test_returns_empty_list_when_all_databases_fail(self):
        """Test returns empty list when all databases fail to extract."""
        database_paths = ["/path/bad1.vscdb", "/path/bad2.vscdb"]
        
        with patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_prompts_data') as mock_prompts:
            mock_prompts.side_effect = Exception("All databases corrupted")
            
            result = extract_from_multiple_databases(database_paths)
            assert result == []
    
    def test_handles_extraction_function_exceptions(self):
        """Test graceful handling of extraction function exceptions."""
        database_paths = ["/path/test.vscdb"]
        
        with patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_prompts_data') as mock_prompts, \
             patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_generations_data') as mock_generations:
            
            # Prompts succeed, generations fail
            mock_prompts.return_value = [{"id": 1, "content": "prompt"}]
            mock_generations.side_effect = Exception("Generation extraction failed")
            
            result = extract_from_multiple_databases(database_paths)
            
            # Should skip this database due to generation failure
            assert result == []


class TestMultipleDatabaseDiscoveryTelemetry:
    """Test telemetry instrumentation for multiple database discovery functions."""
    
    def test_discover_databases_has_telemetry_decorator(self):
        """Test that discover_all_cursor_databases has @trace_mcp_operation decorator."""
        # Check if the function has the telemetry decorator applied
        assert hasattr(discover_all_cursor_databases, '__wrapped__')
        
        # The decorator should set operation name
        # This will be verified when we run the actual function
    
    def test_extract_multiple_has_telemetry_decorator(self):
        """Test that extract_from_multiple_databases has @trace_mcp_operation decorator."""
        # Check if the function has the telemetry decorator applied
        assert hasattr(extract_from_multiple_databases, '__wrapped__')


class TestMultipleDatabaseDiscoveryIntegration:
    """Integration tests combining discovery and extraction."""
    
    def test_end_to_end_multiple_database_workflow(self):
        """Test complete workflow from discovery to extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup multiple databases
            cursor_dir = os.path.join(temp_dir, ".cursor")
            db1_dir = os.path.join(cursor_dir, "session1")
            db2_dir = os.path.join(cursor_dir, "session2")
            os.makedirs(db1_dir)
            os.makedirs(db2_dir)
            
            db1_path = os.path.join(db1_dir, "state.vscdb")
            db2_path = os.path.join(db2_dir, "state.vscdb")
            
            for db_path in [db1_path, db2_path]:
                with open(db_path, 'w') as f:
                    f.write("fake database")
            
            # Mock extraction functions for integration test
            with patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_prompts_data') as mock_prompts, \
                 patch('mcp_commit_story.cursor_db.multiple_database_discovery.extract_generations_data') as mock_generations:
                
                mock_prompts.return_value = [{"id": 1, "content": "test"}]
                mock_generations.return_value = [{"id": 1, "content": "test"}]
                
                # Discover databases
                discovered_paths = discover_all_cursor_databases(temp_dir)
                assert len(discovered_paths) == 2
                
                # Extract from discovered databases
                results = extract_from_multiple_databases(discovered_paths)
                assert len(results) == 2
                
                # Verify each result has expected structure
                for result in results:
                    assert "database_path" in result
                    assert "prompts" in result
                    assert "generations" in result
                    assert result["database_path"] in [db1_path, db2_path] 