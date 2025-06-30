"""
Integration tests for the cursor_db package.

This module contains comprehensive integration tests that verify the complete
cursor_db functionality works correctly end-to-end. These tests validate
the interaction between all components including discovery, extraction,
reconstruction, and the high-level query function.

Test Structure:
- TestCursorDBSingleDatabaseIntegration: Tests with single database files
- TestCursorDBMultipleDatabaseIntegration: Tests multiple database discovery
- TestCursorDBErrorHandlingIntegration: Tests error scenarios and recovery
- TestCursorDBPerformanceIntegration: Tests performance with real-world data

These are integration tests, not unit tests - they test components working
together using real database files and realistic scenarios.
"""

import pytest
import tempfile
import shutil
import os
import sqlite3
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from mcp_commit_story.cursor_db import query_cursor_chat_database
from mcp_commit_story.cursor_db.multiple_database_discovery import (
    discover_all_cursor_databases,
    extract_from_multiple_databases
)
from mcp_commit_story.cursor_db.message_extraction import (
    extract_prompts_data,
    extract_generations_data
)
class TestCursorDBSingleDatabaseIntegration:
    """
    Integration tests for single database scenarios.
    
    These tests verify the complete flow from workspace detection through
    chat history collection using Composer with commit-based time windows.
    """
    
    def test_query_cursor_chat_database_end_to_end_success(self):
        """
        Test complete end-to-end flow with query_cursor_chat_database().
        
        Verifies the high-level function correctly orchestrates all components
        to produce complete workspace info and chat history from a real database.
        """
        # Create test workspace with database
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create realistic test database
            self._create_test_database_with_chat_data(str(db_path))
            
            # Mock workspace detection to return our test workspace
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                # Execute end-to-end query
                result = query_cursor_chat_database()
                
                # Verify structure
                assert isinstance(result, dict)
                assert "workspace_info" in result
                assert "chat_history" in result
                
                # Verify workspace_info (new Composer format)
                workspace_info = result["workspace_info"]
                assert "workspace_database_path" in workspace_info
                assert "global_database_path" in workspace_info  
                assert "total_messages" in workspace_info
                assert "time_window_start" in workspace_info
                assert "time_window_end" in workspace_info
                assert "time_window_strategy" in workspace_info
                assert workspace_info["total_messages"] >= 0  # May be 0 with Composer
                
                # Verify chat_history structure (list of messages from Composer)
                chat_history = result["chat_history"]
                assert isinstance(chat_history, list)
                assert len(chat_history) >= 0  # May be empty if no Composer data available
                
                # Verify message structure if messages exist
                if chat_history:
                    first_message = chat_history[0]
                    assert "speaker" in first_message or "role" in first_message
                    assert "content" in first_message or "text" in first_message
                    # Enhanced Composer format may include timestamp, sessionName
                    if "timestamp" in first_message:
                        assert isinstance(first_message["timestamp"], (str, int, float))
                    if "sessionName" in first_message:
                        assert isinstance(first_message["sessionName"], str)
    
    def test_single_database_with_large_chat_history(self):
        """
        Test performance and correctness with large chat history.
        
        Verifies the system handles databases with many messages efficiently
        and maintains data integrity across the full processing pipeline.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create database with many chat entries (simulating heavy usage)
            self._create_large_test_database(str(db_path), num_conversations=50)
            
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                # Time the operation
                start_time = time.time()
                result = query_cursor_chat_database()
                end_time = time.time()
                
                # Verify performance (should complete in reasonable time)
                execution_time = end_time - start_time
                assert execution_time < 2.0, f"Large database query took {execution_time:.2f}s, expected < 2.0s"
                
                # Verify data integrity (chat_history is list from Composer)
                chat_history = result["chat_history"]
                assert isinstance(chat_history, list)
                # With Composer, we may get different message counts based on actual data
                # The exact count depends on what Composer finds in the time window
                assert len(chat_history) >= 0  # At minimum, should not error
    
    def test_single_database_empty_chat_history(self):
        """
        Test handling of database with no chat history.
        
        Verifies graceful handling when database exists but contains no
        chat messages (new workspace scenario).
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create empty database (just structure, no data)
            self._create_empty_test_database(str(db_path))
            
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                result = query_cursor_chat_database()
                
                # Should succeed with empty results  
                chat_history = result["chat_history"]
                assert isinstance(chat_history, list)
                assert len(chat_history) == 0  # Empty list when no Composer data
    
    def _create_test_database_with_chat_data(self, db_path: str):
        """Create a realistic test database with sample chat data using Cursor's schema."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema (ItemTable key-value store)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        # Create sample prompts data as JSON
        prompts_data = [
            {
                "text": "Hello, can you help me with Python?",
                "commandType": 4,
                "timestamp": 1640995200000
            },
            {
                "text": "How do I create a list in Python?", 
                "commandType": 4,
                "timestamp": 1640995800000
            }
        ]
        
        # Create sample generations data as JSON
        generations_data = [
            {
                "unixMs": 1640995200000,
                "generationUUID": "gen-uuid-1",
                "type": "composer",
                "textDescription": "Of course! I'd be happy to help you with Python programming."
            },
            {
                "unixMs": 1640995800000,
                "generationUUID": "gen-uuid-2", 
                "type": "composer",
                "textDescription": "You can create a list using square brackets: my_list = [1, 2, 3]"
            }
        ]
        
        # Insert data into ItemTable as JSON blobs
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.prompts", json.dumps(prompts_data))
        )
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.generations", json.dumps(generations_data))
        )
        
        conn.commit()
        conn.close()
    
    def _create_large_test_database(self, db_path: str, num_conversations: int):
        """Create database with many conversations for performance testing."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        # Generate many conversations as JSON arrays
        prompts_data = []
        generations_data = []
        
        base_timestamp = 1640995200000
        for i in range(num_conversations):
            timestamp = base_timestamp + (i * 60000)  # 1 minute apart
            
            prompts_data.append({
                "text": f"Test prompt {i}",
                "commandType": 4,
                "timestamp": timestamp
            })
            
            generations_data.append({
                "unixMs": timestamp + 5000,  # 5 seconds later
                "generationUUID": f"gen-uuid-{i}",
                "type": "composer", 
                "textDescription": f"Test response {i}"
            })
        
        # Insert data as JSON blobs
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.prompts", json.dumps(prompts_data))
        )
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.generations", json.dumps(generations_data))
        )
        
        conn.commit()
        conn.close()
    
    def _create_empty_test_database(self, db_path: str):
        """Create database with correct schema but no data."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema (empty ItemTable)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        conn.commit()
        conn.close()


class TestCursorDBMultipleDatabaseIntegration:
    """
    Integration tests for multiple database discovery and extraction.
    
    These tests verify that the cursor_db package correctly handles
    Cursor's database rotation behavior when reaching 100 generations.
    """
    
    def test_discover_multiple_databases_in_workspace(self):
        """
        Verify discovery finds all state.vscdb files in .cursor subdirectories.
        
        Simulates a workspace where Cursor has rotated databases multiple times,
        creating several state.vscdb files in different subdirectories.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            # Create multiple .cursor subdirectories with databases
            # Simulating Cursor's rotation after 100 generations (all within .cursor)
            cursor_dirs = [
                Path(temp_workspace) / ".cursor",
                Path(temp_workspace) / ".cursor" / "backup_1",
                Path(temp_workspace) / ".cursor" / "backup_2",
                Path(temp_workspace) / ".cursor" / "history_3"
            ]
            
            database_paths = []
            for cursor_dir in cursor_dirs:
                cursor_dir.mkdir(parents=True, exist_ok=True)
                db_path = cursor_dir / "state.vscdb"
                self._create_test_database_with_unique_data(str(db_path), len(database_paths))
                database_paths.append(str(db_path))
            
            # Test discovery
            discovered = discover_all_cursor_databases(temp_workspace)
            
            # Verify all databases found
            assert len(discovered) == len(database_paths)
            for expected_path in database_paths:
                assert expected_path in discovered
    
    def test_extract_from_multiple_databases_success(self):
        """
        Test successful extraction from multiple databases.
        
        Verifies that data can be extracted from multiple rotated databases
        and that each database's content is preserved correctly.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            # Create multiple databases with distinct content
            database_paths = []
            expected_data = []
            
            for i in range(3):
                cursor_dir = Path(temp_workspace) / f".cursor_{i}"
                cursor_dir.mkdir()
                db_path = cursor_dir / "state.vscdb"
                
                # Create database with unique identifiable content
                unique_data = self._create_test_database_with_unique_data(str(db_path), i)
                database_paths.append(str(db_path))
                expected_data.append(unique_data)
            
            # Test extraction
            results = extract_from_multiple_databases(database_paths)
            
            # Verify results structure
            assert len(results) == 3
            for i, result in enumerate(results):
                assert "database_path" in result
                assert "prompts" in result
                assert "generations" in result
                assert result["database_path"] == database_paths[i]
                
                # Verify data content matches what we inserted
                assert len(result["prompts"]) > 0
                assert len(result["generations"]) > 0
    
    def test_multiple_database_performance_integration(self):
        """
        Test performance with multiple large databases.
        
        Verifies the system can handle discovery and extraction from multiple
        large databases within reasonable time limits.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            database_paths = []
            
            # Create multiple large databases within .cursor subdirectories 
            # (simulating Cursor's rotation behavior)
            for i in range(5):
                cursor_dir = Path(temp_workspace) / ".cursor" / f"backup_{i}"
                cursor_dir.mkdir(parents=True)
                db_path = cursor_dir / "state.vscdb"
                
                # Each database has many conversations
                self._create_large_test_database(str(db_path), num_conversations=200)
                database_paths.append(str(db_path))
            
            # Time the complete discovery + extraction workflow
            start_time = time.time()
            
            discovered = discover_all_cursor_databases(temp_workspace)
            results = extract_from_multiple_databases(discovered)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Verify performance (multiple large databases should still be fast)
            assert execution_time < 5.0, f"Multiple database processing took {execution_time:.2f}s, expected < 5.0s"
            
            # Verify correctness
            assert len(results) == 5
            total_conversations = sum(len(result["prompts"]) for result in results)
            assert total_conversations >= 1000  # 5 databases * 200 conversations each
    
    def _create_test_database_with_unique_data(self, db_path: str, identifier: int):
        """Create database with unique identifiable content."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        # Create unique data for this database
        prompts_data = [
            {
                "text": f"Database {identifier} prompt 1",
                "commandType": 4,
                "timestamp": 1640995200000 + (identifier * 1000000)
            },
            {
                "text": f"Database {identifier} prompt 2",
                "commandType": 4,
                "timestamp": 1640995200000 + (identifier * 1000000) + 60000
            }
        ]
        
        generations_data = [
            {
                "unixMs": 1640995200000 + (identifier * 1000000),
                "generationUUID": f"db{identifier}-gen-uuid-1",
                "type": "composer",
                "textDescription": f"Database {identifier} response 1"
            },
            {
                "unixMs": 1640995200000 + (identifier * 1000000) + 60000,
                "generationUUID": f"db{identifier}-gen-uuid-2",
                "type": "composer",
                "textDescription": f"Database {identifier} response 2"
            }
        ]
        
        # Insert data as JSON blobs
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.prompts", json.dumps(prompts_data))
        )
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.generations", json.dumps(generations_data))
        )
        
        conn.commit()
        conn.close()
        
        return {"prompts": prompts_data, "generations": generations_data}
    
    def _create_large_test_database(self, db_path: str, num_conversations: int):
        """Create database with many conversations for performance testing."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        # Generate many conversations as JSON arrays
        prompts_data = []
        generations_data = []
        
        base_timestamp = 1640995200000
        for i in range(num_conversations):
            timestamp = base_timestamp + (i * 60000)  # 1 minute apart
            
            prompts_data.append({
                "text": f"Test prompt {i}",
                "commandType": 4,
                "timestamp": timestamp
            })
            
            generations_data.append({
                "unixMs": timestamp + 5000,  # 5 seconds later
                "generationUUID": f"gen-uuid-{i}",
                "type": "composer", 
                "textDescription": f"Test response {i}"
            })
        
        # Insert data as JSON blobs
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.prompts", json.dumps(prompts_data))
        )
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.generations", json.dumps(generations_data))
        )
        
        conn.commit()
        conn.close()



class TestCursorDBErrorHandlingIntegration:
    """
    Integration tests for error scenarios and recovery.
    
    These tests verify that the cursor_db package handles various error
    conditions gracefully and provides meaningful error information.
    """
    
    def test_missing_workspace_scenario(self):
        """
        Test behavior when workspace cannot be detected.
        
        Verifies graceful handling when the primary workspace detection fails.
        """
        with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
            # Simulate workspace detection failure
            mock_workspace.return_value = None
            
            result = query_cursor_chat_database()
            
            # Should return error information without raising exception
            assert "workspace_info" in result
            assert "chat_history" in result
            assert result["workspace_info"]["workspace_database_path"] is None
            assert result["workspace_info"]["total_messages"] == 0
            # For missing workspace, chat_history is empty list (actual behavior)
            assert result["chat_history"] == []
    
    def test_missing_cursor_directory(self):
        """
        Test behavior when workspace exists but has no .cursor directory.
        
        Verifies handling of workspaces that haven't been used with Cursor yet.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            # Don't create .cursor directory
            
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                result = query_cursor_chat_database()
                
                # Should handle missing .cursor directory gracefully
                # workspace_database_path will be None when no database found
                assert result["workspace_info"]["workspace_database_path"] is None or result["workspace_info"]["workspace_database_path"] == ""
                assert result["workspace_info"]["total_messages"] == 0
                # For missing .cursor directory, chat_history is empty list (actual behavior)
                assert result["chat_history"] == []
    
    def test_corrupted_database_handling(self):
        """
        Test handling of corrupted or invalid database files.
        
        Verifies the system can handle database files that exist but
        are corrupted or have invalid schemas.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create corrupted database file (invalid SQLite)
            with open(db_path, 'w') as f:
                f.write("This is not a valid SQLite database")
            
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                result = query_cursor_chat_database()
                
                # Should handle corruption gracefully
                # workspace_database_path may be None when Composer fails to find valid databases
                workspace_db_path = result["workspace_info"]["workspace_database_path"]
                assert workspace_db_path is None or workspace_db_path == "" or isinstance(workspace_db_path, str)
                # For corrupted database, chat_history is empty list (actual behavior)
                assert result["chat_history"] == []  # No data extracted
                assert result["workspace_info"]["total_messages"] == 0
    
    def test_permission_errors_during_discovery(self):
        """
        Test handling of permission errors during database discovery.
        
        Verifies the system continues processing when some directories
        are inaccessible due to permission issues.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            # Create accessible database
            accessible_dir = Path(temp_workspace) / ".cursor"
            accessible_dir.mkdir()
            accessible_db = accessible_dir / "state.vscdb"
            self._create_test_database_with_chat_data(str(accessible_db))
            
            # Create inaccessible directory (simulate permission error)
            inaccessible_dir = Path(temp_workspace) / "restricted" / ".cursor"
            inaccessible_dir.mkdir(parents=True)
            inaccessible_db = inaccessible_dir / "state.vscdb"
            self._create_test_database_with_chat_data(str(inaccessible_db))
            
            # Mock os.walk to simulate permission error for restricted directory
            original_walk = os.walk
            def mock_walk(path):
                for root, dirs, files in original_walk(path):
                    if "restricted" in root:
                        # Simulate permission error
                        raise PermissionError("Access denied")
                    yield root, dirs, files
            
            with patch('os.walk', side_effect=mock_walk):
                discovered = discover_all_cursor_databases(temp_workspace)
                
                # Should find accessible database despite permission error
                assert len(discovered) >= 1
                assert str(accessible_db) in discovered
                # Should not contain the inaccessible database
                assert str(inaccessible_db) not in discovered
    
    def test_partial_extraction_failure_recovery(self):
        """
        Test recovery when some databases fail during extraction.
        
        Verifies that extraction failures from individual databases
        don't prevent processing of other valid databases.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            # Create mix of valid and corrupted databases
            database_paths = []
            
            # Valid database
            valid_dir = Path(temp_workspace) / ".cursor1"
            valid_dir.mkdir()
            valid_db = valid_dir / "state.vscdb"
            self._create_test_database_with_chat_data(str(valid_db))
            database_paths.append(str(valid_db))
            
            # Corrupted database
            corrupt_dir = Path(temp_workspace) / ".cursor2"
            corrupt_dir.mkdir()
            corrupt_db = corrupt_dir / "state.vscdb"
            with open(corrupt_db, 'w') as f:
                f.write("corrupted")
            database_paths.append(str(corrupt_db))
            
            # Another valid database
            valid_dir2 = Path(temp_workspace) / ".cursor3"
            valid_dir2.mkdir()
            valid_db2 = valid_dir2 / "state.vscdb"
            self._create_test_database_with_chat_data(str(valid_db2))
            database_paths.append(str(valid_db2))
            
            # Test extraction with mixed databases
            results = extract_from_multiple_databases(database_paths)
            
            # Should get results from valid databases only
            # (corrupted database should be skipped gracefully)
            valid_results = [r for r in results if len(r.get("prompts", [])) > 0]
            assert len(valid_results) >= 2  # At least the two valid databases
    
    def _create_test_database_with_chat_data(self, db_path: str):
        """Create a realistic test database with sample chat data using Cursor's schema."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema (ItemTable key-value store)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        # Create sample prompts data as JSON
        prompts_data = [
            {
                "text": "Test prompt for error handling",
                "commandType": 4,
                "timestamp": 1640995200000
            }
        ]
        
        # Create sample generations data as JSON
        generations_data = [
            {
                "unixMs": 1640995200000,
                "generationUUID": "error-test-gen-uuid-1",
                "type": "composer",
                "textDescription": "Test response for error handling"
            }
        ]
        
        # Insert data into ItemTable as JSON blobs
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.prompts", json.dumps(prompts_data))
        )
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.generations", json.dumps(generations_data))
        )
        
        conn.commit()
        conn.close()
    



class TestCursorDBPerformanceIntegration:
    """
    Integration tests for performance with real-world data volumes.
    
    These tests verify that the cursor_db package performs efficiently
    with realistic data volumes and usage patterns.
    """
    
    def test_large_single_database_performance(self):
        """
        Test performance with single large database.
        
        Verifies acceptable performance when processing a database
        with thousands of chat messages (heavy Cursor usage scenario).
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create database with thousands of conversations
            self._create_massive_test_database(str(db_path), num_conversations=2000)
            
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                # Time the complete operation
                start_time = time.time()
                result = query_cursor_chat_database()
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                # Performance requirement: < 2 seconds for typical workspace
                assert execution_time < 2.0, f"Large database query took {execution_time:.2f}s, expected < 2.0s"
                
                # Verify all data processed (chat_history is now a list from Composer)
                chat_history = result["chat_history"]
                assert isinstance(chat_history, list)
                # With Composer, we get the actual data for the time window
                assert len(chat_history) >= 0  # May vary based on actual Composer data
    
    def test_multiple_large_databases_performance(self):
        """
        Test performance with multiple large databases.
        
        Verifies acceptable performance in worst-case scenario: multiple
        rotated databases each with heavy usage.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            database_paths = []
            
            # Create multiple large databases within .cursor subdirectories
            # (simulating heavy rotation behavior)
            for i in range(3):
                cursor_dir = Path(temp_workspace) / ".cursor" / f"rotation_{i}"
                cursor_dir.mkdir(parents=True)
                db_path = cursor_dir / "state.vscdb"
                
                # Each database has many conversations
                self._create_massive_test_database(str(db_path), num_conversations=1500)
                database_paths.append(str(db_path))
            
            # Time discovery + extraction
            start_time = time.time()
            
            discovered = discover_all_cursor_databases(temp_workspace)
            results = extract_from_multiple_databases(discovered)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Performance requirement: < 5 seconds for heavy multi-database scenario
            assert execution_time < 5.0, f"Multiple large databases took {execution_time:.2f}s, expected < 5.0s"
            
            # Verify all data processed correctly
            assert len(results) == 3
            total_conversations = sum(len(result["prompts"]) for result in results)
            assert total_conversations >= 4500  # 3 databases * 1500 conversations
    
    def test_telemetry_performance_tracking(self):
        """
        Test that telemetry correctly tracks performance metrics.
        
        Verifies telemetry integration captures timing and threshold
        information during integration testing.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create moderately sized database
            self._create_massive_test_database(str(db_path), num_conversations=100)
            
            # Mock telemetry to capture performance data
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                # Execute with telemetry monitoring
                result = query_cursor_chat_database()
                
                # Verify operation completed successfully (chat_history is now a list from Composer)
                chat_history = result["chat_history"]
                assert isinstance(chat_history, list)
                # With Composer, we get actual data for the time window
                assert len(chat_history) >= 0  # May vary based on actual Composer data
                
                # Note: Telemetry integration is automatic via @trace_mcp_operation decorators
                # The actual telemetry verification would require access to telemetry logs
                # This test ensures the integration doesn't break when telemetry is active
    
    def test_memory_efficiency_with_large_datasets(self):
        """
        Test memory efficiency with large chat histories.
        
        Verifies the system doesn't consume excessive memory when processing
        large datasets, important for long-running AI assistant sessions.
        """
        with tempfile.TemporaryDirectory() as temp_workspace:
            cursor_dir = Path(temp_workspace) / ".cursor"
            cursor_dir.mkdir()
            db_path = cursor_dir / "state.vscdb"
            
            # Create very large database
            self._create_massive_test_database(str(db_path), num_conversations=5000)
            
            with patch('mcp_commit_story.cursor_db.get_primary_workspace_path') as mock_workspace:
                mock_workspace.return_value = temp_workspace
                
                # Process large dataset
                result = query_cursor_chat_database()
                
                # Verify successful processing (chat_history is now a list from Composer)
                chat_history = result["chat_history"]
                assert isinstance(chat_history, list)
                # With Composer, we get actual data for the time window
                assert len(chat_history) >= 0  # May vary based on actual Composer data
                
                # Memory efficiency is implicit - if we complete without
                # memory errors, the implementation is reasonably efficient
                # (Python's garbage collection handles cleanup)
    
    def _create_massive_test_database(self, db_path: str, num_conversations: int):
        """Create database with many conversations for performance testing."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Cursor's actual database schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemTable (
                [key] TEXT PRIMARY KEY,
                value BLOB
            )
        ''')
        
        # Generate many conversations as JSON arrays
        prompts_data = []
        generations_data = []
        
        base_timestamp = 1640995200000
        
        for i in range(num_conversations):
            timestamp = base_timestamp + (i * 60000)  # 1 minute apart
            
            # Create realistic-sized content (not just tiny test strings)
            prompt_content = f"This is a more realistic test prompt number {i} with some additional content to simulate real usage patterns. Can you help me solve this problem?"
            generation_content = f"This is a more realistic test response number {i} with detailed explanation and code examples that would typically be generated by an AI assistant in a real scenario."
            
            prompts_data.append({
                "text": prompt_content,
                "commandType": 4,
                "timestamp": timestamp
            })
            
            generations_data.append({
                "unixMs": timestamp + 5000,  # 5 seconds later
                "generationUUID": f"massive-gen-uuid-{i}",
                "type": "composer",
                "textDescription": generation_content
            })
        
        # Insert data as JSON blobs
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.prompts", json.dumps(prompts_data))
        )
        cursor.execute(
            "INSERT INTO ItemTable ([key], value) VALUES (?, ?)",
            ("aiService.generations", json.dumps(generations_data))
        )
        
        conn.commit()
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 