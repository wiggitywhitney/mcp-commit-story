"""
Tests for journal entry generation workflow functionality.

This module tests the core generate_journal_entry() function that orchestrates
all context collection and section generation functions to build complete
journal entries from commit data.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

# Import the function we'll be testing (this will fail initially - that's expected in TDD)
from src.mcp_commit_story.journal_workflow import generate_journal_entry, is_journal_only_commit
from src.mcp_commit_story.journal_generate import JournalEntry

# Import related classes and types
from src.mcp_commit_story.context_types import JournalContext


class TestGenerateJournalEntry:
    """Test the generate_journal_entry workflow function."""
    
    @patch('src.mcp_commit_story.context_collection.collect_git_context')
    @patch('src.mcp_commit_story.context_collection.collect_chat_history')
    @patch('src.mcp_commit_story.journal_generate.generate_summary_section')
    @patch('src.mcp_commit_story.journal_generate.generate_technical_synopsis_section')
    @patch('src.mcp_commit_story.journal_generate.generate_accomplishments_section')
    @patch('src.mcp_commit_story.journal_generate.generate_frustrations_section')
    @patch('src.mcp_commit_story.journal_generate.generate_tone_mood_section')
    @patch('src.mcp_commit_story.journal_generate.generate_discussion_notes_section')
    @patch('src.mcp_commit_story.journal_generate.generate_commit_metadata_section')
    @patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit')
    def test_successful_complete_journal_entry(
        self,
        mock_is_journal_only_commit,
        mock_commit_metadata,
        mock_discussion_notes,
        mock_tone_mood,
        mock_frustrations,
        mock_accomplishments,
        mock_technical_synopsis,
        mock_summary,
        mock_collect_chat_history,
        mock_collect_git_context
    ):
        """Test successful journal entry generation with all sections."""
        # Create mock GitPython commit object
        mock_commit = MagicMock()
        mock_commit.hexsha = 'abc123def456'
        mock_commit.message = 'Test commit message'
        mock_commit.author = MagicMock()
        mock_commit.author.__str__ = lambda x: 'Test Author'
        mock_commit.committed_datetime = datetime(2025, 6, 3, 14, 30)
        
        # Create mock config
        mock_config = {
            'journal': {
                'path': 'test-journal'
            }
        }
        
        # Configure mocks to return expected data types
        mock_is_journal_only_commit.return_value = False
        
        # Context collection mocks - return correct TypedDict structures
        mock_collect_chat_history.return_value = {'messages': [{'speaker': 'Human', 'text': 'test message'}]}
        mock_collect_git_context.return_value = {
            'metadata': {'hash': 'abc123', 'author': 'Test Author', 'date': '2025-06-03', 'message': 'Test commit'},
            'diff_summary': 'Test diff summary',
            'changed_files': ['test.py'],
            'file_stats': {'source': 1},
            'commit_context': {}
        }
        
        # Section generator mocks - return correct TypedDict structures with proper field names
        mock_summary.return_value = {'summary': 'Test summary content'}
        mock_technical_synopsis.return_value = {'technical_synopsis': 'Test technical content'}
        mock_accomplishments.return_value = {'accomplishments': ['Completed feature X', 'Fixed bug Y']}
        mock_frustrations.return_value = {'frustrations': ['Struggled with Z']}
        mock_tone_mood.return_value = {'mood': 'focused', 'indicators': 'efficient problem solving'}
        mock_discussion_notes.return_value = {'discussion_notes': ['Had productive chat about X']}
        mock_commit_metadata.return_value = {'commit_metadata': {'files_changed': '1', 'insertions': '10'}}
        
        result = generate_journal_entry(mock_commit, mock_config, debug=False)
        
        # Verify result is a JournalEntry
        assert isinstance(result, JournalEntry)
        assert result.commit_hash == 'abc123def456'
        assert result.summary == 'Test summary content'
        assert result.technical_synopsis == 'Test technical content'
        assert result.accomplishments == ['Completed feature X', 'Fixed bug Y']
        assert result.frustrations == ['Struggled with Z']
        assert result.tone_mood == {'mood': 'focused', 'indicators': 'efficient problem solving'}
        assert result.discussion_notes == ['Had productive chat about X']
        assert result.commit_metadata == {'files_changed': '1', 'insertions': '10'}
        
        # Verify context collection was called with correct GitPython commit parameters
        mock_collect_chat_history.assert_called_once_with(since_commit='abc123def456', max_messages_back=150)
        mock_collect_git_context.assert_called_once_with(commit_hash='abc123def456', repo='.', journal_path='test-journal')
        
        # Verify all section generators were called (7 AI functions total, down from 8 after removing terminal)
        for mock_generator in [mock_summary, mock_technical_synopsis, mock_accomplishments,
                              mock_frustrations, mock_tone_mood, mock_discussion_notes,
                              mock_commit_metadata]:
            mock_generator.assert_called_once()

    def test_journal_only_commit_skipped(self):
        """Test that journal-only commits are skipped to prevent infinite loops."""
        # Create mock GitPython commit object
        mock_commit = MagicMock()
        mock_commit.hexsha = 'abc123def456'
        
        mock_config = {
            'journal': {
                'path': 'test-journal'
            }
        }
        
        with patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit', return_value=True):
            result = generate_journal_entry(mock_commit, mock_config, debug=False)
        
        assert result is None

    def test_generate_journal_entry_graceful_degradation_context_failure(self):
        """Test graceful degradation when context collection functions fail."""
        # Create mock GitPython commit object
        mock_commit = MagicMock()
        mock_commit.hexsha = 'abc123def456'
        mock_commit.message = 'Test commit message'
        mock_commit.author = MagicMock()
        mock_commit.author.__str__ = lambda x: 'Test Author'
        mock_commit.committed_datetime = datetime(2025, 6, 3, 14, 30)
        
        mock_config = {
            'journal': {
                'path': 'test-journal'
            }
        }
        
        with patch('src.mcp_commit_story.context_collection.collect_chat_history', side_effect=Exception("Chat collection failed")), \
             patch('src.mcp_commit_story.context_collection.collect_git_context', side_effect=Exception("Git collection failed")), \
             patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit', return_value=False), \
             patch('src.mcp_commit_story.journal_generate.generate_summary_section', return_value={'summary': 'Test summary'}):
            
            result = generate_journal_entry(mock_commit, mock_config, debug=False)
        
        # Should still return a valid journal entry despite context failure
        assert isinstance(result, JournalEntry)
        assert result.commit_hash == 'abc123def456'
        assert result.summary == 'Test summary'

    def test_generate_journal_entry_graceful_degradation_section_failure(self):
        """Test graceful degradation when section generation functions fail."""
        # Create mock GitPython commit object
        mock_commit = MagicMock()
        mock_commit.hexsha = 'abc123def456'
        mock_commit.message = 'Test commit message'
        mock_commit.author = MagicMock()
        mock_commit.author.__str__ = lambda x: 'Test Author'
        mock_commit.committed_datetime = datetime(2025, 6, 3, 14, 30)
        
        mock_config = {
            'journal': {
                'path': 'test-journal'
            }
        }
        
        with patch('src.mcp_commit_story.context_collection.collect_chat_history', return_value={'messages': []}), \
             patch('src.mcp_commit_story.context_collection.collect_git_context', return_value={
                 'metadata': {'hash': 'abc123', 'author': 'Test', 'date': '2025-06-03', 'message': 'Test'},
                 'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
             }), \
             patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit', return_value=False), \
             patch('src.mcp_commit_story.journal_generate.generate_summary_section', return_value={'summary': 'Working summary'}), \
             patch('src.mcp_commit_story.journal_generate.generate_technical_synopsis_section', side_effect=Exception("Synopsis failed")), \
             patch('src.mcp_commit_story.journal_generate.generate_accomplishments_section', side_effect=Exception("Accomplishments failed")):
            
            result = generate_journal_entry(mock_commit, mock_config, debug=False)
        
        # Should still return entry with working sections, failed sections use default values
        assert isinstance(result, JournalEntry)
        assert result.summary == 'Working summary'
        # Failed sections get default values from JournalEntry constructor (None for strings, [] for lists)
        assert result.technical_synopsis is None
        assert result.accomplishments == []  # JournalEntry constructor uses [] as default for list fields

    def test_generate_journal_entry_configuration_driven_sections(self):
        """Test that journal generation includes all supported sections regardless of config."""
        # Create mock GitPython commit object
        mock_commit = MagicMock()
        mock_commit.hexsha = 'configtest123'
        mock_commit.message = 'Configuration test commit'
        mock_commit.author = MagicMock()
        mock_commit.author.__str__ = lambda x: 'Config Author'
        mock_commit.committed_datetime = datetime(2025, 6, 3, 16, 45)
        
        mock_config = {
            'journal': {
                'path': 'config-test-journal'
            }
        }
        
        # Patch all context collection and section generation functions
        with patch('src.mcp_commit_story.context_collection.collect_chat_history', return_value={'messages': []}), \
             patch('src.mcp_commit_story.context_collection.collect_git_context', return_value={
                 'metadata': {'hash': 'configtest123', 'author': 'Config Author', 'date': '2025-06-03', 'message': 'Configuration test'},
                 'diff_summary': 'Config-driven changes', 'changed_files': ['config.py'], 'file_stats': {}, 'commit_context': {}
             }), \
             patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit', return_value=False), \
             patch('src.mcp_commit_story.journal_generate.generate_summary_section', return_value={'summary': 'Configuration summary'}), \
             patch('src.mcp_commit_story.journal_generate.generate_technical_synopsis_section', return_value={'technical_synopsis': 'Config technical details'}), \
             patch('src.mcp_commit_story.journal_generate.generate_accomplishments_section', return_value={'accomplishments': ['Config updated']}), \
             patch('src.mcp_commit_story.journal_generate.generate_frustrations_section', return_value={'frustrations': []}), \
             patch('src.mcp_commit_story.journal_generate.generate_tone_mood_section', return_value={'mood': 'systematic', 'indicators': 'organized approach'}), \
             patch('src.mcp_commit_story.journal_generate.generate_discussion_notes_section', return_value={'discussion_notes': []}), \
             patch('src.mcp_commit_story.journal_generate.generate_commit_metadata_section', return_value={'commit_metadata': {'type': 'config'}}):
            
            result = generate_journal_entry(mock_commit, mock_config, debug=False)
        
        # Verify all sections are generated regardless of configuration
        assert isinstance(result, JournalEntry)
        assert result.summary == 'Configuration summary'
        assert result.technical_synopsis == 'Config technical details'
        assert result.accomplishments == ['Config updated']
        assert result.frustrations == []
        assert result.tone_mood == {'mood': 'systematic', 'indicators': 'organized approach'}
        assert result.discussion_notes == []
        assert result.commit_metadata == {'type': 'config'}

    def test_generate_journal_entry_debug_mode(self):
        """Test that debug mode doesn't break journal generation."""
        # Create mock GitPython commit object
        mock_commit = MagicMock()
        mock_commit.hexsha = 'debug123'
        mock_commit.message = 'Debug test commit'
        mock_commit.author = MagicMock()
        mock_commit.author.__str__ = lambda x: 'Debug Author'
        mock_commit.committed_datetime = datetime(2025, 6, 3, 18, 0)
        
        mock_config = {
            'journal': {
                'path': 'debug-journal'
            }
        }
        
        with patch('src.mcp_commit_story.context_collection.collect_chat_history', return_value={'messages': []}), \
             patch('src.mcp_commit_story.context_collection.collect_git_context', return_value={
                 'metadata': {'hash': 'debug123', 'author': 'Debug Author', 'date': '2025-06-03', 'message': 'Debug test'},
                 'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
             }), \
             patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit', return_value=False), \
             patch('src.mcp_commit_story.journal_generate.generate_summary_section', return_value={'summary': 'Debug summary'}), \
             patch('src.mcp_commit_story.journal_generate.generate_technical_synopsis_section', return_value={'technical_synopsis': 'Debug technical'}), \
             patch('src.mcp_commit_story.journal_generate.generate_accomplishments_section', return_value={'accomplishments': ['Debug feature']}), \
             patch('src.mcp_commit_story.journal_generate.generate_frustrations_section', return_value={'frustrations': []}), \
             patch('src.mcp_commit_story.journal_generate.generate_tone_mood_section', return_value={'mood': 'investigative', 'indicators': 'thorough testing'}), \
             patch('src.mcp_commit_story.journal_generate.generate_discussion_notes_section', return_value={'discussion_notes': []}), \
             patch('src.mcp_commit_story.journal_generate.generate_commit_metadata_section', return_value={'commit_metadata': {'debug': 'true'}}):
            
            # Test with debug=True - should work exactly the same
            result = generate_journal_entry(mock_commit, mock_config, debug=True)
        
        # Verify debug mode produces same result structure
        assert isinstance(result, JournalEntry)
        assert result.commit_hash == 'debug123'
        assert result.summary == 'Debug summary'

    def test_cross_platform_timestamp_format(self):
        """Test that timestamp formatting is consistent across platforms."""
        # Create mock GitPython commit object with specific datetime
        mock_commit = MagicMock()
        mock_commit.hexsha = 'timestamp123'
        mock_commit.message = 'Timestamp test'
        mock_commit.author = MagicMock()
        mock_commit.author.__str__ = lambda x: 'Timestamp Author'
        # Use a specific datetime that should format consistently
        mock_commit.committed_datetime = datetime(2025, 6, 3, 20, 30, 45)
        
        mock_config = {
            'journal': {
                'path': 'timestamp-journal'
            }
        }
        
        with patch('src.mcp_commit_story.context_collection.collect_chat_history', return_value={'messages': []}), \
             patch('src.mcp_commit_story.context_collection.collect_git_context', return_value={
                 'metadata': {'hash': 'timestamp123', 'author': 'Timestamp Author', 'date': '2025-06-03', 'message': 'Timestamp test'},
                 'diff_summary': '', 'changed_files': [], 'file_stats': {}, 'commit_context': {}
             }), \
             patch('src.mcp_commit_story.journal_workflow.is_journal_only_commit', return_value=False), \
             patch('src.mcp_commit_story.journal_generate.generate_summary_section', return_value={'summary': 'Timestamp summary'}):
            
            result = generate_journal_entry(mock_commit, mock_config, debug=False)
        
        # Verify timestamp is properly formatted and present
        assert isinstance(result, JournalEntry)
        assert result.timestamp is not None
        assert isinstance(result.timestamp, str)
        # Should contain time components (timestamp is time-only, not date)
        assert '8:30' in result.timestamp  # 20:30 becomes 8:30 PM in 12-hour format
        assert 'PM' in result.timestamp   # Should be in PM format


class TestIsJournalOnlyCommit:
    """Test the is_journal_only_commit helper function."""
    
    def test_journal_only_commit_detection(self):
        """Test detection of commits that only modify journal files."""
        # Create mock GitPython commit object with journal-only changes
        mock_commit = MagicMock()
        mock_commit.parents = [MagicMock()]  # Has parent
        
        # Mock diff to return only journal files
        mock_diff_item = MagicMock()
        mock_diff_item.a_path = 'journal/daily/2025-06-03-journal.md'
        mock_diff_item.b_path = 'journal/daily/2025-06-03-journal.md'
        mock_commit.diff.return_value = [mock_diff_item]
        
        result = is_journal_only_commit(mock_commit, 'journal')
        
        assert result is True

    def test_mixed_commit_detection(self):
        """Test detection of commits with both journal and non-journal changes."""
        # Create mock GitPython commit object with mixed changes
        mock_commit = MagicMock()
        mock_commit.parents = [MagicMock()]  # Has parent
        
        # Mock diff to return mixed files
        mock_diff_item1 = MagicMock()
        mock_diff_item1.a_path = 'journal/daily/2025-06-03-journal.md'
        mock_diff_item1.b_path = 'journal/daily/2025-06-03-journal.md'
        
        mock_diff_item2 = MagicMock()
        mock_diff_item2.a_path = 'src/main.py'
        mock_diff_item2.b_path = 'src/main.py'
        
        mock_commit.diff.return_value = [mock_diff_item1, mock_diff_item2]
        
        result = is_journal_only_commit(mock_commit, 'journal')
        
        assert result is False

    def test_initial_commit_handling(self):
        """Test handling of initial commits or commits without file stats."""
        # Create mock GitPython commit object without parents (initial commit)
        mock_commit = MagicMock()
        mock_commit.parents = []  # No parents (initial commit)
        
        # Mock diff against NULL_TREE
        mock_diff_item = MagicMock()
        mock_diff_item.a_path = 'src/main.py'
        mock_diff_item.b_path = 'src/main.py'
        mock_commit.diff.return_value = [mock_diff_item]
        
        # Patch NULL_TREE
        with patch('src.mcp_commit_story.git_utils.NULL_TREE') as mock_null_tree:
            result = is_journal_only_commit(mock_commit, 'journal')
        
        # Initial commit with code files should be processed
        assert result is False

    def test_error_handling_in_commit_detection(self):
        """Test graceful error handling when commit stats are unavailable."""
        # Create mock GitPython commit object that raises exception on diff access
        mock_commit = MagicMock()
        mock_commit.parents = [MagicMock()]
        mock_commit.diff.side_effect = Exception("Git error")
        
        # Should handle the error gracefully and default to False
        result = is_journal_only_commit(mock_commit, 'journal')
        
        assert result is False


# Mock exception for testing error handling
class PropertyError(Exception):
    pass 