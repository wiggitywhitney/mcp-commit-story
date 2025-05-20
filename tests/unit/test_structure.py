import os
import pytest

REQUIRED_DIRS = [
    'src/mcp_commit_story',
    'tests/unit',
    'tests/integration',
    'tests/fixtures',
]

REQUIRED_FILES = [
    'src/mcp_commit_story/__init__.py',
    'src/mcp_commit_story/cli.py',
    'src/mcp_commit_story/server.py',
    'src/mcp_commit_story/journal.py',
    'src/mcp_commit_story/git_utils.py',
    'src/mcp_commit_story/config.py',
    'src/mcp_commit_story/telemetry.py',
    'README.md',
    '.mcp-commit-storyrc.yaml',
]

def test_required_directories_exist():
    for d in REQUIRED_DIRS:
        assert os.path.isdir(d), f"Missing directory: {d}"

def test_required_files_exist():
    for f in REQUIRED_FILES:
        assert os.path.isfile(f), f"Missing file: {f}"
