import pytest
import anyio
from pathlib import Path
import subprocess
import sys
import os

@pytest.mark.anyio
def test_full_workflow_success(tmp_path):
    """
    End-to-end: init → install-hook → MCP operations (new-entry, add-reflection)
    Should succeed and produce expected journal files and hooks.
    """
    repo_path = tmp_path
    env = {**os.environ, "PYTHONPATH": "src"}
    # Ensure the temp directory is a git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, stdout=subprocess.PIPE)
    
    # Configure git for the test (required in CI environments)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    
    # 1. Init (CLI setup command)
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "journal-init", "--repo-path", str(repo_path)
    ], cwd=repo_path, capture_output=True, text=True, env=env)
    assert result.returncode == 0, f"Journal-init failed: {result.stderr}"
    
    # 2. Install hook (CLI setup command)
    result = subprocess.run([
        sys.executable, "-m", "mcp_commit_story.cli", "install-hook", "--repo-path", str(repo_path)
    ], cwd=repo_path, capture_output=True, text=True, env=env)
    assert result.returncode == 0, f"Install hook failed: {result.stderr}"
    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    assert hook_path.exists(), "Post-commit hook not created"
    
    # 3. Test MCP operations (operational functionality)
    # Note: In real usage, these would be called via MCP server
    # For integration testing, we test the handler functions directly
    from mcp_commit_story.server import handle_journal_add_reflection
    from mcp_commit_story.config import Config
    from unittest.mock import patch
    
    # Create a test commit for context
    test_file = repo_path / "test.py"
    test_file.write_text("print('hello world')")
    subprocess.run(["git", "add", "test.py"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add test file"], cwd=repo_path, check=True)
    
    # Setup config patching for MCP operations to use tmp_path
    test_config = Config({
        'journal': {'path': str(repo_path / "journal")},
        'git': {'exclude_patterns': []},
        'telemetry': {'enabled': False}
    })
    
    # Test preserved MCP operations (journal/add-reflection)
    import asyncio
    async def test_mcp_operations():
        # Patch config loading to use test directory
        with patch("mcp_commit_story.server.load_config", lambda: test_config), \
             patch("mcp_commit_story.reflection_core.load_config", lambda: test_config), \
             patch("mcp_commit_story.journal_handlers.load_config", lambda: test_config):
            
            # Test journal/add-reflection MCP operation
            reflection_request = {
                "text": "Integration test reflection",
                "date": "2025-01-01"
            }
            
            result = await handle_journal_add_reflection(reflection_request)
            assert result["status"] == "success", f"Add reflection failed: {result.get('error')}"
            
            return result["file_path"]
    
    # Run the async MCP operations
    file_path = asyncio.run(test_mcp_operations())
    
    # 5. Verify journal content
    assert Path(file_path).exists(), "Journal file not created"
    content = Path(file_path).read_text()
    assert "Integration test reflection" in content, "Reflection missing"

@pytest.mark.anyio
def test_partial_failure_and_recovery(tmp_path):
    """
    Simulate a failure in the middle (e.g., install-hook fails), then recover and complete workflow.
    """
    # TODO: Implement partial failure and recovery scenario
    pass

@pytest.mark.anyio
def test_error_handling(tmp_path):
    """
    Test error handling: invalid repo, permission errors, malformed requests.
    """
    # TODO: Implement error handling scenarios
    pass

@pytest.mark.anyio
def test_concurrent_operations(tmp_path):
    """
    Test concurrent MCP operations (e.g., two journal entries at once).
    """
    # TODO: Implement concurrency scenario
    pass

@pytest.mark.asyncio
async def test_journal_add_reflection_integration(tmp_path, monkeypatch):
    """Integration test for MCP journal/add-reflection operation."""
    # Mock the config to use tmp_path instead of real journal directory
    from mcp_commit_story.config import Config
    test_config = Config({
        'journal': {'path': str(tmp_path / "journal")},
        'git': {'exclude_patterns': []},
        'telemetry': {'enabled': False}
    })
    # Patch all places that might call load_config during reflection handling
    monkeypatch.setattr("mcp_commit_story.server.load_config", lambda: test_config)
    monkeypatch.setattr("mcp_commit_story.reflection_core.load_config", lambda: test_config)
    monkeypatch.setattr("mcp_commit_story.journal_handlers.load_config", lambda: test_config)
    
    from mcp_commit_story.server import handle_journal_add_reflection
    request = {"text": "Integration reflection", "date": "2025-05-28"}
    result = await handle_journal_add_reflection(request)
    assert result["status"] == "success"
    assert "file_path" in result
    # Check that the file exists and contains the reflection
    file_path = result["file_path"]
    with open(file_path) as f:
        content = f.read()
        assert "Integration reflection" in content 