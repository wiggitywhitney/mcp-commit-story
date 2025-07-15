"""
Test suite for reflection format functionality.

Tests the format_reflection function to ensure it includes proper separator
and uses unified header format consistent with other journal entries.
"""

import pytest
from unittest.mock import patch
from datetime import datetime

from mcp_commit_story.reflection_core import format_reflection


class TestReflectionFormat:
    """Test the format_reflection function to ensure it includes the separator and unified header format."""
    
    def test_format_reflection_includes_separator(self):
        """Test that format_reflection uses the correct header format."""
        test_reflection = "This is a test reflection"
        
        result = format_reflection(test_reflection)
        
        # Should start with header format (no separator)
        assert result.startswith("\n\n###")
        
        # Should have the reflection content
        assert test_reflection in result
    
    def test_format_reflection_unified_header_format(self):
        """Test that format_reflection uses the unified header format."""
        test_reflection = "This is a test reflection"
        
        with patch('mcp_commit_story.reflection_core.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 7, 9, 14, 30, 0)
            mock_datetime.strftime = datetime.strftime
            
            result = format_reflection(test_reflection)
            
            # Should include unified header format (no separator)
            expected_header = "\n\n### 2:30 PM — Reflection\n\n"
            assert expected_header in result
            assert test_reflection in result
    
    def test_format_reflection_timestamp_formatting(self):
        """Test that timestamp formatting matches the unified format."""
        test_reflection = "Test reflection content"
        
        with patch('mcp_commit_story.reflection_core.datetime') as mock_datetime:
            # Test various times to verify format consistency
            test_times = [
                (datetime(2025, 7, 9, 9, 5, 0), "9:05 AM"),  # Single digit hour/minute
                (datetime(2025, 7, 9, 14, 30, 0), "2:30 PM"),  # PM time
                (datetime(2025, 7, 9, 0, 0, 0), "12:00 AM"),  # Midnight
                (datetime(2025, 7, 9, 12, 0, 0), "12:00 PM"),  # Noon
            ]
            
            for dt, expected_time in test_times:
                mock_datetime.now.return_value = dt
                mock_datetime.strftime = datetime.strftime
                
                result = format_reflection(test_reflection)
                assert f"### {expected_time} — Reflection" in result
    
    def test_format_reflection_content_preservation(self):
        """Test that reflection content is preserved exactly."""
        test_reflection = "This is a multi-line\nreflection with\nspecial characters: @#$%"
        
        result = format_reflection(test_reflection)
        
        # Original content should be preserved
        assert test_reflection in result
        
        # Should have proper structure: header + content (no separator)
        assert "### " in result
        assert " — Reflection\n\n" in result
    
    def test_format_reflection_complete_structure(self):
        """Test the complete structure of formatted reflection."""
        test_reflection = "Complete structure test"
        
        with patch('mcp_commit_story.reflection_core.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 7, 9, 15, 45, 0)
            mock_datetime.strftime = datetime.strftime
            
            result = format_reflection(test_reflection)
            
            # Should have the complete expected structure (no separator)
            expected_structure = "\n\n### 3:45 PM — Reflection\n\n" + test_reflection
            assert result == expected_structure 