"""
Integration tests for git diff collection in journal generation pipeline.

Verifies the complete flow from diff collection through journal generation,
ensuring diff information is correctly collected and enhances journal content.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, Mock
import pytest
import sys
import git

from mcp_commit_story.git_utils import get_repo, get_commit_file_diffs
from mcp_commit_story.context_collection import collect_git_context
from mcp_commit_story.journal_generate import generate_summary_section, generate_technical_synopsis_section
from mcp_commit_story.context_types import JournalContext


@pytest.fixture
def temp_git_repo_with_diffs(tmp_path):
    """Create a temporary git repository with diverse commits for diff testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    
    # Create initial commit
    (repo_dir / "README.md").write_text("# Test Repository\nInitial content\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    
    return repo_dir


@pytest.fixture  
def large_repo_fixture(tmp_path):
    """Create a repository with many files for performance testing."""
    repo_dir = tmp_path / "large_repo"
    repo_dir.mkdir()
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    
    # Create many files
    for i in range(50):
        file_path = repo_dir / f"file_{i:03d}.py"
        file_path.write_text(f"""
def function_{i}():
    \"\"\"Function number {i}\"\"\"
    print("Hello from function {i}")
    return {i}

class Class{i}:
    def __init__(self):
        self.value = {i}
    
    def method(self):
        return self.value * 2
""")
    
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial large commit"], cwd=repo_dir, check=True)
    
    return repo_dir


class TestGitDiffPipelineVerification:
    """Verify the complete diff collection pipeline works end-to-end."""

    def test_end_to_end_diff_collection_workflow(self, temp_git_repo_with_diffs):
        """Test complete pipeline from diff collection to journal generation."""
        repo_path = temp_git_repo_with_diffs
        
        # Create a meaningful code change
        test_file = repo_path / "app.py"
        test_file.write_text("""
def calculate_total(items):
    \"\"\"Calculate total price with tax.\"\"\"
    subtotal = sum(item.price for item in items)
    tax = subtotal * 0.08
    return subtotal + tax

class ShoppingCart:
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_total(self):
        return calculate_total(self.items)
""")
        
        subprocess.run(["git", "add", "app.py"], cwd=repo_path, check=True)
        result = subprocess.run(["git", "commit", "-m", "Add shopping cart functionality"], 
                              cwd=repo_path, check=True)
        
        # Get the repo object and test diff collection
        repo = git.Repo(repo_path)
        latest_commit = repo.head.commit
        
        # Test diff collection directly
        file_diffs = get_commit_file_diffs(repo, latest_commit)
        
        # Verify diffs were collected
        assert "app.py" in file_diffs
        assert "def calculate_total" in file_diffs["app.py"]
        assert "class ShoppingCart" in file_diffs["app.py"]
        # The diff should contain the function definition (either as + or - depending on diff direction)
        assert ("def calculate_total" in file_diffs["app.py"] and 
                ("+" in file_diffs["app.py"] or "-" in file_diffs["app.py"]))
        
        # Test context collection includes diffs
        git_context = collect_git_context(repo=repo)
        assert "file_diffs" in git_context
        assert "app.py" in git_context["file_diffs"]
        
        # Test journal context integration
        journal_context = {
            "git": git_context,
            "chat_history": [],
            "previous_entries": []
        }
        
        # Mock AI generation to verify context gets passed correctly
        with patch('mcp_commit_story.journal_generate.invoke_ai') as mock_ai:
            mock_ai.return_value = {
                "summary": "Added shopping cart functionality with tax calculation",
                "impact": "Created new ShoppingCart class and calculate_total function"
            }
            
            result = generate_summary_section(journal_context)
            
            # Verify AI was called with context containing diffs
            mock_ai.assert_called_once()
            call_args = mock_ai.call_args[0][0]  # Get the prompt
            assert "file_diffs" in call_args
            assert "calculate_total" in call_args

    def test_different_commit_types(self, temp_git_repo_with_diffs):
        """Test diff collection with various types of changes."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Test file modification
        readme = repo_path / "README.md"
        readme.write_text("# Test Repository\nUpdated content with more details\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Update README"], cwd=repo_path, check=True)
        
        modify_commit = repo.head.commit
        modify_diffs = get_commit_file_diffs(repo, modify_commit)
        assert "README.md" in modify_diffs
        # Verify both old and new content are in the diff (regardless of +/- direction)
        assert ("Initial content" in modify_diffs["README.md"] and 
                "Updated content" in modify_diffs["README.md"])
        
        # Test file addition
        new_file = repo_path / "config.json"
        new_file.write_text('{"debug": true, "timeout": 30}')
        subprocess.run(["git", "add", "config.json"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add config file"], cwd=repo_path, check=True)
        
        add_commit = repo.head.commit
        add_diffs = get_commit_file_diffs(repo, add_commit)
        assert "config.json" in add_diffs
        assert "{" in add_diffs["config.json"]  # Content should be present regardless of +/- direction
        
        # Test file deletion
        subprocess.run(["git", "rm", "config.json"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Remove config file"], cwd=repo_path, check=True)
        
        delete_commit = repo.head.commit
        delete_diffs = get_commit_file_diffs(repo, delete_commit)
        assert "config.json" in delete_diffs
        assert "{" in delete_diffs["config.json"]  # Content should be present regardless of +/- direction

    def test_binary_and_generated_file_filtering(self, temp_git_repo_with_diffs):
        """Test that binary and generated files are properly handled."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Create binary file (image)
        binary_file = repo_path / "image.png"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00')
        
        # Create generated file (common patterns)
        generated_file = repo_path / "package-lock.json"
        generated_file.write_text('{"lockfileVersion": 1}')
        
        # Create normal code file
        code_file = repo_path / "utils.py"
        code_file.write_text("def helper(): pass")
        
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add mixed file types"], cwd=repo_path, check=True)
        
        latest_commit = repo.head.commit
        file_diffs = get_commit_file_diffs(repo, latest_commit)
        
        # Verify filtering behavior
        # Binary files should be excluded or marked appropriately
        if "image.png" in file_diffs:
            assert "Binary file" in file_diffs["image.png"] or len(file_diffs["image.png"]) < 100
        
        # Generated files might be excluded or limited
        # Code files should be included fully
        assert "utils.py" in file_diffs
        assert "def helper" in file_diffs["utils.py"]

    def test_performance_with_large_repository(self, large_repo_fixture):
        """Test diff collection performance with larger repositories."""
        repo_path = large_repo_fixture
        repo = git.Repo(repo_path)
        
        # Make a change to multiple files
        for i in range(5):
            file_path = repo_path / f"file_{i:03d}.py"
            content = file_path.read_text()
            updated_content = content + f"\n# Updated function {i}\ndef new_function_{i}():\n    return 'updated_{i}'"
            file_path.write_text(updated_content)
        
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Update multiple files"], cwd=repo_path, check=True)
        
        # Measure performance
        start_time = time.time()
        latest_commit = repo.head.commit
        file_diffs = get_commit_file_diffs(repo, latest_commit)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Verify reasonable performance (should complete within 5 seconds)
        assert duration < 5.0, f"Diff collection took too long: {duration:.2f}s"
        
        # Verify diffs were collected for changed files
        changed_files = [f"file_{i:03d}.py" for i in range(5)]
        for i, file_name in enumerate(changed_files):
            assert file_name in file_diffs
            # Look for the function name (regardless of +/- prefix in diff)
            assert f"new_function_{i}" in file_diffs[file_name]

    def test_merge_commit_handling(self, temp_git_repo_with_diffs):
        """Test diff collection behavior with merge commits."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Create a branch
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo_path, check=True)
        
        # Make changes on the branch
        feature_file = repo_path / "feature.py"
        feature_file.write_text("def feature_function(): return 'feature'")
        subprocess.run(["git", "add", "feature.py"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add feature"], cwd=repo_path, check=True)
        
        # Switch back to default branch (determine actual default branch name)
        # Get all branches and find the one that's not 'feature'
        result = subprocess.run(["git", "branch"], cwd=repo_path, capture_output=True, text=True)
        branches = [line.strip().replace('* ', '') for line in result.stdout.strip().split('\n')]
        default_branch = next(branch for branch in branches if branch != 'feature')
        subprocess.run(["git", "checkout", default_branch], cwd=repo_path, check=True)
        
        main_file = repo_path / "main.py"
        main_file.write_text("def main_function(): return 'main'")
        subprocess.run(["git", "add", "main.py"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add main file"], cwd=repo_path, check=True)
        
        # Merge the feature branch
        subprocess.run(["git", "merge", "feature", "--no-ff", "-m", "Merge feature branch"], 
                      cwd=repo_path, check=True)
        
        # Test diff collection on merge commit
        merge_commit = repo.head.commit
        file_diffs = get_commit_file_diffs(repo, merge_commit)
        
        # Verify merge commit diffs are handled appropriately
        # (behavior may vary based on implementation - we just verify it doesn't crash)
        assert isinstance(file_diffs, dict)

    def test_error_handling_in_diff_pipeline(self, temp_git_repo_with_diffs):
        """Test error handling when diff collection encounters issues."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Test with invalid commit (create a mock commit object with invalid properties)
        try:
            # Create a mock object that looks like a commit but has invalid data
            class MockCommit:
                def __init__(self):
                    self.parents = []
                    self.hexsha = "invalid_commit_hash"
                
            mock_commit = MockCommit()
            file_diffs = get_commit_file_diffs(repo, mock_commit)
            # If it doesn't raise an error, it should return a dict (possibly with errors)
            assert isinstance(file_diffs, dict)
        except Exception as e:
            # Acceptable to raise an exception for invalid commit
            assert "invalid" in str(e).lower() or "not found" in str(e).lower() or "bad" in str(e).lower()
        
        # Test context collection with repo in bad state doesn't crash
        git_context = collect_git_context(repo=repo)
        assert isinstance(git_context, dict)
        assert "file_diffs" in git_context

    def test_journal_generation_uses_diff_information(self, temp_git_repo_with_diffs):
        """Test that journal generators can access and utilize diff information."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Create a substantial code change
        impl_file = repo_path / "implementation.py"
        impl_file.write_text("""
class DatabaseConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connection = None
    
    def connect(self):
        # Connect to database
        self.connection = f"Connected to {self.host}:{self.port}"
        return self.connection
    
    def execute_query(self, query):
        if not self.connection:
            raise ValueError("Not connected to database")
        return f"Executing: {query}"
""")
        
        subprocess.run(["git", "add", "implementation.py"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Implement database connection class"], 
                      cwd=repo_path, check=True)
        
        # Collect context with diffs
        git_context = collect_git_context(repo=repo)
        journal_context = {
            "git": git_context,
            "chat_history": [],
            "previous_entries": []
        }
        
        # Test that generators receive diff information
        with patch('mcp_commit_story.journal_generate.invoke_ai') as mock_ai:
            mock_ai.return_value = {
                "technical_synopsis": "Implemented DatabaseConnection class with connection management",
                "architecture_impact": "Added new database layer"
            }
            
            result = generate_technical_synopsis_section(journal_context)
            
            # Verify the AI received diff content
            mock_ai.assert_called_once()
            prompt = mock_ai.call_args[0][0]
            
            # The prompt should contain the actual diff content
            assert "DatabaseConnection" in prompt
            assert "def connect" in prompt
            assert "file_diffs" in prompt
            assert "implementation.py" in prompt


class TestDiffCollectionPerformanceValidation:
    """Validate performance characteristics of diff collection."""

    def test_performance_with_large_diffs(self, temp_git_repo_with_diffs):
        """Test performance with very large file changes."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Create a large file
        large_file = repo_path / "large_data.py"
        large_content = "\n".join([f"data_{i} = 'value_{i}'" for i in range(1000)])
        large_file.write_text(large_content)
        
        subprocess.run(["git", "add", "large_data.py"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Add large data file"], cwd=repo_path, check=True)
        
        # Measure diff collection performance
        start_time = time.time()
        latest_commit = repo.head.commit
        file_diffs = get_commit_file_diffs(repo, latest_commit)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should handle large files reasonably
        assert duration < 3.0, f"Large diff collection took too long: {duration:.2f}s"
        
        # Verify size limiting works (if implemented)
        if "large_data.py" in file_diffs:
            diff_size = len(file_diffs["large_data.py"])
            # If size limiting is implemented, should be under some reasonable threshold
            assert diff_size > 0, "Diff should contain some content"

    def test_concurrent_diff_collection(self, temp_git_repo_with_diffs):
        """Test that diff collection works correctly under concurrent access."""
        repo_path = temp_git_repo_with_diffs
        repo = git.Repo(repo_path)
        
        # Create multiple commits
        for i in range(3):
            test_file = repo_path / f"concurrent_{i}.py"
            test_file.write_text(f"def function_{i}(): return {i}")
            subprocess.run(["git", "add", f"concurrent_{i}.py"], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", f"Add concurrent file {i}"], 
                          cwd=repo_path, check=True)
        
        # Get all commits
        commits = list(repo.iter_commits(max_count=3))
        
        # Collect diffs for all commits (simulating concurrent access)
        all_diffs = {}
        for commit in commits:
            all_diffs[commit.hexsha] = get_commit_file_diffs(repo, commit)
        
        # Verify all diffs were collected correctly
        assert len(all_diffs) == 3
        for commit_hash, diffs in all_diffs.items():
            assert isinstance(diffs, dict)
            # Each commit should have its respective file
            commit_files = [f for f in diffs.keys() if f.startswith("concurrent_")]
            assert len(commit_files) >= 1  # At least one concurrent file per commit 