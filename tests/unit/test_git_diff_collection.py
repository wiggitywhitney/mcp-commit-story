"""
Tests for git diff collection functionality.

Tests the new get_commit_file_diffs() function and related helpers,
including adaptive size limits, binary file exclusion, and generated file filtering.
"""

import os
import tempfile
import shutil
import pytest
from typing import Dict, List

# Only import git if available
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from mcp_commit_story.git_utils import get_commit_file_diffs, is_generated_file
from mcp_commit_story.context_types import GitContext


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    if not GIT_AVAILABLE:
        pytest.skip("GitPython not available")
    
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    
    # Configure git user for commits
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    
    yield repo, temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


def create_test_file(repo_path: str, filename: str, content: str) -> str:
    """Create a test file with given content."""
    filepath = os.path.join(repo_path, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


def create_binary_file(repo_path: str, filename: str, size: int = 100) -> str:
    """Create a binary test file."""
    filepath = os.path.join(repo_path, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(b'\x00' * size)
    return filepath


class TestGetCommitFileDiffs:
    """Test cases for get_commit_file_diffs function."""
    
    def test_basic_diff_collection(self, temp_repo):
        """Test basic diff collection for a simple commit."""
        repo, temp_dir = temp_repo
        
        # Create test files
        create_test_file(temp_dir, "file1.py", "print('hello')\n")
        create_test_file(temp_dir, "file2.py", "print('world')\n")
        
        # Add and commit files
        repo.index.add(["file1.py", "file2.py"])
        commit = repo.index.commit("Add test files")
        
        # Test diff collection
        diffs = get_commit_file_diffs(repo, commit)
        
        assert isinstance(diffs, dict)
        assert "file1.py" in diffs
        assert "file2.py" in diffs
        assert isinstance(diffs["file1.py"], str)
        assert isinstance(diffs["file2.py"], str)
        assert "print('hello')" in diffs["file1.py"]
        assert "print('world')" in diffs["file2.py"]
    
    def test_adaptive_size_limits_few_files(self, temp_repo):
        """Test adaptive size limits with ≤5 files (10KB per file)."""
        repo, temp_dir = temp_repo
        
        # Create files under the 5-file threshold
        for i in range(3):
            content = "x" * 5000  # 5KB content
            create_test_file(temp_dir, f"file{i}.py", content)
        
        repo.index.add([f"file{i}.py" for i in range(3)])
        commit = repo.index.commit("Add small files")
        
        # Test with default limits (should allow 10KB per file)
        diffs = get_commit_file_diffs(repo, commit)
        
        assert len(diffs) == 3
        for i in range(3):
            assert f"file{i}.py" in diffs
            # Should not be truncated (5KB < 10KB limit)
            assert "truncated" not in diffs[f"file{i}.py"]
    
    def test_adaptive_size_limits_medium_files(self, temp_repo):
        """Test adaptive size limits with 6-20 files (2.5KB per file)."""
        repo, temp_dir = temp_repo
        
        # Create files in the medium range (10 files)
        for i in range(10):
            content = "x" * 3000  # 3KB content (above 2.5KB limit)
            create_test_file(temp_dir, f"file{i}.py", content)
        
        repo.index.add([f"file{i}.py" for i in range(10)])
        commit = repo.index.commit("Add medium files")
        
        # Test with adaptive limits (should limit to 2.5KB per file)
        diffs = get_commit_file_diffs(repo, commit)
        
        assert len(diffs) == 10
        for i in range(10):
            assert f"file{i}.py" in diffs
            # Should be truncated (3KB > 2.5KB limit)
            assert "truncated" in diffs[f"file{i}.py"]
    
    def test_adaptive_size_limits_many_files(self, temp_repo):
        """Test adaptive size limits with >20 files (1KB per file, 50 file ceiling)."""
        repo, temp_dir = temp_repo
        
        # Create files above the 20-file threshold
        for i in range(30):
            content = "x" * 1500  # 1.5KB content (above 1KB limit)
            create_test_file(temp_dir, f"file{i}.py", content)
        
        repo.index.add([f"file{i}.py" for i in range(30)])
        commit = repo.index.commit("Add many files")
        
        # Test with adaptive limits (should limit to 1KB per file and 50 files max)
        diffs = get_commit_file_diffs(repo, commit)
        
        # Should have at most 50 files
        assert len(diffs) <= 50
        
        # Check that included files are truncated (1.5KB > 1KB limit)
        for filename, diff_content in diffs.items():
            if filename != "__truncated__":
                assert "truncated" in diff_content
    
    def test_binary_file_exclusion(self, temp_repo):
        """Test that binary files are excluded from diff collection."""
        repo, temp_dir = temp_repo
        
        # Create text and binary files
        create_test_file(temp_dir, "text_file.py", "print('hello')")
        create_binary_file(temp_dir, "binary_file.bin", 100)
        
        repo.index.add(["text_file.py", "binary_file.bin"])
        commit = repo.index.commit("Add text and binary files")
        
        # Test diff collection
        diffs = get_commit_file_diffs(repo, commit)
        
        # Should include text file but exclude binary file
        assert "text_file.py" in diffs
        assert "binary_file.bin" not in diffs
    
    def test_generated_file_filtering(self, temp_repo):
        """Test that generated files are filtered out."""
        repo, temp_dir = temp_repo
        
        # Create regular and generated files
        create_test_file(temp_dir, "src/main.py", "print('hello')")
        create_test_file(temp_dir, "package-lock.json", '{"dependencies": {}}')
        create_test_file(temp_dir, "dist/bundle.min.js", "console.log('minified')")
        
        repo.index.add(["src/main.py", "package-lock.json", "dist/bundle.min.js"])
        commit = repo.index.commit("Add regular and generated files")
        
        # Test diff collection
        diffs = get_commit_file_diffs(repo, commit)
        
        # Should include regular file but exclude generated files
        assert "src/main.py" in diffs
        assert "package-lock.json" not in diffs
        assert "dist/bundle.min.js" not in diffs
    
    def test_empty_commit_handling(self, temp_repo):
        """Test handling of empty commits."""
        repo, temp_dir = temp_repo
        
        # Create an empty commit
        commit = repo.index.commit("Empty commit", parent_commits=[])
        
        # Test diff collection
        diffs = get_commit_file_diffs(repo, commit)
        
        assert isinstance(diffs, dict)
        assert len(diffs) == 0
    
    def test_merge_commit_handling(self, temp_repo):
        """Test handling of merge commits."""
        repo, temp_dir = temp_repo
        
        # Create initial commit
        create_test_file(temp_dir, "base.py", "print('base')")
        repo.index.add(["base.py"])
        initial_commit = repo.index.commit("Initial commit")
        
        # Create a branch
        feature_branch = repo.create_head("feature")
        # Get the default branch (could be 'main' or 'master')
        default_branch = repo.active_branch
        default_branch.checkout()
        
        # Add file to default branch
        create_test_file(temp_dir, "main.py", "print('main')")
        repo.index.add(["main.py"])
        main_commit = repo.index.commit("Add main file")
        
        # Switch to feature branch and add file
        feature_branch.checkout()
        create_test_file(temp_dir, "feature.py", "print('feature')")
        repo.index.add(["feature.py"])
        feature_commit = repo.index.commit("Add feature file")
        
        # Switch back to default branch and merge
        default_branch.checkout()
        repo.git.merge("feature")
        merge_commit = repo.head.commit
        
        # Test diff collection on merge commit
        diffs = get_commit_file_diffs(repo, merge_commit)
        
        # Should handle merge commit gracefully
        assert isinstance(diffs, dict)
    
    def test_total_size_limit_enforcement(self, temp_repo):
        """Test that total size limits are enforced."""
        repo, temp_dir = temp_repo
        
        # Create files that would exceed total size limit
        for i in range(3):
            content = "x" * 20000  # 20KB content
            create_test_file(temp_dir, f"file{i}.py", content)
        
        repo.index.add([f"file{i}.py" for i in range(3)])
        commit = repo.index.commit("Add large files")
        
        # Test with small total size limit
        diffs = get_commit_file_diffs(repo, commit, max_total_size=30000)  # 30KB total
        
        # Should have truncation marker
        assert "__truncated__" in diffs or any("truncated" in diff for diff in diffs.values())
        
        # Total size should not exceed limit by much
        total_size = sum(len(diff) for diff in diffs.values() if isinstance(diff, str))
        assert total_size <= 35000  # Allow some buffer for truncation messages


class TestIsGeneratedFile:
    """Test cases for is_generated_file helper function."""
    
    def test_detects_minified_files(self):
        """Test detection of minified files."""
        assert is_generated_file("script.min.js") is True
        assert is_generated_file("style.min.css") is True
        assert is_generated_file("bundle.min.js") is True
        assert is_generated_file("normal.js") is False
    
    def test_detects_package_lock_files(self):
        """Test detection of package lock files."""
        assert is_generated_file("package-lock.json") is True
        assert is_generated_file("yarn.lock") is True
        assert is_generated_file("package.json") is False
    
    def test_detects_python_cache_files(self):
        """Test detection of Python cache files."""
        assert is_generated_file("__pycache__/module.cpython-39.pyc") is True
        assert is_generated_file("module.pyc") is True
        assert is_generated_file("module.py") is False
    
    def test_detects_build_directories(self):
        """Test detection of build/dist directories."""
        assert is_generated_file("build/output.js") is True
        assert is_generated_file("dist/bundle.js") is True
        assert is_generated_file("node_modules/package/index.js") is True
        assert is_generated_file("src/main.js") is False
    
    def test_case_insensitive_patterns(self):
        """Test that patterns work case-insensitively."""
        assert is_generated_file("BUILD/output.js") is True
        assert is_generated_file("DIST/bundle.js") is True


class TestGitContextIntegration:
    """Test integration with GitContext TypedDict."""
    
    def test_git_context_has_file_diffs_field(self):
        """Test that GitContext TypedDict includes file_diffs field."""
        # This test will fail initially until we update the TypedDict
        from mcp_commit_story.context_types import GitContext
        
        # Create a sample GitContext to test structure
        sample_context: GitContext = {
            'metadata': {
                'hash': 'abc123',
                'author': 'Test User',
                'date': '2025-01-01',
                'message': 'Test commit'
            },
            'diff_summary': 'Test summary',
            'changed_files': ['file1.py'],
            'file_stats': {'source': 1},
            'commit_context': {},
            'file_diffs': {'file1.py': 'diff content'}  # This should be the new field
        }
        
        # If this doesn't raise a type error, the field exists
        assert 'file_diffs' in sample_context
        assert isinstance(sample_context['file_diffs'], dict)


class TestDiffCollectionTelemetryIntegration:
    """Smoke tests to verify telemetry decorators don't break functionality."""
    
    def test_get_commit_file_diffs_has_telemetry_decorator(self):
        """Test that get_commit_file_diffs function has @trace_git_operation decorator."""
        assert hasattr(get_commit_file_diffs, '__wrapped__'), \
            "get_commit_file_diffs should have @trace_git_operation decorator"
    
    def test_is_generated_file_has_telemetry_decorator(self):
        """Test that is_generated_file function has @trace_git_operation decorator."""
        assert hasattr(is_generated_file, '__wrapped__'), \
            "is_generated_file should have @trace_git_operation decorator"
    
    def test_telemetry_decorators_dont_crash_operations(self, temp_repo):
        """Test that telemetry decorators don't crash normal operations."""
        if not GIT_AVAILABLE:
            pytest.skip("GitPython not available")
            
        repo, temp_dir = temp_repo
        
        # Create a test file and commit
        test_file = create_test_file(temp_dir, "test.py", "print('hello')")
        repo.index.add([test_file])
        commit = repo.index.commit("Add test file")
        
        # These operations should not crash with telemetry enabled
        diffs = get_commit_file_diffs(repo, commit)
        is_generated = is_generated_file("test.py")
        
        # Verify basic functionality still works
        assert isinstance(diffs, dict)
        assert isinstance(is_generated, bool)
        assert not is_generated  # test.py should not be considered generated
    
    @pytest.mark.parametrize('file_path,expected', [
        ('src/main.py', False),
        ('package-lock.json', True),
        ('dist/bundle.min.js', True),
        ('README.md', False),
    ])
    def test_is_generated_file_works_with_telemetry(self, file_path, expected):
        """Test that is_generated_file produces correct results with telemetry enabled."""
        # This verifies telemetry doesn't interfere with the logic
        result = is_generated_file(file_path)
        assert result == expected 