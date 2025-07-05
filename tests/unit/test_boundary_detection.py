import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
from mcp_commit_story.ai_context_filter import get_previous_journal_entry


class TestBoundaryDetection:
    """Tests for journal parsing and boundary detection utilities"""

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_with_single_entry(self, mock_load_config):
        """Test extracting the most recent journal entry from previous day"""
        journal_content = """# Daily Journal

## 14:30 - Commit abc123

Started working on the user authentication feature. Implemented basic login form with validation.

- Added login form component
- Added form validation
- Connected to API endpoint

The implementation is working well and tests are passing.

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure for previous day
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is not None
            assert "## 14:30 - Commit abc123" in result
            assert "Started working on the user authentication feature" in result

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_with_multiple_entries(self, mock_load_config):
        """Test extracting the last entry when multiple exist"""
        journal_content = """# Daily Journal

## 10:00 - Commit first123

First commit of the day. Added some basic setup.

---

## 14:30 - Commit second456

Second commit with more features.

- Added authentication
- Updated UI components

---

## 18:00 - Commit third789

Final commit of the day with bug fixes.

- Fixed authentication bug
- Updated documentation

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure for previous day
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is not None
            # Should get the last entry (third789)
            assert "## 18:00 - Commit third789" in result
            assert "Final commit of the day with bug fixes" in result

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_different_header_formats(self, mock_load_config):
        """Test parsing entries with different header formats"""
        journal_content = """# Daily Journal

### 2025-07-04 10:00 — Commit hash123

Entry with triple hash and em dash.

---

## 14:30 - Commit hash456

Entry with double hash and regular dash.

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure for previous day
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is not None
            # Should get the last entry (hash456)
            assert "## 14:30 - Commit hash456" in result
            assert "Entry with double hash and regular dash" in result

    def test_get_previous_journal_entry_nonexistent_file(self):
        """Test handling when no journal files exist"""
        mock_commit = Mock()
        mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
        
        result = get_previous_journal_entry(mock_commit)
        
        assert result is None

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_empty_file(self, mock_load_config):
        """Test handling of empty journal file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty journal file
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write("")
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is None

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_no_valid_entries(self, mock_load_config):
        """Test handling when file exists but has no valid entries"""
        journal_content = """# Daily Journal

Some random content without proper headers.

---

More content that doesn't match entry format.
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is None

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_header_only(self, mock_load_config):
        """Test handling entry with header but no content"""
        journal_content = """# Daily Journal

## 14:30 - Commit abc123

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            # Should still return the entry even if it has minimal content
            assert result is not None
            assert "## 14:30 - Commit abc123" in result

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_with_minimal_content(self, mock_load_config):
        """Test entry with just header and one line of content"""
        journal_content = """# Daily Journal

## 14:30 - Commit abc123

Added user authentication feature.

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is not None
            assert "## 14:30 - Commit abc123" in result
            assert "Added user authentication feature." in result

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_searches_multiple_days(self, mock_load_config):
        """Test that it searches back multiple days to find a journal"""
        journal_content = """# Daily Journal

## 14:30 - Commit old_work

Working on something from 3 days ago.

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure for 3 days ago
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2024-12-30-journal.md")  # 3 days before 2025-01-02
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is not None
            assert "## 14:30 - Commit old_work" in result
            assert "Working on something from 3 days ago" in result

    @patch('mcp_commit_story.ai_context_filter.load_config')
    def test_get_previous_journal_entry_flexible_commit_hash(self, mock_load_config):
        """Test parsing with different commit hash formats"""
        journal_content = """# Daily Journal

## 14:30 - Commit a1b2c3d4

Entry with standard hex commit hash.

---

## 15:00 - Commit feature-branch-123

Entry with branch-style commit identifier.

---
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create journal structure
            daily_dir = os.path.join(temp_dir, "daily")
            os.makedirs(daily_dir)
            journal_file = os.path.join(daily_dir, "2025-01-01-journal.md")
            
            with open(journal_file, 'w', encoding='utf-8') as f:
                f.write(journal_content)
            
            # Mock config
            mock_config = Mock()
            mock_config.journal_path = temp_dir
            mock_load_config.return_value = mock_config
            
            # Create mock commit for 2025-01-02 (day after journal)
            mock_commit = Mock()
            mock_commit.committed_date = 1735797600  # 2025-01-02 00:00:00
            
            result = get_previous_journal_entry(mock_commit)
            
            assert result is not None
            # Should get the last entry (feature-branch-123)
            assert "## 15:00 - Commit feature-branch-123" in result
            assert "Entry with branch-style commit identifier" in result 