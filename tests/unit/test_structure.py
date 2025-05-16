import os
import pytest

REQUIRED_DIRS = [
    'src/mcp_journal',
    'tests/unit',
    'tests/integration',
    'tests/fixtures',
]

REQUIRED_FILES = [
    'src/mcp_journal/__init__.py',
    'src/mcp_journal/cli.py',
    'src/mcp_journal/server.py',
    'src/mcp_journal/journal.py',
    'src/mcp_journal/git_utils.py',
    'src/mcp_journal/config.py',
    'README.md',
    '.mcp-journalrc.yaml',
]

def test_required_directories_exist():
    for d in REQUIRED_DIRS:
        assert os.path.isdir(d), f"Missing directory: {d}"

def test_required_files_exist():
    for f in REQUIRED_FILES:
        assert os.path.isfile(f), f"Missing file: {f}"
