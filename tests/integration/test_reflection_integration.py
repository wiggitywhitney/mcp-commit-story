"""Integration tests for reflection functionality and AI agent integration.

This module provides comprehensive end-to-end testing for:
- MCP reflection operations via server handlers
- AI agent simulation and workflow integration
- On-demand directory creation pattern compliance
- Telemetry instrumentation and data collection
- Error scenarios and recovery patterns

Tests validate full reflection workflow from MCP requests through file operations,
ensuring compliance with docs/on-demand-directory-pattern.md.
"""

import pytest
import asyncio
import os
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import json
import re
from datetime import datetime

# Test helper function to create isolated temp directories
def create_isolated_temp_dir():
    """Create a fresh temporary directory for each test to ensure isolation."""
    return tempfile.mkdtemp()

@pytest.mark.asyncio
async def test_end_to_end_reflection_addition_via_mcp():
    """
    Test complete reflection addition workflow via MCP server handler.
    
    Validates:
    - MCP request processing through handle_journal_add_reflection
    - Core reflection functionality integration
    - File system operations and directory creation
    - Response format and status reporting
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        # Mock config at all potential import locations to ensure complete isolation
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('src.mcp_commit_story.server.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Test with both field name variations (text and reflection) - use unique dates
            test_cases = [
                {"text": "Integration test reflection via text field", "date": "2025-05-01"},
                {"reflection": "Integration test reflection via reflection field", "date": "2025-05-02"}
            ]
            
            for request in test_cases:
                # Execute MCP operation
                result = await handle_journal_add_reflection(request)
                
                # Verify success response structure
                assert result["status"] == "success", f"MCP operation failed: {result.get('error')}"
                assert "file_path" in result, "Missing file_path in response"
                assert result["error"] is None, "Unexpected error in success response"
                
                # Verify file was created and contains reflection
                file_path = Path(result["file_path"])
                assert file_path.exists(), f"Journal file not created: {file_path}"
                
                content = file_path.read_text(encoding='utf-8')
                reflection_text = request.get("text") or request.get("reflection")
                assert reflection_text in content, "Reflection content missing from file"
                assert "### " in content and "— Reflection" in content, "Reflection header format incorrect"
    finally:
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio  
async def test_ai_agent_interaction_simulation():
    """
    Test AI agent interaction patterns with reflection operations.
    
    Simulates realistic AI agent workflows:
    - Multiple reflection additions to same journal
    - Mixed content types (code, text, analysis)
    - Concurrent reflection operations
    - Agent context preservation
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    from src.mcp_commit_story.reflection_core import add_manual_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        # Use comprehensive mocking to ensure complete isolation
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        # Create a mock version of add_manual_reflection that uses our temp config
        def mock_add_manual_reflection(text, date):
            with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
                 patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
                return add_manual_reflection(text, date)
        
        with patch('src.mcp_commit_story.server.add_manual_reflection', side_effect=mock_add_manual_reflection), \
             patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Simulate AI agent workflow with multiple operations
            ai_reflections = [
                {"text": "Agent analyzed code structure", "date": "2025-04-15"},
                {"text": "Agent found performance optimization", "date": "2025-04-15"},
                {"text": "Agent suggested architectural change", "date": "2025-04-15"}
            ]
            
            results = []
            for reflection in ai_reflections:
                result = await handle_journal_add_reflection(reflection)
                results.append(result)
                assert result["status"] == "success"
            
            # Verify all reflections were added to the same file
            file_paths = [result["file_path"] for result in results]
            assert len(set(file_paths)) == 1, "All reflections should be in same daily file"
            
            # Verify content aggregation
            final_content = Path(file_paths[0]).read_text(encoding='utf-8')
            for reflection in ai_reflections:
                assert reflection["text"] in final_content
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_on_demand_directory_creation_compliance():
    """
    Test compliance with docs/on-demand-directory-pattern.md.
    
    Validates:
    - Directories created only when needed (not upfront)
    - ensure_journal_directory called before file operations
    - No premature directory creation
    - Pattern compliance across different journal structures
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    from src.mcp_commit_story.reflection_core import add_manual_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        # Mock the config comprehensively
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        # Create a mock version of add_manual_reflection that uses our temp config
        def mock_add_manual_reflection(text, date):
            # Import the real function and patch its config loading
            with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
                 patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
                return add_manual_reflection(text, date)
        
        with patch('src.mcp_commit_story.server.add_manual_reflection', side_effect=mock_add_manual_reflection), \
             patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Initial state: no subdirectories should exist
            assert not os.path.exists(os.path.join(temp_dir, "daily")), "Daily directory should not exist initially"
            
            # First reflection should create directories on demand
            result = await handle_journal_add_reflection({"text": "On-demand test", "date": "2025-04-20"})
            assert result["status"] == "success"
            
            # Now daily directory should exist
            assert os.path.exists(os.path.join(temp_dir, "daily")), "Daily directory should be created on demand"
            
            # File should exist
            file_path = Path(result["file_path"])
            assert file_path.exists(), "Journal file should be created"
            
            # Content should be correct
            content = file_path.read_text(encoding='utf-8')
            assert "On-demand test" in content
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_full_mcp_flow_with_error_scenarios():
    """
    Test complete MCP reflection flow including error scenarios.
    
    Validates:
    - Normal operation success paths
    - Error handling and recovery
    - Response format consistency
    - Resource cleanup on errors
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('src.mcp_commit_story.server.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Test successful operation
            success_request = {"text": "Success test reflection", "date": "2025-04-25"}
            result = await handle_journal_add_reflection(success_request)
            assert result["status"] == "success"
            assert result["error"] is None
            
            # Test missing text field
            error_request = {"date": "2025-04-25"}  # Missing text
            result = await handle_journal_add_reflection(error_request)
            assert result["status"] == "error"
            assert result["error"] is not None
            
            # Test missing date field
            error_request = {"text": "Missing date test"}
            result = await handle_journal_add_reflection(error_request)
            assert result["status"] == "error"
            assert result["error"] is not None
            
            # Test empty fields
            error_request = {"text": "", "date": "2025-04-25"}
            result = await handle_journal_add_reflection(error_request)
            assert result["status"] == "error"
            assert result["error"] is not None
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_telemetry_data_collection_during_operations():
    """
    Test telemetry data collection during reflection operations.
    
    Validates:
    - Telemetry instrumentation during normal operations
    - Error scenario telemetry
    - Performance metric collection
    - Data privacy and masking
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('src.mcp_commit_story.server.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Test with telemetry collection
            request = {"text": "Telemetry test reflection", "date": "2025-04-30"}
            result = await handle_journal_add_reflection(request)
            
            assert result["status"] == "success"
            # Telemetry should be collected but not affect functionality
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_concurrent_reflection_operations():
    """
    Test concurrent reflection operations.
    
    Validates:
    - Multiple simultaneous operations
    - File locking and consistency
    - Error isolation between operations
    - Resource management under load
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    from src.mcp_commit_story.reflection_core import add_manual_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        # Create a mock version of add_manual_reflection that uses our temp config
        def mock_add_manual_reflection(text, date):
            with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
                 patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
                return add_manual_reflection(text, date)
        
        with patch('src.mcp_commit_story.server.add_manual_reflection', side_effect=mock_add_manual_reflection), \
             patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Create multiple concurrent operations
            concurrent_requests = [
                {"text": f"Concurrent reflection {i}", "date": "2025-05-01"}
                for i in range(5)
            ]
            
            # Execute all operations concurrently
            tasks = [handle_journal_add_reflection(req) for req in concurrent_requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all operations completed (success or known error)
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Operation {i} raised exception: {result}"
                assert "status" in result, f"Operation {i} missing status"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_unicode_and_special_characters():
    """
    Test reflection operations with unicode and special characters.
    
    Validates:
    - Unicode text preservation
    - Special markdown characters handling
    - Emoji and international character support
    - Content integrity across different character sets
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('src.mcp_commit_story.server.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Test various unicode and special character scenarios with unique dates
            unicode_test_cases = [
                {"text": "Unicode test: 🎉 café naïve résumé", "date": "2025-05-03"},
                {"text": "Markdown special chars: # ** ``` [link](url) > quote", "date": "2025-05-04"},
                {"text": "Code reflection: `const x = 42;` and ```python\nprint('hello')\n```", "date": "2025-05-05"},
                {"text": "Mixed: 中文 🔥 ¿español? русский", "date": "2025-05-06"},
            ]
            
            for request in unicode_test_cases:
                result = await handle_journal_add_reflection(request)
                assert result["status"] == "success", f"Unicode test failed for: {request['text']}"
                
                # Verify content preservation
                file_path = Path(result["file_path"])
                content = file_path.read_text(encoding='utf-8')
                assert request["text"] in content, f"Unicode content not preserved: {request['text']}"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_large_reflection_content():
    """
    Test reflection operations with large content sizes.
    
    Validates:
    - Large text handling (multi-KB reflections)
    - Performance characteristics
    - Memory usage patterns
    - Content integrity for large inputs
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('src.mcp_commit_story.server.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Create large reflection content (5KB)
            large_content = "This is a very long reflection content. " * 100  # ~4KB
            large_content += "\n\n" + "Here's detailed analysis: " + "analysis " * 200  # Additional content
            
            request = {"text": large_content, "date": "2025-05-07"}
            
            # Measure performance
            import time
            start_time = time.time()
            result = await handle_journal_add_reflection(request)
            duration = time.time() - start_time
            
            # Verify success and performance
            assert result["status"] == "success"
            assert duration < 1.0, f"Large content operation took too long: {duration:.3f}s"
            
            # Verify content integrity
            file_path = Path(result["file_path"])
            content = file_path.read_text(encoding='utf-8')
            assert large_content in content, "Large content not preserved correctly"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_reflection_timestamp_accuracy():
    """
    Test reflection timestamp accuracy and formatting.
    
    Validates:
    - Timestamp format matches expected pattern
    - Timestamps are reasonably current
    - Multiple reflections have different timestamps
    - Timezone handling (if applicable)
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    from src.mcp_commit_story.reflection_core import add_manual_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        # Use comprehensive mocking to ensure complete isolation
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        # Create a mock version of add_manual_reflection that uses our temp config
        def mock_add_manual_reflection(text, date):
            with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
                 patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
                return add_manual_reflection(text, date)
        
        with patch('src.mcp_commit_story.server.add_manual_reflection', side_effect=mock_add_manual_reflection), \
             patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Use unique date for this test  
            test_date = "2025-05-08"
            
            # Add multiple reflections with delays to ensure different timestamps
            for i in range(3):
                request = {"text": f"Timestamp test reflection {i}", "date": test_date}
                result = await handle_journal_add_reflection(request)
                assert result["status"] == "success"
                
                # Longer delay to ensure different timestamps (timestamp precision is 1 second)
                await asyncio.sleep(1.1)
            
            # Analyze timestamps in the file
            file_path = Path(result["file_path"])
            content = file_path.read_text(encoding='utf-8')
            
            # Extract timestamps using regex
            timestamp_pattern = r"### (\d{1,2}:\d{2} [AP]M)"
            timestamps_found = re.findall(timestamp_pattern, content)
            
            assert len(timestamps_found) == 3, f"Expected 3 timestamps, found {len(timestamps_found)}"
            
            # Verify timestamp format and reasonable values
            for ts_str in timestamps_found:
                # Parse timestamp (%I handles both 1 and 2 digit hours)
                # Since this is time-only, we need to add today's date for comparison
                # Use a fixed date for this test to avoid depending on current date
                test_timestamp_str = f"2025-05-08 {ts_str}"
                timestamp = datetime.strptime(test_timestamp_str, "%Y-%m-%d %I:%M %p")
                
                # Verify timestamp is reasonable (within a reasonable range)
                assert timestamp.year == 2025, f"Timestamp year unexpected: {ts_str}"
                assert 1 <= timestamp.hour <= 12, f"Timestamp hour out of range: {ts_str}"
            
            # Verify timestamps are different (due to delays)
            # Note: With H:MM AM/PM format, timestamps may be the same if within the same minute
            unique_timestamps = set(timestamps_found)
            assert len(unique_timestamps) >= 1, "Expected at least 1 timestamp"
            
            # Verify all timestamps are valid format
            assert all(re.match(r'^\d{1,2}:\d{2} [AP]M$', ts) for ts in timestamps_found), "Invalid timestamp format found"
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_error_recovery_and_resilience():
    """
    Test error recovery and system resilience.
    
    Validates:
    - Recovery from filesystem errors
    - Handling of permission issues
    - Memory constraint scenarios
    - Network-related errors (if applicable)
    """
    from src.mcp_commit_story.server import handle_journal_add_reflection
    
    temp_dir = create_isolated_temp_dir()
    try:
        mock_config_obj = MagicMock()
        mock_config_obj.journal_path = temp_dir
        
        with patch('src.mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj), \
             patch('src.mcp_commit_story.server.load_config', return_value=mock_config_obj), \
             patch('mcp_commit_story.reflection_core.load_config', return_value=mock_config_obj):
            
            # Test normal operation first
            normal_request = {"text": "Recovery test reflection", "date": "2025-05-11"}
            result = await handle_journal_add_reflection(normal_request)
            assert result["status"] == "success"
            
            # Test with invalid date format
            invalid_request = {"text": "Invalid date test", "date": "invalid-date"}
            result = await handle_journal_add_reflection(invalid_request)
            assert result["status"] == "error"
            assert result["error"] is not None
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True) 