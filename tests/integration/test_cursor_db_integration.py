"""
Integration tests for cursor_db package.

Tests the complete workflow from platform detection → database discovery → 
connection → validation → query with cross-platform scenarios and performance benchmarks.

Focuses on end-to-end validation rather than unit testing already-tested components.
"""

import sqlite3
import pytest
import tempfile
import time
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import List, Dict, Any

# Import the cursor_db package components
from src.mcp_commit_story.cursor_db.platform import (
    detect_platform, 
    get_cursor_workspace_paths,
    validate_workspace_path,
    PlatformType
)
from src.mcp_commit_story.cursor_db.connection import (
    get_cursor_chat_database,
    query_cursor_chat_database,
    cursor_chat_database_context,
    query_multiple_databases
)
from src.mcp_commit_story.cursor_db.validation import (
    validate_database_basics,
    check_database_integrity
)
from src.mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError,
    CursorDatabaseQueryError,
    CursorDatabaseSchemaError
)


class TestCursorDbIntegration:
    """Integration tests for the complete cursor_db workflow."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
    def teardown_method(self):
        """Clean up after each test method."""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def create_mock_database(self, path: Path, include_chat_data: bool = True) -> str:
        """
        Create a mock SQLite database for testing.
        
        Args:
            path: Path where to create the database
            include_chat_data: Whether to include mock chat data
            
        Returns:
            str: Path to created database
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()
        
        # Create ItemTable (required by validation)
        cursor.execute('''
            CREATE TABLE ItemTable (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        if include_chat_data:
            # Insert mock chat data
            cursor.execute('''
                INSERT INTO ItemTable (key, value) VALUES 
                ('aiService.prompts', '{"text": "Test user prompt", "commandType": 4}'),
                ('aiService.generations', '{"unixMs": 1640995200000, "generationUUID": "test-uuid", "type": "composer", "textDescription": "Test AI response"}'),
                ('composer.composerData', '{"allComposers": [], "selectedComposerIds": []}')
            ''')
        
        conn.commit()
        conn.close()
        
        return str(path)
    def test_cross_platform_workflow_complete(self):
        """
        Test complete workflow on current platform:
        platform detection → database discovery → connection → validation → query
        """
        # Step 1: Platform detection (real platform is fine for integration test)
        detected_platform = detect_platform()
        assert detected_platform in [PlatformType.WINDOWS, PlatformType.MACOS, PlatformType.LINUX, PlatformType.WSL]

        # Step 2: Get workspace paths (real paths are fine)
        workspace_paths = get_cursor_workspace_paths()
        assert len(workspace_paths) > 0
        
        # Step 3: Create mock database in expected location
        workspace_hash = "test-workspace-hash"
        db_path = self.temp_path / workspace_hash / "cursor-chat-browser" / "state.vscdb"
        mock_db_path = self.create_mock_database(db_path)
        
        # Mock file system to return our test database
        with patch('src.mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths', 
                  return_value=[str(self.temp_path)]), \
             patch('pathlib.Path.rglob') as mock_rglob, \
             patch('pathlib.Path.stat') as mock_stat:
            
            # Configure file discovery mocks
            mock_rglob.return_value = [Path(mock_db_path)]
            mock_stat_result = MagicMock()
            mock_stat_result.st_mtime = time.time() - 1800  # 30 minutes ago
            mock_stat_result.st_mode = 0o100644  # Regular file mode
            mock_stat.return_value = mock_stat_result
            
            # Step 4: Database discovery and connection
            discovered_db = get_cursor_chat_database()
            assert discovered_db == mock_db_path
            
            # Step 5: Database validation
            with sqlite3.connect(discovered_db) as conn:
                validate_database_basics(conn)
                check_database_integrity(conn)
            
            # Step 6: Query execution
            results = query_cursor_chat_database(
                discovered_db, 
                "SELECT key, value FROM ItemTable WHERE key LIKE 'aiService.%'"
            )
            assert len(results) >= 2  # Should find prompts and generations
            assert any('aiService.prompts' in str(row) for row in results)
            assert any('aiService.generations' in str(row) for row in results)
    
    def test_end_to_end_chat_data_extraction_workflow(self):
        """
        Test realistic scenario: find and extract chat data from discovered database.
        """
        # Create mock database with comprehensive chat data
        db_path = self.temp_path / "workspace" / "state.vscdb"
        mock_db_path = self.create_mock_database(db_path, include_chat_data=True)
        
        # Mock discovery to return our test database
        with patch('src.mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths', 
                  return_value=[str(self.temp_path / "workspace")]), \
             patch('pathlib.Path.rglob', return_value=[Path(mock_db_path)]), \
             patch('pathlib.Path.stat') as mock_stat:
            
            # Create a proper mock stat result with required attributes
            mock_stat_result = MagicMock()
            mock_stat_result.st_mtime = time.time() - 600  # 10 minutes ago
            mock_stat_result.st_mode = 0o100644  # Regular file mode
            mock_stat.return_value = mock_stat_result
            
            # Complete workflow simulation
            start_time = time.time()
            
            # 1. Discover database
            discovered_db = get_cursor_chat_database()
            
            # 2. Validate database structure
            with sqlite3.connect(discovered_db) as conn:
                validate_database_basics(conn)
                is_healthy = check_database_integrity(conn)
                assert is_healthy
            
            # 3. Extract chat data (realistic queries)
            prompts = query_cursor_chat_database(
                discovered_db,
                "SELECT value FROM ItemTable WHERE key = ?",
                ("aiService.prompts",)
            )
            assert len(prompts) > 0
            
            generations = query_cursor_chat_database(
                discovered_db,
                "SELECT value FROM ItemTable WHERE key = ?", 
                ("aiService.generations",)
            )
            assert len(generations) > 0
            
            # 4. Performance assertion
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            assert execution_time < 100, f"Query took {execution_time:.2f}ms, expected < 100ms"
    
    def test_multiple_database_discovery_and_selection(self):
        """
        Test discovery and selection when multiple databases are available.
        """
        # Create multiple mock databases with different ages
        recent_db = self.temp_path / "workspace1" / "state.vscdb"
        old_db = self.temp_path / "workspace2" / "state.vscdb"
        
        recent_path = self.create_mock_database(recent_db)
        old_path = self.create_mock_database(old_db)
        
        def mock_stat_side_effect(*args, **kwargs):
            """Mock stat to return different modification times."""
            mock_stat = MagicMock()
            # Extract the path from args (self is first argument when called as method)  
            path_arg = args[0] if args else None
            if path_arg and "workspace1" in str(path_arg):
                mock_stat.st_mtime = time.time() - 600  # 10 minutes ago (recent)
            elif path_arg and "workspace2" in str(path_arg):
                mock_stat.st_mtime = time.time() - 86400  # 24 hours ago (old)
            else:
                mock_stat.st_mtime = time.time() - 43200  # 12 hours ago (default)
            mock_stat.st_mode = 0o100644  # Regular file mode
            return mock_stat
        
        with patch('src.mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths',
                  return_value=[str(self.temp_path)]), \
             patch('pathlib.Path.rglob', return_value=[Path(old_path), Path(recent_path)]), \
             patch('pathlib.Path.stat', side_effect=mock_stat_side_effect):
            
            # Should select the most recent database (by age, not by order returned)
            selected_db = get_cursor_chat_database()
            assert selected_db == recent_path
    
    def test_context_manager_resource_cleanup(self):
        """
        Test context manager for proper database connection cleanup.
        """
        db_path = self.temp_path / "test.db"
        mock_db_path = self.create_mock_database(db_path)
        
        with patch('src.mcp_commit_story.cursor_db.connection.get_cursor_chat_database',
                  return_value=mock_db_path):
            
            # Test context manager usage - returns database path, not connection
            with cursor_chat_database_context() as db_path_returned:
                assert db_path_returned is not None
                assert db_path_returned == mock_db_path
                
                # Use the returned path to query the database
                results = query_cursor_chat_database(
                    db_path_returned,
                    "SELECT key FROM ItemTable LIMIT 1"
                )
                assert len(results) > 0
            
            # Database path should still be valid after context exit
            # (context manager manages discovery, not connection lifecycle)
    
    def test_error_propagation_through_workflow(self):
        """
        Test that errors are properly propagated through the complete workflow.
        """
        # Test 1: No databases found
        with patch('src.mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths',
                  return_value=[str(self.temp_path)]), \
             patch('pathlib.Path.rglob', return_value=[]):
            
            with pytest.raises(CursorDatabaseNotFoundError) as exc_info:
                get_cursor_chat_database()
            assert "No valid Cursor chat databases found" in str(exc_info.value)
        
        # Test 2: Database validation failure
        invalid_db = self.temp_path / "invalid.db"
        invalid_db.write_text("not a database")
        
        with pytest.raises(CursorDatabaseQueryError):
            query_cursor_chat_database(str(invalid_db), "SELECT 1")
    
    def test_performance_benchmarks(self):
        """
        Test performance benchmarks for database operations.
        """
        # Create larger mock database for performance testing
        db_path = self.temp_path / "large_test.db"
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()
        
        # Create table with more data
        cursor.execute('''
            CREATE TABLE ItemTable (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Insert multiple chat entries
        for i in range(100):
            cursor.execute('''
                INSERT INTO ItemTable (key, value) VALUES (?, ?)
            ''', (f'aiService.prompts.{i}', f'{{"text": "Test prompt {i}", "commandType": 4}}'))
        
        conn.commit()
        conn.close()
        
        mock_db_path = str(path)
        
        # Performance test: Connection establishment
        start_time = time.time()
        with sqlite3.connect(mock_db_path) as conn:
            validate_database_basics(conn)
        connection_time = (time.time() - start_time) * 1000
        assert connection_time < 50, f"Connection took {connection_time:.2f}ms, expected < 50ms"
        
        # Performance test: Query execution
        start_time = time.time()
        results = query_cursor_chat_database(
            mock_db_path,
            "SELECT key, value FROM ItemTable WHERE key LIKE 'aiService.prompts.%'"
        )
        query_time = (time.time() - start_time) * 1000
        assert query_time < 100, f"Query took {query_time:.2f}ms, expected < 100ms"
        assert len(results) == 100
        
        # Performance test: Multiple queries
        start_time = time.time()
        for i in range(10):
            query_cursor_chat_database(
                mock_db_path,
                "SELECT value FROM ItemTable WHERE key = ?",
                (f'aiService.prompts.{i}',)
            )
        batch_time = (time.time() - start_time) * 1000
        assert batch_time < 200, f"Batch queries took {batch_time:.2f}ms, expected < 200ms"
    
    def test_cross_platform_path_resolution(self):
        """
        Test that path resolution works on the current platform.
        """
        # Test current platform detection
        detected = detect_platform()
        assert detected in [PlatformType.WINDOWS, PlatformType.MACOS, PlatformType.LINUX, PlatformType.WSL]
        
        # Test workspace paths generation
        paths = get_cursor_workspace_paths()
        assert len(paths) > 0
        
        # All paths should be Path objects
        for path in paths:
            assert isinstance(path, Path)
        
        # Paths should contain cursor workspace indicators
        path_strings = [str(path) for path in paths]
        assert any('Cursor' in path_str for path_str in path_strings)
        assert any('workspaceStorage' in path_str for path_str in path_strings)
    
    def test_database_schema_validation_integration(self):
        """
        Test that schema validation properly integrates with connection workflow.
        """
        # Test with valid database
        valid_db = self.temp_path / "valid.db"
        self.create_mock_database(valid_db)
        
        with sqlite3.connect(str(valid_db)) as conn:
            # Should not raise exceptions
            validate_database_basics(conn)
            is_healthy = check_database_integrity(conn)
            assert is_healthy
        
        # Test with invalid schema
        invalid_db = self.temp_path / "invalid_schema.db"
        invalid_db.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(invalid_db))
        cursor = conn.cursor()
        # Create wrong table structure
        cursor.execute('CREATE TABLE WrongTable (id INTEGER)')
        conn.commit()
        conn.close()
        
        with sqlite3.connect(str(invalid_db)) as conn:
            with pytest.raises(CursorDatabaseSchemaError):
                validate_database_basics(conn)


# Performance test class for specialized performance scenarios
class TestCursorDbPerformance:
    """Specialized performance and stress tests."""
    
    def setup_method(self):
        """Set up performance test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up performance test fixtures."""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_large_workspace_discovery_performance(self):
        """
        Test performance when discovering databases in large workspace directories.
        """
        # Create multiple workspace directories with databases
        num_workspaces = 50
        for i in range(num_workspaces):
            workspace_dir = self.temp_path / f"workspace_{i:03d}"
            db_path = workspace_dir / "state.vscdb"
            
            # Create database
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
            cursor.execute("INSERT INTO ItemTable VALUES ('test', 'data')")
            conn.commit()
            conn.close()
        
        # Mock discovery to use our test directory
        with patch('src.mcp_commit_story.cursor_db.connection.get_cursor_workspace_paths',
                  return_value=[str(self.temp_path)]):
            
            start_time = time.time()
            
            # This should efficiently discover databases even with many directories
            discovered_db = get_cursor_chat_database()
            
            discovery_time = (time.time() - start_time) * 1000
            assert discovery_time < 1000, f"Discovery took {discovery_time:.2f}ms, expected < 1000ms"
            assert discovered_db is not None
    
    def test_concurrent_database_access_simulation(self):
        """
        Test that the database access patterns work correctly under concurrent access simulation.
        """
        db_path = self.temp_path / "concurrent_test.db"
        
        # Create test database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
        for i in range(100):
            cursor.execute("INSERT INTO ItemTable VALUES (?, ?)", (f'key_{i}', f'value_{i}'))
        conn.commit()
        conn.close()
        
        # Simulate multiple rapid queries (like concurrent access)
        start_time = time.time()
        
        for i in range(20):
            results = query_cursor_chat_database(
                str(db_path),
                "SELECT * FROM ItemTable WHERE key = ?",
                (f'key_{i}',)
            )
            assert len(results) == 1
        
        total_time = (time.time() - start_time) * 1000
        assert total_time < 500, f"Concurrent queries took {total_time:.2f}ms, expected < 500ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 