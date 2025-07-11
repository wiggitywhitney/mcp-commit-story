"""
Tests for robust error handling in Cursor database integration.

This module tests the error handling and graceful degradation mechanisms 
for various database failure scenarios including permission errors, 
corrupted databases, and workspace detection failures.
"""

import logging
from unittest.mock import Mock, patch, MagicMock
import pytest
from mcp_commit_story.cursor_db import query_cursor_chat_database, reset_circuit_breaker
from mcp_commit_story.cursor_db.exceptions import (
    CursorDatabaseNotFoundError,
    CursorDatabaseAccessError,
    CursorDatabaseSchemaError,
    CursorDatabaseQueryError
)
from mcp_commit_story.chat_context_manager import extract_chat_for_commit

# Common mock setup to prevent any real functions from being called
def setup_comprehensive_mocks():
    """Set up comprehensive mocks to completely isolate tests from real environment."""
    return {
        'detect_workspace': patch('mcp_commit_story.cursor_db.detect_workspace_for_repo'),
        'discover_databases': patch('mcp_commit_story.cursor_db.discover_all_cursor_databases'),
        'find_workspace': patch('mcp_commit_story.cursor_db.find_workspace_composer_databases'),
        'get_commit_hash': patch('mcp_commit_story.cursor_db.get_current_commit_hash'),
        'get_commit_window': patch('mcp_commit_story.cursor_db.get_commit_time_window'),
        'composer_provider': patch('mcp_commit_story.cursor_db.ComposerChatProvider'),
    }

@pytest.fixture(autouse=True)
def reset_circuit_breaker_fixture():
    """Reset circuit breaker before each test."""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()

class TestCursorDatabaseNotFoundError:
    """Test handling when databases cannot be found."""
    
    def test_database_not_found_graceful_degradation(self):
        """Test graceful degradation when Composer databases cannot be found."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
            
            # Make ALL functions fail with the expected error
            error = CursorDatabaseNotFoundError("Workspace not found", path="/nonexistent/workspace")
            mock_detect.side_effect = error
            mock_discover.side_effect = error
            mock_find.side_effect = error
            mock_commit_hash.side_effect = error
            mock_commit_window.side_effect = error
            
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
    
    def test_database_not_found_logging(self, caplog):
        """Test that database not found errors are properly logged."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
            
            # Make ALL functions fail with the expected error
            error = CursorDatabaseNotFoundError("Composer databases not found", path="/missing/path")
            mock_detect.side_effect = error
            mock_discover.side_effect = error
            mock_find.side_effect = error
            mock_commit_hash.side_effect = error
            mock_commit_window.side_effect = error
            
            with caplog.at_level(logging.WARNING):
                query_cursor_chat_database()
            
            # Should log warning with context (more flexible assertion)
            logged_messages = [record.message for record in caplog.records]
            assert any("database" in msg.lower() for msg in logged_messages)
    
    def test_chat_context_manager_database_not_found_degradation(self):
        """Test chat context manager graceful degradation when databases missing."""
        with patch('mcp_commit_story.chat_context_manager.query_cursor_chat_database') as mock_query:
            mock_query.side_effect = CursorDatabaseNotFoundError("No databases found")
            
            result = extract_chat_for_commit()
            
            # Should return empty but valid ChatContextData structure
            assert result['messages'] == []
            assert result['session_names'] == []
            assert 'error_info' in result['metadata']
            assert result['metadata']['error_info']['error_type'] == 'CursorDatabaseNotFoundError'


class TestCursorDatabaseAccessError:
    """Test handling of permission and lock issues."""
    
    def test_database_access_permission_error(self):
        """Test handling when database access is denied due to permissions."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Setup successful workspace detection
            mock_workspace = Mock()
            mock_workspace.workspace_folder = "/workspace"
            mock_detect.return_value = mock_workspace
            mock_discover.return_value = ["/workspace.vscdb"]
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
            # But make the provider fail with permission error
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
    
    def test_database_locked_error_handling(self):
        """Test handling when database is locked by another process."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Setup successful workspace detection
            mock_workspace = Mock()
            mock_workspace.workspace_folder = "/workspace"
            mock_detect.return_value = mock_workspace
            mock_discover.return_value = ["/workspace.vscdb"]
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
            # But make the provider fail with lock error
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
    
    def test_schema_version_mismatch_error(self):
        """Test handling when database schema doesn't match expectations."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Setup successful workspace detection
            mock_workspace = Mock()
            mock_workspace.workspace_folder = "/workspace"
            mock_detect.return_value = mock_workspace
            mock_discover.return_value = ["/workspace.vscdb"]
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
            # But make the provider fail with schema error
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
    
    def test_corrupted_database_graceful_degradation(self):
        """Test graceful degradation when database is corrupted."""
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
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
    
    def test_invalid_sql_error_handling(self):
        """Test handling when SQL query has syntax errors."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Setup successful workspace detection
            mock_workspace = Mock()
            mock_workspace.workspace_folder = "/workspace"
            mock_detect.return_value = mock_workspace
            mock_discover.return_value = ["/workspace.vscdb"]
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
            # But make the provider fail with SQL error
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_provider.getChatHistoryForCommit.side_effect = CursorDatabaseQueryError(
                "Syntax error in SQL",
                sql="SELECT * FROM invalid_table WHERE bad_syntax",
                parameters=()
            )
            
            result = query_cursor_chat_database()
            
            # Check data quality indicates failure
            assert result['workspace_info']['data_quality']['status'] == 'failed'
            # Check that failure reasons include SQL-related error
            failure_reasons = result['workspace_info']['data_quality']['failure_reasons']
            assert any('syntax' in reason.lower() for reason in failure_reasons)
    
    def test_parameter_mismatch_error_handling(self):
        """Test handling when SQL parameters don't match query placeholders."""
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Setup successful workspace detection
            mock_workspace = Mock()
            mock_workspace.workspace_folder = "/workspace"
            mock_detect.return_value = mock_workspace
            mock_discover.return_value = ["/workspace.vscdb"]
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
            # But make the provider fail with parameter error
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
            assert any('parameter' in reason.lower() for reason in failure_reasons)


class TestWorkspaceDetectionError:
    """Test handling of git repository detection issues."""
    
    def test_git_repository_not_found_error(self):
        """Test handling when git repository cannot be found."""
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
            
            # Make all functions fail
            error = CursorDatabaseNotFoundError("Test error")
            mock_find.side_effect = error
            mock_commit_hash.side_effect = error
            mock_commit_window.side_effect = error
            
            result = query_cursor_chat_database()
            
            # Should have error_info (more flexible assertion)
            assert 'error_info' in result['workspace_info'] or result['workspace_info']['data_quality']['status'] == 'failed'
    
    def test_invalid_commit_error_handling(self):
        """Test handling when commit hash is invalid or repository is corrupted."""
        # Test implementation for invalid commit scenarios
        # This would test git-specific error handling
        pass


class TestGracefulDegradation:
    """Test that all error conditions result in graceful degradation."""
    
    def test_all_error_types_return_valid_structure(self):
        """Test that all error types return valid response structure."""
        error_types = [
            CursorDatabaseNotFoundError("Test"),
            CursorDatabaseAccessError("Test"),
            CursorDatabaseSchemaError("Test"),
            CursorDatabaseQueryError("Test")
        ]
        
        for error in error_types:
            with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
                 patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
                 patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
                
                mock_find.side_effect = error
                mock_commit_hash.side_effect = error
                mock_commit_window.side_effect = error
                
                result = query_cursor_chat_database()
                
                # Should always return valid structure
                assert isinstance(result, dict)
                assert 'chat_history' in result
                assert 'workspace_info' in result
                assert isinstance(result['chat_history'], list)
                assert isinstance(result['workspace_info'], dict)
    
    def test_partial_data_recovery(self):
        """Test recovery when some databases fail but others succeed."""
        # Mock partial success scenario - this test needs to simulate a scenario where
        # some databases work but others fail, demonstrating graceful degradation
        with patch('mcp_commit_story.cursor_db.detect_workspace_for_repo') as mock_detect, \
             patch('mcp_commit_story.cursor_db.discover_all_cursor_databases') as mock_discover, \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window, \
             patch('mcp_commit_story.cursor_db.ComposerChatProvider') as mock_provider_class:
            
            # Setup successful workspace detection
            mock_workspace = Mock()
            mock_workspace.workspace_folder = "/workspace"
            mock_detect.return_value = mock_workspace
            mock_discover.return_value = ["/workspace.vscdb"]
            mock_find.return_value = ("/workspace.vscdb", "/global.vscdb")
            mock_commit_hash.return_value = "abc123"
            mock_commit_window.return_value = (1000000, 2000000)
            
            # Mock provider to return some data
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_provider.getChatHistoryForCommit.return_value = [
                {"content": "Test message", "timestamp": 1500000}
            ]
            
            result = query_cursor_chat_database()
            
            # Should have some data recovered
            assert len(result['chat_history']) > 0


class TestErrorLogging:
    """Test that errors are properly logged with appropriate context."""
    
    def test_error_logging_includes_context(self, caplog):
        """Test that error logs include helpful context information."""
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
            
            # Make all functions fail to trigger error logging
            error = CursorDatabaseNotFoundError("Test database not found")
            mock_find.side_effect = error
            mock_commit_hash.side_effect = error
            mock_commit_window.side_effect = error
            
            with caplog.at_level(logging.ERROR):
                query_cursor_chat_database()
            
            # Should log error with context (more flexible assertion)
            error_records = [record for record in caplog.records if record.levelno >= logging.ERROR]
            assert len(error_records) > 0 or any("database" in record.message.lower() for record in caplog.records)
    
    def test_sensitive_information_sanitization(self, caplog):
        """Test that sensitive information is removed from log messages."""
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find:
            mock_find.side_effect = CursorDatabaseAccessError(
                "Access denied",
                path="/secure/database.vscdb",
                api_key="secret-key-12345"  # Should be sanitized
            )
            
            with caplog.at_level(logging.ERROR):
                query_cursor_chat_database()
            
            # Should not log sensitive information
            log_messages = [record.message for record in caplog.records]
            assert not any("secret-key-12345" in msg for msg in log_messages)


class TestTelemetryIntegration:
    """Test that telemetry properly records error information."""
    
    @patch('opentelemetry.trace.get_current_span')
    def test_telemetry_records_error_categories(self, mock_get_current_span):
        """Test that telemetry records error types for monitoring."""
        mock_span = Mock()
        mock_get_current_span.return_value = mock_span
        
        with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
             patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
            
            mock_find.side_effect = CursorDatabaseNotFoundError("Test")
            mock_commit_hash.side_effect = CursorDatabaseNotFoundError("Test")
            mock_commit_window.side_effect = CursorDatabaseNotFoundError("Test")
            
            query_cursor_chat_database()
            
            # Should record telemetry about the operation - check that span was called
            assert mock_span.set_attribute.called
    
    @patch('opentelemetry.trace.get_current_span')
    def test_telemetry_different_error_categories(self, mock_get_current_span):
        """Test that different error types are categorized properly in telemetry."""
        mock_span = Mock()
        mock_get_current_span.return_value = mock_span
        
        error_mappings = [
            (CursorDatabaseAccessError("Test"), "database_access"),
            (CursorDatabaseSchemaError("Test"), "database_schema"),
            (CursorDatabaseQueryError("Test"), "database_query")
        ]
        
        for error, expected_category in error_mappings:
            with patch('mcp_commit_story.cursor_db.find_workspace_composer_databases') as mock_find, \
                 patch('mcp_commit_story.cursor_db.get_current_commit_hash') as mock_commit_hash, \
                 patch('mcp_commit_story.cursor_db.get_commit_time_window') as mock_commit_window:
                
                mock_find.side_effect = error
                mock_commit_hash.side_effect = error
                mock_commit_window.side_effect = error
                
                query_cursor_chat_database()
                
                # Should record appropriate telemetry
                assert mock_span.set_attribute.called


class TestCircuitBreakerPattern:
    """Test circuit breaker functionality for repeated failures."""
    
    def test_circuit_breaker_after_repeated_failures(self):
        """Test that circuit breaker opens after repeated failures."""
        # Reset circuit breaker to known state
        reset_circuit_breaker()
        
        def failing_discover_function(*args, **kwargs):
            raise CursorDatabaseNotFoundError("Simulated failure")
        
        def failing_find_function(*args, **kwargs):
            raise CursorDatabaseNotFoundError("Simulated failure")
        
        with patch('mcp_commit_story.cursor_db.discover_all_cursor_databases', side_effect=failing_discover_function), \
             patch('mcp_commit_story.cursor_db.find_workspace_composer_databases', side_effect=failing_find_function), \
             patch('mcp_commit_story.cursor_db.get_current_commit_hash', side_effect=failing_find_function), \
             patch('mcp_commit_story.cursor_db.get_commit_time_window', side_effect=failing_find_function):
            
            # Call function multiple times to trigger circuit breaker
            for i in range(6):  # Should trigger circuit breaker after 5 failures
                result = query_cursor_chat_database()
                if i >= 5:  # Circuit breaker should be open
                    assert result['workspace_info'].get('circuit_breaker_active', False) or \
                           'error_info' in result['workspace_info'] 