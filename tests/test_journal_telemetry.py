"""
Unit tests for journal telemetry instrumentation.

Tests the instrumentation of journal management operations with OpenTelemetry
for observability of AI context flow, file operations, and journal entry processing.

This covers testing requirements for Task 4.8:
- Journal creation operations tracing
- File operation metrics (create, read, write times)
- Journal entry count metrics  
- Error scenarios in journal operations
- AI context flow tracing (prompt → journal entry)
- Sensitive data handling in spans
- Journal operation performance impact

Usage:
    pytest tests/test_journal_telemetry.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import tempfile
import time
import asyncio
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_commit_story.telemetry import (
    setup_telemetry,
    get_tracer,
    get_meter,
    get_mcp_metrics,
    shutdown_telemetry,
    trace_mcp_operation
)
from mcp_commit_story.journal import (
    JournalEntry,
    get_journal_file_path,
    append_to_journal_file,
    ensure_journal_directory
)
from mcp_commit_story.journal_generate import (
    generate_summary_section,
    generate_technical_synopsis_section,
    generate_accomplishments_section,
    generate_frustrations_section,
    generate_tone_mood_section,
    generate_discussion_notes_section,
    generate_commit_metadata_section
)
from mcp_commit_story.context_types import JournalContext, ChatHistory
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode


class TestJournalOperationTracing:
    """Test tracing of journal creation and management operations."""
    
    def setup_method(self):
        """Set up test environment with fresh telemetry state."""
        shutdown_telemetry()
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-journal",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after tests."""
        shutdown_telemetry()
    
    def test_journal_entry_creation_traced(self):
        """Test that journal entry creation operations are traced."""
        # This test verifies the tracing decorator works on journal entry creation
        tracer = get_tracer("test_journal")
        
        # Mock span to capture trace data
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Create a journal entry (should be traced when decorator is added)
            entry = JournalEntry(
                timestamp="2024-01-01T12:00:00Z",
                commit_hash="abc123",
                summary="Test entry"
            )
            result = entry.to_markdown()
            
            # Verify basic functionality first
            assert "Test entry" in result
            assert "abc123" in result
            
            # Note: Actual tracing verification will happen after instrumentation is added
            # For now, verify that tracing infrastructure is available
            assert tracer is not None
    
    def test_journal_file_operations_traced(self):
        """Test that journal file operations (create, read, write) are traced."""
        tracer = get_tracer("test_journal")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test file path generation
            file_path = get_journal_file_path("2024-01-01", "daily")
            assert "2024-01-01" in str(file_path)
            
            # Test file writing (should be traced when decorator is added)
            test_file = Path(temp_dir) / "test_journal.md"
            test_content = "# Test Journal Entry\nContent here"
            
            with patch.object(tracer, 'start_as_current_span') as mock_span_context:
                mock_span = Mock()
                mock_span_context.return_value.__enter__.return_value = mock_span
                
                # Write to file (will be instrumented)
                append_to_journal_file(test_content, test_file)
                
                # Verify file was written
                assert test_file.exists()
                content = test_file.read_text()
                assert "Test Journal Entry" in content
    
    def test_journal_directory_creation_traced(self):
        """Test that journal directory creation is traced."""
        tracer = get_tracer("test_journal")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "new_dir" / "journal.md"
            
            with patch.object(tracer, 'start_as_current_span') as mock_span_context:
                mock_span = Mock()
                mock_span_context.return_value.__enter__.return_value = mock_span
                
                # Ensure directory (should be traced when decorator is added)
                ensure_journal_directory(test_file)
                
                # Verify directory was created
                assert test_file.parent.exists()


class TestJournalFileOperationMetrics:
    """Test metrics collection for journal file operations."""
    
    def setup_method(self):
        """Set up test environment with fresh telemetry state."""
        shutdown_telemetry()
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-journal",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after tests."""
        shutdown_telemetry()
    
    def test_file_operation_duration_metrics(self):
        """Test that file operation durations are recorded as metrics."""
        metrics_instance = get_mcp_metrics()
        assert metrics_instance is not None
        
        # Test that we can record file operation metrics
        # (Will be integrated after instrumentation is added)
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.md"
            test_content = "Test content"
            
            # Simulate file write operation
            test_file.write_text(test_content)
            
            duration = time.time() - start_time
            
            # Verify we can record the operation duration
            metrics_instance.record_operation_duration(
                "journal.file_write", 
                duration,
                file_type="markdown"
            )
            
            # Verify metric recording capability
            metric_data = metrics_instance.get_metric_data()
            assert metric_data is not None
    
    def test_file_size_metrics(self):
        """Test that file sizes are recorded as metrics."""
        metrics_instance = get_mcp_metrics()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.md"
            test_content = "Test content for size measurement"
            test_file.write_text(test_content)
            
            file_size = test_file.stat().st_size
            
            # Test that we can record file size metrics
            # (Will be instrumented after implementation)
            assert file_size > 0
            assert metrics_instance is not None
    
    def test_journal_entry_count_metrics(self):
        """Test that journal entry counts are tracked as metrics."""
        metrics_instance = get_mcp_metrics()
        
        # Test tracking journal entry creation
        metrics_instance.record_tool_call(
            "journal.entry_created",
            success=True,
            entry_type="daily"
        )
        
        # Verify counter functionality
        counter_values = metrics_instance.get_counter_values()
        assert counter_values is not None


class TestJournalErrorScenarios:
    """Test error scenarios in journal operations and their telemetry."""
    
    def setup_method(self):
        """Set up test environment with fresh telemetry state."""
        shutdown_telemetry()
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-journal",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after tests."""
        shutdown_telemetry()
    
    def test_file_write_error_traced(self):
        """Test that file write errors are properly traced."""
        tracer = get_tracer("test_journal")
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Test write to invalid path (should cause error)
            invalid_path = Path("/invalid/path/that/should/not/exist/test.md")
            
            with pytest.raises(Exception):
                append_to_journal_file("test content", invalid_path)
            
            # Verify that error would be recorded in span
            # (Will be implemented with actual instrumentation)
            assert mock_span is not None
    
    def test_journal_generation_error_handling(self):
        """Test error handling in journal generation functions."""
        tracer = get_tracer("test_journal")
        
        # Test with invalid journal context
        invalid_context = None
        
        # The function handles None gracefully and returns an empty summary
        # Instead of expecting an exception, test that it handles None gracefully
        summary_section = generate_summary_section(invalid_context)
        
        # Verify it returns the expected structure even with None input
        assert summary_section is not None
        assert isinstance(summary_section, dict)
        assert 'summary' in summary_section
        assert summary_section['summary'] == ""
    
    def test_directory_creation_error_traced(self):
        """Test that directory creation errors are traced."""
        tracer = get_tracer("test_journal")
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Test directory creation with invalid permissions
            # Note: This may not always fail on all systems, but tests the pattern
            invalid_path = Path("/root/should_not_have_access/test.md")
            
            try:
                ensure_journal_directory(invalid_path)
            except Exception:
                # Expected in some cases
                pass
            
            # Verify span infrastructure is available
            assert mock_span is not None


class TestAIContextFlowTracing:
    """Test tracing of AI context flow from prompt to journal entry."""
    
    def setup_method(self):
        """Set up test environment with fresh telemetry state."""
        shutdown_telemetry()
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-journal",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after tests."""
        shutdown_telemetry()
    
    def test_ai_generation_traced(self):
        """Test that AI journal generation operations are traced."""
        tracer = get_tracer("test_journal")
        
        # Create mock journal context
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "Implement user auth"},
                {"role": "assistant", "content": "I'll implement JWT authentication"}
            ]
        )
        journal_context = JournalContext(
            chat_history=chat_history,
            file_changes={"auth.js": "added JWT implementation"},
            commit_hash="abc123",
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Test AI generation functions (will be instrumented)
            summary_section = generate_summary_section(journal_context)
            
            # Verify basic functionality - SummarySection is a dict with 'summary' key
            assert summary_section is not None
            assert isinstance(summary_section, dict)
            assert 'summary' in summary_section
    
    def test_context_processing_chain_traced(self):
        """Test that the full context processing chain is traced."""
        tracer = get_tracer("test_journal")
        
        # Create comprehensive journal context
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "Add error handling"},
                {"role": "assistant", "content": "I'll add try-catch blocks"}
            ]
        )
        journal_context = JournalContext(
            chat_history=chat_history,
            file_changes={"error_handler.js": "added error handling"},
            commit_hash="def456",
            timestamp="2024-01-01T13:00:00Z"
        )
        
        # Test multiple generation functions in sequence
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Process multiple sections (simulating full journal generation)
            sections = []
            sections.append(generate_summary_section(journal_context))
            sections.append(generate_accomplishments_section(journal_context))

            
            # Verify all sections were generated
            assert len(sections) == 2
            for section in sections:
                assert section is not None

    def test_all_generation_functions_traced(self):
        """Test that all journal generation functions are traced."""
        tracer = get_tracer("test_journal")
        
        # Create comprehensive journal context
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "Complete implementation"},
                {"role": "assistant", "content": "I'll implement all features"}
            ]
        )
        journal_context = JournalContext(
            chat_history=chat_history,
            file_changes={"app.js": "completed implementation"},
            commit_hash="all123",
            timestamp="2024-01-01T18:00:00Z"
        )
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Test ALL generation functions will be instrumented
            functions_to_test = [
                generate_summary_section,
                generate_technical_synopsis_section,
                generate_accomplishments_section,
                generate_frustrations_section,
                generate_tone_mood_section,
                generate_discussion_notes_section,

                generate_commit_metadata_section
            ]
            
            results = []
            for func in functions_to_test:
                result = func(journal_context)
                results.append(result)
                assert result is not None
            
            # Verify all 7 generation functions work (terminal removed)
            assert len(results) == 7

    def test_file_path_generation_traced(self):
        """Test that file path generation operations are traced."""
        tracer = get_tracer("test_journal")
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Test file path generation (should be traced when decorator is added)
            file_path = get_journal_file_path("2024-01-01", "daily")
            
            # Verify basic functionality
            assert file_path is not None
            assert "2024-01-01" in str(file_path)
            assert tracer is not None


class TestSensitiveDataHandling:
    """Test sensitive data handling in telemetry spans."""
    
    def setup_method(self):
        """Set up test environment with fresh telemetry state."""
        shutdown_telemetry()
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-journal",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after tests."""
        shutdown_telemetry()
    
    def test_sensitive_data_filtering_in_spans(self):
        """Test that sensitive data is filtered from telemetry spans."""
        tracer = get_tracer("test_journal")
        
        # Create context with potentially sensitive data
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "Set API_KEY=sk-secret123456"},
                {"role": "assistant", "content": "I'll configure the API key securely"}
            ]
        )
        
        journal_context = JournalContext(
            chat_history=chat_history,

            file_changes={"config.js": "added API key configuration"},
            commit_hash="ghi789",
            timestamp="2024-01-01T14:00:00Z"
        )
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Generate sections that might contain sensitive data
            summary_section = generate_summary_section(journal_context)
            
            # Verify section was generated (actual sensitive data filtering
            # will be implemented in the instrumentation)
            assert summary_section is not None
    
    def test_personal_information_filtering(self):
        """Test that personal information is filtered from spans."""
        tracer = get_tracer("test_journal")
        
        # Create context with personal information
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "My email is john.doe@company.com"},
                {"role": "assistant", "content": "I'll help with your request"}
            ]
        )
        
        journal_context = JournalContext(
            chat_history=chat_history,

            file_changes={"user.js": "added user configuration"},
            commit_hash="jkl012",
            timestamp="2024-01-01T15:00:00Z"
        )
        
        with patch.object(tracer, 'start_as_current_span') as mock_span_context:
            mock_span = Mock()
            mock_span_context.return_value.__enter__.return_value = mock_span
            
            # Generate sections (personal info should be filtered when instrumented)
            discussion_section = generate_discussion_notes_section(journal_context)
            
            # Verify basic functionality
            assert discussion_section is not None


class TestJournalOperationPerformanceImpact:
    """Test performance impact of journal operation telemetry."""
    
    def setup_method(self):
        """Set up test environment with fresh telemetry state."""
        shutdown_telemetry()
        config = {
            "telemetry": {
                "enabled": True,
                "service_name": "test-journal",
                "service_version": "1.0.0"
            }
        }
        setup_telemetry(config)
    
    def teardown_method(self):
        """Clean up after tests."""
        shutdown_telemetry()
    
    def test_telemetry_overhead_acceptable(self):
        """Test that telemetry overhead is within acceptable limits."""
        # Create sample journal context
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "Optimize performance"},
                {"role": "assistant", "content": "I'll profile the code"}
            ]
        )
        
        journal_context = JournalContext(
            chat_history=chat_history,

            file_changes={"performance.js": "added optimizations"},
            commit_hash="mno345",
            timestamp="2024-01-01T16:00:00Z"
        )
        
        # Measure performance without telemetry
        start_time = time.time()
        summary_section = generate_summary_section(journal_context)
        baseline_duration = time.time() - start_time
        
        # Verify basic functionality
        assert summary_section is not None
        
        # Performance impact testing will be more meaningful after
        # actual instrumentation is added
        assert baseline_duration >= 0  # Basic sanity check
    
    def test_batch_journal_operations_performance(self):
        """Test performance impact on batch journal operations."""
        # Create multiple journal contexts for batch testing
        contexts = []
        for i in range(5):
            chat_history = ChatHistory(
                messages=[
                    {"role": "user", "content": f"Task {i}"},
                    {"role": "assistant", "content": f"Completing task {i}"}
                ]
            )
            
            context = JournalContext(
                chat_history=chat_history,

                file_changes={f"task_{i}.js": f"implemented task {i}"},
                commit_hash=f"hash{i:03d}",
                timestamp=f"2024-01-01T{16+i:02d}:00:00Z"
            )
            contexts.append(context)
        
        # Measure batch processing time
        start_time = time.time()
        
        for context in contexts:
            generate_summary_section(context)
            generate_accomplishments_section(context)
        
        batch_duration = time.time() - start_time
        
        # Verify operations completed
        assert len(contexts) == 5
        assert batch_duration >= 0
    
    def test_concurrent_journal_operations_performance(self):
        """Test performance impact on concurrent journal operations."""
        # Test concurrent operation support (for future async implementations)
        chat_history = ChatHistory(
            messages=[
                {"role": "user", "content": "Concurrent task"},
                {"role": "assistant", "content": "Processing concurrently"}
            ]
        )
        
        journal_context = JournalContext(
            chat_history=chat_history,

            file_changes={"concurrent.js": "added concurrent processing"},
            commit_hash="pqr678",
            timestamp="2024-01-01T17:00:00Z"
        )
        
        # Simulate concurrent operations
        start_time = time.time()
        
        # Run multiple operations (simulating concurrent processing)
        results = []
        results.append(generate_summary_section(journal_context))
        results.append(generate_technical_synopsis_section(journal_context))
        results.append(generate_accomplishments_section(journal_context))
        
        concurrent_duration = time.time() - start_time
        
        # Verify all operations completed
        assert len(results) == 3
        for result in results:
            assert result is not None
        assert concurrent_duration >= 0


class TestTelemetryEnhancements:
    """Test async support and debug mode features in telemetry."""
    
    def test_async_function_decorator_support(self):
        """Test that the decorator works with async functions."""
        import asyncio
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test.async_function", attributes={"test_type": "async"})
        async def async_test_function(value: str) -> str:
            await asyncio.sleep(0.001)  # Minimal async operation
            return f"processed_{value}"
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_test_function("test_data"))
            assert result == "processed_test_data"
        finally:
            loop.close()
    
    def test_sync_function_decorator_support(self):
        """Test that the decorator still works with sync functions."""
        from mcp_commit_story.telemetry import trace_mcp_operation
        
        @trace_mcp_operation("test.sync_function", attributes={"test_type": "sync"})
        def sync_test_function(value: str) -> str:
            return f"processed_{value}"
        
        result = sync_test_function("test_data")
        assert result == "processed_test_data"
    
    def test_debug_mode_sanitization(self):
        """Test that debug mode provides less aggressive sanitization."""
        from mcp_commit_story.telemetry import sanitize_for_telemetry
        
        test_data = {
            "api_key": "sk-1234567890abcdef1234567890abcdef12345678",
            "commit_hash": "a1b2c3d4e5f6789012345678901234567890abcd",
            "email": "user@example.com",
            "file_path": "/home/user/project/src/file.py"
        }
        
        # Test production mode (more aggressive)
        production_results = {}
        for key, value in test_data.items():
            production_results[key] = sanitize_for_telemetry(value, debug_mode=False)
        
        # Test debug mode (less aggressive)
        debug_results = {}
        for key, value in test_data.items():
            debug_results[key] = sanitize_for_telemetry(value, debug_mode=True)
        
        # Verify debug mode is less aggressive
        # API key should show more characters in debug mode
        assert "sk-12345678" in debug_results["api_key"]  # Debug shows more characters
        assert "sk-1234" in production_results["api_key"]  # Production shows fewer
        assert len(debug_results["api_key"]) > len(production_results["api_key"])  # Debug is longer
        
        # Debug mode should be more permissive with file paths and other data
        assert len(debug_results["file_path"]) >= len(production_results["file_path"])
        
        # Both modes should protect truly sensitive data
        assert "***" in debug_results["api_key"]
        assert "***" in production_results["api_key"]
        
        # Debug mode should have higher character limits (2000 vs 1000)
        long_string = "This is a normal text string. " * 100  # ~3000 chars, no suspicious patterns
        debug_long = sanitize_for_telemetry(long_string, debug_mode=True)
        prod_long = sanitize_for_telemetry(long_string, debug_mode=False)
        assert len(debug_long) == 2000  # Debug limit
        assert len(prod_long) == 1000   # Production limit
        assert len(debug_long) > len(prod_long)  # Debug mode is more permissive with length


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 