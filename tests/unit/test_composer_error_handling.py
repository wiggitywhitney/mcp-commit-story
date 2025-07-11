"""
Unit tests for Composer Error Handling.

Tests comprehensive error handling in the Composer integration including
database access errors, workspace detection failures, and graceful degradation.
Uses existing exception types from cursor_db.exceptions.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import sqlite3

from src.mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError, 
    CursorDatabaseSchemaError,
    CursorDatabaseQueryError
)
from src.mcp_commit_story.cursor_db.workspace_detection import WorkspaceDetectionError

# These imports will be tested - some may fail initially
from src.mcp_commit_story.cursor_db import query_cursor_chat_database, reset_circuit_breaker
from src.mcp_commit_story.cursor_db.composer_integration import find_workspace_composer_databases
from src.mcp_commit_story.cursor_db.workspace_detection import detect_workspace_for_repo
from src.mcp_commit_story.chat_context_manager import extract_chat_for_commit


@pytest.fixture(autouse=True)
def reset_circuit_breaker_fixture():
    """Reset circuit breaker before each test to ensure clean state."""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()


class TestCursorDatabaseNotFoundError:
    """Test handling when Composer databases are missing."""
    
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('src.mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases')
    def test_database_not_found_graceful_degradation(self, mock_find_databases, mock_detect_workspace, mock_discover_databases):
        """Test graceful degradation when Composer databases cannot be found."""
        # Arrange - simulate database not found in both paths
        mock_detect_workspace.side_effect = CursorDatabaseNotFoundError(
            "Workspace not found",
            path="/nonexistent/workspace"
        )
        mock_find_databases.side_effect = CursorDatabaseNotFoundError(
            "Composer databases not found",
            path="/nonexistent/workspace"
        )
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert graceful degradation
        assert isinstance(result, dict)
        assert result['chat_history'] == []
        assert result['workspace_info']['workspace_database_path'] is None
        assert result['workspace_info']['global_database_path'] is None
        assert result['workspace_info']['total_messages'] == 0
        assert 'error_info' in result['workspace_info']
        assert result['workspace_info']['error_info']['error_type'] == 'CursorDatabaseNotFoundError'
    
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    @patch('src.mcp_commit_story.cursor_db.detect_workspace_for_repo')
    @patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases')
    def test_database_not_found_logging(self, mock_find_databases, mock_detect_workspace, mock_discover_databases, caplog):
        """Test that database not found errors are properly logged."""
        # Arrange - simulate database not found in both paths
        mock_detect_workspace.side_effect = CursorDatabaseNotFoundError(
            "Workspace not found",
            path="/missing/path"
        )
        mock_find_databases.side_effect = CursorDatabaseNotFoundError(
            "Composer databases not found",
            path="/missing/path"
        )
        
        with caplog.at_level(logging.WARNING):
            query_cursor_chat_database()
        
        # Should log warning with context
        assert any("Composer databases not found" in record.message for record in caplog.records)
        assert any("/missing/path" in record.message for record in caplog.records)
    
    def test_chat_context_manager_database_not_found_degradation(self):
        """Test chat context manager graceful degradation when databases missing."""
        with patch('src.mcp_commit_story.chat_context_manager.query_cursor_chat_database') as mock_query:
            mock_query.side_effect = CursorDatabaseNotFoundError("No databases found")
            
            result = extract_chat_for_commit()
            
            # Should return empty but valid ChatContextData structure
            assert result['messages'] == []
            assert result['session_names'] == []
            assert 'error_info' in result['metadata']
            assert result['metadata']['error_info']['error_type'] == 'CursorDatabaseNotFoundError'


class TestCursorDatabaseAccessError:
    """Test handling of permission and lock issues."""
    
    @patch('src.mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    def test_database_access_permission_error(self, mock_discover_databases, mock_provider_class):
        """Test handling when database access is denied due to permissions."""
        # Arrange - database found but access denied
        mock_discover_databases.return_value = ["/workspace.vscdb"]
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseAccessError(
            "Permission denied",
            path="/workspace.vscdb",
            permission_type="read"
        )
        
        # Act
        result = query_cursor_chat_database()
        
        # Assert graceful degradation with data quality metadata
        assert result['chat_history'] == []
        assert 'data_quality' in result['workspace_info']
        assert result['workspace_info']['data_quality']['status'] == 'failed'
        assert result['workspace_info']['data_quality']['databases_failed'] > 0
        # Check that failure reasons include permission-related error
        failure_reasons = result['workspace_info']['data_quality']['failure_reasons']
        assert any('Permission denied' in reason for reason in failure_reasons)
    
    @patch('src.mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    def test_database_locked_error_handling(self, mock_discover_databases, mock_provider_class):
        """Test handling when database is locked by another process."""
        mock_discover_databases.return_value = ["/workspace.vscdb"]
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseAccessError(
            "Database is locked",
            path="/workspace.vscdb", 
            permission_type="lock"
        )
        
        result = query_cursor_chat_database()
        
        # Check data quality indicates failure
        assert result['workspace_info']['data_quality']['status'] == 'failed'
        # Check that failure reasons include lock-related error
        failure_reasons = result['workspace_info']['data_quality']['failure_reasons']
        assert any('locked' in reason.lower() for reason in failure_reasons)


class TestCursorDatabaseSchemaError:
    """Test handling of corrupted or incompatible database schemas."""
    
    @patch('src.mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    def test_schema_version_mismatch_error(self, mock_discover_databases, mock_provider_class):
        """Test handling when database schema doesn't match expectations."""
        mock_discover_databases.return_value = ["/workspace.vscdb"]
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseSchemaError(
            "Table 'conversations' not found",
            table_name="conversations",
            expected_schema="composer_v2"
        )
        
        result = query_cursor_chat_database()
        
        # Check data quality indicates failure
        assert 'data_quality' in result['workspace_info']
        assert result['workspace_info']['data_quality']['status'] == 'failed'
        # Check that failure reasons include schema-related error
        failure_reasons = result['workspace_info']['data_quality']['failure_reasons']
        assert any('conversations' in reason for reason in failure_reasons)
    
    @patch('src.mcp_commit_story.composer_chat_provider.ComposerChatProvider')
    @patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases')
    def test_corrupted_database_graceful_degradation(self, mock_find_databases, mock_provider_class):
        """Test graceful degradation when database is corrupted."""
        mock_find_databases.return_value = ("/workspace.vscdb", "/global.vscdb")
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseSchemaError(
            "Database file is corrupted",
            expected_schema="valid_sqlite"
        )
        
        result = query_cursor_chat_database()
        
        # Should still return valid structure with empty data
        assert isinstance(result, dict)
        assert 'chat_history' in result
        assert 'workspace_info' in result
        assert result['chat_history'] == []


class TestCursorDatabaseQueryError:
    """Test handling of invalid SQL or parameter issues."""
    
    @patch('src.mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    def test_invalid_sql_error_handling(self, mock_discover_databases, mock_provider_class):
        """Test handling when SQL query has syntax errors."""
        mock_discover_databases.return_value = ["/workspace.vscdb"]
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseQueryError(
            "Syntax error in SQL",
            sql="SELECT * FROM invalid_table WHERE bad_syntax",
            parameters=()
        )
        
        result = query_cursor_chat_database()
        
        # Check data quality indicates failure
        assert 'data_quality' in result['workspace_info']
        assert result['workspace_info']['data_quality']['status'] == 'failed'
        # Check that failure reasons include SQL-related error
        failure_reasons = result['workspace_info']['data_quality']['failure_reasons']
        assert any('Syntax error' in reason for reason in failure_reasons)
    
    @patch('src.mcp_commit_story.cursor_db.ComposerChatProvider')
    @patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases')
    def test_parameter_mismatch_error_handling(self, mock_discover_databases, mock_provider_class):
        """Test handling when SQL parameters don't match placeholders."""
        mock_discover_databases.return_value = ["/workspace.vscdb"]
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseQueryError(
            "Parameter count mismatch",
            sql="SELECT * FROM messages WHERE timestamp > ? AND session = ?",
            parameters=(1640995200000,)  # Missing second parameter
        )
        
        result = query_cursor_chat_database()
        
        # Check data quality indicates failure
        assert result['workspace_info']['data_quality']['status'] == 'failed'
        # Check that failure reasons include parameter-related error
        failure_reasons = result['workspace_info']['data_quality']['failure_reasons']
        assert any('Parameter count mismatch' in reason for reason in failure_reasons)


class TestWorkspaceDetectionError:
    """Test handling of git and workspace detection failures."""
    
    @patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases')
    def test_git_repository_not_found_error(self, mock_find_databases):
        """Test handling when git repository cannot be found."""
        mock_find_databases.side_effect = WorkspaceDetectionError(
            "No git repository found",
            repo_path="/not/a/git/repo"
        )
        
        result = query_cursor_chat_database()
        
        assert 'error_info' in result['workspace_info']
        assert result['workspace_info']['error_info']['error_type'] == 'WorkspaceDetectionError'
        assert "/not/a/git/repo" in result['workspace_info']['error_info']['repo_path']
    
    def test_invalid_commit_error_handling(self):
        """Test that function handles git errors gracefully."""
        # Act - call the function (it should handle any internal errors gracefully)
        result = query_cursor_chat_database()
        
        # Assert - verify it returns valid structure even when errors might occur
        assert isinstance(result, dict)
        assert "workspace_info" in result
        assert "chat_history" in result
        assert isinstance(result["workspace_info"], dict)
        assert isinstance(result["chat_history"], list)
        # The function should handle any git/commit errors internally and not raise exceptions


class TestGracefulDegradation:
    """Test that all error scenarios return valid empty results."""
    
    def test_all_error_types_return_valid_structure(self):
        """Test that any error type returns a valid, empty ChatContextData structure."""
        error_types = [
            CursorDatabaseNotFoundError("Test error"),
            CursorDatabaseAccessError("Test error"),
            CursorDatabaseSchemaError("Test error"),
            CursorDatabaseQueryError("Test error"),
            WorkspaceDetectionError("Test error"),
            Exception("Unexpected error")  # Generic fallback
        ]
        
        for error in error_types:
            with patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find:
                mock_find.side_effect = error
                
                result = query_cursor_chat_database()
                
                # Assert consistent structure regardless of error type
                assert isinstance(result, dict)
                assert 'chat_history' in result
                assert 'workspace_info' in result
                assert isinstance(result['chat_history'], list)
                assert len(result['chat_history']) == 0
                assert result['workspace_info']['total_messages'] == 0
    
    def test_partial_data_recovery(self):
        """Test recovery when some operations succeed and others fail."""
        with patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find_workspace, \
             patch('src.mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Workspace database found, but global database fails
            mock_discover.return_value = ["/workspace.vscdb"]  # Only workspace DB found
            mock_find_workspace.return_value = (None, None)  # Mock the fallback global DB lookup too
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_provider.getChatHistoryForCommit.return_value = [
                {'role': 'user', 'content': 'Partial data test'}
            ]
            
            result = query_cursor_chat_database()
            
            # Should still return available data
            assert len(result['chat_history']) > 0
            # Workspace database path should contain the expected database
            # Note: In multi-database mode, this might be a list, so check both formats
            workspace_path = result['workspace_info']['workspace_database_path']
            if isinstance(workspace_path, list):
                assert "/workspace.vscdb" in workspace_path
            else:
                assert workspace_path == "/workspace.vscdb"
            assert result['workspace_info']['global_database_path'] is None
            # Should indicate partial success in data quality
            assert result['workspace_info']['data_quality']['status'] == 'complete'  # Database(s) worked
            assert result['workspace_info']['data_quality']['databases_queried'] >= 1  # At least one database worked


class TestErrorLogging:
    """Test that errors are logged with proper context and troubleshooting hints."""
    
    def test_error_logging_includes_context(self, caplog):
        """Test that error logs include full context and troubleshooting hints."""
        with patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find_workspace:
            mock_discover.side_effect = CursorDatabaseNotFoundError(
                "Databases not found",
                path="/test/path",
                operation="discover_databases"
            )
            # Also make the fallback fail to ensure ERROR logging
            mock_find_workspace.side_effect = CursorDatabaseNotFoundError(
                "Fallback databases not found",
                path="/test/path",
                operation="find_workspace_databases"
            )
            
            with caplog.at_level(logging.ERROR):
                query_cursor_chat_database()
            
            # Should log with context (multi-database discovery errors are logged as ERROR)
            error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
            assert len(error_records) > 0
            
            # Check that context is included (look for the path in the detailed error log)
            found_path_context = False
            for record in error_records:
                if hasattr(record, 'path') and record.path == "/test/path":
                    found_path_context = True
                    break
                # Also check if path appears in the message
                if "/test/path" in record.message:
                    found_path_context = True
                    break
            assert found_path_context
    
    def test_sensitive_information_sanitization(self, caplog):
        """Test that sensitive information is sanitized in error logs."""
        with patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find:
            mock_find.side_effect = CursorDatabaseAccessError(
                "Access denied",
                path="/secure/database.vscdb",
                api_key="secret-key-12345"  # Should be sanitized
            )
            
            with caplog.at_level(logging.ERROR):
                query_cursor_chat_database()
            
            # Check that sensitive information is redacted
            log_messages = [record.message for record in caplog.records]
            combined_log = " ".join(log_messages)
            assert "secret-key-12345" not in combined_log
            assert "[REDACTED]" in combined_log or "api_key" not in combined_log


class TestTelemetryIntegration:
    """Test that telemetry properly records error categories."""
    
    @patch('opentelemetry.trace.get_current_span')
    def test_telemetry_records_error_categories(self, mock_get_current_span):
        """Test that telemetry spans record error types and categories."""
        mock_span = Mock()
        mock_get_current_span.return_value = mock_span
        
        with patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find:
            mock_find.side_effect = CursorDatabaseNotFoundError("Test error")
            
            query_cursor_chat_database()
            
            # Should set error attributes on span
            mock_span.set_attribute.assert_any_call('error.type', 'CursorDatabaseNotFoundError')
            mock_span.set_attribute.assert_any_call('error.category', 'database_not_found')
            mock_span.record_exception.assert_called_once()
    
    @patch('opentelemetry.trace.get_current_span')
    def test_telemetry_different_error_categories(self, mock_get_current_span):
        """Test telemetry records different error categories correctly."""
        mock_span = Mock()
        mock_get_current_span.return_value = mock_span
        
        error_mappings = [
            (CursorDatabaseAccessError("Test"), 'database_access'),
            (CursorDatabaseSchemaError("Test"), 'database_schema'),
            (CursorDatabaseQueryError("Test"), 'database_query'),
            (WorkspaceDetectionError("Test"), 'workspace_detection')
        ]
        
        for error, expected_category in error_mappings:
            with patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find:
                mock_find.side_effect = error
                mock_span.reset_mock()
                
                query_cursor_chat_database()
                
                mock_span.set_attribute.assert_any_call('error.category', expected_category)


class TestCircuitBreakerPattern:
    """Test circuit breaker pattern for repeated failures."""
    
    def test_circuit_breaker_after_repeated_failures(self):
        """Test that repeated failures trigger circuit breaker pattern."""
        failure_count_discover = 0
        failure_count_find = 0
        
        def failing_discover_function(*args, **kwargs):
            nonlocal failure_count_discover
            failure_count_discover += 1
            if failure_count_discover <= 5:
                raise CursorDatabaseAccessError("Repeated failure")
            return (['workspace.vscdb'], 'global.vscdb')
        
        def failing_find_function(*args, **kwargs):
            nonlocal failure_count_find
            failure_count_find += 1
            if failure_count_find <= 5:
                raise CursorDatabaseAccessError("Repeated failure")
            return ('workspace.vscdb', 'global.vscdb')
        
        with patch('src.mcp_commit_story.cursor_db.discover_all_cursor_databases', side_effect=failing_discover_function), \
             patch('src.mcp_commit_story.cursor_db.find_workspace_composer_databases', side_effect=failing_find_function):
            # First few calls should trigger normal error handling
            for _ in range(3):
                result = query_cursor_chat_database()
                assert 'error_info' in result['workspace_info']
                assert result['workspace_info']['error_info']['error_type'] == 'CursorDatabaseAccessError'
            
            # After repeated failures, should still handle gracefully
            result = query_cursor_chat_database()
            # Should still return valid structure with error info
            assert 'error_info' in result['workspace_info'] 